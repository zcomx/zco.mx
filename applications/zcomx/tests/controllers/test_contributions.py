#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/contributions.py

"""
import datetime
import unittest
import urllib.parse
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.events import \
    Contribution, \
    PaypalLog
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):
    _book = None
    _creator = None
    _invalid_book_id = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book from a creator with a paypal_email.
        self._book = db(db.creator.paypal_email != '').select(
            db.book.ALL,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id),
                db.book_page.on(db.book_page.book_id == db.book.id)
            ],
        ).first()

        if not self._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            self._invalid_book_id = rows[0][max_book_id] + 1
        else:
            self._invalid_book_id = 1

        self._creator = Creator.from_query((db.creator.paypal_email != ''))
        if not self._creator:
            raise SyntaxError('Unable to get creator.')

    def test__index(self):
        self.assertWebTest(
            '/contributions/index', match_page_key='/default/index')

    def test__modal(self):
        self.assertWebTest('/contributions/modal')

        # Test with book_id
        url_path = '/contributions/modal?book_id={bid}'.format(
            bid=self._book.id
        )
        self.assertWebTest(
            url_path,
            match_page_key='/contributions/modal/book',
            match_strings=[self._book.name]
        )

        # Test with creator_id
        url_path = '/contributions/modal?creator_id={cid}'.format(
            cid=self._creator.id
        )
        self.assertWebTest(
            url_path,
            match_page_key='/contributions/modal/book',
            match_strings=[self._creator.name]
        )

        # Book is not found in results.
        self.assertRaises(
            self.failureException,
            self.assertWebTest,
            url_path,
            match_page_key='/contributions/modal/book',
            match_strings=[self._book.name]
        )

        # Test with book_id and creator_id
        fmt = '/contributions/modal?book_id={bid}&creator_id={cid}'
        url_path = fmt.format(bid=self._book.id, cid=self._creator.id)
        self.assertWebTest(
            url_path,
            match_page_key='/contributions/modal/book',
            match_strings=[self._book.name]
        )

    def test__paypal(self):
        self.assertWebTest('/contributions/paypal')

    def test__paypal_notify(self):
        book = self.add(Book, dict(name='Text Book'))

        def get_contributions():
            return Records.from_key(Contribution, dict(book_id=book.id))

        def get_zco_contributions():
            return Records.from_key(Contribution, dict(book_id=0))

        def get_paypal_log(txn_id):
            return Records.from_key(PaypalLog, dict(txn_id=txn_id))

        def delete_paypal_log(txn_id):
            for paypal_log in get_paypal_log(txn_id):
                paypal_log.delete()

        self.assertEqual(len(get_contributions()), 0)

        txn_id = '_test_paypal_notify_'
        notify_vars = {
            'address_city': 'Toronto',
            'address_country': 'Canada',
            'address_country_code': 'CA',
            'address_name': 'Test Buyer',
            'address_state': 'Ontario',
            'address_status': 'confirmed',
            'address_street': '1 Maire-Victorin',
            'address_zip': 'M5A 1E1',
            'business': 'showme@zco.mx',
            'charset': 'windows-1252',
            'custom': '/z/faq',
            'first_name': 'Test',
            'ipn_track_id': '9313257df1a27',
            'item_name': 'Test Book',
            'item_number': str(book.id),
            'last_name': 'Buyer',
            'mc_currency': 'USD',
            'mc_fee': '0.43',
            'mc_gross': '4.44',
            'notify_version': '3.8',
            'payer_email': 'payer@gmail.com',
            'payer_id': 'B2TM4GL9CT6CW',
            'payer_status': 'verified',
            'payment_date': '13:36:00 Oct 21, 2014 PDT',
            'payment_fee': '0.43',
            'payment_gross': '4.44',
            'payment_status': 'Completed',
            'payment_type': 'instant',
            'protection_eligibility': 'Eligible',
            'quantity': '0',
            'receiver_email': 'showme@zcomix.com',
            'receiver_id': '67V3XCYF92RQL',
            'residence_country': 'CA',
            'tax': '0.00',
            'test_ipn': '1',
            'transaction_subject': '',
            'txn_id': txn_id,
            'txn_type': 'web_accept',
            'verify_sign':
            'AAh-gjn1ENnDuooduWNAFaW4Pdn0ABa6dKmQ59z53r0b82f1KHtBteKn'
        }

        delete_paypal_log(txn_id)
        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 0)

        url_path = '/contributions/paypal_notify?{q}'.format(
            q=urllib.parse.urlencode(notify_vars),
        )
        self.assertWebTest(url_path, match_page_key='/z/faq')

        contributions = get_contributions()
        self.assertEqual(len(contributions), 1)
        self._objects.append(contributions[0])
        self.assertEqual(contributions[0].book_id, book.id)
        self.assertEqual(contributions[0].amount, 4.44)
        self.assertAlmostEqual(
            contributions[0].time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 1)
        self._objects.append(logs[0])
        self.assertEqual(logs[0].payment_status, 'Completed')

        # Test contribution to zco.mx
        txn_id = '_test_paypal_notify_zco'
        delete_paypal_log(txn_id)
        notify_vars['txn_id'] = txn_id
        del notify_vars['item_number']
        before_zco_contributions = get_zco_contributions()

        url_path = '/contributions/paypal_notify?{q}'.format(
            q=urllib.parse.urlencode(notify_vars),
        )
        self.assertWebTest(url_path, match_page_key='/z/faq')

        after_zco_contributions = get_zco_contributions()
        self.assertEqual(
            len(before_zco_contributions) + 1,
            len(after_zco_contributions)
        )
        before_ids = [x.id for x in before_zco_contributions]
        after_ids = [x.id for x in after_zco_contributions]
        new_contrib_ids = set(after_ids).difference(
            set(before_ids))
        self.assertEqual(len(new_contrib_ids), 1)
        new_contrib_id = list(new_contrib_ids)[0]
        query = (db.contribution.id == new_contrib_id)
        new_contrib = db(query).select(limitby=(0, 1)).first()
        self._objects.append(new_contrib)

        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 1)
        self._objects.append(logs[0])

        # reset
        notify_vars['item_number'] = str(book.id)

        # Test variations on status
        statuses = ['Denied', 'Pending']
        for count, status in enumerate(statuses):
            txn_id = '_test_paypal_notify_{idx:03d}'.format(idx=count)
            notify_vars['payment_status'] = status
            notify_vars['txn_id'] = txn_id
            url_path = '/contributions/paypal_notify?{q}'.format(
                q=urllib.parse.urlencode(notify_vars),
            )
            self.assertWebTest(url_path, match_page_key='/z/faq')

            contributions = get_contributions()
            self.assertEqual(len(contributions), 1)
            logs = get_paypal_log(txn_id)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].payment_status, status)
            self._objects.append(logs[0])

        delete_paypal_log(txn_id)
        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 0)

        # reset
        notify_vars['payment_status'] = 'Completed'

        # Test variations on currency
        del notify_vars['payment_gross']         # mc_gross will be used

        delete_paypal_log(txn_id)
        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 0)

        before_contributions = get_contributions()

        url_path = '/contributions/paypal_notify?{q}'.format(
            q=urllib.parse.urlencode(notify_vars),
        )
        self.assertWebTest(url_path, match_page_key='/z/faq')

        after_contributions = get_contributions()
        self.assertEqual(
            len(before_contributions) + 1,
            len(after_contributions)
        )
        before_ids = [x.id for x in before_contributions]
        after_ids = [x.id for x in after_contributions]
        new_contrib_ids = set(after_ids).difference(
            set(before_ids))
        self.assertEqual(len(new_contrib_ids), 1)
        new_contrib_id = list(new_contrib_ids)[0]
        query = (db.contribution.id == new_contrib_id)
        new_contrib = db(query).select(limitby=(0, 1)).first()
        self._objects.append(new_contrib)
        self.assertEqual(new_contrib.book_id, book.id)
        self.assertEqual(new_contrib.amount, 4.44)
        self.assertAlmostEqual(
            new_contrib.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )

        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 1)
        self._objects.append(logs[0])
        self.assertEqual(logs[0].payment_status, 'Completed')

        # reset
        notify_vars['payment_gross'] = '4.44'

    def test__widget(self):
        # Should handle no id, but display nothing.
        self.assertWebTest(
            '/contributions/widget.load',
            match_page_key='/contributions/widget'
        )

        # Invalid id, should handle gracefully
        url_path = '/contributions/widget.load/{bid}'.format(
            bid=self._invalid_book_id)
        self.assertWebTest(url_path, match_page_key='/contributions/widget')

        # Test valid id
        url_path = '/contributions/widget.load/{bid}'.format(bid=self._book.id)
        self.assertWebTest(url_path, match_page_key='/contributions/widget')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
