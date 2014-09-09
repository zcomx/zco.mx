# -*- coding: utf-8 -*-

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

# E0601: *Using variable %%r before assignment*
# pylint: disable=E0601

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL('sqlite://storage.sqlite',pool_size=1,check_reserved=['all'])
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'

import datetime
import os
import re
from gluon import *
from gluon.storage import Storage
from gluon.tools import PluginManager
from applications.zcomx.modules.books import publication_year_range
from applications.zcomx.modules.creators import add_creator
from applications.zcomx.modules.files import FileName
from applications.zcomx.modules.stickon.sqlhtml import formstyle_bootstrap3_custom
from applications.zcomx.modules.stickon.tools import ModelDb
from applications.zcomx.modules.stickon.validators import IS_ALLOWED_CHARS

model_db = ModelDb(globals())
db = model_db.db
auth = model_db.auth
crud = model_db.crud
service = model_db.service
mail = model_db.mail
local_settings = model_db.local_settings
plugins = PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables(username=False, signature=False)

## configure auth policy
auth.settings.mailer = mail                    # for user email verification
auth.settings.registration_requires_verification = True
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True
auth.settings.login_onaccept = lambda f: add_creator(f)
auth.settings.login_next = URL(c='profile', f='index')
auth.settings.logout_next = URL('index')

auth.settings.renew_session_onlogin = False
auth.settings.renew_session_onlogout = False
auth.settings.formstyle = formstyle_bootstrap3_custom
auth.default_messages['profile_save_button']='Submit'
auth.messages.verify_email = 'Click on the link http://' + request.env.http_host + URL('default', 'user', args=['verify_email']) + '/%(key)s to verify your email'
auth.messages.reset_password = 'Click on the link http://' + request.env.http_host + URL('default', 'user', args=['reset_password']) + '/%(key)s to reset your password'

current.app = Storage()
current.app.auth = auth
current.app.crud = crud
current.app.db = db
current.app.service = service
current.app.mail = mail
current.app.local_settings = local_settings

## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
#from gluon.contrib.login_methods.rpx_account import use_janrain
#use_janrain(auth, filename='private/janrain.key')

crud.settings.auth = None                      # =auth to enforce authorization on crud


auth.signature = db.Table(
    db,
    'auth_signature',
    Field(
        'created_on',
        'datetime',
        default=request.now,
        represent=lambda dt, row: str(dt),
        readable=False,
        writable=False,
    ),
    Field(
        'updated_on',
        'datetime',
        default=request.now,
        update=request.now,
        represent=lambda dt, row: str(dt),
        readable=False,
        writable=False,
    )
)

db._common_fields = [auth.signature]

