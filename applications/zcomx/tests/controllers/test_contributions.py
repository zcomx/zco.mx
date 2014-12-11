#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/contributions.py

"""
import datetime
import unittest
import urllib
from applications.zcomx.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _book = None
    _creator = None
    _invalid_book_id = None

    titles = {
        'contribute_widget': [
            '<input type="text" id="contribute_amount"',
            ' id="contribute_link">contribute</a>',
        ],
        'contribute_widget_nada': [
            '<div class="row contribute_widget">',
            '</div>',
        ],
        'faq': '<h1>FAQ</h1>',
        'index': '<div id="front_page">',
        'modal': 'Your donations help cover the costs of hosting',
        'modal_book': 'Contributions go directly to the cartoonist',
        'paypal': '<form id="paypal_form"',
    }
    url = '/zcomx/contributions'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book from a creator with a paypal_email.
        cls._book = db(db.creator.paypal_email != '').select(
            db.book.ALL,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id),
                db.book_page.on(db.book_page.book_id == db.book.id)
            ],
        ).first()

        if not cls._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            cls._invalid_book_id = rows[0][max_book_id] + 1
        else:
            cls._invalid_book_id = 1

        cls._creator = db(db.creator.paypal_email != '').select().first()
        if not cls._creator:
            raise SyntaxError('Unable to get creator.')

    def test__contribute_widget(self):
        # Should handle no id, but display nothing.
        self.assertTrue(web.test('{url}/contribute_widget.load'.format(
            url=self.url),
            self.titles['contribute_widget_nada']))

        # Invalid id, should display nothing.
        self.assertTrue(web.test('{url}/contribute_widget.load/{bid}'.format(
            url=self.url,
            bid=self._invalid_book_id),
            self.titles['contribute_widget_nada']))

        # Test valid id
        self.assertTrue(web.test('{url}/contribute_widget.load/{bid}'.format(
            url=self.url,
            bid=self._book.id),
            self.titles['contribute_widget']))

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__modal(self):
        self.assertTrue(
            web.test(
                '{url}/modal'.format(url=self.url),
                self.titles['modal']
            )
        )

        # Test with book_id
        self.assertTrue(
            web.test(
                '{url}/modal?book_id={bid}'.format(
                    url=self.url,
                    bid=self._book.id
                ),
                [self.titles['modal_book'], self._book.name]
            )
        )
        # Test with creator_id
        self.assertTrue(
            web.test(
                '{url}/modal?creator_id={cid}'.format(
                    url=self.url,
                    cid=self._creator.id
                ),
                self.titles['modal_book']
            )
        )
        # Book is not found.
        self.assertFalse(
            web.test(
                '{url}/modal?creator_id={cid}'.format(
                    url=self.url,
                    cid=self._creator.id
                ),
                self._book.name
            )
        )

        # Test with book_id and creator_id
        self.assertTrue(
            web.test(
                '{url}/modal?book_id={bid}'.format(
                    url=self.url,
                    bid=self._book.id
                ),
                [self.titles['modal_book'], self._book.name]
            )
        )

    def test__paypal(self):
        self.assertTrue(
            web.test(
                '{url}/paypal'.format(url=self.url),
                self.titles['paypal']
            )
        )

    def test__paypal_notify(self):
        book = self.add(db.book, dict(name='Text Book'))

        def get_contributions():
            return db(db.contribution.book_id == book.id).select()

        def get_paypal_log(txn_id):
            return db(db.paypal_log.txn_id == txn_id).select()

        def delete_paypal_log(txn_id):
            db(db.paypal_log.txn_id == txn_id).delete()
            db.commit()

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
            'custom': '/faq',
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

        self.assertTrue(
            web.test(
                '{url}/paypal_notify?{q}'.format(
                    url=self.url,
                    q=urllib.urlencode(notify_vars),
                ),
                self.titles['faq']
            )
        )

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

        statuses = ['Denied', 'Pending']
        for count, status in enumerate(statuses):
            txn_id = '_test_paypal_notify_{idx:03d}'.format(idx=count)
            notify_vars['payment_status'] = status
            notify_vars['txn_id'] = txn_id
            self.assertTrue(
                web.test(
                    '{url}/paypal_notify?{q}'.format(
                        url=self.url,
                        q=urllib.urlencode(notify_vars),
                    ),
                    self.titles['faq']
                )
            )

            contributions = get_contributions()
            self.assertEqual(len(contributions), 1)
            logs = get_paypal_log(txn_id)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].payment_status, status)
            self._objects.append(logs[0])

        delete_paypal_log(txn_id)
        logs = get_paypal_log(txn_id)
        self.assertEqual(len(logs), 0)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
