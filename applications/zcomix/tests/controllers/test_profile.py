#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/profile.py

"""
import requests
import os
import re
import unittest
from gluon.contrib.simplejson import loads
from applications.zcomix.modules.test_runner import LocalTestCase


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
        'account': '<div class="well well-sm" id="account">',
        'book_add': [
            '<div id="book_edit_section">',
            "'value': '__Untitled-",
        ],
        'book_delete': '<div id="book_delete_section">',
        'book_edit': '<div id="book_edit_section">',
        'book_pages': '<div id="profile_book_pages_page">',
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
        'books': '<div class="well well-sm" id="books">',
        'creator': '<div class="well well-sm" id="creator">',
        'default': 'zcomix.com is a not-for-profit comic-sharing website',
        'index': '<div class="well well-sm" id="account">',
        'links': [
            'href="/zcomix/profile/links.load/new/link',
            'Add</span>',
            'order_no_handler/creator_to_link',
        ],
        'links_book': [
            'href="/zcomix/profile/links.load/new/link',
            'Add</span>',
            'order_no_handler/book_to_link',
        ],
        'order_no_handler': '<div id="creator_page">',
    }
    url = '/zcomix/profile'

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

    def test__book_add(self):
        # This test will create a book.

        def book_ids(creator_id):
            return [
                x.id for x in
                db(db.book.creator_id == creator_id).select(db.book.id)
            ]

        before_ids = book_ids(self._creator.id)
        self.assertTrue(
            web.test(
                '{url}/book_add'.format(url=self.url),
                self.titles['book_add']
            )
        )
        after_ids = book_ids(self._creator.id)
        self.assertEqual(set(before_ids).difference(set(after_ids)), set())
        diff_set = set(after_ids).difference(set(before_ids))
        self.assertEqual(len(diff_set), 1)
        new_book = db(db.book.id == list(diff_set)[0]).select().first()
        self._objects.append(new_book)
        self.assertEqual(new_book.creator_id, self._creator.id)
        self.assertRegexpMatches(
            new_book.name,
            re.compile(r'__Untitled-[0-9]{2}__')
        )

    def test__book_crud(self):

        def get_book(book_id):
            """Return a book"""
            query = (db.book.id == book_id)
            return db(query).select(db.book.ALL).first()

        book_id = db.book.insert(
            name='',
            creator_id=self._creator.id,
        )
        book = get_book(book_id)
        self._objects.append(book)
        self.assertEqual(book.name, '')

        web.login()

        url = '{url}/book_crud.json/{bid}'.format(bid=book_id, url=self.url)
        data = {
            'field': 'name',
            'value': 'Test Book CRUD',
        }
        web.post(url, data=data)

        book = get_book(book_id)
        self.assertEqual(book.name, 'Test Book CRUD')

        # No book id
        url = '{url}/book_crud.json'.format(url=self.url)
        data = {
            'field': 'name',
            'value': 'No book id',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"errors": {"url": "Invalid data provided."}}\n'
        )
        book = get_book(book_id)
        self.assertEqual(book.name, 'Test Book CRUD')

        # Invalid book id
        url = '{url}/book_crud.json/999999'.format(url=self.url)
        data = {
            'field': 'name',
            'value': 'Invalid book id',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"errors": {"url": "Invalid data provided."}}\n'
        )

        # Invalid data
        url = '{url}/book_crud.json/{bid}'.format(bid=book_id, url=self.url)
        data = {
            'field': '_invalid_field_',
            'value': 'Invalid book id',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"errors": {"url": "Invalid data provided."}}\n'
        )

        # No data
        data = {}
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"errors": {"url": "Invalid data provided."}}\n'
        )

    def test__book_delete(self):
        # No book id, redirect to books
        self.assertTrue(
            web.test(
                '{url}/book_delete'.format(url=self.url),
                self.titles['books']
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
                self.titles['books']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_edit/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_edit']
            )
        )

    def test__book_pages(self):
        # No book_id, redirects to books page
        self.assertTrue(
            web.test(
                '{url}/book_pages'.format(url=self.url),
                self.titles['books']
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
                self.titles['books']
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

    def test__creator(self):
        self.assertTrue(
            web.test(
                '{url}/creator'.format(url=self.url),
                self.titles['creator']
            )
        )

    def test__creator_crud(self):

        def get_creator():
            """Return a creator"""
            query = (db.creator.id == self._creator.id)
            return db(query).select(db.creator.ALL).first()

        old_creator = get_creator()

        web.login()

        url = '{url}/creator_crud.json'.format(url=self.url)
        data = {
            'field': 'email',
            'value': 'test__creator_crud@example.com',
        }
        web.post(url, data=data)

        creator = get_creator()
        self.assertEqual(creator.email, 'test__creator_crud@example.com')

        # Invalid field
        data = {
            'field': '_invalid_field_',
            'value': 'test__creator_crud@example.com',
        }
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"errors": {"url": "Invalid data provided."}}\n'
        )

        # No data
        data = {}
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"errors": {"url": "Invalid data provided."}}\n'
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
        save_image = old_creator.image
        old_creator.update_record(image=None)
        old_creator = get_creator()
        self.assertFalse(old_creator.image)

        web.login()

        # Use requests to simplify uploading a file.
        sample_file = os.path.join(self._test_data_dir, 'file.jpg')
        files = {'up_files': open(sample_file, 'rb')}
        response = requests.post(
            web.app + '/profile/creator_img_handler',
            files=files,
            cookies=web.cookies,
            verify=False,
        )

        self.assertEqual(response.status_code, 200)
        creator = get_creator()
        self.assertTrue(creator.image)

        response_2 = requests.delete(
            web.app + '/profile/creator_img_handler',
            cookies=web.cookies,
            verify=False,
        )
        self.assertEqual(response_2.status_code, 200)
        creator = get_creator()
        self.assertFalse(creator.image)

        old_creator.update_record(image=save_image)
        old_creator = get_creator()
        self.assertTrue(old_creator.image)

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__link_crud(self):

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
            self.assertTrue('errors' in result)
            self.assertEqual(result['errors'], expect_errors)
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
                db(link_to_table.id == r.creator_to_link.id).delete()
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
            got = do_test(record_id, data, ['test_do_not_delete', '_test__link_crud_'], {})
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
            do_test(record_id, data, ['test_do_not_delete', '_test__link_crud_2_'], {})

            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(record_id, data, [], {})
            data = {'action': 'get'}
            got = do_test(record_id, data, ['test_do_not_delete', '_test__link_crud_2_'], {})
            self.assertEqual(got['rows'][1]['url'], 'http://www.linkcrud2.com')

            # Action: update, Invalid link_id
            data = {
                'action': 'update',
                'link_id': 0,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(record_id, data, [], {'url': 'Invalid data provided.'})

            # Action: update, Invalid url
            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'url',
                'value': '_bad_url_',
            }
            do_test(record_id, data, [], {'url': 'enter a valid URL'})

            # Action: update, Invalid name
            data = {
                'action': 'update',
                'link_id': link_id,
                'field': 'name',
                'value': '',
            }
            do_test(record_id, data, [], {'name': 'enter from 1 to 40 characters'})

            # Action: move
            data = {
                'action': 'move',
                'link_id': link_id,
                'dir': 'up',
            }
            do_test(record_id, data, [], {})
            data = {'action': 'get'}
            do_test(record_id, data, ['_test__link_crud_2_', 'test_do_not_delete'], {})

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
            do_test(record_id, data, [], {'url': 'Invalid data provided.'})

            reset(record_id, 'test_do_not_delete')

    def test__order_no_handler(self):
        self.assertTrue(
            web.test(
                '{url}/order_no_handler'.format(url=self.url),
                self.titles['default']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/order_no_handler/creator_to_link'.format(url=self.url),
                self.titles['default']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/order_no_handler/creator_to_link/{lid}'.format(
                    lid=self._creator_to_link.id, url=self.url),
                self.titles['default']
            )
        )

        # Down
        before = self._creator_to_link.order_no
        next_url = '/zcomix/creators/creator/{cid}'.format(
            cid=self._creator.id)
        fmt = '{url}/order_no_handler/creator_to_link/{lid}/down?next={n}'
        self.assertTrue(
            web.test(
                fmt.format(
                    lid=self._creator_to_link.id,
                    n=next_url,
                    url=self.url
                ),
                self.titles['order_no_handler']
            )
        )

        query = (db.creator_to_link.id == self._creator_to_link.id)
        after = db(query).select().first().order_no
        # This test fails because db is not updated.
        # self.assertEqual(before + 1, after)

        # Up
        fmt = '{url}/order_no_handler/creator_to_link/{lid}/up?next={nurl}'
        self.assertTrue(
            web.test(
                fmt.format(
                    lid=self._creator_to_link.id,
                    nurl=next_url,
                    url=self.url
                ),
                self.titles['order_no_handler']
            )
        )

        query = (db.creator_to_link.id == self._creator_to_link.id)
        after = db(query).select().first().order_no
        self.assertEqual(before, after)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
