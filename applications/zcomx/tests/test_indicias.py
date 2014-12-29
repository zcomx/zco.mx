#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/indicias.py

"""
import datetime
import os
import shutil
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from applications.zcomx.modules.images import store
from applications.zcomx.modules.indicias import \
    BookIndiciaPage, \
    CreatorIndiciaPage, \
    IndiciaPage, \
    cc_licence_places, \
    cc_licences, \
    render_cc_licence
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301


class TestIndiciaPage(LocalTestCase):
    def test____init__(self):
        indicia = IndiciaPage(None)
        self.assertTrue(indicia)

    def test__default_licence(self):
        indicia = IndiciaPage(None)
        default = indicia.default_licence()
        self.assertEqual(default.code, 'All Rights Reserved')
        fields = ['id', 'number', 'code', 'url', 'template_img', 'template_web']
        for f in fields:
            self.assertTrue(f in default.keys())

    def test__licence_text(self):
        indicia = IndiciaPage(None)
        this_year = datetime.date.today().year
        self.assertEqual(
            indicia.licence_text(),
            ' <i>NAME OF BOOK</i> IS COPYRIGHT (C) {y} BY CREATOR NAME.  ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )

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
        #          <i>NAME OF BOOK</i> IS COPYRIGHT (C) 2014 BY CREATOR NAME.
        #          ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST
        #          BE OBTAINED FROM THE AUTHOR.
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
        self.assertTrue('ALL RIGHTS RESERVED' in div_2b.contents[2])

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
        self.assertTrue('ALL RIGHTS RESERVED' in div_2c.contents[2])

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

    def test__licence_text(self):
        auth_user = self.add(db.auth_user, dict(name='Test Licence Text'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))
        book = self.add(db.book, dict(
            name='test__licence_text',
            creator_id=creator.id,
        ))

        indicia = BookIndiciaPage(book)
        this_year = datetime.date.today().year
        self.assertEqual(
            indicia.licence_text(),
            ' <i>TEST__LICENCE_TEXT</i> IS COPYRIGHT (C) {y} BY TEST LICENCE TEXT.  ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )

        query = (db.cc_licence.code == 'CC BY')
        cc_licence = db(query).select().first()
        book.update_record(cc_licence_id=cc_licence.id)
        db.commit()
        book = db(db.book.id == book.id).select().first()

        indicia = BookIndiciaPage(book)
        self.assertEqual(
            indicia.licence_text(),
            ' <i>TEST__LICENCE_TEXT</i> IS COPYRIGHT (C) {y} BY TEST LICENCE TEXT.  THIS WORK IS LICENSED UNDER THE <a href="http://creativecommons.org/licenses/by/4.0">CC BY 4.0 INT`L LICENSE</a>.'.format(y=this_year)
        )

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

    def test__licence_text(self):
        auth_user = self.add(db.auth_user, dict(name='Creator Licence Text'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))
        this_year = datetime.date.today().year

        indicia = CreatorIndiciaPage(creator)
        self.assertEqual(
            indicia.licence_text(),
            ' <i>NAME OF BOOK</i> IS COPYRIGHT (C) {y} BY CREATOR LICENCE TEXT.  ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )


class TestFunctions(LocalTestCase):

    def test__cc_licence_places(self):
        places = cc_licence_places()
        got = loads('[' + str(places) + ']')
        self.assertTrue({'text': 'Canada', 'value': 'Canada'} in got)
        self.assertTrue(len(got) > 245)
        for d in got:
            self.assertEqual(sorted(d.keys()), ['text', 'value'])
            self.assertEqual(d['text'], d['value'])

    def test__cc_licences(self):
        auth_user = self.add(db.auth_user, dict(name='Test CC Licence'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))
        book = self.add(db.book, dict(
            name='test__cc_licences',
            creator_id=creator.id,
        ))

        # Add a cc_licence with quotes in the template. Should be handled.
        self.add(db.cc_licence, dict(
            number=999,
            code='test__cc_licences',
            url='http://cc_licence.com',
            template_img='',
            template_web="""It's {title} the "in" from {owner}."""
        ))

        licences = cc_licences(book)
        # loads(dumps(str)) escapes double quotes.
        got = loads('[' + str(licences) + ']')
        self.assertEqual(len(got), 8 + 1)
        for d in got:
            self.assertEqual(sorted(d.keys()), ['info', 'text', 'value'])
            query = (db.cc_licence.id == d['value'])
            cc_licence = db(query).select().first()
            self.assertEqual(cc_licence.code, d['text'])

    def test__render_cc_licence(self):

        cc_licence = self.add(db.cc_licence, dict(
            number=999,
            code='test__render_cc_licence',
            url='http://cc_licence.com',
            template_img='The {title} is owned by {owner} for {year} in {place} at {url}.',
            template_web='THE {title} IS OWNED BY {owner} FOR {year} IN {place} AT {url}.'
        ))

        this_year = datetime.date.today().year

        tests = [
            #(data, template, expect)
            (
                {},
                'template_img',
                'The NAME OF BOOK is owned by CREATOR NAME for {y} in &LT;YOUR COUNTRY&GT; at http://cc_licence.com.'.format(y=this_year)
            ),
            (
                {},
                'template_web',
                'THE NAME OF BOOK IS OWNED BY CREATOR NAME FOR {y} IN &LT;YOUR COUNTRY&GT; AT http://cc_licence.com.'.format(y=this_year)
            ),
            (
                {
                    'title': "My Book's",
                    'owner': 'Joe Doe',
                    'year': '1999',
                    'place': 'Canada'
                },
                'template_img',
                'The MY BOOK`S is owned by JOE DOE for 1999 in CANADA at http://cc_licence.com.'
            ),
            (
                {
                    'title': "My Book's",
                    'owner': 'Joe Doe',
                    'year': '1999',
                    'place': 'Canada'
                },
                'template_web',
                'THE MY BOOK`S IS OWNED BY JOE DOE FOR 1999 IN CANADA AT http://cc_licence.com.'
            ),
        ]
        for t in tests:
            self.assertEqual(
                render_cc_licence(t[0], cc_licence, template_field=t[1]),
                t[2]
            )

        self.assertRaises(NotFoundError, render_cc_licence, {}, -1)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
