# -*- coding: utf-8 -*-
"""
Controllers for contributions.
"""

from applications.zcomix.modules.books import \
    ContributionEvent, \
    default_contribute_amount


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
        amount = '{a:0.2f}'.format(
            a=default_contribute_amount(db, book_record))
    else:
        amount = 1.00

    return dict(
        amount=amount,
        book=book_record,
        creator=creator,
    )


def index():
    """Contributions grid."""
    redirect(URL(c='default', f='index'))


def paypal():
    """Controller for paypal donate page.
    request.args(0): id of book, optional, if 0, payment is for admin.
    request.vars.amount: double, amount to contribute
    """
    if request.args(0):
        # Contribute to a creator's book.
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL).first()
        creator = None
        if book_record:
            creator = db(db.creator.id == book_record.creator_id).select(
                db.creator.ALL).first()

        business = creator.paypal_email or ''
        item_name = book_record.name or ''
        item_number = book_record.id or ''
        amount = request.vars.amount if 'amount' in request.vars else ''
    else:
        # Contribute to zcomix.com
        business = 'show.me@zcomix.com'
        item_name = 'zcomix.com'
        item_number = None
        amount = ''

    return dict(
        business=business,
        item_name=item_name,
        item_number=item_number,
        amount=amount,
    )


def record():
    """Controller to record the contribution.

    request.args(0): id of book
    request.vars.amount: double, amount to contribute

    """
    if request.args(0) and request.vars.amount:
        ContributionEvent(request.args(0), auth.user_id or 0).log(
            request.vars.amount)
    redirect(URL('paypal', args=request.args, vars=request.vars))
