#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Unit test helper classes and functions.
"""
import hashlib
import os
import shutil
import subprocess
import glob
from PIL import Image
from gluon import *
from applications.zcomx.modules.images import \
    ImageDescriptor, \
    UploadImage, \
    store
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.shell_utils import TempDirectoryMixin


class FileTestCase(LocalTestCase):
    """Base class for test cases associated with files.

    Provides file related functions.
    """
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


class WithTestDataDirTestCase(LocalTestCase):
    """Base class for test cases that need access to test data directory."""

    _test_data_dir = None

    def setUp(self):
        self._test_data_dir = os.path.join(
            current.request.folder, 'private/test/data/')
        super(WithTestDataDirTestCase, self).setUp()


class ImageTestCase(WithTestDataDirTestCase):
    """Base class for test cases associated with images. """

    _image_dir = '/tmp/test_image'
    _image_name = 'file.jpg'
    _image_original_dir = os.path.join(_image_dir, 'original')
    _uploadfolders = {}

    def _create_image(
            self,
            image_name,
            dimensions=None,
            working_directory=None):
        """Create an image to test with.

        Args:
            image_name: string, name of image file
            dimensions: tuple, (width px, height px) if not None, the image
                will be created with these dimensions.
            working_directory: string, path of working directory to copy to.
                If None, uses self._image_dir
        """
        if working_directory is None:
            working_directory = os.path.abspath(self._image_dir)
        if not os.path.exists(working_directory):
            os.makedirs(working_directory)

        image_filename = os.path.join(working_directory, image_name)
        if not dimensions:
            dimensions = (1200, 1200)

        im = Image.new('RGB', dimensions)
        with open(image_filename, 'wb') as f:
            im.save(f)
        return image_filename

    def _prep_image(self, img, working_directory=None, to_name=None):
        """Prepare an image for testing.
        Copy an image from private/test/data to a working directory.

        Args:
            img: string, name of source image, eg file.jpg
                must be in self._test_data_dir
            working_directory: string, path of working directory to copy to.
                If None, uses self._image_dir
            to_name: string, optional, name of image to copy file to.
                If None, img is used.
        """
        src_filename = os.path.join(
            os.path.abspath(self._test_data_dir),
            img
        )

        if working_directory is None:
            working_directory = os.path.abspath(self._image_dir)
        if not os.path.exists(working_directory):
            os.makedirs(working_directory)

        if to_name is None:
            to_name = img

        filename = os.path.join(working_directory, to_name)
        shutil.copy(src_filename, filename)
        return filename

    def _set_image(self, field, record, img, resizer=None):
        """Set the image for a record field.

        Args:
            field: gluon.dal.Field instance
            record: Row instance.
            img: string, path/to/name of image.
        Returns:
            Name of the stored image file.
        """
        # Delete images if record field is set.
        db = current.app.db
        if record[field.name]:
            up_image = UploadImage(field, record[field.name])
            up_image.delete_all()
        stored_filename = store(field, img, resizer=resizer)
        data = {field.name: stored_filename}
        record.update_record(**data)
        db.commit()
        return stored_filename

    def setUp(self):
        if not os.path.exists(self._image_dir):
            os.makedirs(self._image_dir)
        super(ImageTestCase, self).setUp()

    def tearDown(self):
        if os.path.exists(self._image_dir):
            shutil.rmtree(self._image_dir)
        super(ImageTestCase, self).tearDown()

    @classmethod
    def setUpClass(cls):
        db = current.app.db
        if not os.path.exists(cls._image_original_dir):
            os.makedirs(cls._image_original_dir)

        # Store images in tmp directory
        for table in ['book_page', 'creator']:
            if table not in cls._uploadfolders:
                cls._uploadfolders[table] = {}
            for field in db[table].fields:
                if db[table][field].type == 'upload':
                    cls._uploadfolders[table][field] = \
                        db[table][field].uploadfolder
                    db[table][field].uploadfolder = cls._image_original_dir

    @classmethod
    def tearDownClass(cls):
        db = current.app.db
        for table in ['book_page', 'creator']:
            for field in db[table].fields:
                if db[table][field].type == 'upload':
                    db[table][field].uploadfolder = \
                        cls._uploadfolders[table][field]


class ResizerQuick(TempDirectoryMixin):
    """Class representing resizer for testing.

    The file sizes are just copied from test data. <size>.jpg
    Much faster than the default resizer.
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
        test_data_dir = os.path.join(
            current.request.folder, 'private/test/data/')
        os.nice(nice and 10 or 0)

        descriptor = ImageDescriptor(self.filename)
        width = descriptor.dimensions()[0]

        for k in self.filenames.keys():
            if k == 'ori':
                src = self.filename
            else:
                src = os.path.join(test_data_dir, '{k}.jpg'.format(k=k))
                # If a small image is resized, it shouldn't create versions
                # of larger images, eg a 'web' sized image won't create 'cbz'
                descriptor = ImageDescriptor(src)
                src_width = descriptor.dimensions()[0]
                if src_width > width:
                    continue
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
