# -*- coding: utf-8 -*-
"""
Default controller.
"""
from applications.zcomix.modules.stickon.sqlhtml import formstyle_bootstrap3_login


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
        redirect(URL(c='profile', f='index', extension=False))
    if request.args(0) == 'change_password' and request.extension == 'html':
        redirect(URL(c='profile', f='change_password', extension=False))

    if request.extension == 'html':
        auth.settings.formstyle = formstyle_bootstrap3_login

    # The next lines are from Auth._get_login_settings
    table_user = auth.table_user()
    userfield = auth.settings.login_userfield or 'username' \
        if 'username' in table_user.fields else 'email'
    passfield = auth.settings.password_field

    form = auth()

    for w in form.custom.widget.keys():
        if hasattr(form.custom.widget[w], 'add_class'):
            form.custom.widget[w].add_class('input-lg')
    if form.custom.widget.password_two:
        # Looks like a web2py bug, formstyle is not applied
        form.custom.widget.password_two.add_class('form-control')
    if form.custom.submit:
        form.custom.submit.add_class('btn-block')
        form.custom.submit.add_class('input-lg')

    hide_labels = True \
        if request.args(0) in ['login', 'retrieve_password', 'request_reset_password']\
        else False
    if hide_labels:
        table_user[userfield].label = ''
        table_user[passfield].label = ''
        for label in form.elements('label'):
            label.add_class('labels_hidden')
        if form.custom.widget[userfield]:
            form.custom.widget[userfield].update(_placeholder="Email Address")
            form.custom.widget[userfield].add_class('align_center')
            form.custom.widget[userfield]['_label'] = 'false'
        if form.custom.widget[passfield]:
            form.custom.widget[passfield].update(_placeholder="Password")
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
