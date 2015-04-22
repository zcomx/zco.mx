#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/indicias.py

"""
import datetime
import os
import shutil
import time
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from gluon.validators import IS_INT_IN_RANGE
from applications.zcomx.modules.books import short_url as book_short_url
from applications.zcomx.modules.creators import short_url as creator_short_url
from applications.zcomx.modules.images import \
    on_delete_image, \
    store
from applications.zcomx.modules.indicias import \
    BookIndiciaPage, \
    BookIndiciaPagePng, \
    CreatorIndiciaPage, \
    CreatorIndiciaPagePng, \
    IndiciaPage, \
    IndiciaSh, \
    IndiciaShError, \
    PublicationMetadata, \
    cc_licence_by_code, \
    cc_licence_places, \
    cc_licences, \
    create_creator_indicia, \
    render_cc_licence
from applications.zcomx.modules.tests.runner import \
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
# C0302: *Too many lines in module (%%s)*
# pylint: disable=C0302


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _auth_user = None
    _book = None
    _book_page = None
    _creator = None
    _image_dir = '/tmp/test_indicias'
    _image_name = 'file.jpg'
    _test_data_dir = None
    _type_id_by_name = {}

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

        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id

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
            name_for_url='ImageTestCase',
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

    def test__call_to_action_text(self):
        data = dict(
            twitter=None,
            tumblr=None,
            facebook=None,
        )
        self._creator.update_record(**data)
        db.commit()

        indicia = BookIndiciaPage(self._book)
        xml = indicia.call_to_action_text()
        v = int(time.mktime(request.now.timetuple()))
        self.assertEqual(
            xml.xml(),
            'IF YOU ENJOYED THIS WORK YOU CAN HELP OUT BY GIVING SOME MONIES!!&nbsp; OR BY TELLING OTHERS ON <a href="https://twitter.com/share?url=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase&amp;text=Check+out+%27Image+Test+Case%27+by+First+Last&amp;hashtage=" target="_blank">TWITTER</a>, <a href="https://www.tumblr.com/share/photo?source=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase%2F001.jpg&amp;clickthru=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase&amp;caption=Check+out+Image+Test+Case+by+%3Ca+class%3D%22tumblelog%22%3EFirst+Last%3C%2Fa%3E" target="_blank">TUMBLR</a> AND <a href="http://www.facebook.com/sharer.php?p%5Burl%5D=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase%2F001&amp;v={v}" target="_blank">FACEBOOK</a>.'.format(cid=self._creator.id, v=v)
        )

    def test__follow_icons(self):
        socials = dict(
            twitter='@tweeter',
            tumblr='http://tmblr.tumblr.com',
            facebook='http://www.facebook.com/facepalm',
        )
        self._creator.update_record(**socials)
        db.commit()
        indicia = BookIndiciaPage(self._book)
        icons = indicia.follow_icons()
        self.assertEqual(sorted(icons.keys()), sorted(socials.keys()))

        # facebook
        soup = BeautifulSoup(str(icons['facebook']))
        # <a href="http://www.facebook.com/facepalm" target="_blank">
        #     <img src="/zcomx/static/images/facebook_logo.svg"/>
        # </a>
        anchor = soup.a
        self.assertEqual(anchor['href'], 'http://www.facebook.com/facepalm')
        self.assertEqual(anchor['target'], '_blank')
        img = anchor.img
        self.assertEqual(img['src'], '/zcomx/static/images/facebook_logo.svg')

        # tumblr
        soup = BeautifulSoup(str(icons['tumblr']))
        # <a href="https://www.tumblr.com/follow/tmblr" target="_blank">
        #     <img src="/zcomx/static/images/tumblr_logo.svg"/>
        # </a>
        anchor = soup.a
        self.assertEqual(anchor['href'], 'https://www.tumblr.com/follow/tmblr')
        self.assertEqual(anchor['target'], '_blank')
        img = anchor.img
        self.assertEqual(img['src'], '/zcomx/static/images/tumblr_logo.svg')

        # twitter
        soup = BeautifulSoup(str(icons['twitter']))
        # <a href="http://twitter.com/intent/follow?screen_name=@tweeter" target="_blank">
        #     <img src="/zcomx/static/images/twitter_logo.svg"/>
        # </a>
        anchor = soup.a
        self.assertEqual(
            anchor['href'],
            'https://twitter.com/intent/follow?screen_name=@tweeter'
        )
        self.assertEqual(anchor['target'], '_blank')
        img = anchor.img
        self.assertEqual(img['src'], '/zcomx/static/images/twitter_logo.svg')

    def test__get_orientation(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
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
            '<a href="{b_url}">IMAGE TEST CASE</a>&nbsp; IS COPYRIGHT (C) {y} BY <a href="{c_url}">FIRST LAST</a>.&nbsp; ALL RIGHTS RESERVED.&nbsp; PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(
                b_url=book_short_url(self._book),
                c_url=creator_short_url(self._creator),
                y=this_year
            )
        )

        cc_licence_id = cc_licence_by_code('CC BY', want='id', default=0)
        self._book.update_record(cc_licence_id=cc_licence_id)
        db.commit()
        book = db(db.book.id == self._book.id).select().first()

        indicia = BookIndiciaPage(book)
        self.assertEqual(
            indicia.licence_text(),
            '<a href="{b_url}">IMAGE TEST CASE</a>&nbsp; IS COPYRIGHT (C) {y} BY <a href="{c_url}">FIRST LAST</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="http://creativecommons.org/licenses/by/4.0" target="_blank">CC BY 4.0 INT`L LICENSE</a>.'.format(
                b_url=book_short_url(self._book),
                c_url=creator_short_url(self._creator),
                y=this_year
            )
        )

        # template_field='template_img'
        self.assertEqual(
            indicia.licence_text(template_field='template_img'),
            ' "IMAGE TEST CASE" IS COPYRIGHT (C) {y} BY FIRST LAST.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT http://creativecommons.org/licenses/by/4.0.'.format(
                y=this_year
            )
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
        # <div class="indicia_preview_section portrait">
        #   <div class="indicia_image_container"><img src="/zcomx/static/images/indicia_image.png" /></div>
        #   <div class="indicia_text_container">
        #     <div class="call_to_action">IF YOU ENJOYED THIS WORK YOU CAN HELP OUT BY GIVING SOME MONIES!!&nbsp; OR BY TELLING OTHERS ON <a href="https://twitter.com/share?url=Image_Test_Case&amp;text=Check+out+%27Image+Test+Case%27+by+First+Last&amp;hashtage=" target="_blank">TWITTER</a>, <a href="https://www.tumblr.com/share/photo?source=Image_Test_Case%2F001.png&amp;clickthru=Image_Test_Case&amp;caption=Check+out+Image+Test+Case+by+%3Ca+class%3D%22tumblelog%22%3EFirst+Last%3C%2Fa%3E" target="_blank">TUMBLR</a> AND <a href="http://www.facebook.com/sharer.php?p%5Burl%5D=Image_Test_Case%2F001.png&amp;s=100" target="_blank">FACEBOOK</a>.
        #     </div>
        #     <div class="contribute_widget"></div>
        #     <div class="follow_creator">FOLLOW<a href="None://9996.zco.mx">First Last</a></div>
        #     <div class="follow_icons">
        #       <div class="follow_icon"><a href="https://www.tumblr.com" target="_blank"><img src="/zcomx/static/images/tumblr_logo.svg" /></a>
        #       </div>
        #       <div class="follow_icon"><a href="https://twitter.com" target="_blank"><img src="/zcomx/static/images/twitter_logo.svg" /></a>
        #       </div>
        #       <div class="follow_icon"><a href="https://www.facebook.com" target="_blank"><img src="/zcomx/static/images/facebook_logo.svg" /></a>
        #       </div>
        #     </div>
        #     <div class="copyright_licence"><a href="Image_Test_Case">IMAGE TEST CASE</a> &nbsp; IS COPYRIGHT (C) 2015 BY <a href="None://9996.zco.mx">FIRST LAST</a>.  ALL RIGHTS RESERVED.  PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.
        #     </div>
        #   </div>
        # </div>

        self.assertEqual(div['class'], 'indicia_preview_section portrait')
        div_1 = div.div
        div_2 = div_1.nextSibling
        div_2a = div_2.div
        div_2b = div_2a.nextSibling
        div_2c = div_2b.nextSibling
        div_2d = div_2c.nextSibling
        div_2e = div_2d.nextSibling
        div_2di = div_2d.div
        div_2dii = div_2di.nextSibling
        div_2diii = div_2dii.nextSibling

        self.assertEqual(div_1['class'], 'indicia_image_container')
        self.assertEqual(div_2['class'], 'indicia_text_container')
        self.assertEqual(div_2a['class'], 'call_to_action')
        self.assertEqual(div_2b['class'], 'contribute_widget')
        self.assertEqual(div_2c['class'], 'follow_creator')
        self.assertEqual(div_2d['class'], 'follow_icons')
        self.assertEqual(div_2e['class'], 'copyright_licence')
        self.assertEqual(div_2di['class'], 'follow_icon')
        self.assertEqual(div_2dii['class'], 'follow_icon')
        self.assertEqual(div_2diii['class'], 'follow_icon')

        self.assertEqual(
            div_1.img['src'], '/zcomx/static/images/indicia_image.png')
        self.assertTrue(div_2a.contents[0].startswith('IF YOU ENJOYED '))
        self.assertEqual(div_2b.contents, [])
        self.assertEqual(div_2c.contents[0], 'FOLLOW')
        self.assertEqual(div_2c.a.string, 'First Last')
        self.assertTrue('ALL RIGHTS RESERVED' in div_2e.contents[3])

        self.assertEqual(div_2di.a['href'], 'https://www.tumblr.com')
        self.assertEqual(div_2di.img['src'], '/zcomx/static/images/tumblr_logo.svg')
        self.assertEqual(div_2dii.a['href'], 'https://twitter.com')
        self.assertEqual(div_2dii.img['src'], '/zcomx/static/images/twitter_logo.svg')
        self.assertEqual(div_2diii.a['href'], 'http://www.facebook.com')
        self.assertEqual(div_2diii.img['src'], '/zcomx/static/images/facebook_logo.svg')

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

    def test__call_to_action_text(self):
        indicia = BookIndiciaPagePng(self._book)
        self.assertEqual(
            indicia.call_to_action_text(),
            'IF YOU ENJOYED THIS WORK YOU CAN HELP OUT BY GIVING SOME MONIES!!  OR BY TELLING OTHERS ON TWITTER, TUMBLR AND FACEBOOK.'
        )

    def test__create(self):
        png_page = BookIndiciaPagePng(self._book)
        png = png_page.create()

        output, error = UnixFile(png).file()
        self.assertTrue('PNG image' in output)
        self.assertEqual(error, '')


class TestCreatorIndiciaPage(ImageTestCase):
    def test____init__(self):
        indicia = CreatorIndiciaPage(self._creator)
        self.assertTrue(indicia)

    def test__licence_text(self):
        this_year = datetime.date.today().year

        indicia = CreatorIndiciaPage(self._creator)
        self.assertEqual(
            indicia.licence_text(),
            '<a href="/">NAME OF BOOK</a>&nbsp; IS COPYRIGHT (C) {y} BY <a href="{url}">FIRST LAST</a>.&nbsp; ALL RIGHTS RESERVED.&nbsp; PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(url=creator_short_url(self._creator), y=this_year)
        )


class TestCreatorIndiciaPagePng(ImageTestCase):
    def test____init__(self):
        png_page = CreatorIndiciaPagePng(self._creator)
        self.assertTrue(png_page)
        self.assertEqual(png_page.creator.id, self._creator.id)

    def test__create(self):
        data = dict(
            indicia_portrait=None,
            indicia_landscape=None,
        )
        self._creator.update_record(**data)
        db.commit()

        png_page = CreatorIndiciaPagePng(self._creator)
        filename = png_page.create('portrait')
        self.assertRegexpMatches(
            filename,
            r'^applications/zcomx/uploads/original/../tmp/tmp.*/indicia.png$'
        )
        im = Image.open(filename)
        width, height = im.size
        self.assertTrue(height > width)

        filename = png_page.create('landscape')
        self.assertRegexpMatches(
            filename,
            r'^applications/zcomx/uploads/original/../tmp/tmp.*/indicia.png$'
        )
        im = Image.open(filename)
        width, height = im.size
        self.assertTrue(width > height)


class TestIndiciaPage(LocalTestCase):
    def test____init__(self):
        indicia = IndiciaPage(None)
        self.assertTrue(indicia)

    def test__call_to_action_text(self):
        indicia = IndiciaPage(None)
        self.assertEqual(
            indicia.call_to_action_text(),
            'IF YOU ENJOYED THIS WORK YOU CAN HELP OUT BY GIVING SOME MONIES!!  OR BY TELLING OTHERS ON TWITTER, TUMBLR AND FACEBOOK.'
        )

    def test__default_licence(self):
        indicia = IndiciaPage(None)
        default = indicia.default_licence()
        self.assertEqual(default.code, 'All Rights Reserved')
        fields = ['id', 'number', 'code', 'url', 'template_img', 'template_web']
        for f in fields:
            self.assertTrue(f in default.keys())

    def test__follow_icons(self):
        indicia = IndiciaPage(None)
        self.assertEqual(indicia.follow_icons(), {})

    def test__licence_text(self):
        indicia = IndiciaPage(None)
        this_year = datetime.date.today().year
        self.assertEqual(
            indicia.licence_text(),
            '<a href="/">NAME OF BOOK</a>&nbsp; IS COPYRIGHT (C) {y} BY <a href="/">CREATOR NAME</a>.&nbsp; ALL RIGHTS RESERVED.&nbsp; PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )
        # template_field='template_img'
        self.assertEqual(
            indicia.licence_text(template_field='template_img'),
            ' "NAME OF BOOK" IS COPYRIGHT (C) 2015 BY CREATOR NAME.  ALL RIGHTS RESERVED.  PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year)
        )

    def test__render(self):
        indicia = IndiciaPage(None)

        # test without creator name
        got = indicia.render()
        soup = BeautifulSoup(str(got))

        # <div class="indicia_preview_section portrait">
        #   <div class="indicia_image_container">
        #     <img src="/zcomx/static/images/indicia_image.png" />
        #   </div>
        #   <div class="indicia_text_container">
        #     <div class="call_to_action">
        #       IF YOU ENJOYED THIS WORK... TUMBLR AND FACEBOOK.
        #     </div>
        #     <div class="contribute_widget"></div>
        #     <div class="copyright_licence">
        #       <a href="/">NAME OF BOOK</a> &nbsp; IS COPYRIGHT (C) 2015 BY
        #       <a href="/">CREATOR NAME</a>.  ALL RIGHTS RESERVED.
        #       PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED
        #       FROM THE AUTHOR.
        #     </div>
        #   </div>
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
        self.assertEqual(div_2a['class'], 'call_to_action')
        self.assertTrue(div_2a.string.startswith('IF YOU ENJOYED '))
        div_2b = div_2a.nextSibling
        self.assertEqual(div_2b['class'], 'contribute_widget')
        self.assertEqual(div_2b.contents, [])
        div_2c = div_2b.nextSibling
        self.assertEqual(div_2c['class'], 'copyright_licence')
        self.assertTrue('ALL RIGHTS RESERVED' in div_2c.contents[3])

        # test orientation
        got = indicia.render(orientation='landscape')
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section landscape')

        # test creator name set but no indicia image
        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            indicia_image=None,
        ))
        indicia = IndiciaPage(None)
        indicia.creator = creator
        got = indicia.render()

        soup = BeautifulSoup(str(got))
        div = soup.div

        # <div class="indicia_preview_section portrait">
        #   <div class="indicia_image_container">
        #     <img src="/zcomx/static/images/indicia_image.png" />
        #   </div>
        #   <div class="indicia_text_container">
        #     <div class="call_to_action">
        #       IF YOU ENJOYED THIS WORK... TUMBLR AND FACEBOOK.
        #     </div>
        #     <div class="contribute_widget"></div>
        #     <div class="follow_creator">
        #       FOLLOW<a href="https://10001.zco.mx">First Last</a>
        #     </div>
        #     <div class="copyright_licence">
        #       <a href="/">NAME OF BOOK</a> &nbsp; IS COPYRIGHT (C) 2015 BY
        #       <a href="/">CREATOR NAME</a>.  ALL RIGHTS RESERVED.
        #       PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED
        #       FROM THE AUTHOR.
        #     </div>
        #   </div>
        # </div>

        self.assertEqual(div['class'], 'indicia_preview_section portrait')
        div_1 = div.div
        self.assertEqual(div_1['class'], 'indicia_image_container')
        img = div_1.img
        self.assertEqual(img['src'], '/zcomx/static/images/indicia_image.png')
        div_2 = div_1.nextSibling
        self.assertEqual(div_2['class'], 'indicia_text_container')
        div_2a = div_2.div
        div_2b = div_2a.nextSibling
        self.assertEqual(div_2b['class'], 'contribute_widget')
        div_2c = div_2b.nextSibling
        self.assertEqual(div_2c['class'], 'follow_creator')
        self.assertEqual(div_2c.contents[0], 'FOLLOW')
        self.assertEqual(div_2c.a.string, 'First Last')
        div_2d = div_2c.nextSibling
        self.assertTrue('ALL RIGHTS RESERVED' in div_2d.contents[3])

        # test creator with indicia
        indicia = IndiciaPage(None)
        creator.update_record(indicia_image='creator.indicia_image.000.aaa.jpg')
        db.commit()
        indicia.creator = creator
        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        div_1 = div.div
        img = div_1.img
        self.assertEqual(
            img['src'], '/images/download/creator.indicia_image.000.aaa.jpg?size=web')


class TestIndiciaPagePng(ImageTestCase):

    # Use BookIndiciaPagePng (which subclasses IndiciaPagePng) to test.
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
            """ "IMAGE TEST CASE" IS COPYRIGHT (C) 2015 BY FIRST LAST.  ALL RIGHTS RESERVED.  PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR."""
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


class TestIndiciaSh(ImageTestCase):

    def test____init__(self):
        indicia_sh = IndiciaSh(101, '', '')
        self.assertTrue(indicia_sh)
        self.assertEqual(
            indicia_sh.font,
            os.path.abspath(
                'applications/zcomx/static/fonts/sf_cartoonist/sfcartoonisthand-bold-webfont.ttf'
            )
        )
        self.assertTrue(os.path.exists(indicia_sh.font))
        self.assertEqual(
            indicia_sh.action_font,
            os.path.abspath(
                'applications/zcomx/static/fonts/brushy_cre/Brushy-Cre.ttf'
            )
        )
        self.assertTrue(os.path.exists(indicia_sh.action_font))

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
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc. '
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc. '
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
            is_anthology=False,
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
            sequence=1,
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
            sequence=0,
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
        expect.serials = [serial_2, serial_1]   # Sorted by sequence
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
                'This work was originally published digitally in 2000-2001 as "Sheerios 2 #2" at Acme 2. '
                'This work was originally published digitally in 1998-1999 as "Sheerios #1" at Acme. '
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

    def test__publication_year(self):
        book = self.add(db.book, dict(name='test__publication_year'))
        meta = PublicationMetadata(book.id)

        # Test: no metadata or serial data
        self.assertRaises(ValueError, meta.publication_year)

        # Test: metadata, no serial
        metadata = Storage(dict(
            book_id=book.id,
            from_year=1998,
            to_year=1999,
        ))
        meta.metadata = metadata
        self.assertEqual(meta.publication_year(), 1999)

        # Test: single serial
        serial_1 = Storage(dict(
            book_id=book.id,
            from_year=2010,
            to_year=2011,
        ))
        meta.serials = [serial_1]
        self.assertEqual(meta.publication_year(), 2011)

        # Test: multiple serial
        serial_2 = Storage(dict(
            book_id=book.id,
            from_year=2013,
            to_year=2014,
        ))
        serial_3 = Storage(dict(
            book_id=book.id,
            from_year=2000,
            to_year=2001,
        ))
        meta.serials = [serial_1, serial_2, serial_3]
        self.assertEqual(meta.publication_year(), 2014)

    def test__serial_text(self):

        # METADATA see mod 12687

        #     repub -> repub - serial -> anthology no -> digital [8]
        #     repub -> repub - serial -> anthology no -> paper -> press [9]
        #     repub -> repub - serial -> anthology no -> paper -> self [10]
        #     repub -> repub - serial -> anthology yes -> digital [11]
        #     repub -> repub - serial -> anthology yes -> paper -> press [12]
        #     repub -> repub - serial -> anthology yes -> paper -> self [13]

        # [8] This work was originally published digitally in YYYY as NAME #1 at username.tumblr.com.
        #     This work was originally published digitally in YYYY as NAME #2 at username.tumblr.com.
        # ...
        #
        # [9] This work was originally published in print in YYYY as NAME #1 by publisher/press.
        #     This work was originally published in print in YYYY as NAME #2 by publisher/press.
        # ...
        #
        # [10] This work was originally self-published in print in as NAME #1 YYYY.
        #      This work was originally self-published in print in as NAME #2 YYYY.
        # ...
        #
        # [11] STORY_NAME #1 was originally published digitally in ANTHOLOGY_NAME in YYYY at username.tumblr.com.
        #      STORY_NAME #2 was originally published digitally in ANTHOLOGY_NAME in YYYY at username.tumblr.com.
        # ...
        #
        # [12] STORY_NAME #1 was originally published in print in ANTHOLOGY_NAME in YYYY by publisher/press.
        #      STORY_NAME #2 was originally published in print in ANTHOLOGY_NAME in YYYY by publisher/press.
        # ...
        #
        # [13] STORY_NAME #1 was originally self-published in print in ANTHOLOGY_NAME in YYYY.
        #      STORY_NAME #2 was originally self-published in print in ANTHOLOGY_NAME in YYYY.
        # ...

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
        s.published_name = '-'
        s.published_format = 'digital'
        s.publisher_type = 'self'
        s.publisher = 'tumblr.com'
        s.serial_title = 'My Story'
        s.story_number = 0

        expects = [
            'This work was originally published digitally in 2014-2015 as "My Story" at tumblr.com.',
            'This work was originally published digitally in 2014-2015 as "My Story #1" at tumblr.com.',
            'This work was originally published digitally in 2014-2015 as "My Story #2" at tumblr.com.',
        ]
        for idx, expect in enumerate(expects):
            s.serial_number = idx
            self.assertEqual(meta.serial_text(s, is_anthology=False), expect)

        # [9]
        s = Storage(default_serial)
        s.published_name = '-'
        s.published_format = 'paper'
        s.publisher_type = 'press'
        s.publisher = 'Acme Pub Inc.'
        s.serial_title = 'My Story'
        s.story_number = 0

        expects = [
            'This work was originally published in print in 2014-2015 as "My Story" by Acme Pub Inc.',
            'This work was originally published in print in 2014-2015 as "My Story #1" by Acme Pub Inc.',
            'This work was originally published in print in 2014-2015 as "My Story #2" by Acme Pub Inc.',
        ]

        for idx, expect in enumerate(expects):
            s.serial_number = idx
            self.assertEqual(meta.serial_text(s, is_anthology=False), expect)

        # [10]
        s = Storage(default_serial)
        s.published_name = '-'
        s.published_format = 'paper'
        s.publisher_type = 'self'
        s.publisher = 'Acme Pub Inc.'
        s.serial_title = 'My Story'
        s.story_number = 0

        expects = [
            'This work was originally self-published in print in 2014-2015 as "My Story".',
            'This work was originally self-published in print in 2014-2015 as "My Story #1".',
            'This work was originally self-published in print in 2014-2015 as "My Story #2".',
        ]

        for idx, expect in enumerate(expects):
            s.serial_number = idx
            self.assertEqual(meta.serial_text(s, is_anthology=False), expect)

        # [11]
        s = Storage(default_serial)
        s.published_name = 'My Story'
        s.published_format = 'digital'
        s.publisher_type = 'self'
        s.publisher = 'tumblr.com'
        s.serial_title = 'Aaa Series'
        s.serial_number = 9

        expects = [
            '"My Story" was originally published digitally in "Aaa Series #9" in 2014-2015 at tumblr.com.',
            '"My Story #1" was originally published digitally in "Aaa Series #9" in 2014-2015 at tumblr.com.',
            '"My Story #2" was originally published digitally in "Aaa Series #9" in 2014-2015 at tumblr.com.',
        ]

        for idx, expect in enumerate(expects):
            s.story_number = idx
            self.assertEqual(meta.serial_text(s, is_anthology=True), expect)

        # [12]
        s = Storage(default_serial)
        s.published_name = 'My Story'
        s.published_format = 'paper'
        s.publisher_type = 'press'
        s.publisher = 'Acme Pub Inc.'
        s.serial_title = 'Aaa Series'
        s.serial_number = 9

        expects = [
            '"My Story" was originally published in print in "Aaa Series #9" in 2014-2015 by Acme Pub Inc.',
            '"My Story #1" was originally published in print in "Aaa Series #9" in 2014-2015 by Acme Pub Inc.',
            '"My Story #2" was originally published in print in "Aaa Series #9" in 2014-2015 by Acme Pub Inc.',
        ]

        for idx, expect in enumerate(expects):
            s.story_number = idx
            self.assertEqual(meta.serial_text(s, is_anthology=True), expect)

        # [13]
        s = Storage(default_serial)
        s.published_name = 'My Story'
        s.published_format = 'paper'
        s.publisher_type = 'self'
        s.publisher = 'Acme Pub Inc.'
        s.serial_title = 'Aaa Series'
        s.serial_number = 9

        expects = [
            '"My Story" was originally self-published in print in "Aaa Series #9" in 2014-2015.',
            '"My Story #1" was originally self-published in print in "Aaa Series #9" in 2014-2015.',
            '"My Story #2" was originally self-published in print in "Aaa Series #9" in 2014-2015.',
        ]

        for idx, expect in enumerate(expects):
            s.story_number = idx
            self.assertEqual(meta.serial_text(s, is_anthology=True), expect)

    def test__serials_text(self):
        book = self.add(db.book, dict(name='test__serials_text'))

        meta = PublicationMetadata(book.id)
        serial_1 = Storage(dict(
            book_id=book.id,
            sequence=0,
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
            sequence=1,
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

        meta.metadata = {'is_anthology': False}
        meta.serials = [serial_1]
        self.assertEqual(
            meta.serials_text(),
            ['This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.']
        )

        meta.serials = [serial_1, serial_2]
        self.assertEqual(
            meta.serials_text(),
            [
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.',
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.',
            ]
        )

        meta.metadata = {'is_anthology': True}
        meta.serials = [serial_1]
        self.assertEqual(
            meta.serials_text(),
            ['"My Story #1" was originally published in print in "Aaa Series #2" in 2014-2015 by Acme Pub Inc.']
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
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.',
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.',
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
            is_anthology=True,
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

        meta.metadata['is_anthology'] = False
        meta.validate()
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
                'publication_serial_published_format__0',
                'publication_serial_publisher_type__0',
                'publication_serial_publisher__0',
                'publication_serial_from_year__0',
                'publication_serial_to_year__0',
            ])
        )

        meta.metadata['is_anthology'] = True
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


class TestFunctions(ImageTestCase):

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
            book_type_id=self._type_id_by_name['one-shot'],
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

    def test__create_creator_indicia(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        fields = ['indicia_image', 'indicia_portrait', 'indicia_landscape']

        def exists(field, img_name):
            _, f = db.creator[field].retrieve(img_name, nameonly=True)
            return os.path.exists(f)

        # Test cleared
        data = dict(
            indicia_image=None,
            indicia_portrait=None,
            indicia_landscap=None,
        )
        self._creator.update_record(**data)
        db.commit()

        creator = entity_to_row(db.creator, self._creator.id)
        for f in fields:
            # Field is cleared
            self.assertEqual(creator[f], None)

        filename = self._prep_image('cbz_plus.png')
        indicia_image = store(db.creator.indicia_image, filename)
        self._creator.update_record(indicia_image=indicia_image)
        db.commit()

        create_creator_indicia(self._creator)

        creator_1 = entity_to_row(db.creator, self._creator.id)
        # Prove images exist
        for f in fields:
            # Field is not clear
            self.assertNotEqual(creator_1[f], None)
            # Prove image exists
            self.assertTrue(exists(f, creator_1[f]))

        # Cleanup
        fields = ['indicia_image', 'indicia_portrait', 'indicia_landscape']
        for field in fields:
            if creator_1[field]:
                on_delete_image(creator_1[field])
        data = dict(
            indicia_image=None,
            indicia_portrait=None,
            indicia_landscape=None,
        )
        creator_1.update_record(**data)
        db.commit()

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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
