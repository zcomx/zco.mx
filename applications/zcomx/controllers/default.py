# -*- coding: utf-8 -*-
"""
Default controller.
"""
import logging
import os
from applications.zcomx.modules.books import \
    page_url, \
    url as book_url
from applications.zcomx.modules.creators import \
    add_creator, \
    for_path, \
    profile_onaccept, \
    url as creator_url
from applications.zcomx.modules.files import FileName
from applications.zcomx.modules.stickon.sqlhtml import \
    formstyle_bootstrap3_login
from applications.zcomx.modules.stickon.tools import ExposeImproved
from applications.zcomx.modules.stickon.validators import \
    IS_ALLOWED_CHARS, \
    IS_NOT_IN_DB_SCRUBBED
from applications.zcomx.modules.utils import \
    faq_tabs, \
    markmin_content

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

    hide_labels = True if request.args(0) not in ['register'] else False
    if request.extension == 'html' or hide_labels:
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
            row = db(query).select(db.creator.path_name).first()
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
    if form in ['ACCESS DENIED', 'Insufficient privileges']:
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
            if label.attributes['_id'] != 'auth_user_remember_me__label':
                label.add_class('labels_hidden')
        if form.custom.label[userfield]:
            form.custom.label[userfield] = 'Email Address'
        for f in form.custom.widget.keys():
            if hasattr(form.custom.widget[f], 'update'):
                if form.custom.widget[f].attributes['_type'] \
                        not in ['checkbox']:
                    form.custom.widget[f].update(
                        _placeholder=form.custom.label[f]
                    )
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
    # undefined-variable (E0602): *Undefined variable %%r* # crud
    # pylint: disable=E0602
    return dict(form=crud())


def about():
    """About page"""
    return dict(text=markmin_content('about.mkd'))


def contribute():
    """Contribute to zcomx admin controller"""
    session.paypal_in_progress = None
    redirect(URL(c='contributions', f='paypal', extension=False))


def expenses():
    """Expenses page"""
    return dict(text=markmin_content('expenses.mkd'))


def faq():
    """FAQ page"""
    # Set up for 'donations' contributions to paypal handling.
    layout = 'login/layout.html' if auth and auth.user_id \
        else 'layout_main.html'
    session.next_url = URL(
        c=request.controller,
        f=request.function,
        args=request.args,
        vars=request.vars
    )
    response.files.append(
        URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
    )
    return dict(
        tabs=faq_tabs(active='faq'),
        layout=layout,
        text=markmin_content('faq.mkd')
    )


def faqc():
    """Creator FAQ page"""
    if not auth or not auth.user_id:
        redirect(URL('faq'))

    return dict(
        tabs=faq_tabs(active='faqc'),
        text=markmin_content('faqc.mkd')
    )


def files():
    """Logos page"""
    base_path = os.path.join(request.folder, 'static', 'files')
    expose = ExposeImproved(base=base_path, display_breadcrumbs=False)
    return dict(expose=expose)


def goodwill():
    """Goodwill page"""
    session.next_url = URL(
        c=request.controller,
        f=request.function,
        args=request.args,
        vars=request.vars
    )
    response.files.append(
        URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
    )
    return dict(text=markmin_content('goodwill.mkd'))


def logos():
    """Logos page"""
    base_path = os.path.join(request.folder, 'static', 'images', 'logos')
    expose = ExposeImproved(base=base_path, display_breadcrumbs=False)
    return dict(expose=expose)


def overview():
    """Overview page"""
    return dict(text=markmin_content('overview.mkd'))


def todo():
    """Todo page"""
    return dict(text=markmin_content('todo.mkd'))


def top():
    """Controller for top header component

    request.args(0): name of page, optional. Set to None for home page.
    """
    left_links = []
    right_links = []
    delimiter_class = 'pipe_delimiter'

    home = A(
        'home',
        _href=URL(c='default', f='index', extension=False)
    )
    left_links.append(LI(home))

    def li_link(label, url, **kwargs):
        """Return a LI(A(...)) structure."""
        if url is not None:
            li_text = A(label, _href=url)
        else:
            li_text = label
        return LI(li_text, **kwargs)

    def book_link(book_id, text_only=False):
        """Return a book link."""
        label = 'book'
        url = book_url(book_id, extension=False) \
            if book_id and not text_only else None
        return li_link(label, url)

    def creator_link(creator_id, text_only=False):
        """Return a creator link."""
        label = 'cartoonist'
        url = creator_url(creator_id, extension=False) \
            if creator_id and not text_only else None
        return li_link(label, url)

    def login_link(label):
        """Return a link suitable for a login label"""
        return li_link(
            label,
            URL(c='login', f=label, extension=False),
            _class='active' if request.args(1) == label else '',
        )

    def page_link(page_id, text_only=False):
        """Return a read (book page) link."""
        label = 'read'
        url = page_url(page_id, extension=False) \
            if page_id and not text_only else None
        return li_link(label, url)

    def search_link(request):
        """Return a search results link."""
        label = 'search'
        url = URL(c='search', f='index', vars=request.vars)
        return li_link(label, url)

    if request.args(0):
        if request.args(0) == 'reader':
            delimiter_class = 'gt_delimiter'
            left_links.append(creator_link(request.vars.creator_id))
            left_links.append(book_link(request.vars.book_id))
            left_links.append(page_link(
                request.vars.book_page_id,
                text_only=True
            ))
        elif request.args(0) == 'book':
            delimiter_class = 'gt_delimiter'
            left_links.append(creator_link(request.vars.creator_id))
            left_links.append(book_link(
                request.vars.book_id,
                text_only=True
            ))
        elif request.args(0) == 'creator':
            delimiter_class = 'gt_delimiter'
            left_links.append(creator_link(
                request.vars.creator_id,
                text_only=True
            ))
        elif request.args(0) == 'login':
            delimiter_class = 'pipe_delimiter'
            left_links.append(login_link('books'))
            left_links.append(login_link('profile'))
            left_links.append(login_link('account'))
    else:
        if request.vars.o == 'search':
            delimiter_class = 'gt_delimiter'
            left_links.append(search_link(request))

    breadcrumbs = {}
    breadcrumbs['left'] = OL(
        left_links,
        _class='breadcrumb left {d}'.format(d=delimiter_class),
    )

    if right_links:
        breadcrumbs['right'] = OL(
            right_links,
            _class='breadcrumb right',
        )

    return dict(breadcrumbs=breadcrumbs)
