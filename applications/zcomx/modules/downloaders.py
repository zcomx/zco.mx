#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to images.
"""
import os
import re
from gluon import *
from gluon.globals import Response
from gluon.streamer import DEFAULT_CHUNK_SIZE
from gluon.contenttype import contenttype
from applications.zcomx.modules.archives import TorrentArchive
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.images import (
    filename_for_size,
    SIZES,
)

LOG = current.app.logger


class CBZDownloader(Response):
    """Class representing a cbz downloader"""

    def download(
            self, request, db, chunk_size=DEFAULT_CHUNK_SIZE, attachment=True,
            download_filename=None):
        """
        Adapted from Response.download.
        request.args(0): integer, id of book record.
        """
        # pylint: disable=redefined-outer-name
        current.session.forget(current.response)

        if not request.args:
            raise HTTP(404)

        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            raise HTTP(404)
        filename = book.cbz

        if not filename or not os.path.exists(filename):
            raise HTTP(404)

        stream = os.path.abspath(filename)

        headers = self.headers
        headers['Content-Type'] = contenttype(filename)
        if download_filename is None:
            download_filename = os.path.basename(filename)
        if attachment:
            fmt = 'attachment; filename="%s"'
            headers['Content-Disposition'] = \
                fmt % download_filename.replace('"', '\"')
        return self.stream(stream, chunk_size=chunk_size, request=request)


class ImageDownloader(Response):
    """Class representing an image downloader"""

    def download(
            self, request, db, chunk_size=DEFAULT_CHUNK_SIZE, attachment=True,
            download_filename=None):
        """
        Adapted from Response.download.

        request.args: path to image file, the last item is the image filename.
        request.vars.size: string, one of SIZES. If provided the image is
            streamed from a subdirectory with that name.
        request.vars.cache: boolean, if set, set response headers to
            enable caching.
        """
        # pylint: disable=redefined-outer-name
        current.session.forget(current.response)

        if not request.args:
            raise HTTP(404)
        name = request.args[-1]
        items = re.compile(r'(?P<table>.*?)\.(?P<field>.*?)\..*').match(name)
        if not items:
            raise HTTP(404)
        (t, f) = (items.group('table'), items.group('field'))
        try:
            field = db[t][f]
        except AttributeError:
            raise HTTP(404)
        try:
            (filename, stream) = field.retrieve(name, nameonly=True)
        except (IOError, TypeError):
            raise HTTP(404)

        # Customization: start
        if request.vars.size and request.vars.size in SIZES \
                and request.vars.size != 'original':
            resized = filename_for_size(stream, request.vars.size)
            if os.path.exists(resized):
                stream = resized
        # Customization: end

        headers = self.headers
        headers['Content-Type'] = contenttype(name)
        if download_filename is None:
            download_filename = filename
        if attachment:
            fmt = 'attachment; filename="%s"'
            headers['Content-Disposition'] = \
                fmt % download_filename.replace('"', '\"')
        if request.vars.cache:
            headers['Cache-Control'] = 'max-age=315360000, public'
            headers['Expires'] = 'Thu, 31 Dec 2037 23:59:59 GMT'
        return self.stream(stream, chunk_size=chunk_size, request=request)


class TorrentDownloader(Response):
    """Class representing a torrent downloader"""

    def download(
            self, request, db, chunk_size=DEFAULT_CHUNK_SIZE, attachment=True,
            download_filename=None):
        """
        Adapted from Response.download.

        request.args(0): one of 'all', 'book', 'creator'
        request.args(1): integer, id of record if request.args(0) is 'book' or
            'creator'
        """
        # pylint: disable=redefined-outer-name
        current.session.forget(current.response)

        if not request.args:
            raise HTTP(404)

        tor_type = request.args(0)
        if tor_type not in ['all', 'book', 'creator']:
            raise HTTP(404)

        if tor_type in ['book', 'creator'] and not request.args(1):
            raise HTTP(404)

        filename = None
        if tor_type == 'all':
            tor_archive = TorrentArchive()
            name = '.'.join([tor_archive.name, 'torrent'])
            filename = os.path.join(
                tor_archive.base_path,
                tor_archive.category,
                tor_archive.name,
                name
            )
        elif tor_type == 'creator':
            try:
                creator = Creator.from_id(request.args(1))
            except LookupError:
                raise HTTP(404)
            filename = creator.torrent
        else:
            try:
                book = Book.from_id(request.args(1))
            except LookupError:
                raise HTTP(404)
            filename = book.torrent

        if not filename or not os.path.exists(filename):
            raise HTTP(404)

        stream = os.path.abspath(filename)

        headers = self.headers
        headers['Content-Type'] = contenttype(filename)
        if download_filename is None:
            download_filename = os.path.basename(filename)
        if attachment:
            fmt = 'attachment; filename="%s"'
            headers['Content-Disposition'] = \
                fmt % download_filename.replace('"', '\"')
        return self.stream(stream, chunk_size=chunk_size, request=request)
