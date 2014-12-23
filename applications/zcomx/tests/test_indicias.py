#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/indicias.py

"""
import os
import shutil
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.images import store
from applications.zcomx.modules.indicias import \
    BookIndiciaPage, \
    CreatorIndiciaPage, \
    IndiciaPage
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestIndiciaPage(LocalTestCase):
    def test____init__(self):
        indicia = IndiciaPage(None)
        self.assertTrue(indicia)

    def test__render(self):
        indicia = IndiciaPage(None)

        got = indicia.render()
        soup = BeautifulSoup(str(got))

        # <div class="indicia_preview_section portrait">
        #     <div class="indicia_image_container">
        #         <img src="/zcomx/static/images/indicia_image.png" />
        #     </div>
        #     <div class="indicia_text_container">
        #         <div>If you enjoyed this book... consider giving monies</div>
        #         <div>
        #           <div>contribute: http://1234.zco.mx/monies</div>
        #           <div>contact info: http://1234.zco.mx</div>
        #         </div>
        #         <div>
        #     NAME OF BOOK copyright @ 2014 by CREATOR NAME
        #     All rights reserved. No copying without written
        #     consent from the author.
        #         </div>
        #     </div>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section portrait')
        div_1 = div.div
        self.assertEqual(div_1['class'], 'indicia_image_container')
        img = div_1.img
        self.assertEqual(img['src'], '/zcomx/static/images/indicia_image.png')
        div_2 = div_1.nextSibling
        self.assertEqual(div_2['class'], 'indicia_text_container')
        div_2a = div_2.div
        self.assertTrue(div_2a.string.startswith('If you enjoyed '))
        div_2b = div_2a.nextSibling
        self.assertTrue(div_2b.string.find('All rights reserved') > 0)

        # test orientation
        got = indicia.render(orientation='landscape')
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section landscape')

        # test creator
        indicia = IndiciaPage(None)
        indicia.creator = Storage({'id': 1234})
        got = indicia.render()

        soup = BeautifulSoup(str(got))
        div = soup.div

        self.assertEqual(div['class'], 'indicia_preview_section portrait')
        div_1 = div.div
        self.assertEqual(div_1['class'], 'indicia_image_container')
        img = div_1.img
        self.assertEqual(img['src'], '/zcomx/static/images/indicia_image.png')
        div_2 = div_1.nextSibling
        self.assertEqual(div_2['class'], 'indicia_text_container')
        div_2a = div_2.div
        self.assertTrue(div_2a.string.startswith('If you enjoyed '))
        div_2b = div_2a.nextSibling
        div_2b1 = div_2b.div
        self.assertTrue(
            div_2b1.string,
            'contribute: http://1234.zco.mx/monies'
        )
        div_2b2 = div_2b1.nextSibling
        self.assertTrue(
            div_2b2.string,
            'contact info: http://1234.zco.mx'
        )
        div_2c = div_2b.nextSibling
        self.assertTrue(div_2c.string.find('All rights reserved') > 0)

        # test creator with indicia
        indicia = IndiciaPage(None)
        indicia.creator = Storage(
            {'id': 1234, 'indicia_image': 'path/to/file.png'})
        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        div_1 = div.div
        img = div_1.img
        self.assertEqual(
            img['src'], '/images/download/path/to/file.png?size=web')


class TestBookIndiciaPage(LocalTestCase):

    _image_dir = '/tmp/image_for_books'
    _image_original = os.path.join(_image_dir, 'original')
    _test_data_dir = None

    @classmethod
    def _prep_image(cls, img, working_directory=None, to_name=None):
        """Prepare an image for testing.
        Copy an image from private/test/data to a working directory.

        Args:
            img: string, name of source image, eg file.jpg
                must be in cls._test_data_dir
            working_directory: string, path of working directory to copy to.
                If None, uses cls._image_dir
            to_name: string, optional, name of image to copy file to.
                If None, img is used.
        """
        src_filename = os.path.join(
            os.path.abspath(cls._test_data_dir),
            img
        )

        if working_directory is None:
            working_directory = os.path.abspath(cls._image_dir)

        if to_name is None:
            to_name = img

        filename = os.path.join(working_directory, to_name)
        shutil.copy(src_filename, filename)
        return filename

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

    def test____init__(self):
        creator = self.add(db.creator, dict(path_name='BookIndiciaPage'))
        book = self.add(db.book, dict(
            name='BookIndiciaPage__init__',
            creator_id=creator.id,
        ))
        indicia = BookIndiciaPage(book)
        self.assertTrue(indicia)

    def test__render(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        creator = self.add(db.creator, dict(path_name='BookIndiciaPage'))
        book = self.add(db.book, dict(
            name='BookIndiciaPage__init__',
            creator_id=creator.id,
        ))

        portrait_filename = store(
            db.book_page.image, self._prep_image('portrait.png'))

        self.add(db.book_page, dict(
            book_id=book.id,
            image=portrait_filename,
            page_no=1,
        ))

        indicia = BookIndiciaPage(book)

        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section portrait')

        landscape_filename = store(
            db.book_page.image, self._prep_image('landscape.png'))

        self.add(db.book_page, dict(
            book_id=book.id,
            image=landscape_filename,
            page_no=2,
        ))

        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section landscape')


class TestCreatorIndiciaPage(LocalTestCase):
    def test____init__(self):
        creator = self.add(db.creator, dict(path_name='CreatorIndiciaPage'))
        indicia = CreatorIndiciaPage(creator)
        self.assertTrue(indicia)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
