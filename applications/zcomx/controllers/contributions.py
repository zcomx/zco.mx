# -*- coding: utf-8 -*-
"""
Controllers for contributions.
"""

from applications.zcomx.modules.books import \
    ContributionEvent, \
    default_contribute_amount
from applications.zcomx.modules.utils import entity_to_row


def contribute_widget():
    """Contribute widget component controller.

    request.args(0): id of book

    Notes:
        If any errors occur, nothing is displayed.
    """
    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))

    creator = None
    if book_record:
        creator = entity_to_row(db.creator, book_record.creator_id)
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
        book_record = entity_to_row(db.book, request.args(0))
        creator = None
        if book_record:
            creator = entity_to_row(db.creator, book_record.creator_id)

        business = creator.paypal_email or ''
        item_name = book_record.name or ''
        item_number = book_record.id or ''
        amount = request.vars.amount if 'amount' in request.vars else ''
    else:
        # Contribute to zcomx.com
        business = 'show.me@zcomx.com'
        item_name = 'zcomx.com'
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
