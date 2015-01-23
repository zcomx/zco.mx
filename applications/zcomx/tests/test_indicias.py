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
from PIL import Image
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from gluon.validators import IS_INT_IN_RANGE
from applications.zcomx.modules.images import store
from applications.zcomx.modules.indicias import \
    BookIndiciaPage, \
    BookIndiciaPagePng, \
    CreatorIndiciaPage, \
    IndiciaPage, \
    IndiciaSh, \
    IndiciaShError, \
    IndiciaUpdateInProgress, \
    PublicationMetadata, \
    cc_licence_by_code, \
    cc_licence_places, \
    cc_licences, \
    render_cc_licence, \
    update_creator_indicia
from applications.zcomx.modules.test_runner import \
    LocalTestCase, \
    _mock_date as mock_date
from applications.zcomx.modules.shell_utils import UnixFile
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _auth_user = None
    _book = None
    _book_page = None
    _creator = None
    _image_dir = '/tmp/test_indicias'
    _image_name = 'file.jpg'
    _test_data_dir = None

    _objects = []

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

        if not os.path.exists(cls._image_dir):
            os.makedirs(cls._image_dir)

        def create_image(image_name):
            image_filename = os.path.join(cls._image_dir, image_name)

            # Create an image to test with.
            im = Image.new('RGB', (1200, 1200))
            with open(image_filename, 'wb') as f:
                im.save(f)

            # Store the image in the uploads/original directory
            stored_filename = None
            with open(image_filename, 'rb') as f:
                stored_filename = db.book_page.image.store(f)
            return stored_filename

        cls._auth_user = cls.add(db.auth_user, dict(
            name='First Last'
        ))

        cls._creator = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email='image_test_case@example.com',
        ))

        cls._book = cls.add(db.book, dict(
            name='Image Test Case',
            creator_id=cls._creator.id,
        ))

        cls._book_page = cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=1,
            image=create_image('file.jpg'),
        ))

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)


