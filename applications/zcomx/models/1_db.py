# -*- coding: utf-8 -*-

#########################################################################
# # This scaffolding model makes your app work on Google App Engine too
# # File is released under public domain and you can use without limitations
#########################################################################

# # if SSL/HTTPS is properly configured and you want all HTTP requests to
# # be redirected to HTTPS, uncomment the line below:
# request.requires_https()

# E0601: *Using variable %%r before assignment*
# pylint: disable=E0601

# # by default give a view/generic.extension to all actions from localhost
# # none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
# # (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
# # (optional) static assets folder versioning
# response.static_version = '0.0.0'

import datetime
import logging
import os
import re
from gluon import *
from gluon.storage import Storage
from gluon.tools import PluginManager
from applications.zcomx.modules.stickon.validators import \
    IS_ALLOWED_CHARS, \
    IS_TWITTER_HANDLE, \
    IS_URL_FOR_DOMAIN
from applications.zcomx.modules.zco import \
    BOOK_STATUS_DRAFT, \
    ZcoMigratedModelDb, \
    ZcoModelDb

try:
    # MIGRATE is optionally defined in models/0_migrate.py
    model_class = ZcoMigratedModelDb if MIGRATE else ZcoModelDb
except NameError:
    model_class = ZcoModelDb

model_db = model_class(globals())
model_db.load()

db = model_db.db
auth = model_db.auth
crud = model_db.crud
service = model_db.service
mail = model_db.mail
local_settings = model_db.local_settings
plugins = PluginManager()

current.app = Storage()
current.app.auth = auth
current.app.crud = crud
current.app.db = db
current.app.service = service
current.app.mail = mail
current.app.local_settings = local_settings
if request.is_shell:
    logger_name = request.env.cmd_options.run.replace('/', '.')
else:
    logger_name = 'applications.{a}.{c}.{f}'.format(
        a=request.application, f=request.function, c=request.controller)
LOG = logging.getLogger(logger_name)
current.app.logger = LOG

from applications.zcomx.modules.book_page.utils import \
    before_delete as book_page_before_delete
from applications.zcomx.modules.books import publication_year_range
from applications.zcomx.modules.creators import add_creator
from applications.zcomx.modules.files import FileName
from applications.zcomx.modules.stickon.sqlhtml import \
    formstyle_bootstrap3_custom

# configure auth policy
auth.settings.mailer = mail                    # for user email verification
auth.settings.registration_requires_verification = True
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True
auth.settings.login_onaccept = [add_creator]
auth.settings.login_next = URL(c='login', f='books')
auth.settings.logout_next = URL('index')

auth.settings.renew_session_onlogin = False
auth.settings.renew_session_onlogout = False
auth.settings.formstyle = formstyle_bootstrap3_custom
auth.default_messages['profile_save_button'] = 'Submit'
auth.messages.verify_email = 'Click on the link http://' + request.env.http_host + URL('default', 'user', args=['verify_email']) + '/%(key)s to verify your email'
auth.messages.reset_password = 'Click on the link http://' + request.env.http_host + URL('default', 'user', args=['reset_password']) + '?key=%(key)s to reset your password'
auth.messages.logged_out = ''               # Suppress flash message
auth.messages.profile_updated = ''          # Suppress flash message
auth.messages.password_changed = ''         # Suppress flash message


# # if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
# # register with janrain.com, write your domain:api_key in private/janrain.key
# from gluon.contrib.login_methods.rpx_account import use_janrain
# use_janrain(auth, filename='private/janrain.key')

crud.settings.auth = None                      # =auth to enforce authorization on crud

db._common_fields = [auth.signature]

