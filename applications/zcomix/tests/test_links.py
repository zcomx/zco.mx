#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/links.py

"""
import unittest
from gluon import *
from gluon.storage import Storage
from BeautifulSoup import BeautifulSoup
from applications.zcomix.modules.links import \
        CustomLinks, \
        ReorderLink
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904

class TestCustomLinks(LocalTestCase):
    _creator = None
    _creator_2 = None
    _creator_to_links = []
    _links = []

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        creator_id = db.creator.insert(email='testcustomlinks@example.com')
        db.commit()
        cls._creator = db(db.creator.id == creator_id).select(
                db.creator.ALL).first()
        for count in range(0, 3):
            link_id = db.link.insert(
                    name='test_custom_links',
                    url='http://www.test_custom_links.com',
                    title=str(count),
                    )
            db.commit()
            query = (db.link.id == link_id)
            cls._links.append(db(query).select(db.link.ALL).first())
            creator_to_link_id = db.creator_to_link.insert(
                    link_id=link_id,
                    creator_id=creator_id,
                    order_no = count + 1,
                    )
            db.commit()
            query = (db.creator_to_link.id == creator_to_link_id)
            cls._creator_to_links.append(
                    db(query).select(db.creator_to_link.ALL).first())

        # Create a second creator with no links
        creator_2_id = db.creator.insert(email='testcustomlinks@example.com')
        db.commit()
        cls._creator_2 = db(db.creator.id == creator_2_id).select(
                db.creator.ALL).first()

    @classmethod
    def tearDownClass(cls):
        for creator_to_link in cls._creator_to_links:
            query = (db.creator_to_link.id == creator_to_link['id'])
            db(query).delete()
            db.commit()

        for link in cls._links:
            query = (db.link.id == link['id'])
            db(query).delete()
            db.commit()

        query = (db.creator.id == cls._creator['id'])
        db(query).delete()
        db.commit()
        query = (db.creator.id == cls._creator_2['id'])
        db(query).delete()
        db.commit()

    def _ordered_records(self):
        query = (db.creator_to_link.creator_id == self._creator['id'])
        return db(query).select(db.creator_to_link.ALL,
                orderby=db.creator_to_link.order_no)

    def _ordered_ids(self):
        return [x['id'] for x in self._ordered_records()]

    def _order_nos(self):
        return [x['order_no'] for x in self._ordered_records()]


    def test____init__(self):
        links = CustomLinks(db.creator, self._creator['id'])
        self.assertTrue(links)

        self.assertEqual(links.to_link_tablename, 'creator_to_link')
        self.assertEqual(links.to_link_table, db['creator_to_link'])
        self.assertEqual(links.join_to_link_fieldname, 'creator_id')
        self.assertEqual(links.join_to_link_field,
                db.creator_to_link['creator_id'])

    def test__attach(self):
        links = CustomLinks(db.creator, self._creator['id'])

        form = crud.update(db.creator, self._creator['id'])

        links.attach(form, 'creator_wikipedia__row',
                edit_url='http://test.com')
        soup = BeautifulSoup(str(form))
        trs = soup.findAll('tr')
        tr_ids = [x['id'] for x in trs]
        self.assertTrue('creator_wikipedia__row' in tr_ids)
        self.assertTrue('creator_custom_links__row' in tr_ids)
        self.assertEqual(
                tr_ids.index('creator_custom_links__row'),
                tr_ids.index('creator_wikipedia__row') + 1
                )

    def test__links(self):
        links = CustomLinks(db.creator, self._creator['id'])

        got = links.links()
        self.assertEqual(len(got), 3)
        # Eg <a data-w2p_disable_with="default"
        #       href="http://www.test_custom_links.com" target="_blank"
        #       title="Test Custom Links">test_custom_links</a>
        for count, got_link in enumerate(got):
            soup = BeautifulSoup(str(got_link))
            anchor = soup.find('a')
            self.assertEqual(anchor['href'], 'http://www.test_custom_links.com')
            self.assertEqual(anchor['title'], str(count))

        links = CustomLinks(db.creator, self._creator_2['id'])
        self.assertEqual(links.links(), [])

    def test__move_link(self):
        links = CustomLinks(db.creator, self._creator['id'])

        # Set up data
        original = self._ordered_ids()
        link_ids = [original[0], original[1], original[2]]
        links.reorder(link_ids=link_ids)
        got = self._ordered_ids()
        self.assertEqual(got, original)

        # Move top link up, should not change
        links.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got, original)

        # Move bottom link down, should not change
        links.move_link(original[2], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got, original)

        # Move top link down
        links.move_link(original[0], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got,
                 [original[1], original[0], original[2]])

        # Move top link down again
        links.move_link(original[0], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got,
                 [original[1], original[2], original[0]])

        # Move top link up
        links.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got,
                 [original[1], original[0], original[2]])

        # Move top link up again, back to start
        links.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got, original)

    def test__reorder(self):
        links = CustomLinks(db.creator, self._creator['id'])

        original = self._ordered_ids()

        links.reorder()
        got = self._ordered_ids()
        self.assertEqual(got, original)
        self.assertEqual(self._order_nos(), [1, 2, 3])

        link_ids = [original[2], original[1], original[0]]
        links.reorder(link_ids=link_ids)
        got = self._ordered_ids()
        self.assertEqual(got, link_ids)
        self.assertEqual(self._order_nos(), [1, 2, 3])

        # Test that holes are closed.
        link_ids = [original[0], original[1], original[2]]
        links.reorder(link_ids=link_ids)

        for x in self._ordered_records():
            x.update_record(order_no=db.creator_to_link.order_no * 2)
        db.commit()
        self.assertEqual(self._order_nos(), [2, 4, 6])
        links.reorder(link_ids=link_ids)
        self.assertEqual(self._order_nos(), [1, 2, 3])

    def test__represent(self):
        links = CustomLinks(db.creator, self._creator['id'])
        got = links.represent()
        soup = BeautifulSoup(str(got))
        ul = soup.find('ul')
        self.assertEqual(ul['class'], 'list-inline custom_links')
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 3)
        for count, li in enumerate(lis):
            anchor = li.find('a')
            self.assertEqual(anchor['title'], str(count))

        # Test pre_links and post_links
        pre_links = [
            A('1', _href='http://1.com', _title='pre_link 1'),
            A('2', _href='http://2.com', _title='pre_link 2'),
            ]
        post_links = [
            A('1', _href='http://1.com', _title='post_link 1'),
            A('2', _href='http://2.com', _title='post_link 2'),
            ]
        links = CustomLinks(db.creator, self._creator['id'])
        got = links.represent(pre_links=pre_links, post_links=post_links)
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
        links = CustomLinks(db.creator, self._creator_2['id'])
        self.assertEqual(links.represent(), None)



class TestReorderLink(LocalTestCase):

    _creator = None
    _creator_2 = None
    _creator_to_links = []
    _links = []

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        creator_id = db.creator.insert(email='testreorderlinke@example.com')
        db.commit()
        cls._creator = db(db.creator.id == creator_id).select(
                db.creator.ALL).first()
        for count in range(0, 3):
            link_id = db.link.insert(
                    name='test_reorder_link',
                    url='http://www.test_reorder_link.com',
                    title=str(count),
                    )
            db.commit()
            query = (db.link.id == link_id)
            cls._links.append(db(query).select(db.link.ALL).first())
            creator_to_link_id = db.creator_to_link.insert(
                    link_id=link_id,
                    creator_id=creator_id,
                    order_no = count + 1,
                    )
            db.commit()
            query = (db.creator_to_link.id == creator_to_link_id)
            cls._creator_to_links.append(
                    db(query).select(db.creator_to_link.ALL).first())

        # Create a second creator with no links
        creator_2_id = db.creator.insert(email='testreorderlinke@example.com')
        db.commit()
        cls._creator_2 = db(db.creator.id == creator_2_id).select(
                db.creator.ALL).first()

    @classmethod
    def tearDownClass(cls):
        for creator_to_link in cls._creator_to_links:
            query = (db.creator_to_link.id == creator_to_link['id'])
            db(query).delete()
            db.commit()

        for link in cls._links:
            query = (db.link.id == link['id'])
            db(query).delete()
            db.commit()

        query = (db.creator.id == cls._creator['id'])
        db(query).delete()
        db.commit()
        query = (db.creator.id == cls._creator_2['id'])
        db(query).delete()
        db.commit()


    def test____init__(self):
        link = ReorderLink(db.creator_to_link)
        self.assertTrue(link)
        self.assertEqual(link.direction, 'up')
        self.assertEqual(link.label, 'up')
        self.assertEqual(link.header, 'Up')

        link = ReorderLink(db.creator_to_link, direction='down')
        self.assertEqual(link.direction, 'down')
        self.assertEqual(link.label, 'dn')
        self.assertEqual(link.header, 'Dn')

        link = ReorderLink(db.creator_to_link, direction='fake')
        self.assertEqual(link.direction, 'up')
        self.assertEqual(link.label, 'up')
        self.assertEqual(link.header, 'Up')

    def test__get_max_order_no(self):
        link = ReorderLink(db.creator_to_link)
        self.assertEqual(link._max_order_no, None)

        row = {}
        max_order_no = link.get_max_order_no(row)
        self.assertEqual(max_order_no, link._max_order_no)
        self.assertEqual(max_order_no, None)

        link._max_order_no = None
        data = Storage({'id': self._creator_to_links[0].id, 'order_no': 1, 'creator_id': self._creator.id})
        row = {'creator_to_link': data}
        max_order_no = link.get_max_order_no(row)
        self.assertEqual(max_order_no, link._max_order_no)
        self.assertEqual(max_order_no, 3)

    def test__grid_body_func(self):
        empty_span = '<span>-</span>'
        link = ReorderLink(db.creator_to_link)

        # No row data, should be empty
        row = {}
        self.assertEqual(str(link.grid_body_func(row)), empty_span)

        # No order_no, should be empty
        data = Storage({'id': 123})
        row = {'creator_to_link': data}
        self.assertEqual(str(link.grid_body_func(row)), empty_span)

        # Order_no 1, direction 'up', empty
        link = ReorderLink(db.creator_to_link, direction='up')
        data = Storage({'order_no': 1})
        row = {'creator_to_link': data}
        self.assertEqual(str(link.grid_body_func(row)), empty_span)

        # Order_no max, direction 'down', empty
        link = ReorderLink(db.creator_to_link, direction='down')
        data = Storage({'id': 1, 'order_no': 999})
        row = {'creator_to_link': data}
        self.assertEqual(str(link.grid_body_func(row)), empty_span)

        # Order no 1, direction 'down', down arrow
        link = ReorderLink(db.creator_to_link, direction='down')
        data = Storage({'id': self._creator_to_links[0].id, 'order_no': 1, 'creator_id': self._creator.id})
        row = {'creator_to_link': data}
        soup = BeautifulSoup(str(link.grid_body_func(row)))
        anchor = soup.find('a')
        span = anchor.find('span')
        self.assertEqual(anchor['href'],
            '/profile/order_no_handler/creator_to_link/{id}/down?next=None'.format(id=self._creator_to_links[0].id)
            )
        self.assertEqual(span['class'], 'glyphicon glyphicon-arrow-down')
        self.assertEqual(span['title'], 'down')

        # Order no max, direction 'up', up arrow
        link = ReorderLink(db.creator_to_link, direction='up')
        data = Storage({'id': 1, 'order_no': 999})
        row = {'creator_to_link': data}
        soup = BeautifulSoup(str(link.grid_body_func(row)))
        anchor = soup.find('a')
        span = anchor.find('span')
        self.assertEqual(anchor['href'],
            '/profile/order_no_handler/creator_to_link/1/up?next=None'
            )
        self.assertEqual(span['class'], 'glyphicon glyphicon-arrow-up')
        self.assertEqual(span['title'], 'up')

    def test__links_dict(self):
        link = ReorderLink(db.creator_to_link)
        links_dict = link.links_dict()
        self.assertEqual(links_dict['header'], 'Up')
        self.assertEqual(links_dict['body'], link.grid_body_func)

        link = ReorderLink(db.creator_to_link, direction='down')
        links_dict = link.links_dict()
        self.assertEqual(links_dict['header'], 'Dn')
        self.assertEqual(links_dict['body'], link.grid_body_func)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