class TestBookIndiciaPage(ImageTestCase):

    def test____init__(self):
        indicia = BookIndiciaPage(self._book)
        self.assertTrue(indicia)

    def test__get_orientation(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        indicia = BookIndiciaPage(self._book)
        self.assertEqual(indicia._orientation, None)

        for t in ['portrait', 'landscape', 'square']:
            img = '{n}.png'.format(n=t)
            filename = self._prep_image(img)
            stored_filename = store(db.book_page.image, filename)
            self._book_page.update_record(image=stored_filename)
            db.commit()

            indicia._orientation = None     # Clear cache
            self.assertEqual(
                indicia.get_orientation(),
                'portrait' if t == 'square' else t
            )

        # Test cache
        indicia._orientation = '_cache_'
        self.assertEqual(indicia.get_orientation(), '_cache_')

    def test__licence_text(self):
        indicia = BookIndiciaPage(self._book)
        this_year = datetime.date.today().year
        self.assertEqual(
            indicia.licence_text(),
            ' <i>IMAGE TEST CASE</i> IS COPYRIGHT (C) {y} BY FIRST LAST.  ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )

        cc_licence_id = cc_licence_by_code('CC BY', want='id', default=0)
        self._book.update_record(cc_licence_id=cc_licence_id)
        db.commit()
        book = db(db.book.id == self._book.id).select().first()

        indicia = BookIndiciaPage(book)
        self.assertEqual(
            indicia.licence_text(),
            ' <i>IMAGE TEST CASE</i> IS COPYRIGHT (C) {y} BY FIRST LAST.  THIS WORK IS LICENSED UNDER THE <a href="http://creativecommons.org/licenses/by/4.0">CC BY 4.0 INT`L LICENSE</a>.'.format(y=this_year)
        )

    def test__render(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        portrait_filename = store(
            db.book_page.image, self._prep_image('portrait.png'))

        self._book_page.update_record(image=portrait_filename)
        db.commit()
        indicia = BookIndiciaPage(self._book)

        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section portrait')

        landscape_filename = store(
            db.book_page.image, self._prep_image('landscape.png'))
        self._book_page.update_record(image=landscape_filename)
        db.commit()

        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        indicia._orientation = None     # clear cache
        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section landscape')


class TestBookIndiciaPagePng(ImageTestCase):
    def test____init__(self):
        png_page = BookIndiciaPagePng(self._book)
        self.assertTrue(png_page)
        self.assertEqual(png_page.book.id, self._book.id)

    def test__create(self):
        png_page = BookIndiciaPagePng(self._book)
        png = png_page.create()

        output, error = UnixFile(png).file()
        self.assertTrue('PNG image' in output)
        self.assertEqual(error, '')

    def test__create_metatext_file(self):
        png_page = BookIndiciaPagePng(self._book)
        png_page.create_metatext_file()

        output, error = UnixFile(png_page.metadata_filename).file()
        self.assertTrue('ASCII text' in output)
        self.assertEqual(error, '')
        lines = []
        with open(png_page.metadata_filename, 'r') as f:
            lines.append(f.read())

        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0],
            """ <i>IMAGE TEST CASE</i> IS COPYRIGHT (C) 2015 BY FIRST LAST.  ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR."""
        )

    def test__get_indicia_filename(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        png_page = BookIndiciaPagePng(self._book)
        self.assertEqual(png_page._indicia_filename, None)

        # No creator indicia image, should use default.
        self.assertEqual(
            png_page.get_indicia_filename(),
            'applications/zcomx/static/images/indicia_image.png'
        )

        # Add creator indicia_image
        filename = self._prep_image('file.png', to_name='indicia.png')
        stored_filename = store(db.creator.indicia_image, filename)
        png_page.creator.update_record(indicia_image=stored_filename)
        db.commit()

        png_page._indicia_filename = None       # Clear cache
        _, expect = db.creator.indicia_image.retrieve(
            png_page.creator.indicia_image, nameonly=True)
        self.assertEqual(png_page.get_indicia_filename(), expect)

        # Test cache
        png_page._indicia_filename = '_cache_'
        self.assertEqual(
            png_page.get_indicia_filename(),
            '_cache_'
        )


class TestCreatorIndiciaPage(ImageTestCase):
    def test____init__(self):
        indicia = CreatorIndiciaPage(self._creator)
        self.assertTrue(indicia)

    def test__licence_text(self):
        this_year = datetime.date.today().year

        indicia = CreatorIndiciaPage(self._creator)
        self.assertEqual(
            indicia.licence_text(),
            ' <i>NAME OF BOOK</i> IS COPYRIGHT (C) {y} BY FIRST LAST.  ALL RIGHTS RESERVED.  PREMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )


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
        #         <div>IF  YOU  ENJOYED THIS WORK... TUMBLR AND FACEBOOK</div>
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
        self.assertTrue(div_2a.string.startswith('IF  YOU  ENJOYED '))
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
        self.assertTrue(div_2a.string.startswith('IF  YOU  ENJOYED '))
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


class TestIndiciaSh(ImageTestCase):

    def test____init__(self):
        indicia_sh = IndiciaSh(101, '', '')
        self.assertTrue(indicia_sh)

    def test__run(self):
        creator_id = 919

        metadata_filename = os.path.join(self._image_dir, 'meta.txt')
        with open(metadata_filename, 'w') as f:
            f.write(
                'This is a test metadata text. Copyright 2014.'
            )

        indicia_filename = self._prep_image('file.png', to_name='indicia.png')
        indicia_sh = IndiciaSh(creator_id, metadata_filename, indicia_filename)
        indicia_sh.run()
        png_filename = os.path.join(
            indicia_sh.temp_directory(),
            '919-indicia.png'
        )
        self.assertEqual(indicia_sh.png_filename, png_filename)
        self.assertTrue(os.path.exists(indicia_sh.png_filename))
        output, error = UnixFile(indicia_sh.png_filename).file()
        self.assertTrue('PNG image' in output)
        self.assertEqual(error, '')

        im = Image.open(indicia_sh.png_filename)
        width, height = im.size
        self.assertTrue(height > width)

        # Test: landscape option.
        indicia_sh.landscape = True
        indicia_sh.run()
        im = Image.open(indicia_sh.png_filename)
        width, height = im.size
        self.assertTrue(width > height)

        def do_invalid(obj, msg):
            try:
                obj.run()
            except IndiciaShError as err:
                self.assertTrue(msg in str(err))
            else:
                self.fail('IndiciaShError not raised.')

        # Invalid: creator id is not an integer
        indicia_sh = IndiciaSh('abc', metadata_filename, indicia_filename)
        do_invalid(indicia_sh, 'ID is not an integer')

        # Invalid: metadata_filename is not text
        indicia_sh = IndiciaSh(creator_id, indicia_filename, indicia_filename)
        do_invalid(indicia_sh, 'File {f} is not a text file'.format(
            f=indicia_filename))

        # Invalid: indicia_filename is not image
        indicia_sh = IndiciaSh(creator_id, metadata_filename, metadata_filename)
        do_invalid(indicia_sh, 'File {f} is not an image file'.format(
            f=metadata_filename))


class TestPublicationMetadata(LocalTestCase):
    def test____init__(self):
        str_to_date = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        book = self.add(db.book, dict(
            name='TestPublicationMetadata',
        ))
        meta = PublicationMetadata(book.id)
        self.assertTrue(meta)
        self.assertEqual(
            meta.first_publication_text,
            'First publication: zco.mx 2014.'
        )

    def test____str__(self):
        book = self.add(db.book, dict(name='My Book'))

        meta = PublicationMetadata(book.id)
        self.assertEqual(str(meta), '')

        meta.metadata = dict(
            book_id=book.id,
            republished=True,
            published_type='whole',
            published_name='My Old Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme Pub Inc',
            from_year=2014,
            to_year=2015,
        )

        meta.serials = [
            dict(
                book_id=book.id,
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=1,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            ),
            dict(
                book_id=book.id,
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=2,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            ),
        ]

        cc_licence_id = cc_licence_by_code('CC BY-NC-SA', want='id', default=0)

        meta.derivative = dict(
            book_id=book.id,
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=cc_licence_id,
            from_year=2014,
            to_year=2015,
        )

        self.assertEqual(
            str(meta),
            (
                'This work was originally published in print in 2014-2015 as "My Old Book" by Acme Pub Inc. '
                '"My Story #1" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc. '
                '"My Story #2" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc. '
                '"My Book" is a derivative of "My Derivative" from 2014-2015 by John Doe used under CC BY-NC-SA.'
            )
        )

    def test__derivative_text(self):

        # METADATA see mod 12687

        # if [[ derivative ]]; then
        #     input:their_works_name && input:their_YYYY && input:their_name && their_licence && append [14] to above
        # fi

        # [14] "Name of Book", is a derivative of "Their work's name" from "their_YYYY" by Their_Name, used under Their_Licence eg CC BY.

        book = self.add(db.book, dict(name='My Book'))

        cc_licence_id = cc_licence_by_code('CC BY-ND', want='id', default=0)

        meta = PublicationMetadata(book.id)
        derivative = dict(
            book_id=book.id,
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=cc_licence_id,
            from_year=2014,
            to_year=2015,
        )

        meta.derivative = dict(derivative)
        self.assertEqual(
            meta.derivative_text(),
            '"My Book" is a derivative of "My Derivative" from 2014-2015 by John Doe used under CC BY-ND.'
        )

    def test__load(self):
        book = self.add(db.book, dict(
            name='test__load',
        ))

        def test_meta(meta, expect):
            self.assertEqual(meta.metadata, expect.metadata)
            self.assertEqual(meta.serials, expect.serials)
            self.assertEqual(meta.derivative, expect.derivative)

        meta = PublicationMetadata(book.id)
        expect = Storage({})
        expect.metadata = {}
        expect.serials = []
        expect.derivative = {}
        test_meta(meta, expect)
        meta.load()
        test_meta(meta, expect)

        metadata = dict(
            book_id=book.id,
            republished=True,
            published_type='whole',
            published_name='My Book',
            published_format='digital',
            publisher_type='press',
            publisher='Acme',
            from_year=2014,
            to_year=2015,
        )

        self.add(db.publication_metadata, metadata)
        meta.load()
        expect.metadata = metadata
        test_meta(meta, expect)

        serial_1 = dict(
            book_id=book.id,
            published_name='My Book',
            published_format='digital',
            publisher_type='press',
            publisher='Acme',
            story_number=99,
            serial_title='Sheerios',
            serial_number=1,
            from_year=1998,
            to_year=1999,
        )

        serial_2 = dict(
            book_id=book.id,
            published_name='My Book 2',
            published_format='digital',
            publisher_type='press',
            publisher='Acme 2',
            story_number=11,
            serial_title='Sheerios 2',
            serial_number=2,
            from_year=2000,
            to_year=2001,
        )

        self.add(db.publication_serial, serial_1)
        meta.load()
        expect.metadata = metadata
        expect.serials = [serial_1]
        test_meta(meta, expect)

        self.add(db.publication_serial, serial_2)
        meta.load()
        expect.metadata = metadata
        expect.serials = [serial_2, serial_1]   # Sorted by story_number
        test_meta(meta, expect)

        derivative_data = dict(
            book_id=book.id,
            title='Derivative',
            creator='Dr Drawer',
            cc_licence_id=1,
            from_year=2006,
            to_year=2007,
        )

        self.add(db.derivative, derivative_data)
        meta.load()
        expect.metadata = metadata
        expect.serials = [serial_2, serial_1]   # Sorted by story_number
        expect.derivative = derivative_data
        test_meta(meta, expect)

        # Test chaining.
        self.assertEqual(meta.load().metadata, expect.metadata)
        self.assertEqual(
            str(meta.load()),
            (
                'This work was originally published digitally in 2014-2015 as "My Book" by Acme. '
                '"My Book 2 #11" was originally published digitally in "Sheerios 2 #2" in 2000-2001 by Acme 2. '
                '"My Book #99" was originally published digitally in "Sheerios" in 1998-1999 by Acme. '
                '"test__load" is a derivative of "Derivative" from 2006-2007 by Dr Drawer used under CC0.'
            )
        )

    def test__load_from_vars(self):
        book = self.add(db.book, dict(
            name='test__load_from_vars',
        ))

        meta = PublicationMetadata(book.id)
        self.assertEqual(meta.metadata, {})
        self.assertEqual(meta.serials, [])
        self.assertEqual(meta.derivative, {})

        metadata = dict(
            republished='first',
            published_type='whole',
            published_name='My Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme',
            from_year=1999,
            to_year=2000,
        )

        serials = [
            dict(
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=1,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            ),
            dict(
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=2,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            )
        ]

        derivative = dict(
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=1,
            from_year=2014,
            to_year=2015,
        )

        request_vars = {}
        for k, v in metadata.items():
            request_vars['publication_metadata_' + k] = v
        for count, serial in enumerate(serials):
            for k, v in serial.items():
                request_vars['publication_serial_' + k + '__' + str(count)] = v
        for k, v in derivative.items():
            request_vars['derivative_' + k] = v
        request_vars['is_derivative'] = 'no'

        meta.load_from_vars(request_vars)
        expect = dict(metadata)
        expect['republished'] = False
        self.assertEqual(meta.metadata, expect)
        self.assertEqual(len(meta.serials), 0)
        self.assertEqual(meta.derivative, {})

        request_vars['publication_metadata_republished'] = 'repub'
        request_vars['publication_metadata_published_type'] = 'whole'
        meta.load_from_vars(request_vars)
        self.assertEqual(len(meta.serials), 0)

        request_vars['publication_metadata_republished'] = 'repub'
        request_vars['publication_metadata_published_type'] = 'serial'
        meta.load_from_vars(request_vars)
        self.assertEqual(len(meta.serials), 2)
        self.assertEqual(meta.serials[0], serials[0])
        self.assertEqual(meta.serials[1], serials[1])

        request_vars['is_derivative'] = 'yes'
        meta.load_from_vars(request_vars)
        self.assertEqual(meta.derivative, derivative)

        # Test 'republished' variations
        tests = [
            # (republished, expect)
            ('', None),
            ('first', False),
            ('repub', True),
            ('_fake_', None),
        ]
        for t in tests:
            request_vars['publication_metadata_republished'] = t[0]
            meta.load_from_vars(request_vars)
            self.assertEqual(meta.metadata['republished'], t[1])

        # Test chaining
        request_vars['publication_metadata_republished'] = 'repub'
        request_vars['publication_metadata_published_type'] = 'whole'
        expect = dict(metadata)
        expect['republished'] = True
        self.assertEqual(meta.load_from_vars(request_vars).metadata, expect)

    def test__metadata_text(self):

        # METADATA see mod 12687
        # If 'first publication'; then
        #     echo [1]

        # elif 'republish - in-whole'; then
        #     if old_bookname == name; then
        #         [[ digital ]]       && input:site_name  && echo [2]
        #         [[ paper - press ]] && input:press_name && echo [3]
        #         [[ paper - self ]]  && [4]
        #     elif old_bookname != name; then
        #         input:old_bookname
        #         [[ digital ]]       && input:site_name  && echo [5]
        #         [[ paper - press ]] && input:press_name && echo [6]
        #         [[ paper - self ]]  && [7]
        #     fi

        #     ---
        # [1] First publication: zco.mx YYYY.
        #     ---
        # [2] This work was originally published digitally in YYYY at username.tumblr.com.
        #     ---
        # [3] This work was originally published in print in YYYY by publisher/press.
        #     ---
        # [4] This work was originally self-published in print in YYYY.
        #     ---
        # [5] This work was originally published digitally in YYYY as old_name at username.tumblr.com.
        #     ---
        # [6] This work was originally published in print in YYYY as old_name by publisher/press.
        #     ---
        # [7] This work was originally self-published in print as old_name in YYYY.
        #     ---

        book_name = 'My Book'
        original_name = 'My Old Book'

        book = self.add(db.book, dict(name=book_name))

        meta = PublicationMetadata(book.id)
        metadata = Storage(dict(
            book_id=book.id,
            republished=False,
            published_type='',
            published_name=original_name,
            published_format='',
            publisher_type='',
            publisher='',
            from_year=2014,
            to_year=2015,
        ))

        str_to_date = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        # [1]
        meta.metadata = dict(metadata)
        self.assertEqual(
            meta.metadata_text(),
            'First publication: zco.mx 2014.'
        )
        # Test variations on first_publication_text

        meta.first_publication_text = ''
        self.assertEqual(meta.metadata_text(), '')
        meta.first_publication_text = 'La de do la de da'
        self.assertEqual(meta.metadata_text(), 'La de do la de da')

        # [2]
        meta.metadata = Storage(metadata)
        meta.metadata.republished = True
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = book_name
        meta.metadata.published_format = 'digital'
        meta.metadata.publisher_type = 'self'
        meta.metadata.publisher = 'tumblr.com'
        self.assertEqual(
            meta.metadata_text(),
            'This work was originally published digitally in 2014-2015 at tumblr.com.'
        )

        # [3]
        meta.metadata = Storage(metadata)
        meta.metadata.republished = True
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = book_name
        meta.metadata.published_format = 'paper'
        meta.metadata.publisher_type = 'press'
        meta.metadata.publisher = 'Acme Pub Inc.'
        self.assertEqual(
            meta.metadata_text(),
            'This work was originally published in print in 2014-2015 by Acme Pub Inc.'
        )

        # [4]
        meta.metadata = Storage(metadata)
        meta.metadata.republished = True
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = book_name
        meta.metadata.published_format = 'paper'
        meta.metadata.publisher_type = 'self'
        meta.metadata.publisher = ''
        self.assertEqual(
            meta.metadata_text(),
            'This work was originally self-published in print in 2014-2015.'
        )

        # [5]
        meta.metadata = Storage(metadata)
        meta.metadata.republished = True
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = original_name
        meta.metadata.published_format = 'digital'
        meta.metadata.publisher_type = 'self'
        meta.metadata.publisher = 'tumblr.com'
        self.assertEqual(
            meta.metadata_text(),
            'This work was originally published digitally in 2014-2015 as "My Old Book" at tumblr.com.'
        )

        # [6]
        meta.metadata = Storage(metadata)
        meta.metadata.republished = True
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = original_name
        meta.metadata.published_format = 'paper'
        meta.metadata.publisher_type = 'press'
        meta.metadata.publisher = 'Acme Pub Inc.'
        self.assertEqual(
            meta.metadata_text(),
            'This work was originally published in print in 2014-2015 as "My Old Book" by Acme Pub Inc.'
        )

        # [7]
        meta.metadata = Storage(metadata)
        meta.metadata.republished = True
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = original_name
        meta.metadata.published_format = 'paper'
        meta.metadata.publisher_type = 'self'
        meta.metadata.publisher = ''
        self.assertEqual(
            meta.metadata_text(),
            'This work was originally self-published in print in 2014-2015 as "My Old Book".'
        )

    def test__serial_text(self):

        # METADATA see mod 12687

        # elif 'republish - serial/anthology'; then
        #     while read input; do
        #         [[ $input == done ]] && coninute
        #         num=( input:story_name && input:anthology/serial name && input:a/s YYYY )
        #     done

        #     [[ digital ]] && num=0 && input:site_name && printf [8]
        #     [[ digital ]] && num>1 && input:site_name && printf [9]
        #     [[ paper - press ]] && num=0 && input:press_name && echo [10]
        #     [[ paper - press ]] && num>1 && input:press_name && echo [11]
        #     [[ paper - self ]] && num=0 && echo [12]
        #     [[ paper - self ]] && num>1 && echo [13]
        # fi

        # [8] Story Name was originally published digitally in anthology/serial name in YYYY at username.tumblr.com
        # [9] Story Name #1 was originally serialized digitally in anthology/serial name in YYYY at username.tumblr.com
        #     Story Name #2 was originally serialized digitally in anthology/serial name in YYYY at username.tumblr.com
        #     ...
        #     ---
        # [10] Story Name was originally published in print in anthology/serial name in YYYY by publisher/press
        # [11] Story Name #1 was originally published in print in anthology/serial name in YYYY by publisher/press
        #      Story Name #2 was originally published in print in anthology/serial name in YYYY by publisher/press
        #     ...
        #     ---
        # [12] Story Name was originally self-published in print in anthology/serial name in YYYY by publisher/press
        # [13] Story Name #1 was originally self-published in print in anthology/serial name in YYYY by publisher/press
        #      Story Name #2 was originally self-published in print in anthology/serial name in YYYY by publisher/press
        #     ...

        book = self.add(db.book, dict(name='test__serials_text'))

        meta = PublicationMetadata(book.id)
        default_serial = Storage(dict(
            book_id=book.id,
            published_name='',
            published_format='',
            publisher_type='',
            publisher='',
            story_number=0,
            serial_title='',
            serial_number=0,
            from_year=2014,
            to_year=2015,
        ))

        # [8]
        s = Storage(default_serial)
        s.published_name = 'My Story'
        s.published_format = 'digital'
        s.publisher_type = 'self'
        s.publisher = 'tumblr.com'
        s.story_number = 1
        s.serial_title = 'Aaa Series'
        s.serial_number = 0

        self.assertEqual(
            meta.serial_text(s, single=True),
            '"My Story" was originally published digitally in "Aaa Series" in 2014-2015 at tumblr.com.'
        )

        # [9]
        s.story_number = 1
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #1" was originally published digitally in "Aaa Series" in 2014-2015 at tumblr.com.'
        )
        s.story_number = 2
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #2" was originally published digitally in "Aaa Series" in 2014-2015 at tumblr.com.'
        )

        # [10]
        s = Storage(default_serial)
        s.published_name = 'My Story'
        s.published_format = 'paper'
        s.publisher_type = 'press'
        s.publisher = 'Acme Pub Inc.'
        s.story_number = 1
        s.serial_title = 'Aaa Series'
        s.serial_number = 0

        self.assertEqual(
            meta.serial_text(s, single=True),
            '"My Story" was originally published in print in "Aaa Series" in 2014-2015 by Acme Pub Inc.'
        )

        # [11]
        s.story_number = 1
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #1" was originally published in print in "Aaa Series" in 2014-2015 by Acme Pub Inc.'
        )
        s.story_number = 2
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #2" was originally published in print in "Aaa Series" in 2014-2015 by Acme Pub Inc.'
        )

        # [12]
        s = Storage(default_serial)
        s.published_name = 'My Story'
        s.published_format = 'paper'
        s.publisher_type = 'self'
        s.publisher = ''
        s.story_number = 1
        s.serial_title = 'Aaa Series'
        s.serial_number = 0

        self.assertEqual(
            meta.serial_text(s, single=True),
            '"My Story" was originally self-published in print in "Aaa Series" in 2014-2015.'
        )

        # [13]
        s.story_number = 1
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #1" was originally self-published in print in "Aaa Series" in 2014-2015.'
        )
        s.story_number = 2
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #2" was originally self-published in print in "Aaa Series" in 2014-2015.'
        )

        # Test serial_number variations.
        s.serial_number = 1
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #2" was originally self-published in print in "Aaa Series" in 2014-2015.'
        )
        s.serial_number = 2
        self.assertEqual(
            meta.serial_text(s, single=False),
            '"My Story #2" was originally self-published in print in "Aaa Series #2" in 2014-2015.'
        )

    def test__serials_text(self):
        book = self.add(db.book, dict(name='test__serials_text'))

        meta = PublicationMetadata(book.id)
        serial_1 = Storage(dict(
            book_id=book.id,
            published_name='My Story',
            published_format='paper',
            publisher_type='press',
            publisher='Acme Pub Inc',
            story_number=1,
            serial_title='Aaa Series',
            serial_number=2,
            from_year=2014,
            to_year=2015,
        ))

        serial_2 = Storage(dict(
            book_id=book.id,
            published_name='My Story',
            published_format='paper',
            publisher_type='press',
            publisher='Acme Pub Inc',
            story_number=2,
            serial_title='Aaa Series',
            serial_number=2,
            from_year=2014,
            to_year=2015,
        ))

        meta.serials = [serial_1]
        self.assertEqual(
            meta.serials_text(),
            ['"My Story" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc.']
        )

        meta.serials = [serial_1, serial_2]
        self.assertEqual(
            meta.serials_text(),
            [
                '"My Story #1" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc.',
                '"My Story #2" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc.',
            ]
        )

    def test__texts(self):
        book = self.add(db.book, dict(name='My Book'))

        meta = PublicationMetadata(book.id)

        meta.metadata = dict(
            book_id=book.id,
            republished=True,
            published_type='whole',
            published_name='My Old Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme Pub Inc',
            from_year=2014,
            to_year=2015,
        )

        meta.serials = [
            dict(
                book_id=book.id,
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=1,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            ),
            dict(
                book_id=book.id,
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=2,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            ),
        ]

        cc_licence_id = cc_licence_by_code('CC BY-NC-SA', want='id', default=0)

        meta.derivative = dict(
            book_id=book.id,
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=cc_licence_id,
            from_year=2014,
            to_year=2015,
        )

        self.assertEqual(
            meta.texts(),
            [
                'This work was originally published in print in 2014-2015 as "My Old Book" by Acme Pub Inc.',
                '"My Story #1" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc.',
                '"My Story #2" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc.',
                '"My Book" is a derivative of "My Derivative" from 2014-2015 by John Doe used under CC BY-NC-SA.',
            ]
        )

    def test__to_year_requires(self):
        book = self.add(db.book, dict(
            name='test__to_year_requires',
        ))
        meta = PublicationMetadata(book.id)
        min_year, max_year = meta.year_range()

        requires = meta.to_year_requires('2000')
        self.assertTrue(isinstance(requires, IS_INT_IN_RANGE))
        self.assertEqual(requires.minimum, 2000)
        self.assertEqual(requires.maximum, max_year)
        self.assertEqual(
            requires.error_message,
            'Enter a year 2000 or greater'
        )

        requires = meta.to_year_requires('_fake_')
        self.assertTrue(isinstance(requires, IS_INT_IN_RANGE))
        self.assertEqual(requires.minimum, min_year)
        self.assertEqual(requires.maximum, max_year)
        self.assertEqual(
            requires.error_message,
            'Enter a year 1970 or greater'
        )

    def test__update(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103
        book = self.add(db.book, dict(
            name='test__update',
        ))

        meta = PublicationMetadata(book.id)

        def get_metadatas(book_id):
            query = (db.publication_metadata.book_id == book_id)
            return db(query).select(
                orderby=[db.publication_metadata.id],
            )

        def get_serials(book_id):
            query = (db.publication_serial.book_id == book_id)
            return db(query).select(
                orderby=[
                    db.publication_serial.story_number,
                    db.publication_serial.id,
                ],
            )

        self.assertEqual(len(get_metadatas(book.id)), 0)
        self.assertEqual(len(get_serials(book.id)), 0)

        # Add blank record
        meta.metadata = {}
        meta.serials = [{}]
        meta.update()
        got = get_metadatas(book.id)
        self.assertEqual(len(got), 1)
        metadata_id = got[0].id

        got = get_serials(book.id)
        self.assertEqual(len(got), 1)
        serial_ids = [got[0].id]

        # Add populated records
        meta.metadata = {'publisher': 'aaa'}
        meta.serials = [
            {
                'publisher': 'bbb',
                'story_number': 1,
            },
            {
                'publisher': 'ccc',
                'story_number': 2,
            },
        ]

        meta.update()
        got = get_metadatas(book.id)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].publisher, 'aaa')
        # existing record should be reused.
        self.assertTrue(got[0].id == metadata_id)

        got = get_serials(book.id)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0].publisher, 'bbb')
        self.assertEqual(got[0].story_number, 1)
        self.assertEqual(got[1].publisher, 'ccc')
        self.assertEqual(got[1].story_number, 2)

        # existing record should be reused.
        self.assertTrue(got[0].id in serial_ids or got[1].id in serial_ids)
        serial_ids = [got[0].id, got[1].id]

        # Add fewer serial records
        meta.serials = [
            {
                'publisher': 'ddd',
                'story_number': 3,
            },
        ]

        meta.update()
        got = get_metadatas(book.id)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].publisher, 'aaa')
        # existing record should be reused.
        self.assertTrue(got[0].id == metadata_id)

        got = get_serials(book.id)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].publisher, 'ddd')
        self.assertEqual(got[0].story_number, 3)
        # existing record should be reused.
        self.assertTrue(got[0].id in serial_ids)

        # cleanup
        for record in get_metadatas(book.id):
            self._objects.append(record)
        for record in get_serials(book.id):
            self._objects.append(record)

    def test__validate(self):
        book = self.add(db.book, dict(
            name='test__validate',
        ))

        meta = PublicationMetadata(book.id)
        self.assertEqual(meta.errors, {})
        meta.validate()
        self.assertEqual(meta.errors, {})

        metadata = dict(
            republished=True,
            published_type='whole',
            published_name='My Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme',
            from_year=1999,
            to_year=2000,
        )

        serials = [
            dict(
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=1,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            ),
            dict(
                published_name='My Story',
                published_format='paper',
                publisher_type='press',
                publisher='Acme Pub Inc',
                story_number=2,
                serial_title='Aaa Series',
                serial_number=2,
                from_year=2014,
                to_year=2015,
            )
        ]

        derivative = dict(
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=1,
            from_year=2014,
            to_year=2015,
        )

        meta.metadata = dict(metadata)
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.metadata['published_type'] = '_fake_'
        meta.validate()
        self.assertEqual(
            meta.errors['publication_metadata_published_type'],
            'Please select an option'
        )

        # whole
        meta.metadata['published_type'] = 'whole'
        meta.metadata['published_name'] = ''
        meta.metadata['published_format'] = '_fake_'
        meta.metadata['publisher_type'] = '_fake_'
        meta.metadata['publisher'] = ''
        meta.metadata['from_year'] = -1
        meta.metadata['to_year'] = -2
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_metadata_published_name',
                'publication_metadata_published_format',
                'publication_metadata_publisher_type',
                'publication_metadata_publisher',
                'publication_metadata_from_year',
                'publication_metadata_to_year',
            ])
        )
        meta.metadata = dict(metadata)
        meta.metadata['from_year'] = 2000
        meta.metadata['to_year'] = 1999
        meta.validate()
        self.assertEqual(
            meta.errors['publication_metadata_to_year'],
            'Enter a year 2000 or greater'
        )

        # serial
        meta.metadata = dict(metadata)
        meta.metadata['published_type'] = 'serial'
        meta.serials = []
        meta.derivative = {}
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.serials = [dict(serials[0])]
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.serials[0]['published_name'] = ''
        meta.serials[0]['published_format'] = '_fake_'
        meta.serials[0]['publisher_type'] = '_fake_'
        meta.serials[0]['publisher'] = ''
        meta.serials[0]['from_year'] = -1
        meta.serials[0]['to_year'] = -2
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_serial_published_name__0',
                'publication_serial_published_format__0',
                'publication_serial_publisher_type__0',
                'publication_serial_publisher__0',
                'publication_serial_from_year__0',
                'publication_serial_to_year__0',
            ])
        )
        meta.serials = [dict(serials[0])]
        meta.validate()
        self.assertEqual(meta.errors, {})
        meta.serials[0]['from_year'] = 1981
        meta.serials[0]['to_year'] = 1980
        meta.validate()
        self.assertEqual(
            meta.errors['publication_serial_to_year__0'],
            'Enter a year 1981 or greater'
        )

        meta.serials = list(serials)
        meta.validate()
        self.assertEqual(meta.errors, {})
        meta.serials[0]['published_name'] = ''
        meta.serials[1]['published_format'] = '_fake_'
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_serial_published_name__0',
                'publication_serial_published_format__1',
            ])
        )

        # derivative
        meta.metadata = dict(metadata)
        meta.serials = list(serials)
        meta.deriviate = dict(derivative)
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.derivative['title'] = ''
        meta.derivative['creator'] = ''
        meta.derivative['cc_licence_id'] = 999999
        meta.derivative['from_year'] = -1
        meta.derivative['to_year'] = -2
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'derivative_title',
                'derivative_creator',
                'derivative_cc_licence_id',
                'derivative_from_year',
                'derivative_to_year',
            ])
        )
        meta.deriviate = dict(derivative)
        meta.derivative['from_year'] = 1977
        meta.derivative['to_year'] = 1976
        meta.validate()
        self.assertEqual(
            meta.errors['derivative_to_year'],
            'Enter a year 1977 or greater'
        )

    def test__year_range(self):
        str_to_date = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        book = self.add(db.book, dict(
            name='test__year_range',
        ))

        meta = PublicationMetadata(book.id)

        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        self.assertEqual(
            meta._publication_year_range,
            (None, None)
        )
        min_year, max_year = meta.year_range()
        self.assertEqual(min_year, 1970)
        self.assertEqual(max_year, 2014 + 5)
        self.assertEqual(
            meta._publication_year_range,
            (1970, 2014 + 5)
        )

        # Test cache
        meta._publication_year_range = (888, 999)
        self.assertEqual(meta.year_range(), (888, 999))