db.define_table('activity_log',
    Field(
        'book_id',
        'integer',
    ),
    Field(
        'book_page_ids',
        'list:reference book_page',
        default=[],
    ),
    Field('action'),
    Field('time_stamp', 'datetime'),
    Field(
        'ongoing_post_id',
        'integer',
    ),
    Field(
        'deleted_book_page_ids',
        'list:integer',
        default=[],
    ),
)

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
        requires=IS_INT_IN_RANGE(),
    ),
    Field(
        'of_number',
        'integer',
        default=1,
        requires=IS_INT_IN_RANGE(),
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
        requires=IS_INT_IN_RANGE(*publication_year_range(),
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
        label='Completed',
        comment='Leave blank if not yet completed (ongoing).',
    ),
    Field(
        'fileshare_date',
        'date',
        default=None,
        label='Released for filesharing',
        comment='Leave blank if not yet released for filesharing.',
    ),
    Field('contributions', 'double',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('contributions_remaining', 'double',
        default=0,
        represent=lambda v, r: '${v:0,.0f}'.format(v=v),
        writable=False,
        readable=False,
    ),
    Field('views', 'integer',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('rating', 'double',
        default=0,
        writable=False,
        readable=False,
    ),
    Field('downloads', 'integer',
        default=0,
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
        'name_for_search'
    ),
    Field(
        'name_for_url'
    ),
    Field(
        'cc_licence_id',
        'integer',
        default=0,
        label='Copyright Licence',
    ),
    Field(
        'cc_licence_place',
        label='Licence Territory',
        comment='Jurisdiction from which the work is being offered under CC0.'
    ),
    # page_added_on: Used to sort ongoing books and control necrobumping.
    Field(
        'page_added_on',
        'datetime',
    ),
    Field(
        'cbz'
    ),
    Field(
        'torrent'
    ),
    Field(
        'complete_in_progress',
        'boolean',
        default=False,
    ),
    Field(
        'fileshare_in_progress',
        'boolean',
        default=False,
    ),
    Field('facebook_post_id'),
    Field('tumblr_post_id'),
    Field('twitter_post_id'),
    Field(
        'status',
        'string',
        default=BOOK_STATUS_DRAFT,
    ),
    format='%(name)s',
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
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    format='%(page_no)s',
)

db.define_table('book_type',
    Field('name'),
    Field('description'),
    Field('sequence', 'integer'),
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
)

db.define_table('cc_licence',
    Field('number', 'integer'),
    Field('code'),
    Field('url'),
    Field('template_img'),
    Field('template_web'),
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
            _href='https://twitter.com/{t}'.format(t=twit.replace('@', '')),
            _target="_blank",
            ) if twit else '',
        requires=IS_EMPTY_OR(IS_TWITTER_HANDLE()),
    ),
    Field('shop',
        label='shop',
        represent=lambda url, row: A(url,
            _href=url,
            _target="_blank",
            ) if url else '',
        requires=IS_EMPTY_OR(IS_URL()),
    ),
    Field('tumblr',
        comment='Eg. http://username.tumblr.com',
        label='tumblr',
        represent=lambda url, row: A(url,
            _href=url,
            _target="_blank",
            ) if url else '',
        requires=IS_EMPTY_OR(
            IS_MATCH(
                r'^http://[A-Za-z0-9]+[A-Za-z0-9\-]*.tumblr.com$',
                error_message='Enter a valid tumblr url, eg.\nhttp://username.tumblr.com'
            )
        ),
    ),
    Field('facebook',
        comment='Eg. http://www.facebook.com/username',
        label='facebook',
        represent=lambda url, row: A(url,
            _href=url,
            _target="_blank",
        ) if url else '',
        requires=IS_EMPTY_OR(IS_URL_FOR_DOMAIN(
            'facebook.com',
            error_message='Enter a valid facebook url, eg.\nhttp://www.facebook.com/username'
        )
        ),
    ),
    Field('bio', 'text',
        label='bio',
        comment='Provide a biography, for example, a few sentences similar to the first paragraph of a wikipedia article.'
    ),
    Field('image', 'upload',
        autodelete=True,
        label='photo',
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    Field(
        'photo_credit',
        label='photo courtesy of',
    ),
    Field(
        'photo_credit_url',
        label="photographer's website",
        comment='Eg. http://photographerspage.com',
        represent=lambda url, row: A(
            re.sub(r'^http[s]*://', '', url),
            _href=url,
            _target="_blank",
        ) if url else '',
        requires=IS_EMPTY_OR(IS_URL(error_message='Enter a valid URL')),
    ),
    Field(
        'name_for_search'
    ),
    Field(
        'name_for_url'
    ),
    Field(
        'contributions_remaining',
        'double',
        default=0,
        represent=lambda v, r: '${v:0,.0f}'.format(v=v),
    ),
    Field('indicia_image', 'upload',
        autodelete=True,
        label='indicia image',
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    Field('indicia_portrait', 'upload',
        autodelete=True,
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    Field('indicia_landscape', 'upload',
        autodelete=True,
        uploadfolder=os.path.join(request.folder, 'uploads', 'original'),
        uploadseparate=True,
    ),
    Field(
        'torrent'
    ),
    Field(
        'rebuild_torrent',
        'boolean',
        default=False,
    ),
    Field(
        'agreed_to_terms',
        'boolean',
        default=None,
    ),
)

db.define_table('derivative',
    Field(
        'book_id',
        'integer',
    ),
    Field(
        'title',
        label='Derivative Title',
        requires=IS_NOT_EMPTY(),
    ),
    Field(
        'creator',
        label='Derivative Creator Name',
        requires=IS_NOT_EMPTY(),
    ),
    Field(
        'cc_licence_id',
        'integer',
        label='Derivative Licence',
        requires=IS_IN_DB(db, db.cc_licence.id, '%(code)s', zero=None),
    ),
    Field(
        'from_year',
        'integer',
        default=request.now.year,
        label='Derivative Pub Year',
    ),
    Field(
        'to_year',
        'integer',
        default=request.now.year,
        label='To',
    ),
)

db.define_table('download',
    Field(
        'download_click_id',
        'integer',
    ),
    Field(
        'auth_user_id',
        'integer',
    ),
    Field(
        'book_id',
        'integer',
    ),
    Field('time_stamp', 'datetime'),
)

db.define_table('download_click',
    Field('ip_address'),
    Field('time_stamp', 'datetime'),
    Field('auth_user_id', 'integer'),
    Field('record_table'),
    Field('record_id', 'integer'),
    Field(
        'is_bot',
        'boolean',
        default=False,
    ),
    Field(
        'loggable',
        'boolean',
        default=False,
    ),
    Field(
        'completed',
        'boolean',
        default=False,
    ),
)


"""
job_common_fields         # Jobs are added to a queue and processed in order.
# Note: this isn't a database table. If defines fields shared by the
# job and job_history tables.

job_queuer_id  integer    # References job_queuer.id
start          datetime   # Scheduled start time.
                          # Job will not be run prior to this time.
priority       integer    # Priority of job, higher value = higher priority
command        varchar    # Command to execute.
ignorable      char(1)    # Job can be ignored.
queued_time    datetime   # Time job was added to queue.
start_time     datetime   # Time job was started.
end_time       datetime   # Time job was completed.
wait_seconds   integer    # Seconds job had to wait in queue.
run_seconds    integer    # Seconds job took to complete.
ignored        char(1)    # Was job ignored.
status         char       # 'a' = active (queued),
                          # 'c' = complete
                          # 'd' = deactive (done)
                          # 'p' = running (in progress)
"""
job_common_fields = db.Table(db, 'job_common_fields',
    Field('job_queuer_id',
        'integer',
    ),
    Field('start',
        'datetime',
        requires=IS_DATETIME(),
    ),
    Field('priority',
        'integer',
    ),
    Field('command',
        'string',
        requires=IS_NOT_EMPTY(),
    ),
    Field('ignorable',
        'boolean',
        default=False,
        represent=lambda v, r=None: 'Yes' if v is True else 'No',
    ),
    Field('queued_time',
        'datetime',
        requires=IS_EMPTY_OR(IS_DATETIME()),
    ),
    Field('start_time',
        'datetime',
        requires=IS_EMPTY_OR(IS_DATETIME()),
    ),
    Field('end_time',
        'datetime',
        requires=IS_EMPTY_OR(IS_DATETIME()),
    ),
    Field('wait_seconds',
        'integer',
    ),
    Field('run_seconds',
        'integer',
    ),
    Field('ignored',
        'boolean',
        default=False,
        represent=lambda v, r=None: 'Yes' if v is True else 'No',
    ),
    Field('status',
        'string',
        default='a',
        requires=IS_IN_SET([
            ('a', 'Enabled'),
            ('c', 'Complete'),
            ('d', 'Disabled'),
            ('p', 'In Progress')
        ], zero=None),
    ),
)

db.define_table('job', job_common_fields)
db.define_table('job_history', job_common_fields)

db.define_table('job_queuer',
    Field('code', 'string', requires=IS_NOT_EMPTY()),
    Field('estimate_run_seconds', 'integer'),
)

db.define_table('link',
    Field('link_type_id', 'integer'),
    Field('record_table'),
    Field('record_id', 'integer'),
    Field('order_no', 'integer'),
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
    format='%(name)s',
)

db.define_table('link_type',
    Field('code'),
    Field('label'),
    Field('name_placeholder'),
    Field('url_placeholder'),
    format='%(code)s',
)

db.define_table('ongoing_post',
    Field(
        'post_date',
        'date',
        default=None,
    ),
    Field('facebook_post_id'),
    Field('tumblr_post_id'),
    Field('twitter_post_id'),
)

db.define_table('optimize_img_log',
    Field(
        'image',
    ),
    Field(
        'size',
    ),
)

db.define_table('page_comment',
    Field(
        'book_page_id',
        'integer',
    ),
    Field('comment_text'),
    format='%(comment_text)s',
)

db.define_table('paypal_log',
    Field('text'),
    Field('txn_id'),
    Field('ipn_track_id'),
    Field('txn_type'),
    Field('business'),
    Field('item_number'),
    Field('item_name'),
    Field('quantity'),
    Field('payer_id'),
    Field('payer_email'),
    Field('payer_status'),
    Field('first_name'),
    Field('last_name'),
    Field('address_name'),
    Field('address_street'),
    Field('address_city'),
    Field('address_state'),
    Field('address_country'),
    Field('address_country_code'),
    Field('address_zip'),
    Field('address_status'),
    Field('residence_country'),
    Field('receiver_id'),
    Field('receiver_email'),
    Field('payment_status'),
    Field('payment_type'),
    Field('payment_gross'),
    Field('payment_fee'),
    Field('tax'),
    Field('payment_date'),
    Field('mc_currency'),
    Field('mc_fee'),
    Field('mc_gross'),
    Field('notify_version'),
    Field('protection_eligibility'),
    Field('test_ipn'),
    Field('transaction_subject'),
    Field('charset'),
    Field('custom'),
    Field('verify_sign'),
    format='%(txn_id)s',
)

db.define_table('publication_metadata',
    Field(
        'book_id',
        'integer',
    ),
    Field(
        'republished',
        'boolean',
        label='Publication Type',
        requires=IS_IN_SET(
            [True, False],
            error_message='Please select an option',
        ),
    ),
    Field(
        'published_type',
        label='Republication Type',
    ),
    Field(
        'is_anthology',
        'boolean',
        default=False,
        label='Anthology',
        requires=IS_IN_SET(
            [True, False],
            error_message='Please select an option',
        ),
    ),
    Field(
        'published_name',
        label='Original Book Title',
        default='',
    ),
    Field(
        'published_format',
        label='Format',
        default='digital',
    ),
    Field(
        'publisher_type',
        label='Publisher',
        default='press',
    ),
    Field(
        'publisher',
        label='Publisher Name',
        default='',
    ),
    Field(
        'from_month',
        'integer',
        default=request.now.month,
        label='Start Month/Year',
    ),
    Field(
        'from_year',
        'integer',
        default=request.now.year,
    ),
    Field(
        'to_month',
        'integer',
        default=request.now.month,
        label='Finish Month/Year',
    ),
    Field(
        'to_year',
        'integer',
        default=request.now.year,
    ),
)

db.define_table('publication_serial',
    Field(
        'book_id',
        'integer',
    ),
    Field('sequence', 'integer'),
    Field(
        'published_name',
        label='Story Name',
        requires=IS_NOT_EMPTY(),
    ),
    Field(
        'published_format',
        label='Format',
        default='digital',
        requires=IS_IN_SET(['digital', 'paper']),
    ),
    Field(
        'publisher_type',
        default='press',
        requires=IS_IN_SET(['press', 'self']),
    ),
    Field(
        'publisher',
        requires=IS_NOT_EMPTY(),
    ),
    Field(
        'story_number',
        'integer',
        default=1,
    ),
    Field(
        'serial_title',
        requires=IS_NOT_EMPTY(),
    ),
    Field(
        'serial_number',
        'integer',
        label='Book/Anthology Number',
        default=1,
    ),
    Field(
        'from_month',
        'integer',
        default=request.now.month,
        label='Start Month/Year',
    ),
    Field(
        'from_year',
        'integer',
        default=request.now.year,
    ),
    Field(
        'to_month',
        'integer',
        default=request.now.month,
        label='Finish Month/Year',
    ),
    Field(
        'to_year',
        'integer',
        default=request.now.year,
    ),
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
)

db.define_table('tentative_activity_log',
    Field(
        'book_id',
        'integer',
    ),
    Field(
        'book_page_id',
        'integer',
    ),
    Field('action'),
    Field('time_stamp', 'datetime'),
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
db.book_page._before_delete.append(book_page_before_delete)

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

db.download.auth_user_id.requires = IS_IN_DB(
    db,
    db.auth_user.id,
    '%(last_name)s, %(first_name)s',
    zero=None
)

db.download.book_id.requires = IS_IN_DB(
    db,
    db.book.id,
    '%(name)s',
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
