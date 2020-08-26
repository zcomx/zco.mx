#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/sitemap.py

"""
import datetime
import re
import unittest
from applications.zcomx.modules.sitemap import SiteMapUrl
from applications.zcomx.modules.tests.runner import LocalTestCase

# pylint: disable=missing-docstring


class TestSiteMapUrl(LocalTestCase):

    def test____init__(self):
        sitemap_url = SiteMapUrl('http://example.com')
        self.assertTrue(sitemap_url)
        self.assertEqual(sitemap_url.last_modified, datetime.date.today())

    def test__xml_component(self):

        def rm_whitespace(text):
            """Remove whitespace from text."""
            return re.sub(r'\s+', '', text)

        last_modified = datetime.date(2001, 12, 31)

        sitemap_url = SiteMapUrl(
            'http://example.com',
            last_modified=last_modified,
        )
        got = sitemap_url.xml_component()
        expect = rm_whitespace(
            """<url>
                <loc>http://example.com</loc>
                <lastmod>2001-12-31</lastmod>
                <changefreq>daily</changefreq>
                <priority>1.0</priority>
            </url>
            """
        ).encode('utf-8')
        self.assertEqual(got.xml(), expect)

        sitemap_url = SiteMapUrl(
            'http://example.com',
            last_modified=last_modified,
            changefreq='monthly',
            priority=0.3,
        )
        got = sitemap_url.xml_component()
        expect = rm_whitespace(
            """<url>
                <loc>http://example.com</loc>
                <lastmod>2001-12-31</lastmod>
                <changefreq>monthly</changefreq>
                <priority>0.3</priority>
            </url>
            """
        ).encode('utf-8')
        self.assertEqual(got.xml(), expect)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
