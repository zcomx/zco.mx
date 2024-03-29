#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/images.py
"""
import grp
import inspect
import os
import pwd
import re
import unittest
import urllib.parse
from bs4 import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.html import DIV, IMG
from gluon.http import HTTP
from applications.zcomx.modules.creators import (
    AuthUser,
    Creator,
)
from applications.zcomx.modules.images import (
    CachedImgTag,
    CreatorImgTag,
    ImageDescriptor,
    ImageOptimizeError,
    ImgTag,
    ResizeImgError,
    ResizeImg,
    ResizeImgIndicia,
    SIZES,
    UploadImage,
    filename_for_size,
    is_image,
    optimize,
    rename,
    scrub_extension_for_store,
    square_image,
    store,
)
from applications.zcomx.modules.tests.helpers import (
    FileTestCase,
    ImageTestCase,
    ResizerQuick,
    skip_if_quick,
)
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.shell_utils import imagemagick_version
# pylint: disable=missing-docstring


class WithObjectsTestCase(LocalTestCase):
    """ Base class for test cases. Sets up test data."""

    _auth_user = None
    _creator = None
    _uuid_key = None

    # pylint: disable=invalid-name
    def setUp(self):
        # Create a creator and set the image
        email = 'up_image@example.com'
        self._auth_user = self.add(AuthUser, dict(
            name='Image UploadImage',
            email=email,
        ))

        self._creator = self.add(Creator, dict(
            auth_user_id=self._auth_user.id,
            email=email,
        ))
        super().setUp()

    def tearDown(self):
        if self._creator.image:
            up_image = UploadImage(db.creator.image, self._creator.image)
            up_image.delete_all()
        super().tearDown()


class TestCachedImgTag(LocalTestCase):

    def test__url_vars(self):
        img_tag = CachedImgTag(None)
        self.assertEqual(
            img_tag.url_vars(),
            {'cache': 1, 'size': 'original'}
        )

        img_tag.size = 'web'
        self.assertEqual(
            img_tag.url_vars(),
            {'cache': 1, 'size': 'web'}
        )


class TestCreatorImgTag(WithObjectsTestCase):

    def test_parent__init__(self):
        img_tag = CreatorImgTag('')
        self.assertTrue(img_tag)
        self.assertEqual(img_tag.placeholder_tag, IMG)

    def test__set_placeholder(self):
        img_dir = '/zcomx/static/images/placeholders/creator'
        img_tag = CreatorImgTag(None)
        self.assertEqual(img_tag.attributes, {})
        img_tag.set_placeholder()
        self.assertEqual(len(img_tag.components), 0)
        self.assertEqual(
            img_tag.attributes,
            {
                '_src': '/'.join([img_dir, '01.png']),
                '_class': 'preview img-responsive'
            }
        )

        tests = [
            # creator_id, expect img
            (100, '01.png'),
            (101, '02.png'),
            (102, '03.png'),
            (103, '04.png'),
            (104, '01.png'),
        ]
        for t in tests:
            attrs = {
                '_class': 'img_class',
                '_data-creator_id': t[0],
                '_id': 'img_id',
            }
            img_tag = CreatorImgTag(None, attributes=attrs)
            self.assertEqual(img_tag.attributes, attrs)
            img_tag.set_placeholder()

            self.assertEqual(
                img_tag.attributes,
                {
                    '_class': 'img_class preview img-responsive',
                    '_data-creator_id': t[0],
                    '_id': 'img_id',
                    '_src': '/'.join([img_dir, t[1]]),
                }
            )


class TestImageDescriptor(WithObjectsTestCase, ImageTestCase):

    def test____init__(self):
        descriptor = ImageDescriptor('/path/to/file')
        self.assertTrue(descriptor)

    def test__dimensions(self):
        tests = [
            # (filename, expect)
            ('landscape.png', (300, 170)),
            ('portrait.png', (140, 168)),
            ('square.png', (200, 200)),
        ]
        for t in tests:
            filename = self._prep_image(t[0])
            descriptor = ImageDescriptor(filename)
            self.assertEqual(descriptor.dimensions(), t[1])

        # Test cache
        descriptor = ImageDescriptor('/path/to/file')
        # pylint: disable=protected-access
        descriptor._dimensions = (1, 1)
        self.assertEqual(descriptor.dimensions(), (1, 1))

    def test__number_of_colours(self):
        tests = [
            # (filename, expect)
            ('square.png', 1),
            ('256colour-png.png', 256),
            ('256+colour.jpg', 2594),
        ]
        for t in tests:
            filename = self._prep_image(t[0])
            descriptor = ImageDescriptor(filename)
            self.assertEqual(descriptor.number_of_colours(), t[1])

        # Test cache
        descriptor = ImageDescriptor('/path/to/file')
        # pylint: disable=protected-access
        descriptor._number_of_colours = -1
        self.assertEqual(descriptor.number_of_colours(), -1)

    def test__orientation(self):
        for t in ['portrait', 'landscape', 'square']:
            img = '{n}.png'.format(n=t)
            filename = self._prep_image(img)
            descriptor = ImageDescriptor(filename)
            self.assertEqual(descriptor.orientation(), t)

    def test__pil_image(self):
        filename = self._prep_image('file.png')
        descriptor = ImageDescriptor(filename)
        im = descriptor.pil_image()
        self.assertTrue(hasattr(im, 'size'))
        self.assertTrue(hasattr(im, 'info'))
        self.assertTrue(hasattr(im, 'getcolors'))

    def test__size_bytes(self):
        tests = [
            # (filename, expect)
            ('landscape.png', 690),
            ('portrait.png', 255),
            ('square.png', 274),
        ]
        for t in tests:
            filename = self._prep_image(t[0])
            descriptor = ImageDescriptor(filename)
            self.assertEqual(descriptor.size_bytes(), t[1])

        # Test cache
        descriptor = ImageDescriptor('/path/to/file')
        # pylint: disable=protected-access
        descriptor._size_bytes = 1
        self.assertEqual(descriptor.size_bytes(), 1)


class TestImageOptimizeError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise ImageOptimizeError(msg)
        except ImageOptimizeError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('ImageOptimizeError not raised')


class TestImgTag(WithObjectsTestCase, ImageTestCase):

    def test____init__(self):
        img_tag = ImgTag('')
        self.assertTrue(img_tag)
        self.assertEqual(img_tag.placeholder_tag, DIV)
        self.assertEqual(img_tag.size, 'original')
        self.assertEqual(img_tag.tag, None)
        self.assertEqual(img_tag.components, [])
        self.assertEqual(img_tag.attributes, {})

        for size in SIZES:
            img_tag = ImgTag(db.creator.image, size=size)
            self.assertEqual(img_tag.size, size)

        img_tag = ImgTag(db.creator.image, size='_fake_')
        self.assertEqual(img_tag.size, 'original')

    def test____call__(self):
        filename = self._prep_image(self._image_name)
        self._set_image(
            db.creator.image,
            self._creator,
            filename,
            resizer=ResizerQuick
        )

        def get_tag(tag, tag_type):
            soup = BeautifulSoup(str(tag), 'html.parser')
            return soup.find(tag_type)

        def has_attr(element, attr, value, oper='equal'):
            self.assertTrue(element)
            self.assertTrue(hasattr(element, attr))
            if oper == 'equal':
                self.assertEqual(element[attr], value)
            elif oper == 'in':
                self.assertTrue(value in element[attr])

        img_tag = ImgTag(self._creator.image)
        tag = img_tag()
        has_attr(
            get_tag(tag, 'img'),
            'src',
            urllib.parse.quote(self._creator.image),
            oper='in'
        )
        has_attr(get_tag(tag, 'img'), 'src', 'size=original', oper='in')

        img_tag = ImgTag(self._creator.image, size='web')
        tag = img_tag()
        has_attr(get_tag(tag, 'img'), 'src', 'size=web', oper='in')

        # Test no image
        img_tag = ImgTag(None)
        tag = img_tag()
        has_attr(get_tag(tag, 'div'), 'class', ['portrait_placeholder'])
        img_tag = ImgTag(None, size='web')
        tag = img_tag()
        has_attr(get_tag(tag, 'div'), 'class', ['portrait_placeholder'])

        # Test: provide tag
        img_tag = ImgTag(self._creator.image, tag=SPAN)
        tag = img_tag()
        has_attr(get_tag(tag, 'span'), '', '', oper='')

        # Test: provide components
        components = [DIV('_test_imgtag_')]
        img_tag = ImgTag(self._creator.image, tag=DIV, components=components)
        tag = img_tag()
        soup = BeautifulSoup(str(tag), 'html.parser')
        div = soup.find('div')
        self.assertTrue(div)
        div_2 = div.find('div')
        self.assertTrue(div_2)
        self.assertEqual(div_2.string, '_test_imgtag_')

        # Test: provide attributes
        attrs = {
            '_id': 'img_id',
            '_class': 'img_class',
            '_src': 'http://www.aaa.com'
        }
        img_tag = ImgTag(self._creator.image, attributes=attrs)
        tag = img_tag()
        has_attr(get_tag(tag, 'img'), 'class', ['img_class'])
        has_attr(get_tag(tag, 'img'), 'id', 'img_id')
        has_attr(get_tag(tag, 'img'), 'src', 'http://www.aaa.com')

    def test__set_placeholder(self):
        img_tag = ImgTag(None)
        self.assertEqual(img_tag.attributes, {})
        img_tag.set_placeholder()
        self.assertEqual(
            img_tag.attributes,
            {'_class': 'portrait_placeholder'}
        )

        img_tag = ImgTag(None, size='web')
        self.assertEqual(img_tag.attributes, {})
        img_tag.set_placeholder()
        self.assertEqual(
            img_tag.attributes, {'_class': 'portrait_placeholder'})

        attrs = {'_id': 'img_id', '_class': 'img_class'}
        img_tag = ImgTag(None, attributes=attrs)
        self.assertEqual(img_tag.attributes, attrs)
        img_tag.set_placeholder()
        self.assertEqual(
            img_tag.attributes,
            {'_class': 'img_class portrait_placeholder', '_id': 'img_id'}
        )

    def test__url_vars(self):
        img_tag = ImgTag(None)
        self.assertEqual(img_tag.url_vars(), {'size': 'original'})

        img_tag.size = 'web'
        self.assertEqual(img_tag.url_vars(), {'size': 'web'})

        img_tag.size = '_fake_'
        self.assertEqual(img_tag.url_vars(), {'size': '_fake_'})


class TestResizeImg(ImageTestCase, WithObjectsTestCase, FileTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        resize_img = ResizeImg(filename)
        self.assertTrue(resize_img)
        # pylint: disable=protected-access
        self.assertEqual(resize_img._temp_directory, None)
        self.assertEqual(
            resize_img.filenames,
            {
                'cbz': None,
                'ori': None,
                'web': None,
            }
        )

    @skip_if_quick
    def test__run(self):
        # !!!! ResizeImg.run() moves the image to a working directory.
        # Make copies of test data images before using so they don't get
        # removed from test data.

        # resize_img.sh relies on RobidouxSharp filter added in imagemagick
        # ver 6.7.6-8. Abort if that version is not available.
        minimum_ver = '6.7.6-8'

        def version_as_num(value):
            return float(value.replace('.', '').replace('-', '.'))

        imagemagick_ver = imagemagick_version()
        if version_as_num(imagemagick_ver) < version_as_num(minimum_ver):
            msg = 'Upgrade ImageMagick. Minimum version: {ver}'.format(
                ver=minimum_ver)
            self.fail(msg)
            return

        def test_it(image_name, expect, to_name=None, md5s=None, colors=None):
            filename = self._prep_image(image_name, to_name=to_name)
            resize_img = ResizeImg(filename)
            resize_img.run()
            tmp_dir = resize_img.temp_directory()
            for fmt, prefixes in list(expect.items()):
                for prefix in prefixes:
                    self.assertTrue(prefix in resize_img.filenames)
                    self.assertEqual(
                        resize_img.filenames[prefix],
                        os.path.join(tmp_dir, fmt.format(typ=prefix))
                    )
                    if md5s is not None:
                        self.assertEqual(
                            self._md5sum(resize_img.filenames[prefix]),
                            md5s[fmt.format(typ=prefix)]
                        )
                    if colors is not None:
                        img = ImageDescriptor(resize_img.filenames[prefix])
                        self.assertTrue(img.number_of_colours() in colors)
                        im = Image.open(resize_img.filenames[prefix])
                        self.assertTrue(
                            len(im.getcolors(maxcolors=99999)) in colors
                        )

        # pylint: disable=line-too-long

        # Test: test the md5 sum of files.
        #
        # mkdir ~/tmp/img/before
        # cp applications/zcomx/private/test/data/256* ~/tmp/img/before/
        # pushd ~/tmp/img
        # rm ~/tmp/img/*.jpg
        # rm ~/tmp/img/*.png
        # rm ~/tmp/img/*.gif
        # ./applications/zcomx/private/bin/resize_img.sh before/*
        # # Remove the dates from png files
        # for f in *.png; do echo "$f"; convert "$f" +set date:modify +set date:create "$f"; done
        # md5sum * | awk -v q="'" '{print q$2q": " q$1q","}'

        md5s = {
            '6.9.10-16': {
                'cbz-256+colour.jpg': 'c94fb0c0f0b1328a70ed02367210455e',
                'cbz-256colour-jpg.jpg': '3800ee82f710fcefc913ad2a9fd19d57',
                'ori-256+colour.jpg': '02f34f15b65cb06712a4b18711c21cf6',
                'ori-256colour-jpg.jpg': 'a0c2469208f00a9c2ba7e6cb71858008',
                'web-256+colour.jpg': '6a5073e10b0108168d3eade3ede41739',
                'web-256colour-jpg.jpg': '493e25643f3ce4b6a72d6445c4ca1a53',
            },
            '7.1.0-53': {
                'cbz-256+colour.jpg': '7459d40aa320af79aa137f9f232a03cd',
                'cbz-256colour-jpg.jpg': '412858c926740d6ff7effb60f2352433',
                'ori-256+colour.jpg': '02f34f15b65cb06712a4b18711c21cf6',
                'ori-256colour-jpg.jpg': 'a0c2469208f00a9c2ba7e6cb71858008',
                'web-256+colour.jpg': '3ef1017981eefa6e5896a3e3dbaad5ac',
                'web-256colour-jpg.jpg': '5f754bd77232f1d6d5036932f479f0f6',
            }
        }

        # Test 256 colour jpg.
        # JPG images need special consideration regarding color conversions.
        # After conversion image should have no more than 256, and possibly
        # a few less. If a lot less, could be a sign of a problem.

        #
        test_it(
            '256colour-jpg.jpg',
            {
                '{typ}-256colour-jpg.jpg': ['ori', 'cbz', 'web'],
            },
            md5s=md5s[imagemagick_ver],
            colors=[256 - x for x in range(0, 2)]
        )

        # Test: more than 256 colours
        test_it(
            '256+colour.jpg',
            {
                '{typ}-256+colour.jpg': ['ori', 'cbz', 'web'],
            },
            md5s=md5s[imagemagick_ver],
        )

        # Test: standard jpg
        test_it(
            'file.jpg',
            {
                '{typ}-file.jpg': ['ori', 'web'],
            }
        )

        # Test: file with no extension
        test_it(
            'image_with_no_ext',
            {
                # Image is not big enough to produce a cbz file.
                '{typ}-image_with_no_ext.jpg': ['ori', 'web'],
            }
        )

        # Test: jpeg extension
        test_it(
            'file.jpeg',
            {
                '{typ}-file.jpg': ['ori', 'web'],
            }
        )

        # Test: convert gif to png
        test_it(
            'eg.gif',
            {
                # Image is not big enough to produce a cbz file.
                '{typ}-eg.png': ['ori', 'web'],
            }
        )

        # Test: animated.gif
        test_it(
            'animated.gif',
            {
                # Image is not big enough to produce a cbz file.
                '{typ}-animated.png': ['ori', 'web'],
            }
        )

        # Test: cmyk
        test_it(
            'cmyk.jpg',
            {
                # Image is small so only an original should be produced.
                '{typ}-cmyk.jpg': ['ori'],
            }
        )

        # Test: file with incorrect extension
        test_it(
            'jpg_with_wrong_ext.png',
            {
                # Image is not big enough to produce a cbz file.
                '{typ}-jpg_with_wrong_ext.jpg': ['ori', 'web'],
            }
        )

        # Test: files with prefixes
        # The resize should handle files whose original names have formats
        # similar to those of the temporary files created by the resize
        # script.
        for dest in ['ori-file.png', 'web-file.png']:
            fmt = '{{typ}}-{dest}'.format(dest=dest)
            test_it(
                'file.png',
                {
                    fmt: ['ori', 'web'],
                },
                to_name=dest,
            )

        # Exception: No args
        resize_img = ResizeImg('')
        try:
            resize_img.run()
        except ResizeImgError as err:
            self.assertTrue('usage: resize_img.sh' in str(err))
        else:
            self.fail('ResizeImgError not raised.')

        # Exception: image doesn't exist
        filename = '/tmp/_fake_.jpg'
        resize_img = ResizeImg(filename)
        try:
            resize_img.run()
        except ResizeImgError as err:
            self.assertTrue('is not an image or image is corrupt' in str(err))
        else:
            self.fail('ResizeImgError not raised.')

        # Exception: image is corrupt
        filename = self._prep_image('corrupt.jpg')
        resize_img = ResizeImg(filename)
        try:
            resize_img.run()
        except ResizeImgError as err:
            self.assertTrue('corrupt.jpg is corrupt' in str(err))
        else:
            self.fail('ResizeImgError not raised.')

        filename = self._prep_image('corrupt.png')
        resize_img = ResizeImg(filename)
        try:
            resize_img.run()
        except ResizeImgError as err:
            expect = 'corrupt.png is not an image or image is corrupt'
            self.assertTrue(expect in str(err))
        else:
            self.fail('ResizeImgError not raised.')

        # Exception: not a gif, jpg or png image, eg tiff
        filename = self._prep_image('eg.tiff')
        resize_img = ResizeImg(filename)
        try:
            resize_img.run()
        except ResizeImgError as err:
            expect = 'eg.tiff is not a GIF, PNG or JPEG image'
            self.assertTrue(expect in str(err))
        else:
            self.fail('ResizeImgError not raised.')


class TestResizeImgIndicia(WithObjectsTestCase, ImageTestCase, FileTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        resize_img = ResizeImgIndicia(filename)
        self.assertTrue(resize_img)
        # pylint: disable=protected-access
        self.assertEqual(resize_img._temp_directory, None)
        self.assertEqual(
            resize_img.filenames,
            {'ori': None}
        )

    def test__run(self):
        filename = self._prep_image('256colour-jpg.jpg')
        resize_img = ResizeImgIndicia(filename)
        resize_img.run()
        tmp_dir = resize_img.temp_directory()
        self.assertEqual(list(resize_img.filenames.keys()), ['ori'])
        self.assertEqual(
            resize_img.filenames['ori'],
            os.path.join(tmp_dir, 'ori-256colour-jpg.jpg')
        )

        # mkdir ~/tmp/img/before
        # cp applications/zcomx/private/test/data/256* ~/tmp/img/before/
        # pushd ~/tmp/img
        # rm ~/tmp/img/*.jpg
        # rm ~/tmp/img/*.png
        # rm ~/tmp/img/*.gif
        # convert before/256colour-jpg.jpg -quiet -filter catrom \
        #    -resize '1600x1600>' -colorspace sRGB +repage file.jpg
        # md5sum * | awk -v q="'" '{print q$2q": " q$1q","}'
        md5s = {
            '6.9.10-16': {
                'ori-256colour-jpg.jpg': '9b130b9e36d3e45ee711b9cebd85cb96',
            },
            '7.1.0-53': {
                'ori-256colour-jpg.jpg': '2a2044593502677db9321be6337e289d',
            }
        }

        imagemagick_ver = imagemagick_version()
        self.assertEqual(
            self._md5sum(resize_img.filenames['ori']),
            md5s[imagemagick_ver]['ori-256colour-jpg.jpg']
        )


class TestUploadImage(WithObjectsTestCase, ImageTestCase):

    def _exist(self, have=None, have_not=None):
        """Test if image files exist"""
        if have is None:
            have = []
        if have_not is None:
            have_not = []
        unused_filename, original_fullname = db.creator.image.retrieve(
            self._creator.image,
            nameonly=True,
        )
        for size in have:
            self.assertTrue(os.path.exists(filename_for_size(
                original_fullname, size)))
        for size in have_not:
            self.assertTrue(not os.path.exists(filename_for_size(
                original_fullname, size)))

    def test____init__(self):
        filename = self._prep_image(self._image_name)
        self._set_image(
            db.creator.image,
            self._creator,
            filename,
            resizer=ResizerQuick
        )
        up_image = UploadImage(db.creator.image, self._image_name)
        self.assertTrue(up_image)
        file_name, unused_fullname = db.creator.image.retrieve(
            self._creator.image,
            nameonly=True,
        )
        self.assertEqual(self._image_name, file_name)
        # pylint: disable=protected-access
        self.assertEqual(up_image._full_name, None)
        self.assertEqual(up_image._original_name, None)

    def test__delete(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(
            db.creator.image, self._creator, filename, resizer=ResizerQuick)

        up_image = UploadImage(db.creator.image, self._creator.image)

        self._exist(have=['original', 'cbz', 'web'])
        up_image.delete('web')
        self._exist(have=['original', 'cbz'], have_not=['web'])
        up_image.delete('web')     # Handle subsequent delete gracefully
        up_image.delete('cbz')
        self._exist(have=['original'], have_not=['cbz', 'web'])
        up_image.delete('original')
        self._exist(have_not=['original', 'cbz', 'web'])

    def test__delete_all(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(
            db.creator.image, self._creator, filename, resizer=ResizerQuick)

        up_image = UploadImage(db.creator.image, self._creator.image)

        self._exist(have=['original', 'cbz', 'web'])
        up_image.delete_all()
        self._exist(have_not=['original', 'cbz', 'web'])
        up_image.delete_all()        # Handle subsequent delete gracefully
        self._exist(have_not=['original', 'cbz', 'web'])

    def test__fullname(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(
            db.creator.image, self._creator, filename, resizer=ResizerQuick)
        uuid_key = self._creator.image.split('.')[2][:2]

        up_image = UploadImage(db.creator.image, self._creator.image)
        original_folder = db.creator.image.uploadfolder
        parent_folder = os.path.dirname(original_folder)
        fmt = '{p}/{s}/creator.image/{u}/{i}'
        self.assertEqual(
            up_image.fullname(),
            fmt.format(
                p=parent_folder,
                s='original',
                u=uuid_key,
                i=self._creator.image,
            ),
        )
        self.assertEqual(
            up_image.fullname(size='web'),
            fmt.format(
                p=parent_folder,
                s='web',
                u=uuid_key,
                i=self._creator.image,
            ),
        )
        self.assertEqual(
            up_image.fullname(size='_fake_'),
            fmt.format(
                p=parent_folder,
                s='_fake_',
                u=uuid_key,
                i=self._creator.image,
            ),
        )

    def test__original_name(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='abc.jpg')
        self._set_image(
            db.creator.image, self._creator, filename, resizer=ResizerQuick)

        up_image = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(up_image.original_name(), 'abc.jpg')

    def test__retrieve(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(
            db.creator.image, self._creator, filename, resizer=ResizerQuick)
        uuid_key = self._creator.image.split('.')[2][:2]

        up_image = UploadImage(db.creator.image, self._creator.image)
        up_folder = db.creator.image.uploadfolder
        fmt = '{f}/creator.image/{u}/{i}'
        self.assertEqual(
            up_image.retrieve(),
            (
                'file.jpg',
                fmt.format(f=up_folder, u=uuid_key, i=self._creator.image)
            )
        )

        # pylint: disable=protected-access
        # Test cache
        up_image._original_name = '_original_'
        up_image._full_name = '_full_'
        self.assertEqual(up_image.retrieve(), ('_original_', '_full_'))


class TestFunctions(WithObjectsTestCase, ImageTestCase):

    def test__filename_for_size(self):
        tests = [
            # (original, size, expect),
            ('/path/original/file.jpg', 'cbz', '/path/cbz/file.jpg'),
            ('/path/original/file.jpg', 'web', '/path/web/file.jpg'),
            ('/path/original/file.jpg', 'tbn', '/path/tbn/file.jpg'),
            ('/path/original/file.jpg', '_fake_', '/path/_fake_/file.jpg'),
            ('/path/_fake_/file.jpg', 'cbz', '/path/_fake_/file.jpg'),
            ('/path/original/file.png', 'cbz', '/path/cbz/file.png'),
            ('/path/original/file.gif', 'cbz', '/path/cbz/file.png'),
        ]

        for t in tests:
            got = filename_for_size(t[0], t[1])
            self.assertEqual(got, t[2])

    def test__is_image(self):
        # Test common image types.
        original_filename = os.path.join(self._image_dir, 'original.jpg')

        # Create an image to test with.
        im = Image.new('RGB', (1200, 1200))
        with open(original_filename, 'wb') as f:
            im.save(f)

        tests = [
            # (filename, format, expect)
            ('file.gif', 'GIF', True),
            ('file.ppm', 'PPM', True),
            ('file.tiff', 'TIFF', True),
            ('file.jpg', 'JPEG', True),
            ('file.jpeg', 'JPEG', True),
            ('file.bmp', 'BMP', True),
            ('file.png', 'PNG', True),
        ]

        only_bmp = ['bmp']
        for t in tests:
            with open(original_filename, 'rb') as f:
                outfile = os.path.join(
                    os.path.dirname(original_filename), t[0])
                im.save(outfile, format=t[1])
                self.assertEqual(is_image(outfile), t[2])

                # Test image_types parameter
                expect = t[1] == 'BMP'
                self.assertEqual(
                    is_image(outfile, image_types=only_bmp),
                    expect
                )

        # Test non-image files.
        # This file is a python ASCII text, test it.
        this_filename = inspect.getfile(inspect.currentframe())
        self.assertFalse(is_image(this_filename))

    def test__on_delete_image(self):
        pass        # FIXME this is due for overhaul.

    def test__optimize(self):

        for img in ['unoptimized.png', 'unoptimized.jpg']:
            quick_opts = [False]
            if img.endswith('.png'):
                quick_opts.append(True)
            for quick in quick_opts:
                working_image = self._prep_image(img)
                size_bef = os.stat(working_image).st_size
                optimize(working_image, quick=quick)
                size_aft = os.stat(working_image).st_size
                self.assertTrue(size_aft <= size_bef)

    @skip_if_quick
    def test__rename(self):
        working_image = self._prep_image('cbz_plus.jpg')
        stored_fullname = store(db.book_page.image, working_image)
        _, old_fullname = db.book_page.image.retrieve(
            stored_fullname, nameonly=True)
        old_up_image = UploadImage(db.book_page.image, stored_fullname)
        for size in SIZES:
            fullname = old_up_image.fullname(size=size)
            self.assertTrue(os.path.exists(fullname))

        new_filename = 'new_cbz_plus.jpg'
        stored_filenames = rename(
            old_fullname, db.book_page.image, new_filename)

        new_up_image = UploadImage(
            db.book_page.image,
            os.path.basename(stored_filenames['original'])
        )
        original_name = new_up_image.original_name()
        self.assertEqual(original_name, new_filename)
        for size in SIZES:
            fullname = new_up_image.fullname(size=size)
            self.assertTrue(os.path.exists(fullname))
            fullname = old_up_image.fullname(size=size)
            self.assertFalse(os.path.exists(fullname))

        old_up_image.delete_all()
        new_up_image.delete_all()

    def test__scrub_extension_for_store(self):
        tests = [
            # (filename, expect)
            (None, None),
            ('', ''),
            ('file.jpg', 'file.jpg'),
            ('file.jpeg', 'file.jpg'),
            ('file.png', 'file.png'),
            ('file.gif', 'file.png'),
        ]
        for t in tests:
            self.assertEqual(scrub_extension_for_store(t[0]), t[1])

    def test__square_image(self):

        # It's not possible to determine if the offsets actually adjust the
        # image squaring properly, but we can test that the method handles
        # them.
        offsets = [None, '10', '10%']

        for offset in offsets:
            working_image = self._prep_image('web_plus.jpg')
            descriptor = ImageDescriptor(working_image)
            dims = descriptor.dimensions()
            self.assertNotEqual(dims[0], dims[1])

            square_image(working_image, offset=offset)

            descriptor = ImageDescriptor(working_image)
            dims = descriptor.dimensions()
            self.assertEqual(dims[0], dims[1])

    @skip_if_quick
    def test__store(self):

        def owner(filename):
            """Return the owner (user, group) of the file."""
            stat_info = os.stat(filename)
            uid = stat_info.st_uid
            gid = stat_info.st_gid
            user = pwd.getpwuid(uid)[0]
            group = grp.getgrgid(gid)[0]
            return (user, group)

        working_image = self._prep_image('cbz_plus.jpg')
        got = store(db.book_page.image, working_image)
        re_store = re.compile(
            r'book_page\.image\.[a-f0-9]{16}\.[a-zA-Z0-9]+\.jpg')
        # Eg book_page.image.8ee3a1b8e0ee83e7.Y2J6X3BsdXMuanBn.jpg
        #    book_page.image.810bab749df4eaeb.63627a5f706c75732e6a7067.jpg
        self.assertTrue(re_store.match(got))

        # Check that files exists for all sizes
        up_image = UploadImage(db.book_page.image, got)
        dims = {}
        for size in ['original', 'cbz', 'web']:
            filename = up_image.fullname(size=size)
            self.assertTrue(os.path.exists(filename))
            self.assertEqual(owner(filename), ('http', 'http'))
            dims[size] = ImageDescriptor(filename).dimensions()
        for i in range(0, 2):
            self.assertTrue(dims['original'][i] > dims['cbz'][i])
            self.assertTrue(dims['cbz'][i] > dims['web'][i])

        # Cleanup: Remove all files
        up_image.delete_all()
        for size in ['original', 'cbz', 'web']:
            filename = up_image.fullname(size=size)
            # os.unlink(filename)
            self.assertFalse(os.path.exists(filename))

        # Prove original filename is preserved.
        working_image = self._prep_image('image_with_no_ext')
        got = store(db.book_page.image, working_image, resizer=ResizerQuick)
        original_filename, _ = db.book_page.image.retrieve(got, nameonly=True)
        self.assertEqual(original_filename, 'image_with_no_ext')
        up_image = UploadImage(db.book_page.image, got)
        up_image.delete_all()

        # Test resize=False
        working_image = self._prep_image('cbz_plus.jpg')
        got = store(db.book_page.image, working_image, resize=False)
        self.assertTrue(re_store.match(got))
        up_image = UploadImage(db.book_page.image, got)
        dims = {}
        for size in ['original', 'cbz', 'web']:
            filename = up_image.fullname(size=size)
            self.assertTrue(os.path.exists(filename))
            self.assertEqual(owner(filename), ('http', 'http'))
            dims[size] = ImageDescriptor(filename).dimensions()
        # All should be the same size
        for i in range(0, 2):
            self.assertEqual(dims['original'][i], dims['cbz'][i])
            self.assertEqual(dims['original'][i], dims['web'][i])

        # Test resizer param
        working_image = self._prep_image('cbz_plus.jpg')
        got = store(db.book_page.image, working_image, resizer=ResizerQuick)
        self.assertTrue(re_store.match(got))


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
