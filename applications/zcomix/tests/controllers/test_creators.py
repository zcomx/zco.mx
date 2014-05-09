#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/creators.py

"""
import unittest
from applications.zcomix.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'books': [
            'Released',
            'Ongoing',
            '<div class="grid_section">'
        ],
        'creator': '<div id="creator_page">',
        'default': 'zcomix.com is a not-for-profit comic-sharing website',
    }
    url = '/zcomix/creators'

    def test__books(self):
        self.assertTrue(web.test(
            '{url}/books.load'.format(url=self.url),
            self.titles['books']
        ))

    def test__creator(self):
        creators = db(db.creator.auth_user_id > 0).select(
            db.creator.ALL,
            orderby=db.creator.id,
            limitby=(0, 1)
        )
        if not creators:
            self.fail('No creator found in db.')
        creator = creators[0]
        auth_user = db(db.auth_user.id == creator.auth_user_id).select().first()

        # Without a creator id, should revert to default page.
        self.assertTrue(web.test(
            '{url}/creator'.format(url=self.url),
            self.titles['default']
        ))

        self.assertTrue(web.test('{url}/creator/{id}'.format(
            url=self.url, id=creator.id),
            self.titles['creator']
        ))

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['default']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
