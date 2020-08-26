#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/links.py

"""
import unittest
from gluon import *
from bs4 import BeautifulSoup
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.links import \
    BaseLinkSet, \
    Link, \
    Links, \
    LinksKey, \
    LinkType
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubLinkSet(BaseLinkSet):
    link_type_code = 'dub_link'

    def link_type(self):
        return LinkType({
            'code': 'dub_link',
            'label': 'My Links',
        })

    def links(self):
        return Links([
            Link({
                'name': 'link 1',
                'url': 'url 1',
            }),
            Link({
                'name': 'link 2',
                'url': 'url 2',
            }),
        ])


class DubLinkSet2(BaseLinkSet):
    link_type_code = 'buy_book'


class TestBaseLinkSet(LocalTestCase):

    def test____init__(self):
        book = Book({'name': 'My Book'})
        link_set = DubLinkSet(book)
        self.assertTrue(link_set)

    def test____len__(self):
        book = Book({'name': 'My Book'})
        link_set = DubLinkSet(book)
        self.assertTrue(len(link_set), 2)

        link_set = DubLinkSet(book, pre_links=[1, 2])
        self.assertTrue(len(link_set), 4)

        link_set = DubLinkSet(book, post_links=[1, 2, 3])
        self.assertTrue(len(link_set), 5)

        link_set = DubLinkSet(book, pre_links=[1, 2], post_links=[1, 2, 3])
        self.assertTrue(len(link_set), 7)

    def test__label(self):
        book = Book({'name': 'My Book'})
        link_set = DubLinkSet(book)
        self.assertTrue(link_set.label(), 'My Links')

    def test__link_type(self):
        book = Book({'name': 'My Book'})
        link_set = DubLinkSet2(book)
        expect = LinkType.by_code(DubLinkSet2.link_type_code)
        self.assertEqual(link_set.link_type(), expect)

        # Test cache
        fake_link_type = LinkType({'code': 'fake'})
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        link_set._link_type = fake_link_type
        self.assertEqual(link_set.link_type(), fake_link_type)

    def test__links(self):
        book_row = self.add(Book, dict(
            name='test__links',
        ))

        book = Book(book_row)

        self.add(Link, dict(
            link_type_id=LinkType.by_code(DubLinkSet2.link_type_code).id,
            record_table='book',
            record_id=book.id,
            order_no=1,
        ))

        link_2 = self.add(Link, dict(
            link_type_id=LinkType.by_code(DubLinkSet2.link_type_code).id,
            record_table='book',
            record_id=book.id,
            order_no=2,
        ))

        link_set = DubLinkSet2(book)
        got = link_set.links()
        self.assertTrue(isinstance(got, Links))
        self.assertEqual(len(got.links), 2)

        # Test cache
        fake_links = Links([link_2])
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        link_set._links = fake_links
        got = link_set.links()
        self.assertTrue(isinstance(got, Links))
        self.assertEqual(len(got.links), 1)

    def test__represent(self):
        book = Book({'name': 'My Book'})
        link_set = DubLinkSet(book)
        got = link_set.represent()
        soup = BeautifulSoup(str(got), 'html.parser')
        # <ul class="custom_links breadcrumb pipe_delimiter">
        #  <li>
        #   <a href="url 1" target="_blank" rel="noopener noreferrer">
        #    link 1
        #   </a>
        #  </li>
        #  <li>
        #   <a href="url 2" target="_blank" rel="noopener noreferrer">
        #    link 2
        #   </a>
        #  </li>
        # </ul>

        ul = soup.find('ul')
        self.assertEqual(ul['class'], ['custom_links', 'breadcrumb', 'pipe_delimiter'])
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 2)
        for count, li in enumerate(lis):
            anchor = li.find('a')
            self.assertEqual(anchor.string, 'link {c}'.format(c=count + 1))
            self.assertEqual(anchor['href'], 'url {c}'.format(c=count + 1))
            self.assertEqual(anchor['target'], '_blank')
            self.assertEqual(anchor['rel'], ['noopener', 'noreferrer'])

        # Test pre_links and post_links
        pre_links = [
            A('1', _href='http://1.com', _title='pre_link 1'),
            A('2', _href='http://2.com', _title='pre_link 2'),
        ]
        post_links = [
            A('3', _href='http://3.com', _title='post_link 1'),
            A('4', _href='http://4.com', _title='post_link 2'),
        ]

        link_set = DubLinkSet(book, pre_links=pre_links, post_links=post_links)
        got = link_set.represent()
        soup = BeautifulSoup(str(got), 'html.parser')
        ul = soup.find('ul')
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 6)
        self.assertEqual(
            [x.find('a').string for x in lis],
            ['1', '2', 'link 1', 'link 2', '3', '4']
        )


class TestLink(LocalTestCase):

    def test_parent__init__(self):
        link = Link({'link_type_id': 1})
        self.assertEqual(link.link_type_id, 1)
        self.assertEqual(link.db_table, 'link')


class TestLinks(LocalTestCase):

    _creator = None
    _creator_2 = None
    _link = None
    _link_2 = None
    _link_3 = None
    _links_key = None
    _links = []
    _links_data = [
        {'name': 'First Site', 'url': 'http://site1.com'},
        {'name': 'Second Site', 'url': 'http://site2.com'},
        {'name': 'Third Site', 'url': 'http://site3.com'},
    ]

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        self._creator = self.add(Creator, dict(
            email='testcustomlinks@example.com'
        ))

        # Create a second creator with no links
        self._creator_2 = self.add(Creator, dict(
            email='testcustomlinks_2@example.com'
        ))

        self._links = []
        for count, link_data in enumerate(self._links_data):
            link = Link.from_add(dict(
                link_type_id=LinkType.by_code('creator_page').id,
                record_table='creator',
                record_id=self._creator.id,
                name=link_data['name'],
                url=link_data['url'],
                order_no=count,
            ))
            self._links.append(link)
            self._objects.append(link)

        self._links_key = LinksKey.from_link(self._links[0])

    def test____init__(self):
        links = Links(self._links)
        self.assertTrue(links)

    def test____len__(self):
        links = Links(self._links)
        self.assertEqual(len(links), len(self._links))

    def test__as_links(self):
        links = Links(self._links)
        got = links.as_links()
        self.assertEqual(len(got), 3)
        for count, element in enumerate(got):
            soup = BeautifulSoup(str(element), 'html.parser')
            anchor = soup.find('a')
            self.assertEqual(anchor.string, self._links[count].name)
            self.assertEqual(anchor['href'], self._links[count].url)
            self.assertEqual(anchor['target'], '_blank')
            self.assertEqual(anchor['rel'], ['noopener', 'noreferrer'])

    def test__from_links_key(self):
        links = Links.from_links_key(self._links_key)
        self.assertEqual(len(links.links), len(self._links))

        fields = list(self._links[0].keys())
        ignore_fields = ['delete_record', 'update_record']
        for count, link in enumerate(links.links):
            for f in fields:
                if f in ignore_fields:
                    continue
                self.assertEqual(link[f], self._links[count][f])

    def test__represent(self):
        links = Links(self._links)

        got = links.represent()
        soup = BeautifulSoup(str(got), 'html.parser')
        # <ul class="custom_links breadcrumb pipe_delimiter">
        #  <li>
        #   <a href="http://site1.com" target="_blank" rel="noopener noreferrer">
        #    First Site
        #   </a>
        #  </li>
        #  <li>
        #   <a href="http://site2.com" target="_blank" rel="noopener noreferrer">
        #    Second Site
        #   </a>
        #  </li>
        #  <li>
        #   <a href="http://site3.com" target="_blank" rel="noopener noreferrer">
        #    Third Site
        #   </a>
        #  </li>
        # </ul>

        ul = soup.find('ul')
        self.assertEqual(ul['class'], ['custom_links', 'breadcrumb', 'pipe_delimiter'])
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 3)
        for count, li in enumerate(lis):
            anchor = li.find('a')
            self.assertEqual(anchor.string, self._links[count]['name'])
            self.assertEqual(anchor['href'], self._links[count]['url'])
            self.assertEqual(anchor['target'], '_blank')
            self.assertEqual(anchor['rel'], ['noopener', 'noreferrer'])

        # Test pre_links and post_links
        pre_links = [
            A('1', _href='http://1.com', _title='pre_link 1'),
            A('2', _href='http://2.com', _title='pre_link 2'),
        ]
        post_links = [
            A('1', _href='http://1.com', _title='post_link 1'),
            A('2', _href='http://2.com', _title='post_link 2'),
        ]

        got = links.represent(pre_links=pre_links, post_links=post_links)
        soup = BeautifulSoup(str(got), 'html.parser')
        ul = soup.find('ul')
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 7)
        pres = lis[:2]
        for count, li in enumerate(pres, 1):
            anchor = li.find('a')
            self.assertEqual(anchor['title'], 'pre_link {c}'.format(c=count))

        posts = lis[-2:]
        for count, li in enumerate(posts, 1):
            anchor = li.find('a')
            self.assertEqual(anchor['title'], 'post_link {c}'.format(c=count))

        # Test no links
        links_2 = Links([])
        self.assertEqual(links_2.represent(), None)

        # Test ul_class parameter
        got = links.represent(ul_class='class_1 class_2')
        soup = BeautifulSoup(str(got), 'html.parser')
        ul = soup.find('ul')
        self.assertEqual(ul['class'], ['class_1', 'class_2'])


class TestLinksKey(LocalTestCase):

    def test____init__(self):
        key = LinksKey(1, 'table', 1)
        self.assertTrue(key)

    def test__filter_query(self):
        key = LinksKey(111, 'fake_table', 222)
        query = key.filter_query(db.link)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            str(query),
            """((("link"."link_type_id" = 111) AND ("link"."record_table" = 'fake_table')) AND ("link"."record_id" = 222))"""
        )

    def test__from_link(self):
        link = self.add(Link, dict(
            link_type_id=111,
            record_table='a_table',
            record_id=222,
        ))
        key = LinksKey.from_link(link)
        self.assertEqual(key.link_type_id, 111)
        self.assertEqual(key.record_table, 'a_table')
        self.assertEqual(key.record_id, 222)


class TestLinkType(LocalTestCase):

    def test_parent__init__(self):
        link_type = LinkType({'code': 'fake_code'})
        self.assertEqual(link_type.db_table, 'link_type')
        self.assertEqual(link_type.code, 'fake_code')

    def test__by_code(self):
        link_type = LinkType.by_code('buy_book')
        self.assertTrue(isinstance(link_type, LinkType))
        self.assertEqual(link_type.code, 'buy_book')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
