# -*- coding: utf-8 -*-
"""
Controllers for contributions.
"""
import logging
from applications.zcomx.modules.books import \
    ContributionEvent, \
    default_contribute_amount
from applications.zcomx.modules.creators import \
    book_for_contributions
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

LOG = logging.getLogger('app')


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
    request.vars.amount: double, amount to contribute
    request.vars.book_id: id of book, optional
    request.vars.creator_id: id of creator, optional

    if request.vars.book_id is provided, a contribution to a book is presumed.
    if request.vars.creator_id is provided, a contribution to a creator is
        presumed.
    if neither request.vars.book_id nor request.vars.creator_id are provided
        a contribution to zco.mx is presumed.
    request.vars.book_id takes precendence over request.vars.creator_id.
    """
    def book_data(book_id_str):
        """Return paypal data for the book."""
        try:
            book_id = int(book_id_str)
        except (TypeError, ValueError):
            book_id = None
        if not book_id:
            raise NotFoundError('Invalid book id: {i}'.format(i=book_id_str))
        book_record = entity_to_row(db.book, book_id)
        if not book_record:
            raise NotFoundError('Book not found, id: {i}'.format(i=book_id))
        creator_record = entity_to_row(db.creator, book_record.creator_id)
        if not creator_record:
            raise NotFoundError('Creator not found, id: {i}'.format(
                i=book_record.creator_id))
        if not creator_record.paypal_email:
            raise NotFoundError('Creator has no paypal email, id: {i}'.format(
                i=book_record.creator_id))
        auth_user = entity_to_row(db.auth_user, creator_record.auth_user_id)
        if not auth_user:
            raise NotFoundError('Auth user not found, id: {i}'.format(
                i=creator_record.auth_user_id))
        data = Storage({})
        data.business = creator_record.paypal_email
        data.item_name = '{b} ({c})'.format(
            b=book_record.name, c=auth_user.name)
        data.item_number = book_record.id
        return data

    def creator_data(creator_id_str):
        """Return paypal data for the creator."""
        try:
            creator_id = int(creator_id_str)
        except (TypeError, ValueError):
            creator_id = None
        if not creator_id:
            raise NotFoundError('Invalid creator id: {i}'.format(
                i=creator_id_str))
        creator_record = entity_to_row(db.creator, creator_id)
        if not creator_record:
            raise NotFoundError('Creator not found, id: {i}'.format(
                i=creator_id))
        if not creator_record.paypal_email:
            raise NotFoundError('Creator has no paypal email, id: {i}'.format(
                i=creator_id))
        auth_user = entity_to_row(db.auth_user, creator_record.auth_user_id)
        if not auth_user:
            raise NotFoundError('Auth user not found, id: {i}'.format(
                i=creator_record.auth_user_id))
        book_record = book_for_contributions(db, creator_record)
        if not book_record:
            raise NotFoundError(
                'Creator has no book for contributions, id: {i}'.format(
                    i=creator_id
                )
            )
        data = Storage({})
        data.business = creator_record.paypal_email
        data.item_name = '{c}'.format(c=auth_user.name)
        data.item_number = book_record.id
        return data

    data = None
    if request.vars.book_id:
        try:
            data = book_data(request.vars.book_id)
        except NotFoundError as err:
            LOG.error(err)
    elif request.vars.creator_id:
        try:
            data = creator_data(request.vars.creator_id)
        except NotFoundError as err:
            LOG.error(err)

    if not data:
        data = Storage({})
        data.business = 'show.me@zco.mx'
        data.item_name = 'zco.mx'
        data.item_number = ''

    data.amount = request.vars.amount if 'amount' in request.vars else ''

    paypal_url = 'https://www.paypal.com/cgi-bin/webscr'
    notify_url = URL(
        c='contributions', f='paypal_notify', scheme='https', host=True)
    if DEBUG:
        paypal_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr'
        notify_url = 'https://dev.zco.mx/contributions/paypal_notify.html'

    return dict(
        amount=data.amount,
        business=data.business,
        item_name=data.item_name,
        item_number=data.item_number,
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
            LOG.error('Invalid book item_number: {i}'.format(
                i=request.vars.item_number))
            valid = False

        try:
            amount = float(request.vars.payment_gross)
        except (TypeError, ValueError):
            LOG.error('Invalid gross payment: {i}'.format(
                i=request.vars.payment_gross))
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
