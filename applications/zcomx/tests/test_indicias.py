#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/indicias.py

"""
import datetime
import os
import time
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from gluon.validators import IS_INT_IN_RANGE
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import \
    Book, \
    short_url as book_short_url
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator, \
    short_url as creator_short_url
from applications.zcomx.modules.images import \
    on_delete_image, \
    store
from applications.zcomx.modules.indicias import \
    BookIndiciaPage, \
    BookIndiciaPagePng, \
    CCLicence, \
    CreatorIndiciaPagePng, \
    Derivative, \
    IndiciaPage, \
    IndiciaSh, \
    IndiciaShError, \
    BookPublicationMetadata, \
    PublicationMetadata, \
    PublicationSerial, \
    cc_licence_places, \
    cc_licences, \
    create_creator_indicia, \
    render_cc_licence
from applications.zcomx.modules.links import \
    Link, \
    LinkType
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    ResizerQuick, \
    skip_if_quick
from applications.zcomx.modules.tests.runner import \
    LocalTestCase, \
    _mock_date as mock_date
from applications.zcomx.modules.shell_utils import UnixFile

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301
# C0302: *Too many lines in module (%%s)*
# pylint: disable=C0302


class WithObjectsTestCase(LocalTestCase):
    """ Base class for test cases. Sets up test data."""

    _auth_user = None
    _book = None
    _book_page = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):

        self._auth_user = self.add(AuthUser, dict(
            name='First Last'
        ))

        self._creator = self.add(Creator, dict(
            auth_user_id=self._auth_user.id,
            email='image_test_case@example.com',
            paypal_email='image_test_case@example.com',
        ))

        self._book = self.add(Book, dict(
            name='Image Test Case',
            number=1,
            book_type_id=BookType.by_name('ongoing').id,
            creator_id=self._creator.id,
            name_for_url='ImageTestCase-001',
        ))

        self._book_page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
            image='book_page.image.aaa.000.jpg',
        ))

        self.add(Link, dict(
            link_type_id=LinkType.by_code('buy_book').id,
            record_table='book',
            record_id=self._book.id,
            url='http://www.test.com',
            name='test',
        ))

        # Next book in series
        next_book = self.add(Book, dict(
            name=self._book.name,
            number=self._book.number + 1,
            book_type_id=self._book.book_type_id,
            creator_id=self._book.creator_id,
            name_for_url='ImageTestCase-002',
        ))

        self.add(BookPage, dict(
            book_id=next_book.id,
            page_no=1,
        ))

        super(WithObjectsTestCase, self).setUp()


class TestBookIndiciaPage(WithObjectsTestCase, ImageTestCase):

    def test____init__(self):
        indicia = BookIndiciaPage(self._book)
        self.assertTrue(indicia)

    def test__call_to_action_text(self):
        data = dict(
            twitter=None,
            tumblr=None,
            facebook=None,
        )
        self._creator = Creator.from_updated(self._creator, data)

        indicia = BookIndiciaPage(self._book)
        xml = indicia.call_to_action_text()
        v = int(time.mktime(request.now.timetuple()))
        self.assertEqual(
            xml.xml(),
            'IF YOU ENJOYED THIS WORK YOU CAN HELP OUT BY GIVING SOME MONIES!!  OR BY TELLING OTHERS ON <a href="https://twitter.com/share?url=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase-001&amp;text=Check+out+%27Image+Test+Case%27+by+First+Last&amp;hashtage=" target="_blank">TWITTER</a>, <a href="https://www.tumblr.com/share/photo?source=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase-001%2F001.jpg&amp;clickthru=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase-001&amp;caption=Check+out+Image+Test+Case+by+%3Ca+class%3D%22tumblelog%22%3EFirst+Last%3C%2Fa%3E" target="_blank">TUMBLR</a> AND <a href="http://www.facebook.com/sharer.php?p%5Burl%5D=http%3A%2F%2F{cid}.zco.mx%2FImageTestCase-001%2F001&amp;v={v}" target="_blank">FACEBOOK</a>.'.format(cid=self._creator.id, v=v)
        )

    def test__follow_icons(self):

        socials = dict(
            twitter='@tweeter',
            tumblr='http://tmblr.tumblr.com',
            facebook='http://www.facebook.com/facepalm',
        )
        self._creator = Creator.from_updated(self._creator, socials)
        indicia = BookIndiciaPage(self._book)
        icons = indicia.follow_icons()

        icon_keys = ['rss', 'tumblr', 'twitter', 'facebook']
        self.assertEqual(len(icons), len(icon_keys))

        # facebook
        soup = BeautifulSoup(str(icons[icon_keys.index('facebook')]))
        # <a href="http://www.facebook.com/facepalm" target="_blank">
        #     <img src="/zcomx/static/images/facebook_logo.svg"/>
        # </a>
        anchor = soup.a
        self.assertEqual(anchor['href'], 'http://www.facebook.com/facepalm')
        self.assertEqual(anchor['target'], '_blank')
        img = anchor.img
        self.assertEqual(img['src'], '/zcomx/static/images/facebook_logo.svg')

        # rss
        soup = BeautifulSoup(str(icons[icon_keys.index('rss')]))
        # <a class="rss_button" href="/rss/modal/12920" target="_blank">
        #     <img src="/zcomx/static/images/follow_logo.svg" />
        # </a>
        anchor = soup.a
        self.assertEqual(anchor['href'], '/rss/modal/{i}'.format(i=self._creator.id))
        self.assertEqual(anchor['target'], '_blank')
        img = anchor.img
        self.assertEqual(img['src'], '/zcomx/static/images/follow_logo.svg')

        # tumblr
        soup = BeautifulSoup(str(icons[icon_keys.index('tumblr')]))
        # <a href="https://www.tumblr.com/follow/tmblr" target="_blank">
        #     <img src="/zcomx/static/images/tumblr_logo.svg"/>
        # </a>
        anchor = soup.a
        self.assertEqual(anchor['href'], 'https://www.tumblr.com/follow/tmblr')
        self.assertEqual(anchor['target'], '_blank')
        img = anchor.img
        self.assertEqual(img['src'], '/zcomx/static/images/tumblr_logo.svg')

        # twitter
        soup = BeautifulSoup(str(icons[icon_keys.index('twitter')]))
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
        indicia = BookIndiciaPage(self._book)
        self.assertEqual(indicia._orientation, None)

        for t in ['portrait', 'landscape', 'square']:
            img = '{n}.png'.format(n=t)
            filename = self._prep_image(img)
            stored_filename = store(
                db.book_page.image, filename, resizer=ResizerQuick)
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

        cc_by = CCLicence.by_code('CC BY')
        self._book = Book.from_updated(self._book, dict(cc_licence_id=cc_by.id))
        indicia = BookIndiciaPage(self._book)
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

        portrait_filename = store(
            db.book_page.image,
            self._prep_image('portrait.png'),
            resizer=ResizerQuick
        )

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
        div_2bi = div_2b.div
        div_2bii = div_2bi.nextSibling
        div_2c = div_2b.nextSibling
        div_2d = div_2c.nextSibling
        div_2di = div_2d.div
        div_2dii = div_2di.nextSibling
        div_2diii = div_2dii.nextSibling
        div_2diiii = div_2diii.nextSibling
        div_2e = div_2d.nextSibling
        div_2f = div_2e.nextSibling

        self.assertEqual(div_1['class'], 'indicia_image_container')
        self.assertEqual(div_2['class'], 'indicia_text_container')
        self.assertEqual(div_2a['class'], 'call_to_action')
        self.assertEqual(div_2b['class'], 'row contribute_and_links_container non_empty bordered')
        self.assertEqual(div_2bi['class'], 'contribute_widget_container col-xs-12 col-sm-6 col-sm-offset-0')
        self.assertEqual(div_2bii['class'], 'book_links_container col-xs-12 col-sm-6 col-sm-offset-0')
        self.assertEqual(div_2c['class'], 'follow_creator')
        self.assertEqual(div_2d['class'], 'follow_icons')
        self.assertEqual(div_2di['class'], 'follow_icon')
        self.assertEqual(div_2dii['class'], 'follow_icon')
        self.assertEqual(div_2diii['class'], 'follow_icon')
        self.assertEqual(div_2diiii['class'], 'follow_icon')
        self.assertEqual(div_2e['class'], 'read_next_link')
        self.assertEqual(div_2f['class'], 'copyright_licence')

        self.assertEqual(
            div_1.img['src'], '/zcomx/static/images/indicia_image.png')
        self.assertTrue(div_2a.contents[0].startswith('IF YOU ENJOYED '))
        self.assertTrue('Contribute' in div_2bi.contents[0])
        self.assertTrue('Buy this book' in div_2bii.contents[0])
        self.assertEqual(div_2c.a.string, 'First Last')

        self.assertEqual(div_2di.a['href'], '/rss/modal/{cid}'.format(cid=self._creator.id))
        self.assertEqual(div_2di.img['src'], '/zcomx/static/images/follow_logo.svg')
        self.assertEqual(div_2dii.a['href'], 'https://www.tumblr.com')
        self.assertEqual(div_2dii.img['src'], '/zcomx/static/images/tumblr_logo.svg')
        self.assertEqual(div_2diii.a['href'], 'https://twitter.com')
        self.assertEqual(div_2diii.img['src'], '/zcomx/static/images/twitter_logo.svg')
        self.assertEqual(div_2diiii.a['href'], 'http://www.facebook.com')
        self.assertEqual(div_2diiii.img['src'], '/zcomx/static/images/facebook_logo.svg')

        anchor = div_2e.find('a')
        self.assertEqual(anchor.contents[0], 'Read Next')
        icon = anchor.find('i')
        self.assertEqual(icon['class'], 'glyphicon glyphicon-play')

        self.assertTrue('ALL RIGHTS RESERVED' in div_2f.contents[3])

        landscape_filename = store(
            db.book_page.image,
            self._prep_image('landscape.png'),
            resizer=ResizerQuick
        )
        self._book_page.update_record(image=landscape_filename)
        db.commit()

        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        indicia._orientation = None     # clear cache
        got = indicia.render()
        soup = BeautifulSoup(str(got))
        div = soup.div
        self.assertEqual(div['class'], 'indicia_preview_section landscape')


class TestBookIndiciaPagePng(WithObjectsTestCase, ImageTestCase):
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

    @skip_if_quick
    def test__create(self):
        filename = self._prep_image('portrait.png')
        stored_filename = store(
            db.book_page.image, filename, resizer=ResizerQuick)

        self._book_page.update_record(image=stored_filename)
        db.commit()

        png_page = BookIndiciaPagePng(self._book)
        png = png_page.create()

        output, error = UnixFile(png).file()
        self.assertTrue('PNG image' in output)
        self.assertEqual(error, '')


class TestCreatorIndiciaPagePng(WithObjectsTestCase):
    def test____init__(self):
        png_page = CreatorIndiciaPagePng(self._creator)
        self.assertTrue(png_page)
        self.assertEqual(png_page.creator.id, self._creator.id)

    @skip_if_quick
    def test__create(self):
        data = dict(
            indicia_portrait=None,
            indicia_landscape=None,
        )
        self._creator = Creator.from_updated(self._creator, data)

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

    def test__licence_text(self):
        this_year = datetime.date.today().year

        indicia = CreatorIndiciaPagePng(self._creator)
        self.assertEqual(
            indicia.licence_text(),
            '<a href="/">NAME OF BOOK</a>&nbsp; IS COPYRIGHT (C) {y} BY <a href="{url}">FIRST LAST</a>.&nbsp; ALL RIGHTS RESERVED.&nbsp; PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(url=creator_short_url(self._creator), y=this_year)
        )


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

    def test__follow_icons(self):
        indicia = IndiciaPage(None)
        self.assertEqual(indicia.follow_icons(), [])

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
            ' "NAME OF BOOK" IS COPYRIGHT (C) {y} BY CREATOR NAME.  ALL RIGHTS RESERVED.  PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.'.format(y=this_year).format(y=this_year)
        )


class TestIndiciaPagePng(WithObjectsTestCase, ImageTestCase):

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
            """ "IMAGE TEST CASE" IS COPYRIGHT (C) 2016 BY FIRST LAST.  ALL RIGHTS RESERVED.  PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR."""
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
        stored_filename = store(
            db.creator.indicia_image, filename, resizer=ResizerQuick)

        data = dict(indicia_image=stored_filename)
        png_page.creator = Creator.from_updated(png_page.creator, data)

        png_page = BookIndiciaPagePng(self._book)         # Reload
        _, expect = db.creator.indicia_image.retrieve(
            png_page.creator.indicia_image, nameonly=True)
        self.assertEqual(png_page.get_indicia_filename(), expect)

        # Test cache
        png_page._indicia_filename = '_cache_'
        self.assertEqual(
            png_page.get_indicia_filename(),
            '_cache_'
        )


class TestIndiciaSh(WithObjectsTestCase, ImageTestCase):

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

    @skip_if_quick
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


class TestBookPublicationMetadata(LocalTestCase):
    def test____init__(self):
        save_datetime_date = datetime.date

        str_to_date = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        book = self.add(Book, dict(
            name='TestBookPublicationMetadata',
        ))
        meta = BookPublicationMetadata(book)
        self.assertTrue(meta)
        self.assertEqual(
            meta.first_publication_text,
            'First publication: zco.mx 2014.'
        )

        datetime.date = save_datetime_date

    def test____str__(self):
        book = self.add(Book, dict(name='My Book'))

        meta = BookPublicationMetadata(book)
        self.assertEqual(str(meta), '')

        meta.metadata = PublicationMetadata(dict(
            book_id=book.id,
            republished=True,
            published_type='whole',
            published_name='My Old Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme Pub Inc',
            from_year=2014,
            to_year=2015,
        ))

        meta.serials = [
            PublicationSerial(dict(
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
            )),
            PublicationSerial(dict(
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
            )),
        ]

        cc_by_nc_sa = CCLicence.by_code('CC BY-NC-SA')

        meta.derivative = Derivative(dict(
            book_id=book.id,
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=cc_by_nc_sa.id,
            from_year=2014,
            to_year=2015,
        ))

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

        book = self.add(Book, dict(name='My Book'))

        cc_by_nd = CCLicence.by_code('CC BY-ND')

        meta = BookPublicationMetadata(book)
        meta.derivative = Derivative(dict(
            book_id=book.id,
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=cc_by_nd.id,
            from_year=2014,
            to_year=2015,
        ))

        self.assertEqual(
            meta.derivative_text(),
            '"My Book" is a derivative of "My Derivative" from 2014-2015 by John Doe used under CC BY-ND.'
        )

    def test__from_book(self):
        book = self.add(Book, dict(name='test__from_book'))

        def test_meta(meta, expect):
            self.assertEqual(meta.metadata, expect.metadata)
            self.assertEqual(meta.serials, expect.serials)
            self.assertEqual(meta.derivative, expect.derivative)

        expect = Storage({})
        expect.metadata = None
        expect.serials = []
        expect.derivative = None
        meta = BookPublicationMetadata.from_book(book)
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

        publication_metadata = self.add(PublicationMetadata, metadata)
        meta = BookPublicationMetadata.from_book(book)
        expect.metadata = publication_metadata
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

        publication_serial_1 = self.add(PublicationSerial, serial_1)
        meta = BookPublicationMetadata.from_book(book)
        expect.metadata = publication_metadata
        expect.serials = [publication_serial_1]
        test_meta(meta, expect)

        publication_serial_2 = self.add(PublicationSerial, serial_2)
        meta = BookPublicationMetadata.from_book(book)
        expect.metadata = publication_metadata
        # Expect serials sorted by sequence
        expect.serials = [publication_serial_2, publication_serial_1]
        test_meta(meta, expect)

        derivative_data = dict(
            book_id=book.id,
            title='Derivative',
            creator='Dr Drawer',
            cc_licence_id=1,
            from_year=2006,
            to_year=2007,
        )

        derivative = self.add(Derivative, derivative_data)
        meta = BookPublicationMetadata.from_book(book)
        expect.metadata = publication_metadata
        expect.serials = [publication_serial_2, publication_serial_1]
        expect.derivative = derivative
        test_meta(meta, expect)

        # Test chaining.
        self.assertEqual(
            BookPublicationMetadata.from_book(book).metadata,
            expect.metadata
        )
        self.assertEqual(
            str(BookPublicationMetadata.from_book(book)),
            (
                'This work was originally published digitally in 2014-2015 as "My Book" by Acme. '
                'This work was originally published digitally in 2000-2001 as "Sheerios 2 #2" at Acme 2. '
                'This work was originally published digitally in 1998-1999 as "Sheerios #1" at Acme. '
                '"test__from_book" is a derivative of "Derivative" from 2006-2007 by Dr Drawer used under CC0.'
            )
        )

    def test__from_vars(self):
        book = self.add(Book, dict(
            name='test__load_from_vars',
        ))

        self.assertRaises(
            LookupError, BookPublicationMetadata.from_vars, book, {})

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

        meta = BookPublicationMetadata.from_vars(book, request_vars)
        expect = PublicationMetadata(dict(metadata))
        expect.republished = False
        self.assertEqual(meta.metadata, expect)
        self.assertEqual(len(meta.serials), 0)
        self.assertEqual(meta.derivative, None)

        request_vars['publication_metadata_republished'] = 'repub'
        request_vars['publication_metadata_published_type'] = 'whole'
        meta = BookPublicationMetadata.from_vars(book, request_vars)
        self.assertEqual(len(meta.serials), 0)

        request_vars['publication_metadata_republished'] = 'repub'
        request_vars['publication_metadata_published_type'] = 'serial'
        meta = BookPublicationMetadata.from_vars(book, request_vars)
        self.assertEqual(len(meta.serials), 2)
        self.assertEqual(meta.serials[0], PublicationSerial(serials[0]))
        self.assertEqual(meta.serials[1], PublicationSerial(serials[1]))

        request_vars['is_derivative'] = 'yes'
        meta = BookPublicationMetadata.from_vars(book, request_vars)
        self.assertEqual(meta.derivative, Derivative(derivative))

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
            meta = BookPublicationMetadata.from_vars(book, request_vars)
            self.assertEqual(meta.metadata.republished, t[1])

        # Test chaining
        request_vars['publication_metadata_republished'] = 'repub'
        request_vars['publication_metadata_published_type'] = 'whole'
        expect = PublicationMetadata(dict(metadata))
        expect.republished = True
        self.assertEqual(
            BookPublicationMetadata.from_vars(book, request_vars).metadata,
            expect
        )

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
        save_datetime_date = datetime.date
        str_to_date = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        book_name = 'My Book'
        original_name = 'My Old Book'

        book = self.add(Book, dict(name=book_name))

        meta = BookPublicationMetadata(book)
        metadata = dict(
            book_id=book.id,
            republished=False,
            published_type='',
            published_name=original_name,
            published_format='',
            publisher_type='',
            publisher='',
            from_year=2014,
            to_year=2015,
        )

        # [1]
        meta.metadata = PublicationMetadata(metadata)
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
        meta.metadata = PublicationMetadata(metadata)
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
        meta.metadata = PublicationMetadata(metadata)
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
        meta.metadata = PublicationMetadata(metadata)
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
        meta.metadata = PublicationMetadata(metadata)
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
        meta.metadata = PublicationMetadata(metadata)
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
        meta.metadata = PublicationMetadata(metadata)
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

        datetime.date = save_datetime_date

    def test__publication_year(self):
        book = self.add(Book, dict(name='test__publication_year'))
        meta = BookPublicationMetadata(book)

        # Test: no metadata or serial data
        self.assertRaises(ValueError, meta.publication_year)

        # Test: metadata, no serial
        metadata = PublicationMetadata(dict(
            book_id=book.id,
            from_year=1998,
            to_year=1999,
        ))
        meta.metadata = metadata
        self.assertEqual(meta.publication_year(), 1999)

        # Test: single serial
        serial_1 = PublicationSerial(dict(
            book_id=book.id,
            from_year=2010,
            to_year=2011,
        ))
        meta.serials = [serial_1]
        self.assertEqual(meta.publication_year(), 2011)

        # Test: multiple serial
        serial_2 = PublicationSerial(dict(
            book_id=book.id,
            from_year=2013,
            to_year=2014,
        ))
        serial_3 = PublicationSerial(dict(
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

        book = self.add(Book, dict(name='test__serials_text'))

        meta = BookPublicationMetadata(book)
        default_serial = dict(
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
        )

        # [8]
        s = PublicationSerial(default_serial)
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
        s = PublicationSerial(default_serial)
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
        s = PublicationSerial(default_serial)
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
        s = PublicationSerial(default_serial)
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
        s = PublicationSerial(default_serial)
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
        s = PublicationSerial(default_serial)
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
        book = self.add(Book, dict(name='test__serials_text'))

        meta = BookPublicationMetadata(book)
        serial_1 = PublicationSerial(dict(
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

        serial_2 = PublicationSerial(dict(
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

        meta.metadata = PublicationMetadata({'is_anthology': False})
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

        meta.metadata.is_anthology = True
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
        book = self.add(Book, dict(name='My Book'))

        meta = BookPublicationMetadata(book)

        meta.metadata = PublicationMetadata(dict(
            book_id=book.id,
            republished=True,
            published_type='whole',
            published_name='My Old Book',
            published_format='paper',
            publisher_type='press',
            publisher='Acme Pub Inc',
            from_year=2014,
            to_year=2015,
        ))

        meta.serials = [
            PublicationSerial(dict(
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
            )),
            PublicationSerial(dict(
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
            )),
        ]

        cc_by_nc_sa = CCLicence.by_code('CC BY-NC-SA')

        meta.derivative = Derivative(dict(
            book_id=book.id,
            title='My Derivative',
            creator='John Doe',
            cc_licence_id=cc_by_nc_sa.id,
            from_year=2014,
            to_year=2015,
        ))

        self.assertEqual(
            meta.texts(),
            [
                'This work was originally published in print in 2014-2015 as "My Old Book" by Acme Pub Inc.',
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.',
                'This work was originally published in print in 2014-2015 as "Aaa Series #2" by Acme Pub Inc.',
                '"My Book" is a derivative of "My Derivative" from 2014-2015 by John Doe used under CC BY-NC-SA.',
            ]
        )

    def test__to_month_requires(self):
        meta = BookPublicationMetadata(Book())

        err_msg = (
            'The "Finish" must be the same as or after'
            ' the "Start" month/year.'
        )

        tests = [
            # from_month, from_year, to_month, to_year, expect
            (01, 1999, 01, 1999, None),
            (01, 1999, 01, 2000, None),
            (12, 1999, 01, 2000, None),
            (11, 1999, 12, 1999, None),
            (12, 1999, 11, 1999, err_msg),
        ]

        for t in tests:
            # test as integers
            requires = meta.to_month_requires(t[0], t[1], t[3])
            expect = (t[2], t[4])
            self.assertEqual(requires(t[2]), expect)

            # test as strings
            requires = meta.to_month_requires(str(t[0]), str(t[1]), str(t[3]))
            expect = (t[2], t[4])
            self.assertEqual(requires(t[2]), expect)

    def test__to_year_requires(self):
        book = self.add(Book, dict(
            name='test__to_year_requires',
        ))
        meta = BookPublicationMetadata(book)
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
        book = self.add(Book, dict(name='test__update'))

        meta = BookPublicationMetadata(book)

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

        meta.metadata = PublicationMetadata({'publisher': 'aaa'})
        meta.serials = [
            PublicationSerial({
                'published_name': 'name_bbb',
                'publisher': 'bbb',
                'serial_title': 'title_bbb',
                'story_number': 1,
            }),
            PublicationSerial({
                'published_name': 'name_ccc',
                'publisher': 'ccc',
                'serial_title': 'title_ccc',
                'story_number': 2,
            }),
        ]
        meta.derivative = None

        meta.update()
        got = get_metadatas(book.id)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].publisher, 'aaa')
        metadata_id = got[0].id

        got = get_serials(book.id)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0].publisher, 'bbb')
        self.assertEqual(got[0].story_number, 1)
        self.assertEqual(got[1].publisher, 'ccc')
        self.assertEqual(got[1].story_number, 2)
        serial_ids = [x.id for x in got]

        # Test existing records are reused.
        meta.metadata = PublicationMetadata({'publisher': 'aaa_2'})
        meta.serials = [
            PublicationSerial({
                'published_name': 'name_bbb_2',
                'publisher': 'bbb_2',
                'serial_title': 'title_bbb_2',
                'story_number': 1,
            }),
            PublicationSerial({
                'published_name': 'name_ccc_2',
                'publisher': 'ccc_2',
                'serial_title': 'title_ccc',
                'story_number': 2,
            }),
        ]
        meta.update()
        got = get_metadatas(book.id)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].publisher, 'aaa_2')
        self.assertTrue(got[0].id == metadata_id)

        got = get_serials(book.id)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0].publisher, 'bbb_2')
        self.assertEqual(got[0].story_number, 1)
        self.assertEqual(got[1].publisher, 'ccc_2')
        self.assertEqual(got[1].story_number, 2)
        self.assertTrue(got[0].id in serial_ids or got[1].id in serial_ids)
        serial_ids = [got[0].id, got[1].id]

        # Add fewer serial records
        meta.serials = [
            PublicationSerial({
                'published_name': 'name_ddd',
                'publisher': 'ddd',
                'serial_title': 'title_ddd',
                'story_number': 3,
            }),
        ]

        meta.update()
        got = get_metadatas(book.id)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].publisher, 'aaa_2')
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
        book = self.add(Book, dict(
            name='test__validate',
        ))

        meta = BookPublicationMetadata(book)
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
            from_month=11,
            from_year=1999,
            to_month=12,
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
                from_month=11,
                from_year=2014,
                to_month=12,
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
                from_month=11,
                from_year=2014,
                to_month=12,
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

        meta.metadata = PublicationMetadata(metadata)
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.metadata.published_type = '_fake_'
        meta.validate()
        self.assertEqual(
            meta.errors['publication_metadata_published_type'],
            'Please select an option'
        )

        # whole
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = ''
        meta.metadata.published_format = '_fake_'
        meta.metadata.publisher_type = '_fake_'
        meta.metadata.publisher = ''
        meta.metadata.from_month = -1
        meta.metadata.from_year = -1
        meta.metadata.to_month = -2
        meta.metadata.to_year = -2
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_metadata_published_name',
                'publication_metadata_published_format',
                'publication_metadata_publisher_type',
                'publication_metadata_publisher',
                'publication_metadata_from_month',
                'publication_metadata_from_year',
                'publication_metadata_to_month',
                'publication_metadata_to_year',
            ])
        )

        # Valid: whole, paper, self, no publisher
        meta.metadata.published_type = 'whole'
        meta.metadata.published_name = 'Some Name',
        meta.metadata.published_format = 'paper'
        meta.metadata.publisher_type = 'self'
        meta.metadata.publisher = ''
        meta.metadata.from_month = 1
        meta.metadata.from_year = 2000
        meta.metadata.to_month = 12
        meta.metadata.to_year = 2001
        meta.validate()
        self.assertEqual(meta.errors, {})

        # Invalid: whole, paper, press, no publisher
        meta.metadata.publisher_type = 'press'
        meta.metadata.publisher = ''
        meta.validate()
        self.assertEqual(
            meta.errors['publication_metadata_publisher'],
            'Enter a value'
        )

        # Invalid to_month/to_year
        tests = [
            # from_month, from_year, to_month, to_year, expect
            (01, 1999, 01, 1999, None),
            (01, 1999, 01, 2000, None),
            (12, 1999, 01, 2000, None),
            (11, 1999, 12, 1999, None),
            (12, 1999, 11, 1999, meta.to_month_err_msg),
        ]

        for t in tests:
            meta.metadata = PublicationMetadata(metadata)
            meta.metadata.from_month = t[0]
            meta.metadata.from_year = t[1]
            meta.metadata.to_month = t[2]
            meta.metadata.to_year = t[3]
            meta.validate()
            if t[4]:
                self.assertEqual(
                    meta.errors['publication_metadata_to_month'],
                    t[4]
                )
            else:
                self.assertEqual(meta.errors, {})

        # serial
        meta.metadata = PublicationMetadata(metadata)
        meta.metadata.published_type = 'serial'
        meta.serials = []
        meta.derivative = None
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.serials = [PublicationSerial(serials[0])]
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.serials[0].published_name = ''
        meta.serials[0].published_format = '_fake_'
        meta.serials[0].publisher_type = '_fake_'
        meta.serials[0].publisher = ''
        meta.serials[0].from_month = -1
        meta.serials[0].from_year = -1
        meta.serials[0].to_month = -2
        meta.serials[0].to_year = -2
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_serial_published_name__0',
                'publication_serial_published_format__0',
                'publication_serial_publisher_type__0',
                'publication_serial_publisher__0',
                'publication_serial_from_month__0',
                'publication_serial_from_year__0',
                'publication_serial_to_month__0',
                'publication_serial_to_year__0',
            ])
        )

        meta.metadata.is_anthology = False
        meta.validate()
        meta.serials[0].published_name = ''
        meta.serials[0].published_format = '_fake_'
        meta.serials[0].publisher_type = '_fake_'
        meta.serials[0].publisher = ''
        meta.serials[0].from_month = -1
        meta.serials[0].from_year = -1
        meta.serials[0].to_month = -2
        meta.serials[0].to_year = -2
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_serial_published_format__0',
                'publication_serial_publisher_type__0',
                'publication_serial_publisher__0',
                'publication_serial_from_month__0',
                'publication_serial_from_year__0',
                'publication_serial_to_month__0',
                'publication_serial_to_year__0',
            ])
        )

        meta.metadata.is_anthology = True
        meta.serials = [PublicationSerial(serials[0])]
        meta.validate()
        self.assertEqual(meta.errors, {})
        meta.serials[0].from_month = 1
        meta.serials[0].from_year = 1981
        meta.serials[0].to_month = 12
        meta.serials[0].to_year = 1980
        meta.validate()
        self.assertEqual(
            meta.errors['publication_serial_to_month__0'],
            meta.to_month_err_msg
        )

        meta.serials = [PublicationSerial(x) for x in list(serials)]
        meta.validate()
        self.assertEqual(meta.errors, {})
        meta.serials[0].published_name = ''
        meta.serials[1].published_format = '_fake_'
        meta.validate()
        self.assertEqual(
            sorted(meta.errors.keys()),
            sorted([
                'publication_serial_published_name__0',
                'publication_serial_published_format__1',
            ])
        )

        # derivative
        meta.metadata = PublicationMetadata(metadata)
        meta.serials = [PublicationSerial(x) for x in list(serials)]
        meta.derivative = Derivative(derivative)
        meta.validate()
        self.assertEqual(meta.errors, {})

        meta.derivative.title = ''
        meta.derivative.creator = ''
        meta.derivative.cc_licence_id = 999999
        meta.derivative.from_year = -1
        meta.derivative.to_year = -2
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
        meta.deriviate = Derivative(derivative)
        meta.derivative.from_year = 1977
        meta.derivative.to_year = 1976
        meta.validate()
        self.assertEqual(
            meta.errors['derivative_to_year'],
            'Enter a year 1977 or greater'
        )

    def test__year_range(self):
        save_datetime_date = datetime.date
        str_to_date = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        book = self.add(Book, dict(
            name='test__year_range',
        ))

        meta = BookPublicationMetadata(book)

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

        datetime.date = save_datetime_date


class TestFunctions(WithObjectsTestCase, ImageTestCase):

    def test__cc_licence_places(self):
        places = cc_licence_places()
        got = loads('[' + str(places) + ']')
        self.assertTrue({'text': 'Canada', 'value': 'Canada'} in got)
        self.assertTrue(len(got) > 245)
        for d in got:
            self.assertEqual(sorted(d.keys()), ['text', 'value'])
            self.assertEqual(d['text'], d['value'])

    def test__cc_licences(self):
        auth_user = self.add(AuthUser, dict(name='Test CC Licence'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))
        book = Book(dict(
            id=-1,
            name='test__cc_licences',
            creator_id=creator.id,
            book_type_id=BookType.by_name('one-shot').id,
            name_for_url='TestCcLicences',
            cc_licence_place=None,
        ))

        # Add a cc_licence with quotes in the template. Should be handled.
        self.add(CCLicence, dict(
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
            cc_licence = db(query).select(limitby=(0, 1)).first()
            self.assertEqual(cc_licence.code, d['text'])

    @skip_if_quick
    def test__create_creator_indicia(self):
        fields = ['indicia_image', 'indicia_portrait', 'indicia_landscape']

        def exists(field, img_name):
            _, f = db.creator[field].retrieve(img_name, nameonly=True)
            return os.path.exists(f)

        # Test cleared
        data = dict(
            indicia_image=None,
            indicia_portrait=None,
            indicia_landscape=None,
        )
        self._creator = Creator.from_updated(self._creator, data)
        for f in fields:
            # Field is cleared
            self.assertEqual(self._creator[f], None)

        filename = self._prep_image('cbz_plus.png')
        indicia_image = store(
            db.creator.indicia_image, filename, resizer=ResizerQuick)
        data = dict(indicia_image=indicia_image)
        self._creator = Creator.from_updated(self._creator, data)
        create_creator_indicia(self._creator)

        creator_1 = Creator.from_id(self._creator.id)
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
        self._creator = Creator.from_updated(self._creator, data)

    def test__render_cc_licence(self):

        cc_licence_row = self.add(CCLicence, dict(
            number=999,
            code='test__render_cc_licence',
            url='http://cc_licence.com',
            template_img='The {title} is owned by {owner} for {year} in {place} at {url}.',
            template_web='THE {title} IS OWNED BY {owner} FOR {year} IN {place} AT {url}.'
        ))
        cc_licence = CCLicence.from_id(cc_licence_row.id)

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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
