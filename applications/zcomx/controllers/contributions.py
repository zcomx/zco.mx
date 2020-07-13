# -*- coding: utf-8 -*-
"""
Controllers for contributions.
"""
from applications.zcomx.modules.books import \
    Book, \
    default_contribute_amount
from applications.zcomx.modules.creators import \
    Creator, \
    book_for_contributions
from applications.zcomx.modules.events import \
    ContributionEvent, \
    PaypalLog, \
    ZcoContributionEvent
from applications.zcomx.modules.zco import Zco


def modal():
    """Contributions input controller for modal view.

    request.vars.book_id: id of book, optional
    request.vars.creator_id: id of creator, optional

    if request.vars.book_id is provided, a contribution to a book is presumed.
    if request.vars.creator_id is provided, a contribution to a creator is
        presumed.
    if neither request.vars.book_id nor request.vars.creator_id are provided
        a contribution to zco.mx is presumed.
    request.vars.book_id takes precendence over request.vars.creator_id.
    """
    book = None
    creator = None

    if request.vars.book_id:
        book = Book.from_id(request.vars.book_id)
        creator = Creator.from_id(book.creator_id)
    elif request.vars.creator_id:
        creator = Creator.from_id(request.vars.creator_id)
        if not creator:
            raise LookupError(
                'Creator not found, id %s', request.vars.creator_id)

    return dict(
        book=book,
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
    next_url = Zco().next_url or URL(c='search', f='index')
    if Zco().paypal_in_progress:
        Zco().paypal_in_progress = None
        redirect(next_url)

    def book_data(book_id_str):
        """Return paypal data for the book."""
        try:
            book_id = int(book_id_str)
        except (TypeError, ValueError):
            book_id = None
        if not book_id:
            raise LookupError('Invalid book id: {i}'.format(i=book_id_str))
        book = Book.from_id(book_id)
        creator = Creator.from_id(book.creator_id)
        if not creator.paypal_email:
            raise LookupError('Creator has no paypal email, id: {i}'.format(
                i=book.creator_id))
        data = Storage({})
        data.business = creator.paypal_email
        data.item_name = '{b} ({c})'.format(
            b=book.name, c=creator.name)
        data.item_number = book.id
        return data

    def creator_data(creator_id_str):
        """Return paypal data for the creator."""
        try:
            creator_id = int(creator_id_str)
        except (TypeError, ValueError):
            creator_id = None
        if not creator_id:
            raise LookupError('Invalid creator id: {i}'.format(
                i=creator_id_str))
        creator = Creator.from_id(creator_id)
        if not creator.paypal_email:
            raise LookupError('Creator has no paypal email, id: {i}'.format(
                i=creator_id))
        book = book_for_contributions(creator)
        if not book:
            raise LookupError(
                'Creator has no book for contributions, id: {i}'.format(
                    i=creator_id
                )
            )
        data = Storage({})
        data.business = creator.paypal_email
        data.item_name = '{c}'.format(c=creator.name)
        data.item_number = book.id
        return data

    data = None
    if request.vars.book_id:
        try:
            data = book_data(request.vars.book_id)
        except LookupError as err:
            LOG.error(err)
    elif request.vars.creator_id:
        try:
            data = creator_data(request.vars.creator_id)
        except LookupError as err:
            LOG.error(err)

    if not data:
        data = Storage({})
        data.business = 'show.me@zco.mx'
        data.item_name = 'zco.mx'
        data.item_number = ''

    data.amount = request.vars.amount if 'amount' in request.vars else ''

    paypal_url = 'https://www.paypal.com/cgi-bin/webscr'
    if DEBUG:
        paypal_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr'
    return_url = URL(
        c='contributions', f='paypal_notify', scheme='https', host=True)

    Zco().paypal_in_progress = True

    return dict(
        amount=data.amount,
        business=data.business,
        item_name=data.item_name,
        item_number=data.item_number,
        paypal_url=paypal_url,
        return_url=return_url,
        next_url=next_url,
    )


def paypal_notify():
    """Controller for paypal notifications (return_url)

    request.vars: these are provided by paypal
    """
    if request.vars.payment_status == 'Completed':
        valid = True
        if request.vars.item_number:
            try:
                book_id = int(request.vars.item_number)
            except (TypeError, ValueError):
                LOG.error(
                    'Invalid book item_number: %s', request.vars.item_number)
                valid = False
        else:
            book_id = 0     # Contribution to zco.mx

        amount = 0.00
        gross_field = 'payment_gross' if 'payment_gross' in request.vars \
                else 'mc_gross'

        try:
            amount = float(request.vars[gross_field])
        except (KeyError, TypeError, ValueError):
            LOG.error('Invalid gross payment: %s', request.vars.payment_gross)
            LOG.error('request.vars: %s', str(request.vars))
            valid = False

        if valid:
            # Log the event
            auth_user_id = 0      # there is no user is this context
            if book_id:
                book = Book.from_id(book_id)
                ContributionEvent(book, auth_user_id).log(amount)
            else:
                ZcoContributionEvent(auth_user_id).log(amount)

    paypal_log_data = {}
    for f in db.paypal_log.fields:
        if f in request.vars:
            paypal_log_data[f] = request.vars[f]
    if paypal_log_data:
        # unused-variable (W0612): *Unused variable %%r*
        # pylint: disable=W0612
        try:
            paypal_log = PaypalLog.from_add(paypal_log_data)
        except SyntaxError as err:
            LOG.error('Paypal log failed: %s', str(err))

    if request.vars.custom:
        redirect(request.vars.custom)
    else:
        redirect(URL(c='search', f='index'))


def widget():
    """Contribute widget component controller.

    request.vars.book_id: id of book, optional
    request.vars.creator_id: id of creator, optional
    request.vars.link_type: 'button' or 'link', optional

    if request.vars.book_id is provided, a contribution to a book is presumed.
    if request.vars.creator_id is provided, a contribution to a creator is
        presumed.
    if neither request.vars.book_id nor request.vars.creator_id are provided
        a contribution to zco.mx is presumed.
    request.vars.book_id takes precendence over request.vars.creator_id.

    Notes:
        This function doesnt' check if the creator is eligible for
        contributions. Do this before calling.
        If any errors occur, nothing is displayed.
    """
    Zco().paypal_in_progress = None
    book = None
    creator = None
    if request.vars.book_id:
        book = Book.from_id(request.vars.book_id)
    elif request.vars.creator_id:
        creator = Creator.from_id(request.vars.creator_id)
        if not creator:
            raise LookupError(
                'Creator not found, id %s', request.vars.creator_id)

    if book:
        creator = Creator.from_id(book.creator_id)

    amount = default_contribute_amount(book) if book else 1.00

    paypal_vars = {}
    if book:
        paypal_vars['book_id'] = book.id
    elif creator:
        paypal_vars['creator_id'] = creator.id

    link_types = ['link', 'button']
    link_type = request.vars.link_type if request.vars.link in link_types \
        else link_types[0]

    return dict(
        amount='{a:0.2f}'.format(a=amount),
        paypal_vars=paypal_vars,
        link_type=link_type,
    )
