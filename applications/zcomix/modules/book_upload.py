#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to uploading books.

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
class BookPageFile: A class representing an image file used for a book page.

If an image is uploaded there is one UploadedImage instance and one
BookPageFile.

If an archive file is uploaded, there is one UploadedArchive instance and many
BookPageFile instances, one for each image file extracted from the archive.

"""
import cgi
import os
import shutil
import subprocess
import sys
import zipfile
from gluon import *
from gluon.contrib.simplejson import dumps
from applications.zcomix.modules.books import book_page_for_json
from applications.zcomix.modules.images import \
    UploadImage, \
    is_image, \
    set_thumb_dimensions
from applications.zcomix.modules.unix_file import UnixFile
from applications.zcomix.modules.utils import temp_directory


class BookPageFile(object):
    """Class representing a book page file."""

    def __init__(self, page_file):
        """Constructor

        Args:
            page_file: file object or cgi.FieldStorage instance
        """
        self.page_file = page_file
        self.stored_filename = None

    def add(self, book_id):
        """Add the file to the book pages.

        Args:
            book_id: integer, id of book record the files belong to
        """
        # C0103: *Invalid name "%%s" (should match %%s)*      - db
        # pylint: disable=C0103
        db = current.app.db

        if isinstance(self.page_file, cgi.FieldStorage):
            self.stored_filename = db.book_page.image.store(
                self.page_file, self.page_file.filename)
        else:
            self.stored_filename = db.book_page.image.store(self.page_file)

        max_page = db.book_page.page_no.max()
        query = (db.book_page.book_id == book_id)
        try:
            page_no = db(query).select(max_page)[0][max_page] + 1
        except TypeError:
            page_no = 1

        book_page_id = db.book_page.insert(
            book_id=book_id,
            page_no=page_no,
            image=self.stored_filename,
            thumb_shrink=1,
        )
        db.commit()
        try:
            resizer = UploadImage(db.book_page.image, self.stored_filename)
            resizer.resize_all()
            set_thumb_dimensions(
                db, book_page_id, resizer.dimensions(size='thumb'))
        except IOError as err:
            print >> sys.stderr, 'IOError: {err}'.format(err=err)
        return book_page_id


class BookPageUploader(object):
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
        return dumps(dict(files=pages))

    def load_file(self, up_file):
        """Load files into database."""
        local_filename = os.path.join(self.temp_directory, up_file.filename)
        with open(local_filename, 'w+b') as lf:
            shutil.copyfileobj(up_file.file, lf)

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
    pass


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
        for k, types in self.types.items():
            for t in types:
                if t in output:
                    return k
        raise FileTypeError('Unsupported file type.')


class TemporaryDirectory(object):
    """tempfile.mkdtemp() usable with "with" statement."""

    def __init__(self):
        self.name = None

    def __enter__(self):
        self.name = temp_directory()
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.name)


class UnpackError(Exception):
    """Exception class for unpack errors."""
    pass


class Unpacker(object):
    """Base unpacker class representing an unpacker, eg unrar or unzip"""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of archive file
        """
        self.filename = filename
        self._temp_directory = None

    def cleanup(self):
        """Cleanup """
        tmp_dir = self.temp_directory()
        if tmp_dir:
            shutil.rmtree(tmp_dir)
            self._temp_directory = None

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

    def temp_directory(self):
        """Return a temporary directory where files will be extracted to."""
        if self._temp_directory is None:
            self._temp_directory = temp_directory()
        return self._temp_directory


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

        p = subprocess.Popen(
            ['unrar', 'e', self.filename, tmp_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        unused_output, errors = p.communicate()
        if errors:
            # E1103: *%%s %%r has no %%r member (some types not be inferred)
            # pylint: disable=E1103
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
            with zipfile.ZipFile(self.filename, allowZip64=True) as z:
                for zip_info in z.infolist():
                    z.extract(zip_info, tmp_dir)
        except (IOError, RuntimeError, zipfile.BadZipfile) as err:
            raise UnpackError(str(err))
        return self.image_files()


class UploadedFile(object):
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
        for image_filename in self.image_filenames:
            with open(image_filename, 'r+b') as f:
                book_page_file = BookPageFile(f)
                book_page_id = book_page_file.add(book_id)
                self.book_page_ids.append(book_page_id)

    def for_json(self):
        """Return uploaded files as json appropriate for jquery-file-upload."""
        raise NotImplementedError()

    def load(self, book_id):
        """Load uploaded file into database."""
        self.unpack()
        self.create_book_pages(book_id)
        if self.unpacker:
            self.unpacker.cleanup()

    def unpack(self):
        """Unpack file."""
        raise NotImplementedError()


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
        db = current.app.db
        book_page_id = self.book_page_ids[0] if self.book_page_ids else 0

        try:
            size = os.stat(self.filename).st_size
        except (KeyError, OSError):
            size = 0

        cover_page = db(db.book_page.id == book_page_id).select(
            db.book_page.ALL).first()
        thumb = ''
        if cover_page:
            thumb = URL(
                c='images',
                f='download',
                args=cover_page.image,
                vars={'size': 'thumb'},
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
        db = current.app.db
        return book_page_for_json(db, self.book_page_ids[0])

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
