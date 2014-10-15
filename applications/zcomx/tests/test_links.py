#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/links.py

"""
import unittest
from gluon import *
from BeautifulSoup import BeautifulSoup
from applications.zcomx.modules.links import CustomLinks
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestCustomLinks(LocalTestCase):
    _creator = None
    _creator_2 = None
    _creator_to_links = []
    _links = []
    _cls_objects = []

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._creator = cls.add(db.creator, dict(
            email='testcustomlinks@example.com'
        ))

        for count in range(0, 3):
            link = cls.add(db.link, dict(
                name='test_custom_links',
                url='http://www.test_custom_links.com',
                title=str(count),
            ))
            cls._links.append(link)
            creator_to_link = cls.add(db.creator_to_link, dict(
                link_id=link.id,
                creator_id=cls._creator.id,
                order_no=count + 1,
            ))
            cls._creator_to_links.append(creator_to_link)

        # Create a second creator with no links
        cls._creator_2 = cls.add(db.creator, dict(
            email='testcustomlinks_2@example.com'
        ))

        # objects need to be maintained for all tests.
        cls._cls_objects = list(cls._objects)
        cls._objects = []

    @classmethod
    def tearDownClass(cls):
        for obj in cls._cls_objects:
            if hasattr(obj, 'remove'):
                cls._remove_comments_for(cls, obj)
                obj.remove()
            elif hasattr(obj, 'delete_record'):
                obj.delete_record()
                db = current.app.db
                db.commit()

    def _ordered_records(self):
        query = (db.creator_to_link.creator_id == self._creator['id'])
        return db(query).select(
            db.creator_to_link.ALL,
            orderby=db.creator_to_link.order_no
        )

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
        self.assertEqual(
            links.join_to_link_field,
            db.creator_to_link['creator_id']
        )

    def test__attach(self):
        links = CustomLinks(db.creator, self._creator['id'])

        form = crud.update(db.creator, self._creator['id'])

        links.attach(
            form,
            'creator_wikipedia__row',
            edit_url='http://test.com'
        )
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
            self.assertEqual(
                anchor['href'],
                'http://www.test_custom_links.com'
            )
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
        self.assertEqual(got, [original[1], original[0], original[2]])

        # Move top link down again
        links.move_link(original[0], direction='down')
        got = self._ordered_ids()
        self.assertEqual(got, [original[1], original[2], original[0]])

        # Move top link up
        links.move_link(original[0], direction='up')
        got = self._ordered_ids()
        self.assertEqual(got, [original[1], original[0], original[2]])

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
        self.assertEqual(ul['class'], 'custom_links breadcrumb')
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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
