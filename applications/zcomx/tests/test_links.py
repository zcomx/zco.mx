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
    LinkSet, \
    LinkSetKey
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestLinkSet(LocalTestCase):

    _creator = None
    _creator_2 = None
    _link = None
    _link_2 = None
    _link_3 = None
    _link_set_key = None
    _links = [
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

        self._link = self.add(db.link, dict(
            link_type_id=LinkType.by_code('creator_link').id,
            record_table='creator',
            record_id=self._creator.id,
            name=self._links[0]['name'],
            url=self._links[0]['url'],
            order_no=1,
        ))

        self._link_2 = self.add(db.link, dict(
            link_type_id=LinkType.by_code('creator_link').id,
            record_table='creator',
            record_id=self._creator.id,
            name=self._links[1]['name'],
            url=self._links[1]['url'],
            order_no=2,
        ))

        self._link_3 = self.add(db.link, dict(
            link_type_id=LinkType.by_code('creator_link').id,
            record_table='creator',
            record_id=self._creator.id,
            name=self._links[2]['name'],
            url=self._links[2]['url'],
            order_no=2,
        ))

        self._link_set_key = LinkSetKey.from_link(self._link)

    def _ordered_records(self):
        query = \
            (db.link.link_type_id == LinkType.by_code('creator_link').id) & \
            (db.link.record_table == 'creator') &\
            (db.link.record_id == self._creator['id'])
        return db(query).select(
            db.link.ALL,
            orderby=db.link.order_no
        )

    def _ordered_ids(self):
        return [x['id'] for x in self._ordered_records()]

    def _order_nos(self):
        return [x['order_no'] for x in self._ordered_records()]

    def test____init__(self):
        link_set = LinkSet(self._link_set_key)
        self.assertTrue(link_set)

    def test__filter_query(self):
        link_set = LinkSet(self._link_set_key)
        query = link_set.filter_query()
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            str(query),
            "(((link.link_type_id = {lid}) AND (link.record_table = 'creator')) AND (link.record_id = {bid}))".format(
                lid=self._link_set_key.link_type_id,
                bid=self._creator.id
            )
        )

    def test__links(self):
        link_set = LinkSet(self._link_set_key)
        got = link_set.links()
        self.assertEqual(len(got), 3)

        for count, element in enumerate(got):
            soup = BeautifulSoup(str(element))
            anchor = soup.find('a')
            self.assertEqual(anchor.string, self._links[count]['name'])
            self.assertEqual(anchor['href'], self._links[count]['url'])
            self.assertEqual(anchor['target'], '_blank')

        soup = BeautifulSoup(str(got[0]))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'First Site')
        self.assertEqual(anchor['href'], 'http://site1.com')
        self.assertEqual(anchor['target'], '_blank')

        soup = BeautifulSoup(str(got[1]))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Second Site')
        self.assertEqual(anchor['href'], 'http://site2.com')
        self.assertEqual(anchor['target'], '_blank')

        soup = BeautifulSoup(str(got[2]))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Third Site')
        self.assertEqual(anchor['href'], 'http://site3.com')
        self.assertEqual(anchor['target'], '_blank')

    def test__move_link(self):
        link_set = LinkSet(self._link_set_key)

        # Set up data
        original = self._ordered_ids()
        link_ids = [original[0], original[1], original[2]]
        link_set.reorder(link_ids=link_ids)
        got = self._ordered_ids()
        self.assertEqual(got, original)

        # Move top link up, should not change
        link_set.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got, original)

        # Move bottom link down, should not change
        link_set.move_link(original[2], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got, original)

        # Move top link down
        link_set.move_link(original[0], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got, [original[1], original[0], original[2]])

        # Move top link down again
        link_set.move_link(original[0], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got, [original[1], original[2], original[0]])

        # Move top link up
        link_set.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got, [original[1], original[0], original[2]])

        # Move top link up again, back to start
        link_set.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got, original)

    def test__reorder(self):
        link_set = LinkSet(self._link_set_key)

        original = self._ordered_ids()

        link_set.reorder()
        got = self._ordered_ids()
        self.assertEqual(got, original)
        self.assertEqual(self._order_nos(), [1, 2, 3])

        link_ids = [original[2], original[1], original[0]]
        link_set.reorder(link_ids=link_ids)
        got = self._ordered_ids()
        self.assertEqual(got, link_ids)
        self.assertEqual(self._order_nos(), [1, 2, 3])

        # Test that holes are closed.
        link_ids = [original[0], original[1], original[2]]
        link_set.reorder(link_ids=link_ids)

        for x in self._ordered_records():
            x.update_record(order_no=db.link.order_no * 2)
        db.commit()
        self.assertEqual(self._order_nos(), [2, 4, 6])
        link_set.reorder(link_ids=link_ids)
        self.assertEqual(self._order_nos(), [1, 2, 3])

    def test__represent(self):
        link_set = LinkSet(self._link_set_key)

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
        link_set_2 = LinkSet(
            LinkSetKey(
                LinkType.by_code('creator_link').id,
                record_table='creator',
                record_id=self._creator_2.id
            )
        )
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
