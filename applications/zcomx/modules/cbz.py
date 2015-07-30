#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

CBZ classes and functions.
"""
import logging
import math
import os
import subprocess
import zipfile
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.archives import CBZArchive
from applications.zcomx.modules.books import \
    Book, \
    book_name, \
    cbz_comment
from applications.zcomx.modules.creators import \
    Creator, \
    creator_name
from applications.zcomx.modules.images import filename_for_size
from applications.zcomx.modules.indicias import BookIndiciaPagePng
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    os_nice
from applications.zcomx.modules.zco import NICES

LOG = logging.getLogger('app')


class CBZCreateError(Exception):
    """Exception class for a cbz file create error."""
    pass


class CBZCreator(TempDirectoryMixin):
    """Class representing a handler for creating a cbz file from a book."""

    def __init__(self, book):
        """Constructor

        Args:
            book: Book instance
        """
        self.book = book
        self._max_page_no = None
        self._img_filename_fmt = None
        self._working_directory = None

    def cbz_filename(self):
        """Return the name for the cbz file."""
        fmt = '{name} ({year}) ({cid}.zco.mx).cbz'
        return fmt.format(
            name=book_name(self.book, use='file'),
            year=str(self.book.publication_year),
            cid=self.book.creator_id,
        )

    def get_img_filename_fmt(self):
        """Return a str.format() fmt for the image filenames.

        Returns:
            string, eg '{p:03d}{e}'
        """
        if self._img_filename_fmt is None:
            try:
                max_page_no = self.get_max_page_no()
            except LookupError:
                max_page_no = 0

            # Add 1 for indicia page.
            page_count = max_page_no + 1

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
            page_no = db(query).select(max_page_no).first()[max_page_no]
            if not page_no:
                raise LookupError('Book has no pages, id: {i}'.format(
                    i=self.book.id))
            self._max_page_no = page_no
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
            if not os.path.exists(src_filename):
                raise LookupError(
                    'Image for book page not found, {s}'.format(
                        s=src_filename))

            dst_filename = os.path.join(
                self.working_directory(),
                self.image_filename(page, fmt)
            )

            if os.path.exists(dst_filename):
                msg = (
                    "Unable to link image file for page.\n"
                    "File with that name already exists.\n"
                    "Possible duplicate page_no.\n"
                    "Book id: {bid}, page: {page_no}"
                ).format(bid=self.book.id, page_no=page.page_no)
                raise CBZCreateError(msg)

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
        cbz_filename = self.zip()
        zipper = zipfile.ZipFile(cbz_filename, 'a')
        zipper.comment = cbz_comment(self.book)
        zipper.close()
        return cbz_filename

    def working_directory(self):
        """Return working directory where files are compiled."""
        if self._working_directory is None:
            self._working_directory = os.path.join(
                self.temp_directory(),
                self.book.name
            )
            if not os.path.exists(self._working_directory):
                os.makedirs(self._working_directory)
        return self._working_directory

    def zip(self, nice=NICES['zip']):
        """Zip book page images."""
        # Ex 7z a -tzip -mx=9 "Name of Comic 001.cbz" "/path/to/Name_of_Comic/"
        args = ['7z', 'a', '-tzip', '-mx=9']
        cbz_dir = self.temp_directory()
        cbz_filename = os.path.join(cbz_dir, self.cbz_filename())
        args.append(cbz_filename)
        args.append(self.working_directory())
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os_nice(nice),
        )
        unused_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*      # p.returncode
        # pylint: disable=E1101
        if p.returncode:
            LOG.error('7z call failed: %s', p_stderr)
            raise CBZCreateError('Creation of cbz file failed.')
        return cbz_filename


def archive(book, base_path='applications/zcomx/private/var'):
    """Create a cbz file for an book and archive it.

    Args:
        book: Book instance
        base_path: location of cbz archive

    Return:
        string, path to cbz file.
    """
    creator = Creator.from_id(book.creator_id)
    cbz_creator = CBZCreator(book)
    cbz_file = cbz_creator.run()

    cbz_archive = CBZArchive(base_path=base_path)
    subdir = cbz_archive.get_subdir_path(creator_name(creator, use='file'))
    dst = os.path.join(subdir, os.path.basename(cbz_file))
    archive_file = cbz_archive.add_file(cbz_file, dst)

    book = Book.from_updated(book, dict(cbz=archive_file))
    return archive_file