class TestFunctions(LocalTestCase):

    def test__cc_licence_by_code(self):
        cc_licence = self.add(db.cc_licence, dict(
            code='_test_'
        ))

        got = cc_licence_by_code('_test_')
        self.assertEqual(got.id, cc_licence.id)
        self.assertEqual(got.code, '_test_')

        self.assertEqual(cc_licence_by_code(
            '_test_', want='id'), cc_licence.id)
        self.assertEqual(cc_licence_by_code('_test_', want='code'), '_test_')

        self.assertEqual(cc_licence_by_code('_fake_', default={}), {})
        self.assertEqual(cc_licence_by_code('_fake_', want='id', default=0), 0)
        self.assertEqual(cc_licence_by_code(
            '_fake_', want='code', default='mycode'), 'mycode')

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
            # (data, template, expect)
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

    def test__update_creator_indicia(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        creator = self.add(
            db.creator,
            dict(path_name='Update Creator Indicia')
        )
        self.assertEqual(creator.indicia_portrait, None)
        self.assertEqual(creator.indicia_landscape, None)
        self.assertEqual(creator.indicia_start, None)

        update_creator_indicia(creator)

        creator_1 = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator_1.indicia_start, None)
        # creator.indicia_portrait.ae60e66e0ada0b82.696e64696369612e706e67.png
        self.assertRegexpMatches(
            creator_1.indicia_portrait,
            r'^creator\.indicia_portrait\.[a-z0-9.]+\.png$'
        )
        self.assertRegexpMatches(
            creator_1.indicia_landscape,
            r'^creator\.indicia_landscape\.[a-z0-9.]+\.png$'
        )

        # Test in progress
        creator.update_record(
            indicia_portrait=None,
            indicia_landscape=None,
            indicia_start=datetime.datetime.now(),
        )
        db.commit()

        self.assertRaises(
            IndiciaUpdateInProgress, update_creator_indicia, creator)
        # The function should see it as in progress, so the indicias should
        # not be updated.
        creator_1 = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator_1.indicia_portrait, None)
        self.assertEqual(creator_1.indicia_landscape, None)

        # Test background
        creator.update_record(
            indicia_portrait=None,
            indicia_landscape=None,
            indicia_start=None,
        )
        db.commit()

        update_creator_indicia(creator, background=True, nice=True)

        creator_1 = entity_to_row(db.creator, creator.id)
        self.assertAlmostEqual(
            creator_1.indicia_start,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
