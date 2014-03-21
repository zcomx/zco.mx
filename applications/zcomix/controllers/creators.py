# -*- coding: utf-8 -*-
"""Creator controller functions"""

from applications.zcomix.modules.links import CustomLinks
from applications.zcomix.modules.stickon.sqlhtml import LocalSQLFORM


def books():
    """Creator books report controller.
    request.args(0): integer, id of creator.
    """
    return dict()


def creator():
    """Creator page
    request.args(0): integer, id of creator.
    """
    if not request.args(0):
        redirect(URL(c='default', f='index'))

    creator_record = db(db.creator.id == request.args(0)).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))

    auth_user = db(db.auth_user.id == creator_record.auth_user_id).select(
        db.auth_user.ALL
    ).first()
    if not auth_user:
        redirect(URL(c='default', f='index'))

    pre_links = []
    if creator_record.tumblr:
        pre_links.append(A('tumblr', _href=creator_record.tumblr, _target='_blank'))
    if creator_record.wikipedia:
        pre_links.append(A('wikipedia', _href=creator_record.wikipedia, _target='_blank'))

    return dict(
        auth_user=auth_user,
        creator=creator_record,
        links=CustomLinks(db.creator, creator_record.id).represent(pre_links=pre_links),
    )


def index():
    """Creators CRUD grid."""
    # This is no longer used
    redirect(URL(c='default', f='index'))
