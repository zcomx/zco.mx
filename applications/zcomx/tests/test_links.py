#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/links.py

"""
import unittest
from gluon import *
from BeautifulSoup import BeautifulSoup
from applications.zcomx.modules.link_types import LinkType
from applications.zcomx.modules.links import \
    Link, \
    LinkSet, \
    LinkSetKey
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestLink(LocalTestCase):

    def test_parent__init__(self):
        link = Link({'link_type_id': 1})
        self.assertEqual(link.link_type_id, 1)
        self.assertEqual(link.db_table, 'link')


class TestLinkSet(LocalTestCase):

    _creator = None
    _creator_2 = None
    _link = None
    _link_2 = None
    _link_3 = None
    _link_set_key = None
    _links = []
    _links_data = [
        {'name': 'First Site', 'url': 'http://site1.com'},
        {'name': 'Second Site', 'url': 'http://site2.com'},
        {'name': 'Third Site', 'url': 'http://site3.com'},
    ]

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        self._creator = self.add(db.creator, dict(
            email='testcustomlinks@example.com'
        ))

        # Create a second creator with no links
        self._creator_2 = self.add(db.creator, dict(
            email='testcustomlinks_2@example.com'
        ))

        if not self._links:
            for count, link_data in enumerate(self._links_data):
                link = Link(dict(
                    link_type_id=LinkType.by_code('creator_link').id,
                    record_table='creator',
                    record_id=self._creator.id,
                    name=link_data['name'],
                    url=link_data['url'],
                    order_no=count,
                ))
                self._links.append(link)

        self._link_set_key = LinkSetKey.from_link(self._links[0])

    def test____init__(self):
        link_set = LinkSet(self._links)
        self.assertTrue(link_set)

    def test__as_links(self):
        link_set = LinkSet(self._links)
        got = link_set.as_links()
        self.assertEqual(len(got), 3)
        for count, element in enumerate(got):
            soup = BeautifulSoup(str(element))
            anchor = soup.find('a')
            self.assertEqual(anchor.string, self._links[count].name)
            self.assertEqual(anchor['href'], self._links[count].url)
            self.assertEqual(anchor['target'], '_blank')

    def test__from_link_set_key(self):
        links = []
        for link in self._links:
            link_data = link.as_dict()
            link_data['id'] = link.save()
            links.append(Link(link_data))

        for link in links:
            self._objects.append(link)

        link_set = LinkSet.from_link_set_key(self._link_set_key)
        self.assertEqual(len(link_set.links), len(links))

        fields = links[0].keys()
        ignore_fields = ['delete_record', 'update_record']
        for count, link in enumerate(link_set.links):
            for f in fields:
                if f in ignore_fields:
                    continue
                self.assertEqual(link[f], links[count][f])

    def test__represent(self):
        link_set = LinkSet(self._links)

        got = link_set.represent()
        soup = BeautifulSoup(str(got))
        # <ul class="custom_links breadcrumb pipe_delimiter">
        #  <li>
        #   <a href="http://site1.com" target="_blank">
        #    First Site
        #   </a>
        #  </li>
        #  <li>
        #   <a href="http://site2.com" target="_blank">
        #    Second Site
        #   </a>
        #  </li>
        #  <li>
        #   <a href="http://site3.com" target="_blank">
        #    Third Site
        #   </a>
        #  </li>
        # </ul>

        ul = soup.find('ul')
        self.assertEqual(ul['class'], 'custom_links breadcrumb pipe_delimiter')
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 3)
        for count, li in enumerate(lis):
            anchor = li.find('a')
            self.assertEqual(anchor.string, self._links[count]['name'])
            self.assertEqual(anchor['href'], self._links[count]['url'])
            self.assertEqual(anchor['target'], '_blank')

        # Test pre_links and post_links
        pre_links = [
            A('1', _href='http://1.com', _title='pre_link 1'),
            A('2', _href='http://2.com', _title='pre_link 2'),
        ]
        post_links = [
            A('1', _href='http://1.com', _title='post_link 1'),
            A('2', _href='http://2.com', _title='post_link 2'),
        ]

        got = link_set.represent(pre_links=pre_links, post_links=post_links)
        soup = BeautifulSoup(str(got))
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
        link_set_2 = LinkSet([])
        self.assertEqual(link_set_2.represent(), None)

        # Test ul_class parameter
        got = link_set.represent(ul_class='class_1 class_2')
        soup = BeautifulSoup(str(got))
        ul = soup.find('ul')
        self.assertEqual(ul['class'], 'class_1 class_2')


class TestLinkSetKey(LocalTestCase):

    def test____init__(self):
        key = LinkSetKey(1, 'table', 1)
        self.assertTrue(key)

    def test__filter_query(self):
        key = LinkSetKey(111, 'fake_table', 222)
        query = key.filter_query(db.link)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            str(query),
            "(((link.link_type_id = 111) AND (link.record_table = 'fake_table')) AND (link.record_id = 222))"
        )

    def test__from_link(self):
        link = self.add(db.link, dict(
            link_type_id=111,
            record_table='a_table',
            record_id=222,
        ))
        key = LinkSetKey.from_link(link)
        self.assertEqual(key.link_type_id, 111)
        self.assertEqual(key.record_table, 'a_table')
        self.assertEqual(key.record_id, 222)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
