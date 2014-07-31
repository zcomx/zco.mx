#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

CBZ classes and functions.
"""
import math
import os
import subprocess
import sys
from gluon import *
from applications.zcomix.modules.books import formatted_name
from applications.zcomix.modules.files import TitleFileName
from applications.zcomix.modules.images import CBZImage
from applications.zcomix.modules.utils import entity_to_row, temp_directory


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

    def cbz_filename(self):
        """Return the name for the cbz file."""
        db = current.app.db
        fmt = '{name} ({cid}.zco.mx).cbz'
        return fmt.format(
            name=TitleFileName(formatted_name(db, self.book)).scrubbed(),
            cid=self.book.creator_id,
        )

    def image_filename(self, page):
        """Return the name for an image file.

        Args:
            page: Row instance representing a book page.
        """
        db = current.app.db
        unused_root, extension = os.path.splitext(page.image)
        query = (db.book_page.book_id == self.book.id)
        max_page_no = db.book_page.page_no.max()
        page_count = db(query).select(max_page_no).first()[max_page_no]

        # if book has 1 to 999 pages, name image files: 001.jpg, 002.jpg, ...
        # if 1000 to 9999 pages: 0001.jpg, 0002.jpg ..., etc
        dec_width = max(int(math.ceil(math.log(page_count + 1, 10))), 3)
        fmt = '{{c:{w:02d}d}}{{e}}'.format(w=dec_width)
        return fmt.format(c=page.page_no, e=extension)

    def optimize(self):
        """Optimize book page images."""
        db = current.app.db
        pages = db(db.book_page.book_id == self.book.id).select(
            db.book_page.ALL,
            orderby=db.book_page.page_no
        )
        for page in pages:
            unused_file_name, fullname = db.book_page.image.retrieve(
                page.image,
                nameonly=True,
            )
            cbz_img = CBZImage(fullname)
            out_filename = os.path.join(
                self.working_directory(),
                self.image_filename(page)
            )
            cbz_img.optimize(out_filename, size='cbz')

    def run(self):
        """Create the cbz file."""
        self.optimize()
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
