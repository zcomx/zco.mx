#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Unit test helper classes and functions.
"""
import datetime
import hashlib
import os
import shutil
import subprocess
import glob
import unittest
from functools import wraps
from PIL import Image
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.environ import has_terminal
from applications.zcomx.modules.images import \
    ImageDescriptor, \
    UploadImage, \
    store
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.shell_utils import TempDirectoryMixin


class DubMeta(type):
    """Class for creating dub classes with prescribed method behaviour."""

    def __new__(mcs, name, bases, dct):

        def find_method(method):
            """Find a method in all base classes

            Args:
                method: class method
            """
            for base in bases:
                try:
                    return getattr(base, method)
                except AttributeError:
                    pass
            raise AttributeError("No bases have method '{}'".format(method))

        def call_recorder(func):
            """Record every call to func.

            Args:
                func: class method
            """
            def wrapper(self, *args, **kwargs):
                """Wrapper replacing func with call recorder."""
                dub_translate = getattr(self, '_dub_translate')
                calls = getattr(self, dub_translate['calls'])
                if calls is not None:
                    calls.append((func.__name__, args, kwargs))
                # W0212: *Access to a protected member %%s of a client class*
                # pylint: disable=W0212
                dub = getattr(self, dub_translate['dub'])
                if func.__name__ in dub:
                    settings = dub[func.__name__]
                    if 'raise' in settings:
                        if callable(settings['raise']):
                            exception = settings['raise'](
                                self, *args, **kwargs)
                            if exception is not None:
                                raise exception
                        else:
                            if settings['raise'] is not None:
                                raise settings['raise']
                    if 'return' in settings:
                        if callable(settings['return']):
                            return settings['return'](self, *args, **kwargs)
                        else:
                            return settings['return']
                return func(self, *args, **kwargs)
            return wrapper

        def init_calls(self):
            """Initialize calls."""
            dub_translate = getattr(self, '_dub_translate')
            setattr(self, dub_translate['calls'], [])

        _dub_translate = {
            'dub': 'dub',
            'calls': 'calls',
            'init_calls': 'init_calls',
        }

        if '_dub_names' in dct:
            _dub_translate.update(dct['_dub_names'])

        dct['_dub_translate'] = _dub_translate

        dub_name = _dub_translate['dub']
        calls_name = _dub_translate['calls']
        init_calls_name = _dub_translate['init_calls']

        if init_calls_name not in dct:
            dct[init_calls_name] = init_calls

        if dub_name not in dct:
            dct[dub_name] = Storage({})

        if calls_name not in dct:
            dct[calls_name] = []

        for method in dct['_dub_methods']:
            dct[dub_name][method] = Storage({})
            dct[method] = call_recorder(find_method(method))

        return type(name, bases, dct)


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
                print('FIXME p_stdout: {var}'.format(var=p_stdout))
            if p_stderr:
                print('FIXME p_stderr: {var}'.format(var=p_stderr))
            file_to_hash = outfile

        return hashlib.md5(open(file_to_hash, 'rb').read()).hexdigest()


class WithTestDataDirTestCase(LocalTestCase):
    """Base class for test cases that need access to test data directory."""

    _test_data_dir = None

    def setUp(self):
        self._test_data_dir = os.path.join(
            current.request.folder, 'private/test/data/')
        super().setUp()


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
            record: Record instance or Row instance.
            img: string, path/to/name of image.
        Returns:
            Name of the stored image file.
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        # Delete images if record field is set.
        db = current.app.db
        if record[field.name]:
            up_image = UploadImage(field, record[field.name])
            up_image.delete_all()
        stored_filename = store(field, img, resizer=resizer)
        data = {field.name: stored_filename}
        if isinstance(record, Record):
            record.__class__.from_updated(record, data)
            record.update(data)
        else:
            record.update_record(**data)
            db.commit()
        return stored_filename

    def setUp(self):
        if not os.path.exists(self._image_dir):
            os.makedirs(self._image_dir)
        super().setUp()

    def tearDown(self):
        if os.path.exists(self._image_dir):
            shutil.rmtree(self._image_dir)
        super().tearDown()

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

        for k in list(self.filenames.keys()):
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

        for prefix in list(self.filenames.keys()):
            path = os.path.join(
                self.temp_directory(),
                '{pfx}-*'.format(pfx=prefix)
            )
            matches = glob.glob(path)
            if matches:
                self.filenames[prefix] = matches[0]


class WebTestCase(LocalTestCase):
    """Test case for controller tests."""
    page_identifiers = {
        '/admin/index': '<div id="admin_page">',
        '/admin/job_queuers': '<h3>Job Queuers</h3>',
        '/contributions/modal': [
            '<div id="contribute_modal_page">',
            'Your donations help cover the'
        ],
        '/contributions/modal/book': [
            '<div id="contribute_modal_page">',
            'Contributions go directly to the cartoonist',
        ],
        '/contributions/paypal': '<form id="paypal_form"',
        '/contributions/widget': '<div class="row contribute_widget"></div>',
        '/creators/creator': '<div id="creator_page">',
        '/default/data': '<h2>Not authorized</h2>',
        '/default/index': '<div id="front_page">',
        '/default/user': [
            'web2py_user_form',
            'web2py_user_form_container',
            'forgot_password_container',
            'register_container'
        ],
        '/default/user/login': [
            '<div id="login_page">',
            '<h2>Cartoonist Login</h2>',
        ],
        '/downloads/modal': [
            '<div id="download_modal_page">',
            'magnet:?xt=urn:tree:tiger',
        ],
        '/errors/index': '<h3>Server error</h3>',
        '/errors/page_not_found': '<h3>Page not found</h3>',
        '/login/account': [
            'account_profile_container',
            'change_password_container'
        ],
        '/login/agree_to_terms': '<div id="agree_to_terms_page">',
        '/login/book_complete': '<div id="book_complete_section">',
        '/login/book_delete': '<div id="book_delete_section">',
        '/login/book_edit': '<div id="book_edit_section">',
        '/login/book_fileshare': '<div id="book_fileshare_section">',
        '/login/book_list': '<h2>Book List</h2>',
        '/login/book_list.load/completed': '<div id="completed_container">',
        '/login/book_list.load/disabled': '<div id="disabled_container">',
        '/login/book_list.load/ongoing': '<div id="ongoing_container">',
        '/login/book_pages': '<div id="profile_book_pages_page">',
        '/login/book_post_upload_session': [
            '"status": "ok"',
        ],
        '/login/books': '<div id="ongoing_book_list" class="book_list">',
        '/login/indicia': [
            '<div id="profile_page">',
            '<div id="indicia_section">',
        ],
        '/login/order_no_handler': '<div id="creator_page">',
        '/login/profile': '<div id="creator_section">',
        '/login/profile_name_edit_modal':
            '<div id="profile_name_edit_modal_page">',
        '/rss/modal': '<div id="rss_modal">',
        '/rss/rss': [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        ],
        '/rss/widget.load': '<div class="rss_widget_body">',
        '/search/book_page': '<div id="book_page">',
        '/search/box.load': '<div id="search">',
        '/search/creator_page': '<div id="creator_page">',
        '/search/index': '<div id="front_page">',
        '/search/list_grid': '<div class="web2py_grid grid_view_list ',
        '/search/list_grid_tile': '<div class="web2py_grid grid_view_tile ',
        '/search/tile_grid': '<div class="row tile_view">',
        '/torrents/torrent': '30:http://bt.zco.mx:6969/announce',
        '/z/about': '<h1>About</h1>',
        '/z/cartoonists': '<div id="front_page">',
        '/z/completed': '<div id="front_page">',
        '/z/contribute': '<form id="paypal_form"',
        '/z/copyright_claim':
            '<h3>Notice and Procedure for Making Claims of Copyright',
        '/z/expenses': '<h1>Expenses</h1>',
        '/z/faq': '<h1>FAQ</h1>',
        '/z/faqc': [
            '<h1>FAQ</h1>',
            '<div class="faq_options_container">',
        ],
        '/z/files': '<div id="files_page">',
        '/z/index': '<div id="front_page">',
        '/z/login': '<h2>Cartoonist Login</h2>',
        '/z/logos': '<h1>Logos</h1>',
        '/z/modal_error': 'An error occurred. Please try again.',
        '/z/ongoing': '<div id="front_page">',
        '/z/overview': '<h1>Overview</h1>',
        '/z/rss': '<div id="rss_page">',
        '/z/search': '<div id="front_page">',
        '/z/terms': '<h1>Terms and Conditions</h1>',
        '/z/todo': '<h1>TODO</h1>',
        '/z/top': '<h2>Top</h2>',
    }


def reset_signature_timestamps(table):
    """Reset the default timestamps set on the signature fields

    Args:
        table: db.table

    """
    if 'created_on' in table.fields:
        table.created_on.default = datetime.datetime.now()
    if 'updated_on' in table.fields:
        table.updated_on.default = datetime.datetime.now()
        table.updated_on.update = datetime.datetime.now()


def skip_if_not_terminal(func):
    """Decorator to skip tests if test requires a terminal."""
    @wraps(func)
    def wrapper(*args):
        # C0111: *Missing docstring*
        # pylint: disable=C0111
        if not has_terminal():
            raise unittest.SkipTest('Tests requires terminal: {t}'.format(
                t=func.__name__))
        return func(*args)
    return wrapper


def skip_if_quick(func):
    """Decorator to skip tests if quick option is used."""
    @wraps(func)
    def wrapper(*args):
        # C0111: *Missing docstring*
        # pylint: disable=C0111
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        if args[0]._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run {t}'.format(
                t=func.__name__))
        return func(*args)
    return wrapper


def skip_unless_force(func):
    """Decorator to skip tests unless force options is used."""
    @wraps(func)
    def wrapper(*args):
        # C0111: *Missing docstring*
        # pylint: disable=C0111
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        if not args[0]._opts.force:
            raise unittest.SkipTest('Provide --force option to run {t}'.format(
                t=func.__name__))
        return func(*args)
    return wrapper
