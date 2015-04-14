#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/html/meta.py

"""
import copy
import unittest
from applications.zcomx.modules.html.meta import \
    BaseMetaPreparer, \
    MetadataFactory, \
    OpenGraphBookMetaPreparer, \
    OpenGraphCreatorMetaPreparer, \
    OpenGraphMetaPreparer, \
    TwitterBookMetaPreparer, \
    TwitterCreatorMetaPreparer, \
    TwitterMetaPreparer, \
    html_metadata_from_records
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import \
    html_metadata as site_metadata

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904

METADATA = {
    'book': {
        'name': '_book_name_',
        'type': '_book_type_',
        'url': '_book_url_',
        'image_url': '_book_image_url_',
        'creator_name': '_book_creator_name_',
        'creator_twitter': '_book_creator_twitter_',
        'description': '_book_description_',
        'fake': '_book_fake_',                       # Ignored gracefully
    },
    'creator': {
        'name': '_creator_name_',
        'type': '_creator_type_',
        'url': '_creator_url_',
        'image_url': '_creator_image_url_',
        'description': '_creator_description_',
        'twitter': '_creator_twitter_',
        'fake': '_creator_fake_',                    # Ignored gracefully

    },
    'site': {
        'title': '_site_title_',
        'type': '_site_type_',
        'url': '_site_url_',
        'icon': '_site_icon_',
        'name': '_site_name_',
        'description': '_site_description_',
        'twitter': '_site_twitter_',
        'fake': '_site_fake_',                       # Ignored gracefully
    },
    'fake': {'k': 'v'},                              # Ignored gracefully
}


class TestBaseMetaPreparer(LocalTestCase):

    def test____init__(self):
        preparer = BaseMetaPreparer({})
        self.assertTrue(preparer)

    def test__as_property_content(self):
        # Call using class
        self.assertEqual(BaseMetaPreparer.as_property_content({}), {})
        # Call using instance
        preparer = BaseMetaPreparer({})
        self.assertEqual(preparer.as_property_content({}), {})

        data = {
            'prop1': 'cont1',
            'prop2': 'cont2',
        }

        expect = {
            'prop1': {'property': 'prop1', 'content': 'cont1'},
            'prop2': {'property': 'prop2', 'content': 'cont2'},
        }
        self.assertEqual(preparer.as_property_content(data), expect)

    def test__formatter(self):
        func = BaseMetaPreparer.formatter()
        self.assertEqual(func('aaa'), 'aaa')

    def test__prepared(self):
        preparer = BaseMetaPreparer({})
        self.assertRaises(NotImplementedError, preparer.prepared)

    def test__set_data(self):
        preparer = BaseMetaPreparer({})
        self.assertRaises(NotImplementedError, preparer.set_data)


class TestMetadataFactory(LocalTestCase):

    def test____init__(self):
        meta_factory = MetadataFactory([''], {})
        self.assertTrue(meta_factory)
        self.assertEqual(
            sorted(meta_factory.class_lookup.keys()),
            ['opengraph', 'twitter']
        )

    def test__classes(self):
        meta_factory = MetadataFactory([], None)
        self.assertEqual(meta_factory.classes(), [])
        html_metadata = {}

        tests = [
            # (codes, page_type, expect)
            ([], 'site', []),
            ([], 'creator', []),
            ([], 'book', []),
            (['opengraph'], 'site', [OpenGraphMetaPreparer]),
            (['twitter'], 'site', [TwitterMetaPreparer]),
            (
                ['opengraph', 'twitter'], 'site',
                [OpenGraphMetaPreparer, TwitterMetaPreparer]
            ),
            (['opengraph'], 'creator', [OpenGraphCreatorMetaPreparer]),
            (['opengraph'], 'book', [OpenGraphBookMetaPreparer]),
            (
                ['opengraph', 'twitter'], 'book',
                [OpenGraphBookMetaPreparer, TwitterBookMetaPreparer]
            ),
        ]

        for t in tests:
            meta_factory = MetadataFactory(t[0], html_metadata, page_type=t[1])
            self.assertEqual(meta_factory.classes(), t[2])

    def test__instantiated_preparers(self):
        meta_factory = MetadataFactory([], None)
        self.assertEqual(meta_factory.instantiated_preparers(), [])

        html_metadata = {
            'book': {},
            'creator': {},
            'site': {},
        }

        meta_factory = MetadataFactory(['opengraph', 'twitter'], html_metadata)
        preparers = meta_factory.instantiated_preparers()
        self.assertEqual(len(preparers), 2)
        self.assertTrue(isinstance(preparers[0], OpenGraphMetaPreparer))
        self.assertTrue(isinstance(preparers[1], TwitterMetaPreparer))

        meta_factory = MetadataFactory(
            ['opengraph', 'twitter'], html_metadata, page_type='book')
        preparers = meta_factory.instantiated_preparers()
        self.assertEqual(len(preparers), 2)
        self.assertTrue(isinstance(preparers[0], OpenGraphBookMetaPreparer))
        self.assertTrue(isinstance(preparers[1], TwitterBookMetaPreparer))

        meta_factory = MetadataFactory(
            ['opengraph', 'twitter'], html_metadata, page_type='creator')
        preparers = meta_factory.instantiated_preparers()
        self.assertEqual(len(preparers), 2)
        self.assertTrue(isinstance(preparers[0], OpenGraphCreatorMetaPreparer))
        self.assertTrue(isinstance(preparers[1], TwitterCreatorMetaPreparer))

    def test__metadata(self):
        meta_factory = MetadataFactory([], None)
        self.assertEqual(meta_factory.metadata(), {})

        html_metadata = {
            'book': {},
            'creator': {},
            'site': {
                'title': 'zco.mx',
                'type': 'site',
                'url': 'http://zco.mx',
                'icon': 'http://zco.mx/icon.png',
                'name': 'zco.mx',
                'description': 'The zco.mx website',
                'twitter': 'zcomx',
            },
        }

        meta_factory = MetadataFactory(['opengraph', 'twitter'], html_metadata)
        self.assertEqual(
            meta_factory.metadata(),
            {
                'og:description': {
                    'content': 'The zco.mx website',
                    'property': 'og:description'
                },
                'og:image': {
                    'content': 'http://zco.mx/icon.png',
                    'property': 'og:image'
                },
                'og:site_name': {
                    'content': 'zco.mx',
                    'property': 'og:site_name'
                },
                'og:title': {'content': 'zco.mx', 'property': 'og:title'},
                'og:type': {'content': 'site', 'property': 'og:type'},
                'og:url': {'content': 'http://zco.mx', 'property': 'og:url'},
                'twitter:card': 'summary_large_image',
                'twitter:creator': 'zcomx',
                'twitter:description': 'The zco.mx website',
                'twitter:image:src': 'http://zco.mx/icon.png',
                'twitter:site': 'zcomx',
                'twitter:title': 'zco.mx'
            }
        )

class TestOpenGraphBookMetaPreparer(LocalTestCase):

    def test__set_data(self):
        metadata = copy.deepcopy(METADATA)
        expect = {
            'og:title': '_book_name_',
            'og:type': '_book_type_',
            'og:url': '_book_url_',
            'og:image': '_book_image_url_',
            'og:site_name': '_site_name_',
            'og:description': '_book_description_',
        }
        preparer = OpenGraphBookMetaPreparer(metadata)
        self.assertEqual(preparer.set_data(), expect)

        # Test no image
        metadata_no_img = copy.deepcopy(METADATA)
        metadata_no_img['book']['image_url'] = None
        expect_no_img = dict(expect)
        del expect_no_img['og:image']
        preparer = OpenGraphBookMetaPreparer(metadata_no_img)
        self.assertEqual(preparer.set_data(), expect_no_img)

        # Test description variations
        # No description
        metadata_no_desc = copy.deepcopy(METADATA)
        metadata_no_desc['book']['description'] = ''
        expect_no_desc = dict(expect)
        expect_no_desc['og:description'] = \
            'By _book_creator_name_ available at _site_name_'
        preparer = OpenGraphBookMetaPreparer(metadata_no_desc)
        self.assertEqual(preparer.set_data(), expect_no_desc)

        # No creator name
        metadata_no_desc = copy.deepcopy(METADATA)
        metadata_no_desc['book']['description'] = ''
        metadata_no_desc['book']['creator_name'] = None
        expect_no_desc = dict(expect)
        expect_no_desc['og:description'] = 'Available at _site_name_'
        preparer = OpenGraphBookMetaPreparer(metadata_no_desc)
        self.assertEqual(preparer.set_data(), expect_no_desc)


class TestOpenGraphCreatorMetaPreparer(LocalTestCase):

    def test__set_data(self):
        metadata = dict(METADATA)
        expect = {
            'og:title': '_creator_name_',
            'og:type': '_creator_type_',
            'og:url': '_creator_url_',
            'og:image': '_creator_image_url_',
            'og:site_name': '_site_name_',
            'og:description': '_creator_description_',
        }
        preparer = OpenGraphCreatorMetaPreparer(metadata)
        self.assertEqual(preparer.set_data(), expect)

        # Test no image
        metadata_no_img = copy.deepcopy(METADATA)
        metadata_no_img['creator']['image_url'] = None
        expect_no_img = dict(expect)
        expect_no_img['og:image'] = ''
        preparer = OpenGraphCreatorMetaPreparer(metadata_no_img)
        self.assertEqual(preparer.set_data(), expect_no_img)

        # Test description variations
        # No description
        metadata_no_desc = copy.deepcopy(METADATA)
        metadata_no_desc['creator']['description'] = ''
        expect_no_desc = dict(expect)
        expect_no_desc['og:description'] = 'Available at _site_name_'
        preparer = OpenGraphCreatorMetaPreparer(metadata_no_desc)
        self.assertEqual(preparer.set_data(), expect_no_desc)


class TestOpenGraphMetaPreparer(LocalTestCase):

    def test__formatter(self):
        self.assertEqual(
            OpenGraphMetaPreparer.formatter(),
            BaseMetaPreparer.as_property_content
        )

    def test__set_data(self):
        metadata = dict(METADATA)
        expect = {
            'og:title': '_site_title_',
            'og:type': '_site_type_',
            'og:url': '_site_url_',
            'og:image': '_site_icon_',
            'og:site_name': '_site_name_',
            'og:description': '_site_description_',
        }
        preparer = OpenGraphMetaPreparer(metadata)
        self.assertEqual(preparer.set_data(), expect)


class TestTwitterBookMetaPreparer(LocalTestCase):

    def test__set_data(self):
        metadata = dict(METADATA)
        expect = {
            'twitter:card': 'summary_large_image',
            'twitter:site': '_site_twitter_',
            'twitter:creator': '_book_creator_twitter_',
            'twitter:title': '_book_name_',
            'twitter:description': '_book_description_',
            'twitter:image:src': '_book_image_url_',
        }
        preparer = TwitterBookMetaPreparer(metadata)
        self.assertEqual(preparer.set_data(), expect)


class TestTwitterCreatorMetaPreparer(LocalTestCase):

    def test__set_data(self):
        metadata = dict(METADATA)
        expect = {
            'twitter:card': 'summary_large_image',
            'twitter:site': '_site_twitter_',
            'twitter:creator': '_creator_twitter_',
            'twitter:title': '_creator_name_',
            'twitter:description': '_creator_description_',
            'twitter:image:src': '_creator_image_url_',
        }
        preparer = TwitterCreatorMetaPreparer(metadata)
        self.assertEqual(preparer.set_data(), expect)


class TestTwitterMetaPreparer(LocalTestCase):

    def test__set_data(self):
        metadata = dict(METADATA)
        expect = {
            'twitter:card': 'summary_large_image',
            'twitter:site': '_site_twitter_',
            'twitter:creator': '_site_twitter_',
            'twitter:title': '_site_title_',
            'twitter:description': '_site_description_',
            'twitter:image:src': '_site_icon_',
        }
        preparer = TwitterMetaPreparer(metadata)
        self.assertEqual(preparer.set_data(), expect)


class TestFunctions(LocalTestCase):
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103

    def test__html_metadata_from_records(self):

        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            creator_id=creator.id
        ))

        expect_book = {
            'creator_name': 'First Last',
            'creator_twitter': None,
            'description': None,
            'image_url': None,
            'name': 'My Book',
            'type': 'book',
            'url': None,
        }

        expect_creator = {
            'description': None,
            'image_url': None,
            'name': 'First Last',
            'twitter': None,
            'type': 'profile',
            'url': 'http://127.0.0.1:8000/FirstLast',
        }

        expect_site = site_metadata()

        got = html_metadata_from_records(None, None)
        expect = {
            'book': {},
            'creator': {},
            'site': expect_site,
        }
        self.assertEqual(got, expect)

        got = html_metadata_from_records(creator, None)
        expect = {
            'book': {},
            'creator': expect_creator,
            'site': expect_site,
        }
        self.assertEqual(got, expect)

        got = html_metadata_from_records(creator, book)
        expect = {
            'book': expect_book,
            'creator': expect_creator,
            'site': expect_site,
        }
        self.assertEqual(got, expect)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
