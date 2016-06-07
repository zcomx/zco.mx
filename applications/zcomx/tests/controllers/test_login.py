#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/login.py

"""
import os
import requests
import time
import unittest
from gluon.contrib.simplejson import loads
from applications.zcomx.modules.activity_logs import TentativeActivityLog
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import \
    Book, \
    get_page
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.indicias import \
    BookPublicationMetadata, \
    PublicationMetadata
from applications.zcomx.modules.links import \
    Link, \
    LinkType, \
    LinksKey
from applications.zcomx.modules.tests.helpers import WebTestCase
from applications.zcomx.modules.zco import \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DRAFT


# C0111: Missing docstring
# R0904: Too many public methods
# E0602: *Undefined variable %%r*
# pylint: disable=C0111,R0904,E0602

class TestFunctions(WebTestCase):

    _book = None
    _book_page = None
    _creator = None
    _creator_as_dict = {}
    _user = None
    _test_data_dir = None
    _max_optimize_img_log_id = None

    url = '/zcomx/login'

    @classmethod
    def setUpClass(cls):
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        email = web.username
        query = (db.auth_user.email == email)
        cls._user = db(query).select(limitby=(0, 1)).first()
        if not cls._user:
            msg = 'No user with email: {e}'.format(e=email)
            print msg
            raise SyntaxError(msg)

        query = db.creator.auth_user_id == cls._user.id
        cls._creator = Creator.from_query(query)
        if not cls._creator:
            msg = 'No creator with email: {e}'.format(e=email)
            print msg
            raise SyntaxError(msg)

        cls._creator_as_dict = cls._creator.as_dict()

        query = (db.book.creator_id == cls._creator.id) & \
                (db.book.name_for_url == 'TestDoNotDelete-001')
        cls._book = Book.from_query(query)
        cls._book_page = get_page(cls._book, page_no='first')

        id_max = db.optimize_img_log.id.max()
        cls._max_optimize_img_log_id = \
            db(db.optimize_img_log).select(id_max)[0][id_max]
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

    @classmethod
    def tearDownClass(cls):
        for job in db(db.job).select():
            job.delete_record()
        db.commit()

        if cls._max_optimize_img_log_id:
            query = (db.optimize_img_log.id > cls._max_optimize_img_log_id)
            db(query).delete()
            db.commit()

        Creator.from_updated(cls._creator, cls._creator_as_dict)

    def test__account(self):
        self.assertWebTest('/login/account')

    def test__agree_to_terms(self):
        self.assertWebTest('/login/agree_to_terms')

    def test__book_crud(self):

        def get_book(book_id):
            """Return a book"""
            query = (db.book.id == book_id)
            return db(query).select(limitby=(0, 1)).first()

        book = self.add(Book, dict(
            name='_fake_',
            creator_id=self._creator.id,
            status=True,
        ))

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
        self.assertEqual(book.name_for_search, 'untitled')
        self.assertEqual(book.name_for_url, 'Untitled')

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
        self.assertEqual(book.name_for_search, 'test-book-crud')
        self.assertEqual(book.name_for_url, 'TestBookCRUD')

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
            '{"status": "error", "msg": "Invalid data provided"}\n'
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
            '{"status": "error", "msg": "Invalid data provided"}\n'
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
            '{"status": "error", "msg": "Invalid data provided"}\n'
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
            '{"status": "error", "msg": "Invalid data provided"}\n'
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
            '{"status": "error", "msg": "Invalid data provided"}\n'
        )

        # No data
        data = {}
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided"}\n'
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

        # The job to delete the book, may take a few seconds to complete
        tries = 10
        while tries:
            book = get_book(book_id)
            if not book:
                break
            tries -= 1
            time.sleep(1)
        self.assertFalse(book)

    def test__book_delete(self):
        # No book id, redirect to books
        self.assertWebTest(
            '/login/book_delete',
            match_page_key='',
            match_strings=['Invalid data provided']
        )
        self.assertWebTest(
            '/login/book_delete/{bid}'.format(bid=self._book.id),
            match_page_key='/login/book_delete'
        )

    def test__book_edit(self):
        self.assertWebTest('/login/book_edit')
        self.assertWebTest(
            '/login/book_edit/{bid}'.format(bid=self._book.id),
            match_page_key='/login/book_edit',
            match_strings=["'label': 'Reader Background'"],
        )

    def test__book_list(self):
        self.assertWebTest('/login/book_list')
        self.assertWebTest('/login/book_list.load/completed')
        self.assertWebTest('/login/book_list.load/ongoing')
        self.assertWebTest('/login/book_list.load/disabled')

    def test__book_pages(self):
        self.assertWebTest(
            '/login/book_pages',
            match_page_key='',
            match_strings=['Invalid data provided'],
        )

        self.assertWebTest(
            '/login/book_pages/{bid}'.format(bid=self._book.id),
            match_page_key='/login/book_pages',
        )

    def test__book_pages_handler(self):
        # No book_id, return fail message
        self.assertWebTest(
            '/login/book_pages_handler',
            match_page_key='',
            match_strings=[
                '{"files":',
                'Upload service unavailable',
            ],
        )

        def get_book_page_ids(book):
            return [x.id for x in book.pages()]

        def get_activity_log_ids(book_id):
            query = (db.tentative_activity_log.book_id == book_id)
            return [
                x.id for x in db(query).select(db.tentative_activity_log.id)]

        before_ids = get_book_page_ids(self._book)
        before_activity_ids = get_activity_log_ids(self._book.id)

        # Test add file.
        sample_file = os.path.join(self._test_data_dir, 'web_plus.jpg')
        files = {'up_files[]': open(sample_file, 'rb')}
        response = requests.post(
            web.app + '/login/book_pages_handler/{i}'.format(i=self._book.id),
            files=files,
            cookies=web.cookies,
            verify=False,
        )
        self.assertEqual(response.status_code, 200)

        after_ids = get_book_page_ids(self._book)
        self.assertEqual(len(before_ids) + 1, len(after_ids))
        new_id = list(set(after_ids).difference(set(before_ids)))[0]

        # Check for tentative_activity_log record
        after_activity_ids = get_activity_log_ids(self._book.id)
        self.assertEqual(len(before_activity_ids) + 1, len(after_activity_ids))
        new_activity_id = list(set(after_activity_ids).difference(
            set(before_activity_ids)))[0]
        tentative_log = TentativeActivityLog.from_id(new_activity_id)
        self.assertEqual(tentative_log.book_id, self._book.id)
        self.assertEqual(tentative_log.book_page_id, new_id)
        self.assertEqual(tentative_log.action, 'page added')
        self._objects.append(tentative_log)

        # Test delete file
        query = (db.book_page.id == new_id)
        book_page = db(query).select(limitby=(0, 1)).first()
        self.assertTrue(book_page)
        response = requests.delete(
            web.app + '/login/book_pages_handler/{i}'.format(i=new_id),
            files=files,
            cookies=web.cookies,
            verify=False,
        )
        self.assertEqual(response.status_code, 200)

        # A job to delete the image should be created. It may take a bit
        # to complete so check that the job exists, or it is completed.
        query = (db.job.command.like(
            '%process_img.py --delete {i}'.format(i=book_page.image)))
        job_count = db(query).count()
        query = (db.optimize_img_log.image == book_page.image)
        log_count = db(query).count()
        self.assertTrue(job_count == 1 or log_count == 0)

        self._objects.append(book_page)

    def test__book_post_upload_session(self):
        # No book_id, return fail message
        self.assertWebTest(
            '/login/book_post_upload_session',
            match_page_key='',
            match_strings=[
                '"status": "error"',
                '"msg": "Reorder service unavailable"',
            ],
        )

        # Invalid book_id, return fail message
        self.assertWebTest(
            '/login/book_post_upload_session/{bid}'.format(bid=999999),
            match_page_key='',
            match_strings=[
                '"status": "error"',
                '"msg": "Reorder service unavailable"',
            ],
        )

        # Valid book_id, no book pages returns success

        # Protect existing book_page records so they don't get deleted.
        def set_book_page_book_ids(from_book_id, to_book_id):
            from_book = Book.from_id(from_book_id)
            for page in from_book.pages():
                BookPage.from_updated(page, dict(book_id=to_book_id))

        temp_book = self.add(Book, dict(name='Temp Book'))

        set_book_page_book_ids(self._book.id, temp_book.id)

        self._book.update_record(status=BOOK_STATUS_DRAFT)
        db.commit()
        self.assertWebTest(
            '/login/book_post_upload_session/{bid}'.format(bid=self._book.id),
            match_page_key='/login/book_post_upload_session',
        )

        # book has no pages, so it should status should be set accordingly
        book = Book.from_id(self._book.id)
        self.assertEqual(book.status, BOOK_STATUS_DRAFT)

        # Valid
        set_book_page_book_ids(temp_book.id, self._book.id)
        book_page_ids = [x.id for x in self._book.pages()]
        bp_ids = ['book_page_ids[]={pid}'.format(pid=x) for x in book_page_ids]
        self.assertWebTest(
            '/login/book_post_upload_session/{bid}?{bpid}'.format(
                bid=self._book.id,
                bpid='&'.join(bp_ids),
            ),
            match_page_key='/login/book_post_upload_session',
        )

        # book has pages, so it should status should be set accordingly
        book = Book.from_id(self._book.id)
        self.assertEqual(book.status, BOOK_STATUS_ACTIVE)

    def test__book_release(self):
        # No book_id, redirects to books page
        self.assertWebTest(
            '/login/book_release',
            match_page_key='',
            match_strings=['Invalid data provided']
        )

        self.assertWebTest(
            '/login/book_release/{bid}'.format(bid=self._book.id),
            match_page_key='/login/book_release',
        )

    def test__books(self):
        self.assertWebTest('/login/books')

    def test__creator_crud(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        def get_creator():
            """Return a creator"""
            return Creator.from_id(self._creator.id)

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
            '{"status": "error", "msg": "Invalid data provided"}\n'
        )

        # No data
        data = {}
        web.post(url, data=data)
        self.assertEqual(
            web.text,
            '{"status": "error", "msg": "Invalid data provided"}\n'
        )

        Creator.from_updated(self._creator, old_creator.as_dict())

    def test__creator_img_handler(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        def get_creator():
            """Return a Creator instance"""
            return Creator.from_id(self._creator.id)

        old_creator = Creator.from_updated(self._creator, dict(image=None))
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
        self.assertWebTest('/login/index', match_page_key='/login/books')

    def test__indicia(self):
        self.assertWebTest('/login/indicia')

    def test__indicia_preview_urls(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        def get_creator():
            """Return creator"""
            return Creator.from_id(self._creator.id)

        web.login()

        # Test: no images set
        data = dict(
            indicia_portrait=None,
            indicia_landscape=None,
        )
        creator = Creator.from_updated(self._creator, data)
        self.assertEqual(creator.indicia_portrait, None)
        self.assertEqual(creator.indicia_landscape, None)

        url = '{url}/indicia_preview_urls.json'.format(url=self.url)
        web.post(url, data={})
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')

        creator = get_creator()

        self.assertEqual(
            result['urls']['landscape'],
            '/zcomx/static/images/generic_indicia_landscape.png'
        )
        self.assertEqual(
            result['urls']['portrait'],
            '/zcomx/static/images/generic_indicia_portrait.png'
        )

        # Test: with images set
        data = dict(
            indicia_landscape='creator.indicia_landscape.lll.000.png',
            indicia_portrait='creator.indicia_portrait.ppp.111.png',
        )
        creator = Creator.from_updated(self._creator, data)

        web.post(url, data={})
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            result['urls']['landscape'],
            '/images/download.json/creator.indicia_landscape.lll.000.png?size=web'
        )
        self.assertEqual(
            result['urls']['portrait'],
            '/images/download.json/creator.indicia_portrait.ppp.111.png?size=web'
        )

        # Re-run should return exact same results
        url = '{url}/indicia_preview_urls.json'.format(url=self.url)
        web.post(url, data={})
        result_2 = loads(web.text)
        self.assertEqual(result, result_2)
        creator_2 = get_creator()
        self.assertEqual(creator, creator_2)

    def test__link_crud(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        def do_test(links_key, data, expect_names, expect_errors):
            url = '{url}/link_crud.json/{t}/{i}'.format(
                url=self.url,
                t=links_key.record_table,
                i=links_key.record_id,
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

        def reset(links_key, keep_names):
            query = (db.link.link_type_id == links_key.link_type_id) & \
                (db.link.record_table == links_key.record_table) & \
                (db.link.record_id == links_key.record_id)
            rows = db(query).select()
            for r in rows:
                if r.name in keep_names:
                    continue
                Link.from_id(r.id).delete()

        web.login()
        links_keys = [
            LinksKey(
                LinkType.by_code('creator_page').id,
                'creator',
                self._creator.id
            ),
            LinksKey(
                LinkType.by_code('buy_book').id,
                'book',
                self._book.id
            )
        ]
        for links_key in links_keys:
            reset(links_key, 'test_do_not_delete')

            link_type_code = LinkType.from_id(links_key.link_type_id).code

            # Action: get
            data = {
                'action': 'get',
                'link_type_code': link_type_code,
            }
            do_test(links_key, data, ['test_do_not_delete'], {})

            # Action: create
            data = {
                'action': 'create',
                'link_type_code': link_type_code,
                'name': '_test__link_crud_',
                'url': 'http://www.linkcrud.com',
            }
            result = do_test(links_key, data, ['_test__link_crud_'], {})
            link_id = result['rows'][0]['id']

            data = {'action': 'get', 'link_type_code': link_type_code}
            got = do_test(
                links_key,
                data,
                ['test_do_not_delete', '_test__link_crud_'],
                {}
            )

            # Action: get with pk=link_id
            data = {
                'action': 'get',
                'link_type_code': link_type_code,
                'pk': link_id,
            }
            do_test(links_key, data, ['_test__link_crud_'], {})

            # Action: update
            data = {
                'action': 'update',
                'link_type_code': link_type_code,
                'pk': link_id,
                'field': 'name',
                'value': '_test__link_crud_2_',
            }
            do_test(links_key, data, [], {})
            data = {'action': 'get', 'link_type_code': link_type_code}
            do_test(
                links_key,
                data,
                ['test_do_not_delete', '_test__link_crud_2_'],
                {}
            )

            data = {
                'action': 'update',
                'link_type_code': link_type_code,
                'pk': link_id,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(links_key, data, [], {})
            data = {'action': 'get', 'link_type_code': link_type_code}
            got = do_test(
                links_key,
                data,
                ['test_do_not_delete', '_test__link_crud_2_'],
                {}
            )
            self.assertEqual(got['rows'][1]['url'], 'http://www.linkcrud2.com')

            # Action: update, Invalid link_type_code
            data = {
                'action': 'update',
                'link_type_code': '_fake_',
                'pk': 0,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(links_key, data, [], 'Invalid data provided')

            # Action: update, Invalid link_id
            data = {
                'action': 'update',
                'link_type_code': link_type_code,
                'pk': 0,
                'field': 'url',
                'value': 'http://www.linkcrud2.com',
            }
            do_test(links_key, data, [], 'Invalid data provided')

            # Action: update, Invalid url
            data = {
                'action': 'update',
                'link_type_code': link_type_code,
                'pk': link_id,
                'field': 'url',
                'value': '_bad_url_',
            }
            do_test(links_key, data, [], 'url: Enter a valid URL')

            # Action: update, Invalid name
            data = {
                'action': 'update',
                'link_type_code': link_type_code,
                'pk': link_id,
                'field': 'name',
                'value': '',
            }
            do_test(
                links_key,
                data,
                [],
                'name: Enter 1 to 40 characters'
            )

            # Action: move
            data = {
                'action': 'move',
                'link_type_code': link_type_code,
                'pk': link_id,
                'dir': 'up',
            }
            do_test(links_key, data, [], {})
            data = {'action': 'get', 'link_type_code': link_type_code}
            do_test(
                links_key,
                data,
                ['_test__link_crud_2_', 'test_do_not_delete'],
                {}
            )

            # Action: delete
            data = {
                'action': 'delete',
                'link_type_code': link_type_code,
                'pk': link_id,
            }
            do_test(links_key, data, [], {})
            data = {'action': 'get', 'link_type_code': link_type_code}
            do_test(links_key, data, ['test_do_not_delete'], {})

            # Action: delete, Invalid link_id
            data = {
                'action': 'delete',
                'link_type_code': link_type_code,
                'pk': 0,
            }
            do_test(links_key, data, [], 'Invalid data provided')

            reset(links_key, 'test_do_not_delete')

    def test__metadata_crud(self):

        book = self.add(Book, dict(
            name='test__metadata_crud',
            creator_id=self._creator.id,
            book_type_id=BookType.by_name('ongoing').id,
            cc_licence_id=CCLicence.by_code('CC BY').id,
        ))
        db.commit()

        def get_records(table, book_id):
            """Return a book"""
            query = (table.book_id == book_id)
            rows = db(query).select(table.ALL)
            for r in rows:
                self._objects.append(r)
            return rows

        self.assertEqual(len(get_records(db.publication_metadata, book.id)), 0)
        self.assertEqual(len(get_records(db.publication_serial, book.id)), 0)
        self.assertEqual(len(get_records(db.derivative, book.id)), 0)

        web.login()

        # update
        url = '{url}/metadata_crud.json/{bid}'.format(
            url=self.url, bid=str(book.id))
        data = {
            '_action': 'update',
            'publication_metadata_republished': 'repub',
            'publication_metadata_published_type': 'serial',
            'publication_metadata_from_month': '1',
            'publication_metadata_from_year': '1997',
            'publication_metadata_to_month': '12',
            'publication_metadata_to_year': '1998',
            'publication_serial_published_name__0': 'My Story',
            'publication_serial_story_number__0': '1',
            'publication_serial_from_month__0': '1',
            'publication_serial_from_year__0': '2001',
            'publication_serial_to_month__0': '2',
            'publication_serial_to_year__0': '2002',
            'publication_serial_published_name__1': 'My Story',
            'publication_serial_story_number__1': '2',
            'publication_serial_from_month__1': '1',
            'publication_serial_from_year__1': '2005',
            'publication_serial_to_month__1': '2',
            'publication_serial_to_year__1': '2006',
            'is_derivative': 'yes',
            'derivative_title': 'My D Title',
            'derivative_creator': 'Creator Smith',
            'derivative_cc_licence_id': '1',
            'derivative_from_year': '1970',
            'derivative_to_year': '1971',
        }
        web.post(url, data)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')

        metadatas = get_records(db.publication_metadata, book.id)
        self.assertEqual(len(metadatas), 1)
        metadata = metadatas[0]
        self.assertEqual(metadata.republished, True)

        serials = get_records(db.publication_serial, book.id)
        self.assertEqual(len(serials), 2)

        derivatives = get_records(db.derivative, book.id)
        self.assertEqual(len(derivatives), 1)

        # get
        url = '{url}/metadata_crud.json/{bid}'.format(
            url=self.url, bid=str(book.id))
        data = {
            '_action': 'get',
        }
        web.post(url, data)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')
        self.assertTrue('data' in result)

        self.assertEqual(
            sorted(result['data'].keys()),
            sorted([
                'publication_metadata',
                'publication_serial',
                'derivative',
            ])
        )

        # Invalids

        # No action
        url = '{url}/metadata_crud.json/{bid}'.format(
            url=self.url, bid=str(book.id))
        data = {
            '_action': '_fake_',
            'publication_metadata_republished': 'first',
        }
        web.post(url, data)
        result = loads(web.text)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['msg'], 'Invalid data provided')

        # No book_id
        url = '{url}/metadata_crud.json'.format(url=self.url)
        data = {
            '_action': 'get',
        }
        web.post(url, data)
        result = loads(web.text)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['msg'], 'Invalid data provided')

    def test__metadata_text(self):

        book = self.add(Book, dict(
            name='test__metadata_text',
            creator_id=self._creator.id,
        ))

        self.add(PublicationMetadata, dict(
            book_id=book.id,
            republished=True,
            published_type='whole',
            published_name='My Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme',
            from_year=1999,
            to_year=2000,
        ))

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        text = 'This work was originally published in print in 1999-2000 as "My Book" by Acme.'

        meta = BookPublicationMetadata.from_book(book)
        self.assertEqual(str(meta), text)

        web.login()

        url = '{url}/metadata_text.json/{bid}'.format(
            url=self.url, bid=str(book.id))
        web.post(url)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['text'], text)

        # Invalid book id
        url = '{url}/metadata_text.json/{bid}'.format(
            url=self.url, bid=str(9999999))
        web.post(url)
        result = loads(web.text)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['msg'], 'Invalid data provided')

    def test__profile(self):
        self.assertWebTest('/login/profile')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
