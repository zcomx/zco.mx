#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to uploading books.

Pages of uploaded books are stored in book_page_tmp records.

Files for book pages are uploaded multiple files at a time and can be any
combination of image (.jpg, .png, etc), RAR (.cbr) or Zip (.cbz) files.

To give feedback to the user, jquery-file-upload requires a json
object with one 'files' element for each file uploaded. For image files, this
is straight forward, but for archive files, the archive may include many
image files, yet we still return only one file element.

Key classes

class BookPageUploader: A handler class used to manage uploads.
class UploadedFile: A class representing a single file uploaded.
    class UploadedArchive: Subclass, representing an archive file, cbr or cbz.
    class UploadedImage: Subclass, representing an image file, jpg, etc
class Unpacker: A class representing an unpacker, eg unrar or unzip
    class UnpackerRAR: unrar unpacker
    class UnpackerZip: unzip unpacker

If an image is uploaded there is one UploadedImage instance and one
book_page_tmp record.

If an archive file is uploaded, there is one UploadedArchive instance and many
book_page_tmp records, one for each image file extracted from the archive.
"""
import json
import os
import shutil
import subprocess
import zipfile
from gluon import *
from applications.zcomx.modules.book_pages import BookPageTmp
from applications.zcomx.modules.books import (
    Book,
    book_page_for_json,
    get_page,
)
from applications.zcomx.modules.image.validators import CBZValidator
from applications.zcomx.modules.images import (
    ImageDescriptor,
    is_image,
    store,
)
from applications.zcomx.modules.shell_utils import (
    TempDirectoryMixin,
    TemporaryDirectory,
    UnixFile,
)

LOG = current.app.logger


class BookPageUploader():
    """Class representing a book page uploader, a handler used to manage
        uploads.
    """

    def __init__(self, book_id, files):
        """Constructor

        Args:
            book_id: integer, id of book record the files belong to
            files: list of file objects or cgi.FieldStorage instances, files
                to upload
        """
        self.book_id = book_id
        self.files = files
        self.uploaded_files = []
        self.temp_directory = None

    def as_json(self):
        """Return uploaded files as json appropriate for jquery-file-upload."""
        pages = []
        for f in self.uploaded_files:
            for_json = f.for_json()
            for_json['book_id'] = self.book_id
            pages.append(for_json)
        return json.dumps(dict(files=pages))

    def load_file(self, up_file):
        """Load files into database."""
        local_filename = os.path.join(self.temp_directory, up_file.filename)
        with open(local_filename, 'w+b') as f:
            # This will convert cgi.FieldStorage to a regular file.
            shutil.copyfileobj(up_file.file, f)

        uploaded_file = classify_uploaded_file(local_filename)
        self.uploaded_files.append(uploaded_file)
        uploaded_file.load(self.book_id)

    def upload(self):
        """Upload files into database."""
        with TemporaryDirectory() as tmp_dir:
            self.temp_directory = tmp_dir
            for f in self.files:
                self.load_file(f)
            return self.as_json()


class FileTypeError(Exception):
    """Exception class for file type errors."""


class FileTyper(UnixFile):
    """Class representing a file typer used to identify a file."""

    types = {
        # file type, [ identifying string found in 'file' output]
        'image': [
            'GIF image data',
            'JPEG image data',
            'JPG image data',
            'PC bitmap',
            'PNG image data',
        ],
        'rar': [
            'RAR archive data'
        ],
        'zip': [
            'Zip archive data'
        ],
    }

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, first arg
        """
        UnixFile.__init__(self, filename)

    def type(self):
        """Return the file type."""
        output, error = self.file()
        if error:
            raise FileTypeError(error)
        for k, type_list in list(self.types.items()):
            for t in type_list:
                if t in output.decode():
                    return k
        raise FileTypeError('Unsupported file type.')


class UnpackError(Exception):
    """Exception class for unpack errors."""


