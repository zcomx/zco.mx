#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/login.py

"""
import requests
import os
import unittest
from gluon.contrib.simplejson import loads
from applications.zcomx.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# E0602: *Undefined variable %%r*
# pylint: disable=C0111,R0904,E0602


class TestFunctions(LocalTestCase):

    _book = None
    _book_page = None
    _book_to_link = None
    _creator = None
    _creator_to_link = None
    _user = None
    _test_data_dir = None

    titles = {
        'account': ['account_profile_container', 'change_password_container'],
        'book_delete': '<div id="book_delete_section">',
        'book_delete_invalid': 'Invalid data provided.',
        'book_edit_no_id': '<div id="book_edit_section">',
        'book_edit': [
            '<div id="book_edit_section">',
            "'label': 'Reader Background'"
        ],
        'book_list': '<h2>Book List</h2>',
        'book_list_disabled': '<div id="disabled_container">',
        'book_list_ongoing': '<div id="ongoing_container">',
        'book_list_released': '<div id="released_container">',
        'book_pages': '<div id="profile_book_pages_page">',
        'book_pages_invalid': 'Invalid data provided.',
        'book_pages_handler_fail': [
            '{"files":',
            'Upload service unavailable',
        ],
        'book_pages_handler': [
            '{"files":',
            '"thumbnailUrl"',
        ],
        'book_pages_reorder_fail': [
            '"success": false',
            '"error": "Reorder service unavailable."',
        ],
        'book_pages_reorder': [
            '"success": true',
        ],
        'book_release': '<div id="book_release_section">',
        'book_release_invalid': 'Invalid data provided.',
        'books': '<div id="ongoing_book_list" class="book_list">',
        'default': '<div id="front_page">',
        'links': [
            'href="/zcomx/login/links.load/new/link',
            'Add</span>',
            'order_no_handler/creator_to_link',
        ],
        'links_book': [
            'href="/zcomx/login/links.load/new/link',
            'Add</span>',
            'order_no_handler/book_to_link',
        ],
        'modal_error': 'An error occurred. Please try again.',
        'order_no_handler': '<div id="creator_page">',
        'profile': '<div id="creator_section">',
    }
    url = '/zcomx/login'

    @classmethod
    def setUpClass(cls):
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        email = web.username
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = db.creator.auth_user_id == cls._user.id
        cls._creator = db(query).select().first()
        if not cls._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        # Get a book by creator with pages and links.
        count = db.book_page.book_id.count()
        query = (db.creator.id == cls._creator.id)
        book_page = db(query).select(
            db.book_page.ALL,
            count,
            left=[
                db.book.on(db.book.id == db.book_page.book_id),
                db.book_to_link.on(db.book_to_link.book_id == db.book.id),
                db.creator.on(db.creator.id == db.book.creator_id),
            ],
            groupby=db.book_page.book_id,
            orderby=~count
        ).first()
        if not book_page:
            raise SyntaxError(
                'No book page from creator with email: {e}'.format(e=email)
            )

        query = (db.book_page.id == book_page.book_page.id)
        cls._book_page = db(query).select().first()
        if not cls._book_page:
            raise SyntaxError(
                'Unable to get book_page for: {e}'.format(e=email)
            )

        query = (db.book.id == cls._book_page.book_id)
        cls._book = db(query).select(db.book.ALL).first()
        if not cls._book:
            raise SyntaxError(
                'No books for creator with email: {e}'.format(e=email)
            )

        query = (db.creator_to_link.creator_id == cls._creator.id)
        cls._creator_to_link = db(query).select(
            orderby=db.creator_to_link.order_no
        ).first()
        if not cls._creator_to_link:
            raise SyntaxError(
                'No creator_to_link with email: {e}'.format(e=email)
            )

        query = (db.book_to_link.book_id == cls._book.id)
        cls._book_to_link = db(query).select(
            orderby=db.book_to_link.order_no).first()
        if not cls._book_to_link:
            raise SyntaxError(
                'No book_to_link with email: {e}'.format(e=email)
            )

        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

    def test__account(self):
        self.assertTrue(
            web.test(
                '{url}/account'.format(url=self.url),
                self.titles['account']
            )
        )

    def test__book_crud(self):

        def get_book(book_id):
            """Return a book"""
            query = (db.book.id == book_id)
            return db(query).select(db.book.ALL).first()

        book = self.add(db.book, dict(
            name='',
            creator_id=self._creator.id,
        ))
        self.assertEqual(book.name, '')

        web.login()

        # Create book
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            '_action': 'create',
            'name': 'name',
            'value': '_Untitled_',
        }
        web.post(url, data=data)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')
        book_id = int(result['id'])
        self.assertTrue(book_id > 0)

        book = get_book(book_id)
        self.assertEqual(book.name, '_Untitled_')
        self.assertEqual(book.creator_id, self._creator.id)
        self.assertEqual(book.urlify_name, 'untitled')

        # Update
        url = '{url}/book_crud.json/{bid}'.format(bid=book_id, url=self.url)
        data = {
            '_action': 'update',
            'name': 'name',
            'pk': book_id,
            'value': 'Test Book CRUD',
        }
        web.post(url, data=data)

        book = get_book(book_id)
        self.assertEqual(book.name, 'Test Book CRUD')
        self.assertEqual(book.urlify_name, 'test-book-crud')

        # No book id
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            '_action': 'update',
            'field': 'name',
            'value': 'No book id',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )
        book = get_book(book_id)
        self.assertEqual(book.name, 'Test Book CRUD')

        # No action
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            'field': 'name',
            'pk': book_id,
            'value': 'No action',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        # Invalid action
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            '_action': '_fake_',
            'field': 'name',
            'pk': book_id,
            'value': 'Invalid action',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        # Invalid book id
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            '_action': 'update',
            'field': 'name',
            'pk': 9999999,
            'value': 'Invalid book id',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        # Invalid data
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            '_action': 'update',
            'field': '_invalid_field_',
            'pk': book_id,
            'value': 'Invalid book id',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        # No data
        data = {}
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        # Delete book
        url = '{url}/book_crud.json/{bid}'.format(bid=book_id, url=self.url)
        data = {
            '_action': 'delete',
            'pk': book_id,
        }
        web.post(url, data=data)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')

        book = get_book(book_id)
        self.assertFalse(book)

    def test__book_delete(self):
        # No book id, redirect to books
        self.assertTrue(
            web.test(
                '{url}/book_delete'.format(url=self.url),
                self.titles['book_delete_invalid']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_delete/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_delete']
            )
        )

    def test__book_edit(self):
        # No book id, redirect to books
        self.assertTrue(
            web.test(
                '{url}/book_edit'.format(url=self.url),
                self.titles['book_edit_no_id']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_edit/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_edit']
            )
        )

    def test__book_list(self):
        # No type indicator
        self.assertTrue(
            web.test(
                '{url}/book_list'.format(url=self.url),
                self.titles['book_list']
            )
        )

        # Released
        self.assertTrue(
            web.test(
                '{url}/book_list.load/released'.format(url=self.url),
                self.titles['book_list_released']
            )
        )

        # Ongoing
        self.assertTrue(
            web.test(
                '{url}/book_list.load/ongoing'.format(url=self.url),
                self.titles['book_list_ongoing']
            )
        )

        # Disabled
        self.assertTrue(
            web.test(
                '{url}/book_list.load/disabled'.format(url=self.url),
                self.titles['book_list_disabled']
            )
        )

    def test__book_pages(self):
        # No book_id, redirects to books page
        self.assertTrue(
            web.test(
                '{url}/book_pages'.format(url=self.url),
                self.titles['book_pages_invalid']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_pages/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_pages']
            )
        )

    def test__book_pages_handler(self):
        # No book_id, return fail message
        self.assertTrue(
            web.test(
                '{url}/book_pages_handler'.format(url=self.url),
                self.titles['book_pages_handler_fail']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_pages_handler/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_pages_handler']
            )
        )

    def test__book_pages_reorder(self):
        # No book_id, return fail message
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder'.format(url=self.url),
                self.titles['book_pages_reorder_fail']
            )
        )

        # Invalid book_id, return fail message
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder/{bid}'.format(
                    bid=999999, url=self.url),
                self.titles['book_pages_reorder_fail']
            )
        )

        # Valid book_id, no book pages returns success
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder/{bid}'.format(
                    bid=self._book.id,
                    url=self.url,
                ),
                self.titles['book_pages_reorder']
            )
        )

        # Valid
        query = (db.book_page.book_id == self._book.id)
        book_page_ids = [x.id for x in db(query).select(db.book_page.id)]
        bpids = ['book_page_ids[]={pid}'.format(pid=x) for x in book_page_ids]
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder/{bid}?{bpid}'.format(
                    bid=self._book.id,
                    bpid='&'.join(bpids),
                    url=self.url),
                self.titles['book_pages_reorder']
            )
        )

    def test__book_release(self):
        # No book_id, redirects to books page
        self.assertTrue(
            web.test(
                '{url}/book_release'.format(url=self.url),
                self.titles['book_release_invalid']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_release/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_release']
            )
        )

    def test__books(self):
        self.assertTrue(
            web.test(
                '{url}/books'.format(bid=self._book.id, url=self.url),
                self.titles['books']
            )
        )

    def test__creator_crud(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        def get_creator():
            """Return a creator"""
            query = (db.creator.id == self._creator.id)
            return db(query).select(db.creator.ALL).first()

        old_creator = get_creator()

        web.login()

        url = '{url}/creator_crud.json'.format(url=self.url)
        data = {
            'name': 'paypal_email',
            'value': 'test__creator_crud@example.com',
        }
        web.post(url, data=data)

        creator = get_creator()
        self.assertEqual(
            creator.paypal_email,
            'test__creator_crud@example.com'
        )

        # Invalid name
        data = {
            'name': '_invalid_field_',
            'value': 'test__creator_crud@example.com',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        # No data
        data = {}
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided."}\n'
        )

        db(db.creator.id == old_creator.id).update(**old_creator.as_dict())
        db.commit()
        creator = get_creator()

    def test__creator_img_handler(self):

        def get_creator():
            """Return a creator"""
            query = (db.creator.id == self._creator.id)
            return db(query).select(db.creator.ALL).first()

        old_creator = get_creator()
        old_creator.update_record(image=None)
        db.commit()
        old_creator = get_creator()
        self.assertFalse(old_creator.image)

        web.login()

        # Use requests to simplify uploading a file.
        sample_file = os.path.join(self._test_data_dir, 'web_plus.jpg')
        files = {'up_files': open(sample_file, 'rb')}
        response = requests.post(
            web.app + '/login/creator_img_handler',
            files=files,
            cookies=web.cookies,
            verify=False,
        )
        self.assertEqual(response.status_code, 200)
        creator = get_creator()
        self.assertTrue(creator.image)

        response_2 = requests.delete(
            web.app + '/login/creator_img_handler',
            cookies=web.cookies,
            verify=False,
        )
        self.assertEqual(response_2.status_code, 200)
        creator = get_creator()
        self.assertFalse(creator.image)

        # Reset the image
        sample_file = os.path.join(self._test_data_dir, 'web_plus.jpg')
        files = {'up_files': open(sample_file, 'rb')}
        response = requests.post(
            web.app + '/login/creator_img_handler',
            files=files,
            cookies=web.cookies,
            verify=False,
        )
        self.assertEqual(response.status_code, 200)

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['books']
            )
        )

    def test__link_crud(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        def do_test(record_id, data, expect_names, expect_errors):
            # When record_id is None, we're testing creator links.
            # When record_id is set,  we're testing book links.
            url = '{url}/link_crud.json/{rid}'.format(
                url=self.url,
                rid=record_id or '',
            )
            web.post(url, data=data)
            result = loads(web.text)
            if not expect_errors:
                self.assertTrue('rows' in result)
                names = [x['name'] for x in result['rows']]
                self.assertEqual(names, expect_names)
                self.assertEqual(result['errors'], expect_errors)
            else:
                self.assertTrue('status' in result)
                self.assertEqual(result['status'], 'error')
                self.assertEqual(result['msg'], expect_errors)

            return result

        def reset(record_id, keep_names):
            if record_id:
                link_to_table = db.book_to_link
                link_to_table_field = db.book_to_link.book_id
            else:
                link_to_table = db.creator_to_link
                link_to_table_field = db.creator_to_link.creator_id
                record_id = self._creator.id

            query = (link_to_table_field == record_id)
            rows = db(query).select(
                link_to_table.ALL,
                db.link.ALL,
                left=[link_to_table.on(db.link.id == link_to_table.link_id)],
            )
            for r in rows:
                if r.link.name in keep_names:
                    continue
                if 'creator_to_link' in r:
                    db(link_to_table.id == r.creator_to_link.id).delete()
                if 'book_to_link' in r:
                    db(link_to_table.id == r.book_to_link.id).delete()
                if 'link' in r:
                    db(db.link.id == r.link.id).delete()
                db.commit()

        web.login()
        for record_id in [None, self._book.id]:
            # When record_id is None, we're testing creator links.
            # When record_id is set,  we're testing book links.

            reset(record_id, 'test_do_not_delete')

            # Action: get
            data = {'action': 'get'}
            do_test(record_id, data, ['test_do_not_delete'], {})

            # Action: create
            data = {
                'action': 'create',
                'name': '_test__link_crud_',
                'url': 'http://www.linkcrud.com',
            }
            result = do_test(record_id, data, [], {})
            data = {'action': 'get'}
            got = do_test(
                record_id,
                data,
                ['test_do_not_delete', '_test__link_crud_'],
                {}
            )
            self.assertEqual(result['id'], got['rows'][1]['id'])
            link_id = result['id']

            # Action: get with link_id
            data = {
                'action': 'get',
                'link_id': link_id,
            }
            do_test(record_id, data, ['_test__link_crud_'], {})

            # Action: update
            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'name',
                'value': '_test__link_crud_2_',
            }
            do_test(record_id, data, [], {})
            data = {'action': 'get'}
            do_test(
                record_id,
                data,
                ['test_do_not_delete', '_test__link_crud_2_'],
                {}
            )

            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(record_id, data, [], {})
            data = {'action': 'get'}
            got = do_test(
                record_id,
                data,
                ['test_do_not_delete', '_test__link_crud_2_'],
                {}
            )
            self.assertEqual(got['rows'][1]['url'], 'http://www.linkcrud2.com')

            # Action: update, Invalid link_id
            data = {
                'action': 'update',
                'link_id': 0,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(record_id, data, [], 'Invalid data provided.')

            # Action: update, Invalid url
            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'url',
                'value': '_bad_url_',
            }
            do_test(record_id, data, [], 'Enter a valid URL')

            # Action: update, Invalid name
            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'name',
                'value': '',
            }
            do_test(
                record_id,
                data,
                [],
                'Enter 1 to 40 characters'
            )

            # Action: move
            data = {
                'action': 'move',
                'link_id': link_id,
                'dir': 'up',
            }
            do_test(record_id, data, [], {})
            data = {'action': 'get'}
            do_test(
                record_id,
                data,
                ['_test__link_crud_2_', 'test_do_not_delete'],
                {}
            )

            # Action: delete
            data = {
                'action': 'delete',
                'link_id': link_id,
            }
            do_test(record_id, data, [], {})
            data = {'action': 'get'}
            do_test(record_id, data, ['test_do_not_delete'], {})

            # Action: delete, Invalid link_id
            data = {
                'action': 'delete',
                'link_id': 0,
            }
            do_test(record_id, data, [], 'Invalid data provided.')

            reset(record_id, 'test_do_not_delete')

    def test__modal_error(self):
        self.assertTrue(
            web.test(
                '{url}/modal_error'.format(url=self.url),
                self.titles['modal_error']
            )
        )

    def test__profile(self):
        self.assertTrue(
            web.test(
                '{url}/profile'.format(url=self.url),
                self.titles['profile']
            )
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
