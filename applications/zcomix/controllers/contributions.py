# -*- coding: utf-8 -*-
"""
Controllers for contributions.
"""

from applications.zcomix.modules.books import default_contribute_amount
from applications.zcomix.modules.stickon.sqlhtml import LocalSQLFORM


def contribute_widget():
    """Contribute widget component controller.

    request.args(0): id of book

    Notes:
        If any errors occur, nothing is displayed.
    """
    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
                db.book.ALL).first()

    creator = None
    if book_record:
        creator = db(db.creator.id == book_record.creator_id).select(
                db.creator.ALL).first()

    return dict(
            amount='{a:0.2f}'.format(a=default_contribute_amount(db, book_record)),
            book=book_record,
            creator=creator,
            )


@auth.requires_login()
def index():
    """Contributions grid."""
    grid = LocalSQLFORM.grid(
            db.contribution,
            )
    return dict(grid=grid)


def paypal():
    """Controller for paypal donate page.
    request.args(0): id of book
    request.vars.amount: double, amount to contribute
    """
    book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL).first()
    creator = None
    if book_record:
        creator = db(db.creator.id == book_record.creator_id).select(
                db.creator.ALL).first()

    return dict(
            book=book_record,
            creator=creator,
            )


def record():
    """Controller to record the contribution.

    request.args(0): id of book
    request.vars.amount: double, amount to contribute

    """
    if request.args(0) and request.vars.amount:
        db.contribution.insert(
            auth_user_id=auth.user_id or 0,
            book_id=request.args(0),
            time_stamp=request.now,
            amount=request.vars.amount,
            )
        db.commit()

    redirect(URL('paypal', args=request.args, vars=request.vars))