class Unpacker(TempDirectoryMixin):
    """Base unpacker class representing an unpacker, eg unrar or unzip"""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of archive file
        """
        self.filename = filename

    def image_files(self):
        """Find image files amoung extracted files."""

        tmp_dir = self.temp_directory()

        image_files = []
        for root, unused_dirs, files in os.walk(tmp_dir, topdown=False):
            for name in files:
                fullname = os.path.join(root, name)
                if is_image(fullname):
                    image_files.append(fullname)
        return sorted(image_files)


class UnpackerRAR(Unpacker):
    """Class representing a RAR unpacker"""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of RAR file
        """
        Unpacker.__init__(self, filename)

    def extract(self):
        """Extract files."""
        tmp_dir = self.temp_directory()

        with subprocess.Popen(
                ['unrar', 'e', self.filename, tmp_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE) as p:
            unused_output, errors = p.communicate()
        if errors:
            msg = ', '.join([x for x in errors.split("\n") if x])
            raise UnpackError(msg)

        return self.image_files()


class UnpackerZip(Unpacker):
    """Class representing a zip unpacker"""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of zip file
        """
        Unpacker.__init__(self, filename)

    def extract(self):
        """Extract files."""
        tmp_dir = self.temp_directory()
        try:
            with zipfile.ZipFile(self.filename, allowZip64=True) as f:
                for zip_info in f.infolist():
                    f.extract(zip_info, tmp_dir)
        except (IOError, RuntimeError, zipfile.BadZipfile) as err:
            raise UnpackError(str(err))
        return self.image_files()


class UploadedFile():
    """Base class representing a single uploaded file."""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of file.
        """
        self.filename = filename
        self.image_filenames = []
        self.book_pages = []
        self.unpacker = None
        self.book_page_ids = []
        self.errors = []

    def create_book_pages(self, book_id):
        """Create book_pages.

        Args:
            book_id: integer, id of book record the files belong to
        """
        db = current.app.db
        for image_filename in self.image_filenames:
            book_page_id = create_book_page(book_id, image_filename)
            self.book_page_ids.append(book_page_id)

    def for_json(self):
        """Return uploaded files as json appropriate for jquery-file-upload."""
        raise NotImplementedError()

    def load(self, book_id):
        """Load uploaded file into database."""
        self.unpack()
        self.validate_images()
        self.create_book_pages(book_id)
        if self.unpacker:
            self.unpacker.cleanup()

    def unpack(self):
        """Unpack file."""
        raise NotImplementedError()

    def validate_images(self):
        """Validate images.

        Raises:
            InvalidImageError
        """
        for image_filename in self.image_filenames:
            validator = CBZValidator(image_filename)
            validator.validate(image_descriptor=ImageDescriptor)
        return True


class UploadedArchive(UploadedFile):
    """Class representing an archive uploaded file."""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of file.
        """
        UploadedFile.__init__(self, filename)

    def for_json(self):
        """Return uploaded files as json appropriate for jquery-file-upload."""
        book_page_id = self.book_page_ids[0] if self.book_page_ids else 0

        try:
            size = os.stat(self.filename).st_size
        except (KeyError, OSError):
            size = 0

        cover_page = BookPageTmp.from_id(book_page_id) \
            if book_page_id else None
        thumb = ''
        if cover_page:
            thumb = URL(
                c='images',
                f='download',
                args=cover_page.image,
                vars={'size': 'web'},
            )

        json_data = dict(
            book_page_id=book_page_id,
            name=os.path.basename(self.filename),
            size=size,
            url=None,                    # Cbr is not downloadable.
            thumbnailUrl=thumb,
            deleteUrl=None,              # Delete is disabled.
            deleteType='',               # Would have to delete all images.
        )

        if self.errors:
            json_data['error'] = ', '.join(self.errors)
        return json_data

    def unpack(self):
        """Unpack file."""
        try:
            self.image_filenames = self.unpacker.extract()
        except UnpackError as err:
            self.errors.append(str(err))


class UploadedImage(UploadedFile):
    """Class representing an archive uploaded file."""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of file.
        """
        UploadedFile.__init__(self, filename)

    def for_json(self):
        """Return uploaded files as json appropriate for jquery-file-upload."""
        book_page = BookPageTmp.from_id(self.book_page_ids[0])
        return book_page_for_json(book_page)

    def unpack(self):
        """Unpack file."""
        # An image file doesn't need unpacking.
        self.image_filenames.append(self.filename)


class UploadedUnsupported(UploadedFile):
    """Class representing an unsupported uploaded file."""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of file.
        """
        UploadedFile.__init__(self, filename)

    def create_book_pages(self, book_id):
        """Create book_pages.

        Args:
            book_id: integer, id of book record the files belong to
        """
        return

    def for_json(self):
        """Return uploaded files as json appropriate for jquery-file-upload."""
        try:
            size = os.stat(self.filename).st_size
        except (KeyError, OSError):
            size = 0

        json_data = dict(
            name=os.path.basename(self.filename),
            size=size,
        )

        if self.errors:
            json_data['error'] = ', '.join(self.errors)
        return json_data

    def load(self, book_id):
        """Load uploaded file into database."""
        return

    def unpack(self):
        """Unpack file."""
        return


def classify_uploaded_file(filename):
    """Return the appropriate UploadedFile subclass for the file.

    Args:
        filename: string, name of file.

    Returns:
        UploadedFile or subclass instance.
    """
    unpacker = None
    uploaded_class = UploadedImage
    errors = []

    try:
        file_type = FileTyper(filename).type()
    except FileTypeError as err:
        file_type = None
        uploaded_class = UploadedUnsupported
        errors.append(str(err))

    if file_type == 'zip':
        uploaded_class = UploadedArchive
        unpacker = UnpackerZip

    if file_type == 'rar':
        uploaded_class = UploadedArchive
        unpacker = UnpackerRAR

    uploaded_file = uploaded_class(filename)
    uploaded_file.unpacker = unpacker(filename) if unpacker else None
    uploaded_file.errors = errors
    return uploaded_file


def create_book_page(book_id, image_filename):
    """Add the image file to the book pages. Creates a book_page_tmp record.

    Args:
        book_id: integer, id of book record the files belong to
        image_filename: /path/to/name of image file
    """
    db = current.app.db
    try:
        stored_filename = store(db.book_page_tmp.image, image_filename)
    except IOError as err:
        LOG.error('IOError: %s', str(err))
        return

    book = Book.from_id(book_id)
    try:
        last_page = get_page(
            book,
            page_no='last',
            book_page_tbl=db.book_page_tmp
        )
    except LookupError:
        last_page = None
    page_no = last_page.page_no + 1 if last_page else 1

    data = dict(
        book_id=book_id,
        page_no=page_no,
        image=stored_filename,
    )
    book_page_tmp = BookPageTmp.from_add(data)
    return book_page_tmp.id
