# -*- coding: utf-8 -*-
"""
Default controller.
"""
import os
from applications.zcomix.modules.creators import \
    add_creator, \
    for_path, \
    set_path_name
from applications.zcomix.modules.files import FileName
from applications.zcomix.modules.stickon.sqlhtml import \
    formstyle_bootstrap3_login
from applications.zcomix.modules.stickon.tools import ExposeImproved
from applications.zcomix.modules.stickon.validators import \
    IS_ALLOWED_CHARS, \
    IS_NOT_IN_DB_SCRUBBED
from applications.zcomix.modules.utils import markmin_content


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
    def set_creator_path_name(form):
        """Set the creator.path_name field associated with the user."""
        if not form.vars.id:
            return
        creator = db(db.creator.auth_user_id == form.vars.id).select(
            db.creator.ALL).first()
        if creator:
            set_path_name(creator)

    if request.args(0) == 'profile' and request.extension == 'html':
        redirect(URL(c='profile', f='account', extension=False))
    if request.args(0) == 'change_password' and request.extension == 'html':
        redirect(URL(c='profile', f='account', extension=False))

    hide_labels = True if request.args(0) not in ['register'] else False
    if request.extension == 'html' or hide_labels:
        auth.settings.formstyle = formstyle_bootstrap3_login

    if request.args(0) == 'profile':
        auth.settings.profile_next = URL(
            c='profile', f='account', extension=False)
    if request.args(0) == 'change_password':
        auth.settings.change_password_next = URL(
            c='profile', f='account', extension=False)

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
        auth.settings.profile_onaccept = [set_creator_path_name]

    if request.args(0) == 'register':
        auth.settings.register_fields = ['name', userfield, passfield]
        auth.settings.register_onaccept = [add_creator, set_creator_path_name]

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
            row = db(db.creator.auth_user_id == auth.user_id).select(db.creator.path_name).first()
            if row and 'path_name' in row and row['path_name']:
                allowed_override.append(row['path_name'])
        db.auth_user.name.requires = [
            IS_NOT_EMPTY(
                error_message='This is a required field.',
            ),
            IS_ALLOWED_CHARS(not_allowed=FileName.invalid_chars),
            IS_NOT_IN_DB_SCRUBBED(
                db,
                db.creator.path_name,
                error_message=error_msg,
                allowed_override=allowed_override,
                scrub_callback=for_path,
            ),
        ]

    form = auth()
    if form == 'ACCESS DENIED':
        redirect(URL(c='default', f='index'))

    for k in form.custom.widget.keys():
        if hasattr(form.custom.widget[k], 'add_class'):
            form.custom.widget[k].add_class('input-lg')
    if form.custom.widget.password_two:
        # Looks like a web2py bug, formstyle is not applied
        form.custom.widget.password_two.add_class('form-control')
    if form.custom.submit:
        form.custom.submit.add_class('btn-block')
        form.custom.submit.add_class('input-lg')

    if hide_labels:
        for label in form.elements('label'):
            label.add_class('labels_hidden')
        if form.custom.label[userfield]:
            form.custom.label[userfield] = 'Email Address'
        for f in form.custom.widget.keys():
            if hasattr(form.custom.widget[f], 'update'):
                form.custom.widget[f].update(_placeholder=form.custom.label[f])
        if request.args(0) == 'login':
            if form.custom.widget[userfield]:
                form.custom.widget[userfield].add_class('align_center')
            if form.custom.widget[passfield]:
                form.custom.widget[passfield].add_class('align_center')

    if request.extension == 'html' and not hide_labels:
        for label in form.elements('label'):
            label.add_class('align_left')

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
    return dict(form=crud())


def faq():
    """FAQ page"""
    return dict(text=markmin_content('faq.mkd'))


def faqc():
    """Creator FAQ page"""
    return dict(text=markmin_content('faqc.mkd'))


def goodwill():
    """Goodwill page"""
    return dict(text=markmin_content('goodwill.mkd'))


def logos():
    """Logos page"""
    base_path = os.path.join(request.folder, 'static', 'images', 'logos')
    expose = ExposeImproved(base=base_path, display_breadcrumbs=False)
    return dict(expose=expose)


def todo():
    """TODO page"""
    return dict(text=markmin_content('todo.mkd'))


def overview():
    """Overview page"""
    return dict(text=markmin_content('overview.mkd'))
