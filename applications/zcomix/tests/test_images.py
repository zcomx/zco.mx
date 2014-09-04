#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/utils.py

"""
import grp
import inspect
import os
import pwd
import re
import shutil
import time
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.html import DIV, IMG
from gluon.http import HTTP
from gluon.storage import List
from applications.zcomix.modules.images import \
    CreatorImgTag, \
    Downloader, \
    ImageOptimizeError, \
    ImgTag, \
    ResizeImgError, \
    ResizeImg, \
    SIZES, \
    UploadImage, \
    filename_for_size, \
    is_image, \
    optimize, \
    set_thumb_dimensions, \
    store
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
 # pylint: disable=W0212


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _auth_user = None
    _creator = None
    _image_dir = '/tmp/image_resizer'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _uuid_key = None
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

    @classmethod
    def _set_image(cls, field, record, img):
        """Set the image for a record field.

        Args:
            field: gluon.dal.Field instance
            record: Row instance.
            img: string, path/to/name of image.
        """
        # Delete images if record field is set.
        if record[field.name]:
            up_image = UploadImage(field, record[field.name])
            up_image.delete_all()
        stored_filename = store(field, img)
        data = {field.name: stored_filename}
        record.update_record(**data)
        db.commit()

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        src_filename = os.path.join(cls._test_data_dir, 'cbz_plus.jpg')
        image_filename = os.path.join(cls._image_dir, cls._image_name)
        shutil.copy(src_filename, image_filename)

        # Store the image in the uploads/original directory
        stored_filename = store(db.creator.image, image_filename)

        # Create a creator and set the image
        email = 'up_image@example.com'
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

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)
        if cls._creator.image:
            up_image = UploadImage(db.creator.image, cls._creator.image)
            up_image.delete_all()


class TestCreatorImgTag(ImageTestCase):

    def test_parent__init__(self):
        img_tag = CreatorImgTag('')
        self.assertTrue(img_tag)
        self.assertEqual(img_tag.placeholder_tag, DIV)

    def test__set_placeholder(self):
        img_tag = CreatorImgTag(None)
        self.assertEqual(img_tag.attributes, {})
        img_tag.set_placeholder()
        self.assertEqual(len(img_tag.components), 1)
        self.assertEqual(
            str(img_tag.components[0]),
            '<i class="icon zc-torso"></i>'
        )
        self.assertEqual(
            img_tag.attributes,
            {'_class': 'preview placeholder_torso'}
        )

        img_tag = CreatorImgTag(None, size='tbn')
        self.assertEqual(img_tag.attributes, {})
        img_tag.set_placeholder()
        self.assertEqual(
            img_tag.attributes,
            {'_class': 'preview placeholder_torso'}
        )

        attrs = {'_id': 'img_id', '_class': 'img_class'}
        img_tag = CreatorImgTag(None, attributes=attrs)
        self.assertEqual(img_tag.attributes, attrs)
        img_tag.set_placeholder()
        self.assertEqual(
            img_tag.attributes,
            {'_class': 'img_class preview placeholder_torso', '_id': 'img_id'})


class TestDownloader(ImageTestCase):

    def test__download(self):
        downloader = Downloader()
        self.assertTrue(downloader)
        env = globals()
        request = env['request']

        def set_lengths():
            lengths = {}
            for size in ['original', 'cbz', 'web', 'tbn']:
                unused_name, fullname = db.creator.image.retrieve(
                    self._creator.image, nameonly=True)
                filename = filename_for_size(fullname, size)
                if os.path.exists(filename):
                    lengths[size] = os.stat(filename).st_size
            return lengths

        def test_http(expect_size):
            request.args = List([self._creator.image])
            try:
                downloader.download(request, db)
            except HTTP as http:
                self.assertEqual(http.status, 200)
                self.assertEqual(http.headers['Content-Type'], 'image/jpeg')
                self.assertEqual(
                    http.headers['Content-Disposition'],
                    'attachment; filename="file.jpg"'
                )
                self.assertEqual(
                    http.headers['Content-Length'],
                    lengths[expect_size]
                )

        # tbn.jpg is tiny, only the thumbnail should be created.
        filename = self._prep_image('tbn.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        lengths = set_lengths()
        request.vars.size = 'tbn'
        test_http('tbn')
        request.vars.size = 'web'
        test_http('original')
        request.vars.size = 'cbz'
        test_http('original')
        request.vars.size = 'original'
        test_http('original')

        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        lengths = set_lengths()
        request.vars.size = 'tbn'
        test_http('tbn')
        request.vars.size = 'web'
        test_http('web')
        request.vars.size = 'cbz'
        test_http('cbz')
        request.vars.size = 'original'
        test_http('original')


class TestImageOptimizeError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise ImageOptimizeError(msg)
        except ImageOptimizeError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('ImageOptimizeError not raised')


class TestImgTag(ImageTestCase):

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

        def get_tag(tag, tag_type):
            soup = BeautifulSoup(str(tag))
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
        has_attr(get_tag(tag, 'img'), 'src', self._creator.image, oper='in')
        has_attr(get_tag(tag, 'img'), 'src', 'size=original', oper='in')

        img_tag = ImgTag(self._creator.image, size='tbn')
        tag = img_tag()
        has_attr(get_tag(tag, 'img'), 'src', 'size=tbn', oper='in')

        # Test no image
        img_tag = ImgTag(None)
        tag = img_tag()
        has_attr(get_tag(tag, 'div'), 'class', 'portrait_placeholder')
        img_tag = ImgTag(None, size='tbn')
        tag = img_tag()
        has_attr(get_tag(tag, 'div'), 'class', 'placeholder_170x170')

        # Test: provide tag
        img_tag = ImgTag(self._creator.image, tag=SPAN)
        tag = img_tag()
        has_attr(get_tag(tag, 'span'), '', '', oper='')

        # Test: provide components
        components = [DIV('_test_imgtag_')]
        img_tag = ImgTag(self._creator.image, tag=DIV, components=components)
        tag = img_tag()
        soup = BeautifulSoup(str(tag))
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
        has_attr(get_tag(tag, 'img'), 'class', 'img_class')
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

        img_tag = ImgTag(None, size='tbn')
        self.assertEqual(img_tag.attributes, {})
        img_tag.set_placeholder()
        self.assertEqual(img_tag.attributes, {'_class': 'placeholder_170x170'})

        attrs = {'_id': 'img_id', '_class': 'img_class'}
        img_tag = ImgTag(None, attributes=attrs)
        self.assertEqual(img_tag.attributes, attrs)
        img_tag.set_placeholder()
        self.assertEqual(
            img_tag.attributes,
            {'_class': 'img_class portrait_placeholder', '_id': 'img_id'}
        )


class TestResizeImg(ImageTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        resize_img = ResizeImg(filename)
        self.assertTrue(resize_img)
        self.assertEqual(resize_img.filename_base, 'file.jpg')
        self.assertEqual(resize_img._temp_directory, None)
        self.assertEqual(
            resize_img.filenames,
            {
                'cbz': None,
                'ori': None,
                'tbn': None,
                'web': None,
            }
        )

    def test__run(self):
        # !!!! ResizeImg.run() moves the image to a working directory.
        # Make copies of test data images before using so they don't get
        # removed from test data.

        def test_it(image_name, expect, to_name=None):
            filename = self._prep_image(image_name, to_name=to_name)
            resize_img = ResizeImg(filename)
            resize_img.run()
            tmp_dir = resize_img.temp_directory()
            for fmt, prefixes in expect.items():
                for prefix in prefixes:
                    self.assertTrue(prefix in resize_img.filenames)
                    self.assertEqual(
                        resize_img.filenames[prefix],
                        os.path.join(tmp_dir, fmt.format(typ=prefix))
                    )

        # Test: standard jpg
        test_it(
            'cbz_plus.jpg',
            {
                '{typ}-cbz_plus.jpg': ['ori', 'cbz', 'web', 'tbn'],
            }
        )

        # Test: file with no extension
        test_it(
            'image_with_no_ext',
            {
                # Image is not big enough to produce a cbz file.
                '{typ}-image_with_no_ext.jpg': ['ori', 'web', 'tbn'],
            }
        )

        # Test: convert gif to png
        test_it(
            'eg.gif',
            {
                '{typ}-eg.gif': ['ori'],
                # Image is small so only a thumbnail should be produced.
                '{typ}-eg.png': ['tbn'],
            }
        )

        # Test: animated.gif
        test_it(
            'animated.gif',
            {
                '{typ}-animated.gif': ['ori'],
                # Image is small so only a thumbnail should be produced.
                '{typ}-animated.png': ['tbn'],
            }
        )

        # Test: cmyk
        test_it(
            'cmyk.jpg',
            {
                # Image is small so only a thumbnail should be produced.
                '{typ}-cmyk.jpg': ['ori', 'tbn'],
            }
        )

        # Test: file with incorrect extension
        test_it(
            'jpg_with_wrong_ext.png',
            {
                # Image is not big enough to produce a cbz file.
                '{typ}-jpg_with_wrong_ext.jpg': ['ori', 'web', 'tbn'],
            }
        )

        # Test: files with prefixes
        for dest in ['ori-file.png', 'web-file.png', 'tbn-file.png']:
            fmt = '{{typ}}-{dest}'.format(dest=dest)
            test_it(
                'file.png',
                {
                    fmt: ['ori', 'web', 'tbn'],
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
            self.assertTrue(os.path.exists(filename_for_size(
                original_fullname, size)))
        for size in have_not:
            self.assertTrue(not os.path.exists(filename_for_size(
                original_fullname, size)))

    def test____init__(self):
        up_image = UploadImage(db.creator.image, self._image_name)
        self.assertTrue(up_image)
        file_name, unused_fullname = db.creator.image.retrieve(
            self._creator.image,
            nameonly=True,
        )
        self.assertEqual(self._image_name, file_name)
        self.assertEqual(up_image._images, {})
        self.assertEqual(up_image._dimensions, {})

    def test__delete(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)

        self._exist(have=['original', 'cbz', 'web', 'tbn'])
        up_image.delete('web')
        self._exist(have=['original', 'cbz', 'tbn'], have_not=['web'])
        up_image.delete('tbn')
        self._exist(have=['original', 'cbz'], have_not=['web', 'tbn'])
        up_image.delete('tbn')     # Handle subsequent delete gracefully
        up_image.delete('cbz')
        self._exist(have=['original'], have_not=['cbz', 'web', 'tbn'])
        up_image.delete('original')
        self._exist(have_not=['original', 'cbz', 'web', 'tbn'])

    def test__delete_all(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)

        self._exist(have=['original', 'cbz', 'web', 'tbn'])
        up_image.delete_all()
        self._exist(have_not=['original', 'cbz', 'web', 'tbn'])
        up_image.delete_all()        # Handle subsequent delete gracefully
        self._exist(have_not=['original', 'cbz', 'web', 'tbn'])

    def test__dimensions(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(up_image._dimensions, {})

        dims = up_image.dimensions()
        self.assertTrue('original' in up_image._dimensions)
        self.assertEqual(dims, up_image._dimensions['original'])

        # Should get from cache.
        up_image._dimensions['original'] = (1, 1)
        dims_2 = up_image.dimensions()
        self.assertEqual(dims_2, (1, 1))

        dims_3 = up_image.dimensions(size='web')
        self.assertTrue('web' in up_image._dimensions)
        self.assertEqual(dims_3, (750, 1125))

        dims_4 = up_image.dimensions(size='tbn')
        self.assertTrue('tbn' in up_image._dimensions)
        self.assertEqual(dims_4, (112, 168))

    def test__fullname(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        uuid_key = self._creator.image.split('.')[2][:2]

        up_image = UploadImage(db.creator.image, self._creator.image)
        fmt = 'applications/zcomix/uploads/{s}/creator.image/{u}/{i}'
        self.assertEqual(
            up_image.fullname(),
            fmt.format(
                s='original',
                u=uuid_key,
                i=self._creator.image,
            ),
        )
        self.assertEqual(
            up_image.fullname(size='web'),
            fmt.format(
                s='web',
                u=uuid_key,
                i=self._creator.image,
            ),
        )
        self.assertEqual(
            up_image.fullname(size='_fake_'),
            fmt.format(
                s='_fake_',
                u=uuid_key,
                i=self._creator.image,
            ),
        )

    def test__pil_image(self):
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(up_image._images, {})

        im = up_image.pil_image()
        self.assertTrue('original' in up_image._images)
        self.assertEqual(im, up_image._images['original'])

        # Should get from cache.
        up_image._images['original'] = '_stub_'
        im_2 = up_image.pil_image()
        self.assertEqual(im_2, up_image._images['original'])

        im_3 = up_image.pil_image(size='web')
        self.assertTrue('web' in up_image._images)
        self.assertTrue(hasattr(im_3, 'size'))


class TestFunctions(ImageTestCase):

    def test__filename_for_size(self):
        tests = [
            #(original, size, expect),
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

    def test__optimize(self):
        for img in ['unoptimized.png', 'unoptimized.jpg']:
            working_image = self._prep_image(img)
            size_bef = os.stat(working_image).st_size
            optimize(working_image)
            time.sleep(1)          # Wait for background process to complete.
            size_aft = os.stat(working_image).st_size
            self.assertTrue(size_aft < size_bef)

    def test__set_thumb_dimensions(self):
        book_page_id = db.book_page.insert(
            page_no=1,
            thumb_w=0,
            thumb_h=0,
        )
        db.commit()
        book_page = db(db.book_page.id == book_page_id).select().first()
        self._objects.append(book_page)

        tests = [
            # dimensions
            (170, 170),
            (170, 121),
        ]

        for t in tests:
            set_thumb_dimensions(db, book_page.id, t)
            book_page = db(db.book_page.id == book_page_id).select().first()
            self.assertEqual(book_page.thumb_w, t[0])
            self.assertEqual(book_page.thumb_h, t[1])

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
            r'book_page\.image\.[a-f0-9]{16}\.[a-f0-9]+\.jpg')
        # Eg book_page.image.ad8557025bd26287.66696c652e6a7067.jpg
        #    book_page.image.810bab749df4eaeb.63627a5f706c75732e6a7067.jpg
        self.assertTrue(re_store.match(got))

        # Check that files exists for all sizes
        up_image = UploadImage(db.book_page.image, got)
        for size in ['original', 'cbz', 'web', 'tbn']:
            filename = up_image.fullname(size=size)
            self.assertTrue(os.path.exists(filename))
            self.assertEqual(owner(filename), ('http', 'http'))

        # Cleanup: Remove all files
        up_image.delete_all()
        for size in ['original', 'cbz', 'web', 'tbn']:
            filename = up_image.fullname(size=size)
            # os.unlink(filename)
            self.assertFalse(os.path.exists(filename))

        # Prove original filename is preserved.
        working_image = self._prep_image('image_with_no_ext')
        got = store(db.book_page.image, working_image)
        original_filename, _ = db.book_page.image.retrieve(got, nameonly=True)
        self.assertEqual(original_filename, 'image_with_no_ext')
        up_image = UploadImage(db.book_page.image, got)
        up_image.delete_all()


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
