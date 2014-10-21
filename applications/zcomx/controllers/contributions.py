# -*- coding: utf-8 -*-
"""
Controllers for contributions.
"""
import sys
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
        auth_user = None
        if book_record:
            creator = entity_to_row(db.creator, book_record.creator_id)
        if creator:
            auth_user = entity_to_row(db.auth_user, creator.auth_user_id)

        business = creator.paypal_email or ''
        item_name = 'zco.mx book'
        if book_record and auth_user:
            item_name = '{b} ({c})'.format(
                b=book_record.name, c=auth_user.name)
        item_number = book_record.id or ''
        amount = request.vars.amount if 'amount' in request.vars else ''
    else:
        # Contribute to zco.mx
        business = 'show.me@zco.mx'
        item_name = 'zco.mx'
        item_number = None
        amount = ''

    paypal_url = 'https://www.paypal.com/cgi-bin/webscr'
    notify_url = URL(
        c='contributions', f='paypal_notify', scheme='https', host=True)
    if DEBUG:
        paypal_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr'
        notify_url = 'https://dev.zco.mx/contributions/paypal_notify.html'

    return dict(
        amount=amount,
        business=business,
        item_name=item_name,
        item_number=item_number,
        notify_url=notify_url,
        paypal_url=paypal_url,
    )


def paypal_notify():
    """Controller for paypal notifications (notify_url)"""
    response.generic_patterns = ['html']

    if request.vars.payment_status == 'Completed':
        valid = True
        try:
            book_id = int(request.vars.item_number)
        except (TypeError, ValueError):
            print >> sys.stderr, \
                'Invalid book item_number: {i}'.format(
                    i=request.vars.item_number)
            valid = False

        try:
            amount = float(request.vars.payment_gross)
        except (TypeError, ValueError):
            print >> sys.stderr, \
                'Invalid gross payment: {i}'.format(
                    i=request.vars.payment_gross)
            valid = False
        if valid:
            ContributionEvent(book_id, 0).log(amount)

    paypal_log = {}
    for f in db.paypal_log.fields:
        if f in request.vars:
            paypal_log[f] = request.vars[f]
    if paypal_log:
        db.paypal_log.insert(**paypal_log)
        db.commit()

    return dict()
