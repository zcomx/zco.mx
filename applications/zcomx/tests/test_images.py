#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/images.py

"""
import glob
import grp
import hashlib
import inspect
import os
import pwd
import re
import shutil
import subprocess
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.html import DIV, IMG
from gluon.http import HTTP
from applications.zcomx.modules.images import \
    CreatorImgTag, \
    ImageOptimizeError, \
    ImgTag, \
    ResizeImgError, \
    ResizeImg, \
    ResizeImgIndicia, \
    SIZES, \
    UploadImage, \
    filename_for_size, \
    is_image, \
    on_delete_image, \
    optimize, \
    scrub_extension_for_store, \
    store
from applications.zcomx.modules.tests.runner import \
    LocalTestCase
from applications.zcomx.modules.shell_utils import \
    imagemagick_version, \
    TempDirectoryMixin
from applications.zcomx.modules.utils import \
    entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
# pylint: disable=W0212


class ResizerForTesting(TempDirectoryMixin):
    """Class representing resizer for testing.

    The file sizes are just copied from test data. <size>.jpg
    """

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of original image file
        """
        self.filename = filename
        self.filenames = {'ori': None, 'cbz': None, 'web': None}

    def run(self, nice=False):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice.
        """
        # Keep this simple and fast.
        test_data_dir = os.path.join(request.folder, 'private/test/data/')
        os.nice(nice and 10 or 0)
        for k in self.filenames.keys():
            if k == 'ori':
                src = self.filename
            else:
                src = os.path.join(test_data_dir, '{k}.jpg'.format(k=k))
            dst = os.path.join(
                self.temp_directory(), '{k}-test.jpg'.format(k=k))
            shutil.copy(src, dst)

        for prefix in self.filenames.keys():
            path = os.path.join(
                self.temp_directory(),
                '{pfx}-*'.format(pfx=prefix)
            )
            matches = glob.glob(path)
            if matches:
                self.filenames[prefix] = matches[0]


class ResizerUseOri(TempDirectoryMixin):
    """Class representing resizer for testing.

    The file sizes are just duplicates of the original file.
    """

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of original image file
        """
        self.filename = filename
        self.filenames = {'ori': None, 'cbz': None, 'web': None}

    def run(self, nice=False):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice.
        """
        # Keep this simple and fast.
        # Copy files from test data. <size>.jpg
        os.nice(nice and 10 or 0)
        for k in self.filenames.keys():
            src = self.filename
            dst = os.path.join(
                self.temp_directory(), '{k}-test.jpg'.format(k=k))
            shutil.copy(src, dst)

        for prefix in self.filenames.keys():
            path = os.path.join(
                self.temp_directory(),
                '{pfx}-*'.format(pfx=prefix)
            )
            matches = glob.glob(path)
            if matches:
                self.filenames[prefix] = matches[0]


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _auth_user = None
    _creator = None
    _image_dir = '/tmp/image_resizer'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _test_data_dir = None
    _uuid_key = None

    _objects = []

    @classmethod
    def _md5sum(cls, file_obj):
        """Return md5sum of a file.

        Args:
            file_obj: file or file like object.
        """
        file_to_hash = file_obj
        if isinstance(file_obj, str) and file_obj.endswith('.png'):
            # Remove the date metadata from png files as this will
            # be unique everytime the file is converted.
            outfile = file_obj + '.tmp'

            # convert infile.png +set date:modify +set date:create outfile.png
            args = [
                'convert',
                file_obj,
                '+set',
                'date:modify',
                '+set',
                'date:create',
                outfile
            ]
            p = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_stdout, p_stderr = p.communicate()
            if p_stdout:
                print 'FIXME p_stdout: {var}'.format(var=p_stdout)
            if p_stderr:
                print 'FIXME p_stderr: {var}'.format(var=p_stderr)
            file_to_hash = outfile

        return hashlib.md5(open(file_to_hash, 'rb').read()).hexdigest()

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

        src_filename = os.path.join(cls._test_data_dir, 'tbn_plus.jpg')
        image_filename = os.path.join(cls._image_dir, cls._image_name)
        shutil.copy(src_filename, image_filename)

        # Store the image in the uploads/original directory
        stored_filename = store(db.creator.image, image_filename)

        # Create a creator and set the image
        email = 'up_image@example.com'
        cls._auth_user = cls.add(db.auth_user, dict(
            name='Image UploadImage',
            email=email,
        ))

        cls._creator = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email=email,
            image=stored_filename,
        ))

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

        img_tag = CreatorImgTag(None, size='web')
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

        img_tag = ImgTag(self._creator.image, size='web')
        tag = img_tag()
        has_attr(get_tag(tag, 'img'), 'src', 'size=web', oper='in')

        # Test no image
        img_tag = ImgTag(None)
        tag = img_tag()
        has_attr(get_tag(tag, 'div'), 'class', 'portrait_placeholder')
        img_tag = ImgTag(None, size='web')
        tag = img_tag()
        has_attr(get_tag(tag, 'div'), 'class', 'portrait_placeholder')

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


class TestResizeImg(ImageTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        resize_img = ResizeImg(filename)
        self.assertTrue(resize_img)
        self.assertEqual(resize_img._temp_directory, None)
        self.assertEqual(
            resize_img.filenames,
            {
                'cbz': None,
                'ori': None,
                'web': None,
            }
        )

    def test__run(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        # !!!! ResizeImg.run() moves the image to a working directory.
        # Make copies of test data images before using so they don't get
        # removed from test data.

        # resize_img.sh relies on RobidouxSharp filter added in imagemagick
        # ver 6.7.6-8. Abort if that version is not available.
        minimum_ver = '6.7.6-8'
        version_as_num = lambda v: float(v.replace('.', '').replace('-', '.'))
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
            for fmt, prefixes in expect.items():
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
                        im = Image.open(resize_img.filenames[prefix])
                        self.assertTrue(
                            len(im.getcolors(maxcolors=99999)) in colors
                        )

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        # Test: test the md5 sum of files.
        #
        # cp applications/zcomx/private/test/data/256* ~/tmp/img/before/
        # pushd ~/tmp/img
        # rm *.jpg
        # rm *.png
        # rm *.gif
        # ./applications/zcomx/private/bin/resize_img.sh before/*
        # # Remove the dates from png files
        # for f in *.png; do echo "$f"; convert "$f" +set date:modify +set date:create "$f"; done
        # md5sum * | awk -v q="'" '{print q$2q": " q$1q","}'

        md5s = {
            '6.7.0-8': {
                'cbz-256+colour.jpg': '0e11a2cf49d1c1c4166969f463744bc2',
                'cbz-256colour-gif.png': 'f2f7d46dc03973e4d101c81edcb40d28',
                'cbz-256colour-jpg.jpg': '1bf61782de787ba0e4982f87a6617d3e',
                'cbz-256colour-png.png': '003b83e169361b3bf8acc9f625fac93c',
                'ori-256+colour.jpg': '02f34f15b65cb06712a4b18711c21cf6',
                'ori-256colour-gif.gif': 'e5be67271b109de2d8b0cb8a7e7643cf',
                'ori-256colour-jpg.jpg': 'a0c2469208f00a9c2ba7e6cb71858008',
                'ori-256colour-png.png': 'f6fed54a1715af0551bdef77f7bc7ff6',
                'web-256+colour.jpg': 'c74c78460486814115d351ba22fc50b5',
                'web-256colour-gif.png': '5467c6943af05ced624f04c60ebe7c2c',
                'web-256colour-jpg.jpg': '9fe865e5a7ba404e4221779e1cdce336',
                'web-256colour-png.png': '9842a943933ae8ad642bb17b9bdbbd47',
            },
            '6.8.8-7': {
                'cbz-256+colour.jpg': '0e11a2cf49d1c1c4166969f463744bc2',
                'cbz-256colour-gif.png': 'f60e388aa3cf74f81a436b5bdae610cb',
                'cbz-256colour-jpg.jpg': '1bf61782de787ba0e4982f87a6617d3e',
                'cbz-256colour-png.png': '9b2e81c0cf9e27f591d9bd24310fbece',
                'ori-256+colour.jpg': '02f34f15b65cb06712a4b18711c21cf6',
                'ori-256colour-gif.gif': 'e5be67271b109de2d8b0cb8a7e7643cf',
                'ori-256colour-jpg.jpg': 'a0c2469208f00a9c2ba7e6cb71858008',
                'ori-256colour-png.png': 'f6fed54a1715af0551bdef77f7bc7ff6',
                'web-256+colour.jpg': 'c74c78460486814115d351ba22fc50b5',
                'web-256colour-gif.png': 'babcef0095c0082c7b9ffbea2b4bc89c',
                'web-256colour-jpg.jpg': '9fe865e5a7ba404e4221779e1cdce336',
                'web-256colour-png.png': '436c4a952f333d61cdd8a8f61b6538ad',
            },
            '6.9.0-0': {
                'cbz-256+colour.jpg': '0e11a2cf49d1c1c4166969f463744bc2',
                'cbz-256colour-gif.png': 'a98552ba461b7a71e4afbc99d6f7fa81',
                'cbz-256colour-jpeg.jpg': '1bf61782de787ba0e4982f87a6617d3e',
                'cbz-256colour-jpg.jpg': 'e248e32cc276d7e7ec02de22ad98e702',
                'cbz-256colour-png.png': '9b2e81c0cf9e27f591d9bd24310fbece',
                'ori-256+colour.jpg': '02f34f15b65cb06712a4b18711c21cf6',
                'ori-256colour-gif.gif': 'e5be67271b109de2d8b0cb8a7e7643cf',
                'ori-256colour-gif.png': '6c91f0802c68b9f4699d51688db530c5',
                'ori-256colour-jpeg.jpg': 'a0c2469208f00a9c2ba7e6cb71858008',
                'ori-256colour-jpg.jpg': 'a0c2469208f00a9c2ba7e6cb71858008',
                # 'ori-256colour-png.png': 'f6fed54a1715af0551bdef77f7bc7ff6',
                'ori-256colour-png.png': '68d8435b225949d36b428b380dd493ac',
                'web-256+colour.jpg': 'c74c78460486814115d351ba22fc50b5',
                # 'web-256colour-gif.png': '9951bff8ec37124ac7989e0fc465880e',
                'web-256colour-gif.png': 'bc300c3181e8a99e6d7562bc99beead0',
                'web-256colour-jpeg.jpg': '9fe865e5a7ba404e4221779e1cdce336',
                'web-256colour-jpg.jpg': 'd4643040166b53463d04947677b72c74',
                # 'web-256colour-png.png': '436c4a952f333d61cdd8a8f61b6538ad',
                'web-256colour-png.png': '629453bf2ff2c60119c87e74cc8a1b21',
            },
        }

        imgs = [
            '256colour-jpg.jpg',
            '256colour-jpeg.jpeg',
            '256colour-png.png',
            '256colour-gif.gif',
        ]

        for img in imgs:
            dest = img.replace('.gif', '.png').replace('.jpeg', '.jpg')
            fmt = '{{typ}}-{dest}'.format(dest=dest)
            test_it(
                img,
                {
                    fmt: ['ori', 'cbz', 'web'],
                },
                md5s=md5s[imagemagick_ver],
                # The number of colours may be reduced for png files. The
                # exact value is not critical, as long as it is 256 or less.
                colors=[255, 256],
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
            'cbz_plus.jpg',
            {
                '{typ}-cbz_plus.jpg': ['ori', 'cbz', 'web'],
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
        for dest in ['ori-file.png', 'web-file.png', 'tbn-file.png']:
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


class TestResizeImgIndicia(ImageTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        resize_img = ResizeImgIndicia(filename)
        self.assertTrue(resize_img)
        self.assertEqual(resize_img._temp_directory, None)
        self.assertEqual(
            resize_img.filenames,
            {'ori': None}
        )

    def test__run(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        filename = self._prep_image('256colour-jpg.jpg')
        resize_img = ResizeImgIndicia(filename)
        resize_img.run()
        tmp_dir = resize_img.temp_directory()
        self.assertEqual(resize_img.filenames.keys(), ['ori'])
        self.assertEqual(
            resize_img.filenames['ori'],
            os.path.join(tmp_dir, 'ori-256colour-jpg.jpg')
        )

        md5s = {
            '6.9.0-0': {
                'ori-256colour-jpg.jpg': 'c7d7ec3181be621f576111a2569935f2'
            },
        }

        imagemagick_ver = imagemagick_version()
        self.assertEqual(
            self._md5sum(resize_img.filenames['ori']),
            md5s[imagemagick_ver]['ori-256colour-jpg.jpg']
        )


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
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

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
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)

        self._exist(have=['original', 'cbz', 'web'])
        up_image.delete_all()
        self._exist(have_not=['original', 'cbz', 'web'])
        up_image.delete_all()        # Handle subsequent delete gracefully
        self._exist(have_not=['original', 'cbz', 'web'])

    def test__dimensions(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
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

    def test__fullname(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        uuid_key = self._creator.image.split('.')[2][:2]

        up_image = UploadImage(db.creator.image, self._creator.image)
        fmt = 'applications/zcomx/uploads/{s}/creator.image/{u}/{i}'
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

    def test__orientation(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        book_page = self.add(db.book_page, dict())

        for t in ['portrait', 'landscape', 'square']:
            img = '{n}.png'.format(n=t)
            filename = self._prep_image(img)
            self._set_image(db.book_page.image, book_page, filename)
            up_image = UploadImage(db.book_page.image, book_page.image)
            self.assertEqual(up_image.orientation(), t)

    def test__original_name(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        filename = self._prep_image('cbz_plus.jpg', to_name='abc.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(up_image.original_name(), 'abc.jpg')

    def test__pil_image(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
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

    def test__retrieve(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        uuid_key = self._creator.image.split('.')[2][:2]

        up_image = UploadImage(db.creator.image, self._creator.image)
        fmt = 'applications/zcomx/uploads/original/creator.image/{u}/{i}'
        self.assertEqual(
            up_image.retrieve(),
            (
                'file.jpg',
                fmt.format(u=uuid_key, i=self._creator.image)
            )
        )

        # Test cache
        up_image._original_name = '_original_'
        up_image._full_name = '_full_'
        self.assertEqual(up_image.retrieve(), ('_original_', '_full_'))

    def test__size(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)

        up_image = UploadImage(db.creator.image, self._creator.image)
        self.assertEqual(up_image._sizes, {})

        size = up_image.size()
        self.assertTrue('original' in up_image._sizes)
        self.assertEqual(size, up_image._sizes['original'])
        self.assertEqual(size, 77015)

        # Should get from cache.
        up_image._sizes['original'] = 9999
        size_2 = up_image.size()
        self.assertEqual(size_2, 9999)

        size_3 = up_image.size(size='web')
        self.assertTrue('web' in up_image._sizes)
        self.assertEqual(size_3, 3474)


class TestFunctions(ImageTestCase):

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
            working_image = self._prep_image(img)
            size_bef = os.stat(working_image).st_size
            optimize(working_image)
            size_aft = os.stat(working_image).st_size
            self.assertTrue(size_aft < size_bef)

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

    def test__store(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

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
        dims = {}
        for size in ['original', 'cbz', 'web']:
            filename = up_image.fullname(size=size)
            self.assertTrue(os.path.exists(filename))
            self.assertEqual(owner(filename), ('http', 'http'))
            dims[size] = up_image.dimensions(size=size)
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
        got = store(db.book_page.image, working_image)
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
            dims[size] = up_image.dimensions(size=size)
        # All should be the same size
        for i in range(0, 2):
            self.assertEqual(dims['original'][i], dims['cbz'][i])
            self.assertEqual(dims['original'][i], dims['web'][i])

        # Test resizer param
        working_image = self._prep_image('cbz_plus.jpg')
        got = store(
            db.book_page.image, working_image, resizer=ResizerForTesting)
        self.assertTrue(re_store.match(got))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
