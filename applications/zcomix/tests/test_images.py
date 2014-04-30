#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/utils.py

"""
import inspect
import os
import shutil
import sys
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from cStringIO import StringIO
from gluon import *
from gluon.http import HTTP
from gluon.storage import List
from applications.zcomix.modules.images import \
    Downloader, \
    LargeSizer, \
    MediumSizer, \
    Sizer, \
    ThumbnailSizer, \
    UploadImage, \
    img_tag, \
    is_image, \
    set_thumb_dimensions
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _auth_user = None
    _creator = None
    _image_dir = '/tmp/image_resizer'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _uuid_key = None

    _objects = []

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        image_filename = os.path.join(cls._image_dir, cls._image_name)

        # Create an image to test with.
        im = Image.new('RGB', (1200, 1200))
        with open(image_filename, 'wb') as f:
            im.save(f)

        # Store the image in the uploads/original directory
        db.creator.image.uploadfolder = cls._image_original
        with open(image_filename, 'rb') as f:
            stored_filename = db.creator.image.store(f)

        # Create a creator and set the image
        email = 'resizer@example.com'
        auth_user_id = db.auth_user.insert(
            name='Image UploadImage',
            email=email,
        )
        db.commit()

        cls._auth_user = db(db.auth_user.id == auth_user_id).select().first()
        cls._objects.append(cls._auth_user)

        creator_id = db.creator.insert(
            auth_user_id=auth_user_id,
            email=email,
            image=stored_filename,
        )
        db.commit()

        cls._creator = db(db.creator.id == creator_id).select().first()
        cls._objects.append(cls._creator)

        cls._uuid_key = cls._creator.image.split('.')[2][:2]

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)


class TestDownloader(ImageTestCase):

    def test__download(self):
        downloader = Downloader()
        self.assertTrue(downloader)
        env = globals()
        request = env['request']
        request.args = List([self._creator.image])

        lengths = {
            # size: bytes
            'original': 23127,
            'medium': 4723,
            'thumb': 1111,
        }

        def test_http(expect_size):
            try:
                stream = downloader.download(request, db)
            except HTTP as http:
                self.assertEqual(http.status, 200)
                self.assertEqual(http.headers['Content-Type'], 'image/jpeg')
                self.assertEqual(http.headers['Content-Disposition'], 'attachment; filename="file.jpg"')
                self.assertEqual(http.headers['Content-Length'], lengths[expect_size])

        test_http('original')

        # Image not resized, should default to original
        request.vars.size = 'medium'
        test_http('original')
        request.vars.size = 'thumb'
        test_http('original')

        resizer = UploadImage(db.creator.image, self._creator.image)
        resizer.resize_all()

        request.vars.size = None
        test_http('original')
        request.vars.size = 'medium'
        test_http('medium')
        request.vars.size = 'thumb'
        test_http('thumb')


class TestSizer(LocalTestCase):

    def test____init__(self):
        im = Image.new('RGBA', (400, 400))
        sizer = Sizer(im)
        self.assertTrue(sizer)

    def test__size(self):
        im = Image.new('RGBA', (400, 400))
        sizer = Sizer(im)
        self.assertEqual(sizer.size(), (400, 400))


class TestLargeSizer(LocalTestCase):

    _image_dir = '/tmp/image_resizer'

    @classmethod
    def setUp(cls):
        if not os.path.exists(cls._image_dir):
            os.makedirs(cls._image_dir)

    @classmethod
    def tearDown(cls):
        return  # FIXME
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)

    def test____init__(self):
        im = Image.new('RGBA', (400, 400))
        sizer = LargeSizer(im)
        self.assertTrue(sizer)

    def test__size(self):
        tests = [
            # original dimensions (w, h), expect dimensions (w, h)
            ((1200, 750), (1200, 750)),     # landscape
            ((2400, 1500), (1200, 750)),    # large landscape
            ((600, 375), (600, 375)),       # small landscape
            ((750, 1200), (750, 1200)),     # portrait
            ((1500, 2400), (750, 1200)),    # large portrait
            ((375, 600), (375, 600)),       # small portrait
            ((948, 948), (948, 948)),       # square
            ((1000, 1000), (948, 948)),     # large square
            ((400, 400), (400, 400)),       # small square
        ]

        image_filename = os.path.join(self._image_dir, 'test.jpg')

        for t in tests:
            im = Image.new('RGB', t[0])
            with open(image_filename, 'wb') as f:
                im.save(f)
            sizer = LargeSizer(im)
            self.assertEqual(sizer.size(), t[1])


class TestMediumSizer(LocalTestCase):

    def test____init__(self):
        im = Image.new('RGBA', (400, 400))
        sizer = MediumSizer(im)
        self.assertTrue(sizer)

    def test__size(self):
        im = Image.new('RGBA', (1000, 1000))
        sizer = MediumSizer(im)
        self.assertEqual(sizer.size(), MediumSizer.dimensions)

        im = Image.new('RGBA', (400, 400))
        sizer = MediumSizer(im)
        self.assertEqual(sizer.size(), MediumSizer.dimensions)


class TestThumbnailSizer(LocalTestCase):

    def test____init__(self):
        im = Image.new('RGBA', (400, 400))
        sizer = ThumbnailSizer(im)
        self.assertTrue(sizer)

    def test__size(self):
        im = Image.new('RGBA', (400, 400))
        sizer = ThumbnailSizer(im)
        self.assertEqual(sizer.size(), ThumbnailSizer.dimensions)


class TestUploadImage(ImageTestCase):

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
            file_name = original_fullname.replace('/original/', '/{s}/'.format(s=size))
            self.assertTrue(os.path.exists(file_name))
        for size in have_not:
            file_name = original_fullname.replace('/original/', '/{s}/'.format(s=size))
            self.assertTrue(not os.path.exists(file_name))

    def test____init__(self):
        resizer = UploadImage(db.creator.image, self._image_name)
        self.assertTrue(resizer)
        file_name, fullname = db.creator.image.retrieve(
            self._creator.image,
            nameonly=True,
        )
        self.assertEqual(self._image_name, file_name)
        self.assertEqual(resizer._images, {})
        self.assertEqual(resizer._dimensions, {})

    def test__delete(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        resizer.resize_all()

        self._exist(have=['original', 'medium', 'thumb'])
        resizer.delete('medium')
        self._exist(have=['original', 'thumb'], have_not=['medium'])
        resizer.delete('thumb')
        self._exist(have=['original'], have_not=['medium', 'thumb'])
        resizer.delete('thumb')     # Handle subsequent delete gracefully
        self._exist(have=['original'], have_not=['medium', 'thumb'])
        resizer.delete('original')
        self._exist(have_not=['original', 'medium', 'thumb'])

    def test__delete_all(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        resizer.resize_all()

        self._exist(have=['original', 'medium', 'thumb'])
        resizer.delete_all()
        self._exist(have_not=['original', 'medium', 'thumb'])
        resizer.delete_all()        # Handle subsequent delete gracefully
        self._exist(have_not=['original', 'medium', 'thumb'])

    def test__dimensions(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(resizer._dimensions, {})

        dims = resizer.dimensions()
        self.assertTrue('original' in resizer._dimensions)
        self.assertEqual(dims, resizer._dimensions['original'])

        # Should get from cache.
        resizer._dimensions['original'] = (1, 1)
        dims_2 = resizer.dimensions()
        self.assertEqual(dims_2, (1, 1))

        dims_3 = resizer.dimensions(size='medium')
        self.assertTrue('medium' in resizer._dimensions)
        self.assertEqual(dims_3, None)

        del resizer._images['medium']
        del resizer._dimensions['medium']
        medium = resizer.resize('medium')
        dims_4 = resizer.dimensions(size='medium')
        self.assertEqual(dims_4, (500, 500))

    def test__fullname(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(
            resizer.fullname(),
            '/tmp/image_resizer/original/creator.image/{u}/{i}'.format(
                u=self._uuid_key,
                i=self._creator.image,
            ),
        )
        self.assertEqual(
            resizer.fullname(size='medium'),
            '/tmp/image_resizer/medium/creator.image/{u}/{i}'.format(
                u=self._uuid_key,
                i=self._creator.image,
            ),
        )
        self.assertEqual(
            resizer.fullname(size='_fake_'),
            '/tmp/image_resizer/_fake_/creator.image/{u}/{i}'.format(
                u=self._uuid_key,
                i=self._creator.image,
            ),
        )

    def test__pil_image(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(resizer._images, {})

        im = resizer.pil_image()
        self.assertTrue('original' in resizer._images)
        self.assertEqual(im, resizer._images['original'])

        # Should get from cache.
        resizer._images['original'] = '_stub_'
        im_2 = resizer.pil_image()
        self.assertEqual(im_2, resizer._images['original'])

        im_3 = resizer.pil_image(size='medium')
        self.assertTrue('medium' in resizer._images)
        self.assertEqual(im_3, None)

        medium = resizer.resize('medium')
        im_4 = resizer.pil_image(size='medium')
        self.assertEqual(im_4, resizer._images['medium'])

    def test__resize(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        medium = resizer.resize('medium')
        im = Image.open(medium)
        self.assertEqual(im.size, MediumSizer.dimensions)
        thumb = resizer.resize('thumb')
        im = Image.open(thumb)
        self.assertEqual(im.size, ThumbnailSizer.dimensions)

    def test__resize_all(self):
        resizer = UploadImage(db.creator.image, self._creator.image)
        resizer.resize_all()
        unused_filename, original_fullname = db.creator.image.retrieve(
            self._creator.image,
            nameonly=True,
        )
        for size in ['medium', 'thumb']:
            file_name = original_fullname.replace('/original/', '/{s}/'.format(s=size))
            self.assertTrue(os.path.exists(file_name))


class TestFunctions(LocalTestCase):

    def test__img_tag(self):
        def get_tag(tag, tag_type):
            soup = BeautifulSoup(str(tag))
            return soup.find(tag_type)

        def has_attr(element, attr, value):
            self.assertTrue(element)
            self.assertTrue(hasattr(element, attr))
            self.assertEqual(element[attr], value)

        tag = img_tag(None)
        has_attr(get_tag(tag, 'div'), 'class', 'portrait_placeholder')

        tag = img_tag(db.creator.image, size='original')
        has_attr(get_tag(tag, 'img'), 'src', '/images/download?size=original')

        tag = img_tag(db.creator.image, size='thumb')
        has_attr(get_tag(tag, 'img'), 'src', '/images/download?size=thumb')

        tag = img_tag(db.creator.image, size='_fake_')
        has_attr(get_tag(tag, 'img'), 'src', '/images/download?size=original')

        # Test img_attributes parameter
        attrs = dict(_class='img_class', _id='img_id', _style='height: 1px;')
        tag = img_tag(db.creator.image, img_attributes=attrs)
        has_attr(get_tag(tag, 'img'), 'src', '/images/download?size=original')
        has_attr(get_tag(tag, 'img'), 'class', 'img_class')
        has_attr(get_tag(tag, 'img'), 'id', 'img_id')
        has_attr(get_tag(tag, 'img'), 'style', 'height: 1px;')

        # If _src is among img_attributes, it should supercede.
        attrs = dict(_src='http://www.src.com', _id='img_id')
        tag = img_tag(db.creator.image, img_attributes=attrs)
        has_attr(get_tag(tag, 'img'), 'src', 'http://www.src.com')
        has_attr(get_tag(tag, 'img'), 'id', 'img_id')

    def test__is_image(self):
        # Test common image types.
        image_dir = '/tmp/test__is_image'
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        original_filename = os.path.join(image_dir, 'original.jpg')

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
                outfile = os.path.join(os.path.dirname(original_filename), t[0])
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

    def test__set_thumb_dimensions(self):
        book_page_id = db.book_page.insert(
            page_no=1,
            thumb_w=0,
            thumb_h=0,
            thumb_shrink=0,
        )
        db.commit()
        book_page = db(db.book_page.id == book_page_id).select().first()
        self._objects.append(book_page)

        tests = [
            # dimensions, expect
            ((170, 170), 0.80),
            ((170, 121), 0.80),
            ((170, 120), 1),
            ((121, 170), 0.80),
            ((120, 170), 1),
            ((120, 120), 1),
            ((121, 121), 0.80),
        ]

        for t in tests:
            set_thumb_dimensions(db, book_page.id, t[0])
            book_page = db(db.book_page.id == book_page_id).select().first()
            self.assertEqual(book_page.thumb_w, t[0][0])
            self.assertEqual(book_page.thumb_h, t[0][1])
            self.assertEqual(book_page.thumb_shrink, t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
