# -*- coding: utf-8 -*-
"""
Default controller.
"""
import logging
from applications.zcomx.modules.creators import \
    add_creator, \
    for_path, \
    profile_onaccept
from applications.zcomx.modules.files import FileName
from applications.zcomx.modules.stickon.sqlhtml import \
    formstyle_bootstrap3_login
from applications.zcomx.modules.stickon.validators import \
    IS_ALLOWED_CHARS, \
    IS_NOT_IN_DB_SCRUBBED

LOG = logging.getLogger('app')


def index():
    """Default controller.
    request.vars.o: string, orderby field.
    """
    redirect(URL(c='search', f='index'))


def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/manage_users (requires membership in
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    if request.args(0) == 'profile' and request.extension == 'html':
        redirect(URL(c='login', f='account', extension=False))
    if request.args(0) == 'change_password' and request.extension == 'html':
        redirect(URL(c='login', f='account', extension=False))

    auth.settings.formstyle = formstyle_bootstrap3_login

    if request.args(0) == 'profile':
        auth.settings.profile_next = URL(
            c='login', f='account', extension=False)
    if request.args(0) == 'change_password':
        auth.settings.change_password_next = URL(
            c='login', f='account', extension=False)

    auth.messages.logged_in = None      # Hide 'Logged in' flash
    # The next lines are from Auth._get_login_settings
    table_user = auth.table_user()
    userfield = auth.settings.login_userfield or 'username' \
        if 'username' in table_user.fields else 'email'
    passfield = auth.settings.password_field

    table_user.first_name.readable = False
    table_user.first_name.writable = False
    table_user.last_name.readable = False
    table_user.last_name.writable = False

    if request.args(0) == 'profile':
        auth.settings.profile_fields = ['name', userfield]
        auth.settings.profile_onaccept = [profile_onaccept]

    if request.args(0) == 'register':
        auth.settings.register_fields = ['name', userfield, passfield]
        auth.settings.register_onaccept = [add_creator]

    if request.args(0) in ['profile', 'register']:
        error_msg = XML(
            DIV(
                SPAN('An account already exists with this name.'),
                DIV(
                    'The name must be unique as it is used in archive file ',
                    'names and url paths. Consider using a variation of your ',
                    'name. For example:',
                    UL([
                        'Mike Smith',
                        'Michael A Smith',
                        'Michael Andrew Smith',
                    ]),
                    'Note: Punctuation and accents are ignored.',
                    _class="error_extra"
                )
            )
        )
        allowed_override = []
        if auth.user_id:
            query = (db.creator.auth_user_id == auth.user_id)
            row = db(query).select(db.creator.name_for_url).first()
            if row and 'name_for_url' in row and row['name_for_url']:
                allowed_override.append(row['name_for_url'])
        db.auth_user.name.requires = [
            IS_NOT_EMPTY(
                error_message='This is a required field.',
            ),
            IS_LENGTH(minsize=2),
            IS_ALLOWED_CHARS(not_allowed=FileName.invalid_chars),
            IS_NOT_IN_DB_SCRUBBED(
                db,
                db.creator.name_for_url,
                error_message=error_msg,
                allowed_override=allowed_override,
                scrub_callback=for_path,
            ),
        ]

    form = auth()
    if form in ['ACCESS DENIED', 'Insufficient privileges']:
        redirect(URL(c='default', f='index'))

    if request.args(0) != 'register':
        if form.custom.label[userfield]:
            form.custom.label[userfield] = 'Email Address'
        for f in form.custom.widget.keys():
            if hasattr(form.custom.widget[f], 'update'):
                if form.custom.widget[f].attributes['_type'] \
                        not in ['checkbox']:
                    form.custom.widget[f].update(
                        _placeholder=form.custom.label[f]
                    )

    return dict(form=form)


@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    # undefined-variable (E0602): *Undefined variable %%r* # crud
    # pylint: disable=E0602
    return dict(form=crud())


def about():
    """About page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def contribute():
    """Contribute to zcomx admin controller"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def copyright_claim():
    """Copyright claim page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def expenses():
    """Expenses page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def faq():
    """FAQ page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def faqc():
    """Creator FAQ page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


@auth.requires_login()
def files():
    """Logos page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def logos():
    """Logos page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def modal_error():
    """Controller for displaying error messages within modal. """
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def monies():
    """Controller for front page with contribute modal open."""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def overview():
    """Overview page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def terms():
    """Terms page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))


def todo():
    """Todo page"""
    redirect(
        URL(c='z', f=request.function, args=request.args, vars=request.vars))