db.define_table('book',
    Field(
        'name',
        requires=[
            IS_NOT_EMPTY(error_message='Enter a value'),
            IS_ALLOWED_CHARS(not_allowed=FileName.not_allowed_in_inputs),
        ],
    ),
    Field(
        'book_type_id',
        'integer',
        label='Book Type',
    ),
    Field(
        'number',
        'integer',
        default=1,
        requires = IS_INT_IN_RANGE(),
    ),
    Field(
        'of_number',
        'integer',
        default=1,
        requires = IS_INT_IN_RANGE(),
    ),
    Field(
        'creator_id',
        'integer',
        writable=False,
        readable=False,
    ),
    Field(
        'publication_year',
        'integer',
        default=datetime.date.today().year,
        label='Published',
        represent=lambda v, row: str(v) if v else 'N/A',
        requires = IS_INT_IN_RANGE(*publication_year_range(),
            error_message='Enter a valid year')
    ),
    Field(
        'description',
        'text',
        comment='A brief description of the book.',
    ),
    Field(
        'release_date',
        'date',
        default=None,
        represent=lambda v, row: str(v.year) if v else 'ongoing',
        label='Released',
        comment='Leave blank if not yet released (ongoing).',
    ),
    Field('contributions_month', 'double',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('contributions_year', 'double',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('views_month', 'integer',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('views_year', 'integer',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('rating_month', 'double',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('rating_year', 'double',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('downloads', 'integer',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('background_colour',
        default='white',
        label='Reader Background',
    ),
    Field('border_colour',
        default='white',
        label='Reader Border',
    ),
    Field('reader',
        default='slider',
        requires=IS_IN_SET(['scroller', 'slider']),
        comment='Default reader format.'
    ),
    Field(
        'status',
        'boolean',
        default=True,
        represent=lambda v, r=None: 'Active' if v == True else \
            'Deactive' if v == False else 'None',
    ),
    format='%(name)s',
    migrate=True,
)

db.define_table('book_page',
    Field(
        'book_id',
        'integer',
        writable=False,
        readable=False,
    ),
    Field('page_no', 'integer'),
    Field(
        'image',
        'upload',
        autodelete=True,
        requires = IS_IMAGE(),
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    Field(
        'thumb_w',
        'integer',
        default=0,
    ),
    Field(
        'thumb_h',
        'integer',
        default=0,
    ),
    format='%(page_no)s',
    migrate=True,
)

db.define_table('book_to_link',
    Field('book_id', 'integer'),
    Field('link_id', 'integer'),
    Field('order_no', 'integer'),
    migrate=True,
)

db.define_table('book_type',
    Field('name'),
    Field('description'),
    Field('sequence', 'integer'),
    migrate=True,
)

db.define_table('contribution',
    Field(
        'auth_user_id',
        'integer',
    ),
    Field(
        'book_id',
        'integer',
    ),
    Field('time_stamp', 'datetime'),
    Field('amount', 'double'),
    migrate=True,
)

db.define_table('creator',
    Field(
        'auth_user_id',
        'integer',
        readable=False,
        writable=False,
    ),
    Field('email',
        label='email address',
        comment='Leave blank if you do not wish your email published.',
        represent=lambda email, row: A(
            email,
            _href='mailto:{e}'.format(e=email),
            _target="_blank",
        ) if email else '',
        requires=IS_EMPTY_OR(
            IS_EMAIL(error_message='Enter a valid email address')
        ),
    ),
    Field('paypal_email',
        label='paypal address',
        comment='Required to received donations.',
        requires=IS_EMPTY_OR(
            IS_EMAIL(error_message='Enter a valid email address')
        ),
    ),
    Field('website',
        comment='Eg. http://myhomepage.com',
        label='website',
        represent=lambda url, row: A(
            re.sub(r'^http[s]*://', '', url),
            _href=url,
            _target="_blank",
            ) if url else '',
        requires=IS_EMPTY_OR(IS_URL(error_message='Enter a valid URL')),
    ),
    Field('twitter',
        comment='Eg. @username',
        label='twitter',
        represent=lambda twit, row: A(twit,
            _href='https://twitter.com/{t}'.format(t=twit),
            _target="_blank",
            ) if twit else '',
    ),
    Field('tumblr',
        comment='Eg. http://username.tumblr.com',
        label='tumblr',
        represent=lambda url, row: A(url,
            _href=url,
            _target="_blank",
            ) if url else '',
        requires=IS_EMPTY_OR(IS_URL(error_message='Enter a valid URL')),
    ),
    Field('wikipedia',
        comment='Eg. http://en.wikipedia.org/wiki/First_Surname',
        label='wikipedia',
        represent=lambda url, row: A(url,
            _href=url,
            _target="_blank",
            ) if url else '',
        requires=IS_EMPTY_OR(IS_URL(error_message='Enter a valid URL')),
    ),
    Field('bio', 'text',
        label='bio',
        comment='Provide a biography, for example, a few sentences similar to the first paragraph of a wikipedia article.'
    ),
    Field('image', 'upload',
        autodelete=True,
        label='photo',
        requires = IS_EMPTY_OR(IS_IMAGE()),
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    Field(
        'path_name',
    ),
    format='%(path_name)s',
    migrate=True,
)

db.define_table('creator_to_link',
    Field('creator_id', 'integer'),
    Field('link_id', 'integer'),
    Field('order_no', 'integer'),
    migrate=True,
)

db.define_table('link',
    Field('url',
        requires=IS_URL(error_message='Enter a valid URL'),
        widget=lambda field, value: SQLFORM.widgets.string.widget(field,
            value, _placeholder='http://www.example.com'),
    ),
    Field('name',
        label='Text',
        requires=IS_LENGTH(
            40,
            1,
            error_message='Enter %(min)g to %(max)g characters'
        ),
    ),
    Field('title'),
    format='%(name)s',
    migrate=True,
)

db.define_table('page_comment',
    Field(
        'book_page_id',
        'integer',
    ),
    Field('comment_text'),
    format='%(comment_text)s',
    migrate=True,
)

db.define_table('rating',
    Field(
        'auth_user_id',
        'integer',
    ),
    Field(
        'book_id',
        'integer',
    ),
    Field('time_stamp', 'datetime'),
    Field('amount', 'double'),
    migrate=True,
)

db.define_table('book_view',
    Field(
        'auth_user_id',
        'integer',
    ),
    Field(
        'book_id',
        'integer',
    ),
    Field('time_stamp', 'datetime'),
    migrate=True,
)

db.book.book_type_id.requires = IS_IN_DB(
    db,
    db.book_type.id,
    '%(name)s',
    zero=None
)

db.book.creator_id.requires = IS_IN_DB(
    db,
    db.creator.id,
    '%(name)s',
    zero=None
)

db.book_page.book_id.requires = IS_IN_DB(
    db,
    db.book.id,
    '%(name)s',
    zero=None
)

db.contribution.auth_user_id.requires = IS_IN_DB(
    db,
    db.auth_user.id,
    '%(last_name)s, %(first_name)s',
    zero=None
)

db.contribution.book_id.requires = IS_IN_DB(
    db,
    db.book.id,
    '%(name)s',
    zero=None
)

db.creator.auth_user_id.requires = IS_IN_DB(
    db,
    db.auth_user.id,
    '%(page_no)s',
    zero=None
)

db.page_comment.book_page_id.requires = IS_IN_DB(
    db,
    db.book_page.id,
    '%(last_name)s, %(first_name)s',
    zero=None
)
db.rating.auth_user_id.requires = IS_IN_DB(
    db,
    db.auth_user.id,
    '%(last_name)s, %(first_name)s',
    zero=None
)

db.rating.book_id.requires = IS_IN_DB(
    db,
    db.book.id,
    '%(name)s',
    zero=None
)

db.book_view.auth_user_id.requires = IS_IN_DB(
    db,
    db.auth_user.id,
    '%(last_name)s, %(first_name)s',
    zero=None
)

db.book_view.book_id.requires = IS_IN_DB(
    db,
    db.book.id,
    '%(name)s',
    zero=None
)
