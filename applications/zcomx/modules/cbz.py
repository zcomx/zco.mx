#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

CBZ classes and functions.
"""
import math
import os
import shutil
import subprocess
import sys
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.books import formatted_name
from applications.zcomx.modules.creators import for_path
from applications.zcomx.modules.files import TitleFileName
from applications.zcomx.modules.images import filename_for_size
from applications.zcomx.modules.indicias import BookIndiciaPagePng
from applications.zcomx.modules.shell_utils import \
    set_owner, \
    temp_directory
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row


class CBZArchive(object):
    """Class representing a handler for CBZ archive."""

    def __init__(self, base_path, root='/'):
        """Constructor

        Args:
            base_path: string, path pointing to location of archive.
                The base_path must exist.
            root: string, name of root directory under base path, default '/'

        Notes:
            Archive has the follow directory structure
                base_path/root/[A-Z]/subdir/file.cbz
            Eg
                base_path: private/var/cbz
                root: zco.mx

                private/var/cbz/zco.mx/A/Abe Adams/My Book.cbz
                private/var/cbz/zco.mx/A/Arnie Ack/A Book.cbz
                private/var/cbz/zco.mx/B/Betty Baker/Something.cbz
                ...
                private/var/cbz/zco.mx/Z/Zack Zucc/Zebras.cbz

            The base_path must exist. The root, [A-Z], and subdir directories
            will be created if necessary.
        """
        self.base_path = base_path
        self.root = root

    def add_file(self, src, subdir, name=None):
        """Add a file to the archive.

        Args:
            src: string, name of file to copy to archive, path/to/file.cbz
            subdir: string, the name of the archive sub directory to store
                under.
            name: string, the name to store the file as. If None, basename of
                src is used.

        Returns:
            string: path/to/file.cbz relative to base_path.
        """
        if not os.path.exists(src):
            raise NotFoundError('File not found: {f}'.format(f=src))

        if not os.path.exists(self.base_path):
            raise NotFoundError('Base path not found: {f}'.format(
                f=self.base_path))

        subdir_path = self.get_subdir_path(subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
            set_owner(subdir_path)

        if name is None:
            name = os.path.basename(src)

        dst = os.path.join(subdir_path, name)
        shutil.move(src, dst)
        return dst

    def get_subdir_path(self, subdir):
        """Return the archive path for a subdir.

        Args:
            name: string, subdir name

        Returns:
            string, subdir path

        Eg
            base_path: 'private/var/cbz'
            root: 'zco.mx'
            subdir = 'Abe Adams'
            returns: 'private/var/cbz/zco.mx/A/Abe Adams'
        """
        if not subdir:
            return

        letter = str(subdir)[0].upper()
        return os.path.join(self.base_path, self.root, letter, str(subdir))

    def remove_file(self, subdir, name):
        """Remove file from the archive.

        Args:
            subdir: string, the name of the archive sub directory the file
                is archived under.
            name: string, the name of the file
        """
        filename = os.path.join(self.get_subdir_path(subdir), name)

        if not os.path.exists(filename):
            raise NotFoundError('File not found: {f}'.format(f=filename))
        os.unlink(filename)


class CBZCreateError(Exception):
    """Exception class for a cbz file create error."""
    pass


class CBZCreator(object):
    """Class representing a handler for creating a cbz file from a book."""

    def __init__(self, book):
        """Constructor

        Args:
            book: Row instance of book or integer, id of book record.
        """
        db = current.app.db
        self.book = entity_to_row(db.book, book)
        self._working_directory = None
        self._max_page_no = None
        self._img_filename_fmt = None

    def cbz_filename(self):
        """Return the name for the cbz file."""
        db = current.app.db
        fmt = '{name} ({cid}.zco.mx).cbz'
        return fmt.format(
            name=TitleFileName(formatted_name(db, self.book)).scrubbed(),
            cid=self.book.creator_id,
        )

    def get_img_filename_fmt(self):
        """Return a str.format() fmt for the image filenames.

        Returns:
            string, eg '{p:03d}{e}'
        """
        if self._img_filename_fmt is None:
            # Add 1 for indicia page.
            page_count = self.get_max_page_no() + 1

            # if book has 1 to 999 pages, name image files: 001.jpg, 002.jpg,
            # if 1000 to 9999 pages: 0001.jpg, 0002.jpg ..., etc
            dec_width = max(int(math.ceil(math.log(page_count + 1, 10))), 3)
            self._img_filename_fmt = '{{p:{w:02d}d}}{{e}}'.format(w=dec_width)
        return self._img_filename_fmt

    def get_max_page_no(self):
        """Return the maximum page_no value of the page of the book.

        Returns:
            integer
        """
        if self._max_page_no is None:
            db = current.app.db
            query = (db.book_page.book_id == self.book.id)
            max_page_no = db.book_page.page_no.max()
            self._max_page_no = \
                db(query).select(max_page_no).first()[max_page_no]
        return self._max_page_no

    def image_filename(self, page, fmt=None, extension=None):
        """Return the name for an image file.

        Args:
            page: Row instance/Storage representing a book page. Must have
                    {image: image name, page_no: number of page}
            fmt: string,  str.format fmt eg as returned by get_img_filename_fmt
                Must define '{p}{e}' elements.
            extension: string, file extension. If None use the extension of
                page.image
        """
        if fmt is None:
            fmt = self.get_img_filename_fmt()
        if extension is None:
            _, extension = os.path.splitext(page.image)
        return fmt.format(p=page.page_no, e=extension)

    def run(self):
        """Create the cbz file."""
        db = current.app.db
        pages = db(db.book_page.book_id == self.book.id).select(
            db.book_page.ALL,
            orderby=db.book_page.page_no
        )

        fmt = self.get_img_filename_fmt()

        for page in pages:
            unused_file_name, fullname = db.book_page.image.retrieve(
                page.image,
                nameonly=True,
            )

            src_filename = filename_for_size(fullname, 'cbz')
            if not os.path.exists(src_filename):
                src_filename = filename_for_size(fullname, 'original')

            dst_filename = os.path.join(
                self.working_directory(),
                self.image_filename(page, fmt)
            )

            os.link(src_filename, dst_filename)

        # Copy indicia page image file to directory of images.
        png_page = BookIndiciaPagePng(self.book)
        src_filename = png_page.create()
        dst_filename = os.path.join(
            self.working_directory(),
            self.image_filename(
                Storage(dict(
                    image=src_filename,
                    page_no=self.get_max_page_no() + 1,
                )),
                fmt,
                extension='.png'
            )
        )
        os.link(src_filename, dst_filename)
        return self.zip()

    def working_directory(self):
        """Return working directory where files are compiled."""
        if self._working_directory is None:
            self._working_directory = os.path.join(
                temp_directory(),
                self.book.name
            )
            if not os.path.exists(self._working_directory):
                os.makedirs(self._working_directory)
        return self._working_directory

    def zip(self):
        """Zip book page images."""
        db = current.app.db
        # Ex 7z a -tzip -mx=9 "Name of Comic 001.cbz" "/path/to/Name_of_Comic/"
        args = ['7z', 'a', '-tzip', '-mx=9']
        cbz_dir = os.path.join(db.book_page.image.uploadfolder, '..', 'cbz')
        if not os.path.exists(cbz_dir):
            os.makedirs(cbz_dir)
        cbz_filename = os.path.join(cbz_dir, self.cbz_filename())
        args.append(cbz_filename)
        args.append(self.working_directory())
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        unused_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*      # p.returncode
        # pylint: disable=E1101
        if p.returncode:
            print >> sys.stderr, '7z call failed: {e}'.format(e=p_stderr)
            raise CBZCreateError('Creation of cbz file failed.')
        return cbz_filename


def archive(book_entity, base_path='applications/zcomx/private/var'):
    """Create a cbz file for an book and archive it.

    Args:
        book_entity: Row instance or integer representing book
        base_path: location of cbz archive

    Return:
        string, path to cbz file.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))
    creator_record = entity_to_row(db.creator, book_record.creator_id)
    if not creator_record:
        raise NotFoundError('Creator not found, id:{i}'.format(
            i=book_record.creator_id))

    cbz_creator = CBZCreator(book_record)
    cbz_file = cbz_creator.run()

    subdir = for_path(creator_record.path_name)
    cbz_archive = CBZArchive(base_path, 'zco.mx')
    archive_file = cbz_archive.add_file(cbz_file, subdir)
    book_record.update_record(cbz=archive_file)
    db.commit()
    return archive_file
