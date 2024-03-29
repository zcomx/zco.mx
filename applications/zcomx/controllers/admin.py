# -*- coding: utf-8 -*-
""" Admin controller."""
from gluon.http import HTTP
from applications.zcomx.modules.access import requires_admin_ip
from applications.zcomx.modules.stickon.sqlhtml import (
    formstyle_bootstrap3_login,
    search_fields_grid,
)


@auth.requires_membership('admin')
@requires_admin_ip()
def index():
    """Default controller."""
    form = SQLFORM.factory(
        Field(
            'user_id',
            label='Impersonate',
            requires=IS_IN_DB(
                db, db.auth_user.id, '%(name)s - %(email)s', zero='-'),
        ),
        submit_button=auth.messages.submit_button,
        formstyle=formstyle_bootstrap3_login,
        _action=URL('index')
    )
    if form.accepts(request, session, formname='admin_index'):
        try:
            auth.impersonate()
        except HTTP:
            response.flash = 'Not authorized'
        else:
            query = (db.auth_user.id == form.vars.user_id)
            user = db(query).select(limitby=(0, 1)).first()
            name = user.name if user else form.vars.user_id
            msgs = [
                'Impersonating "{name}".'.format(name=name),
                'To stop, logout.',
            ]
            session.flash = ' '.join(msgs)
            redirect(URL(c='login', f='books'))
    elif form.errors:
        response.flash = 'Form could not be submitted.' + \
            ' Please make corrections.'
    impersonating = bool(session.auth.impersonator)
    return dict(form=form, impersonating=impersonating)


@auth.requires_membership('admin')
@requires_admin_ip()
def job_queuers():
    """Controller for grid crud of job_queuer records."""
    response.files.append(URL('static', 'css/clearable_input.css'))
    response.files.append(URL('static', 'css/grid_search_input.css'))

    db.job_queuer.id.readable = False

    search_fields = [
        db.job_queuer.code,
    ]

    grid = search_fields_grid(search_fields)(
        db.job_queuer,
        field_id=db.job_queuer.id,
        details=False,
        maxtextlengths={'job_queuer.code': 100},
    )

    return dict(grid=grid)
