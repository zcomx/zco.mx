#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to images.
"""
import logging
import os
import re
from gluon import *
from gluon.globals import Response
from gluon.streamer import DEFAULT_CHUNK_SIZE
from gluon.contenttype import contenttype
from applications.zcomx.modules.archives import TorrentArchive
from applications.zcomx.modules.images import \
    filename_for_size, \
    SIZES
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')


class ImageDownloader(Response):
    """Class representing an image downloader"""

    def download(
            self, request, db, chunk_size=DEFAULT_CHUNK_SIZE, attachment=True,
            download_filename=None):
        """
        Adapted from Response.download.

        request.vars.size: string, one of SIZES. If provided the image is
                streamed from a subdirectory with that name.
        """
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103

        current.session.forget(current.response)

        if not request.args:
            raise HTTP(404)
        name = request.args[-1]
        # W1401 (anomalous-backslash-in-string): *Anomalous backslash in string
        # pylint: disable=W1401
        items = re.compile('(?P<table>.*?)\.(?P<field>.*?)\..*')\
            .match(name)
        if not items:
            raise HTTP(404)
        (t, f) = (items.group('table'), items.group('field'))
        try:
            field = db[t][f]
        except AttributeError:
            raise HTTP(404)
        try:
            (filename, stream) = field.retrieve(name, nameonly=True)
        except IOError:
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
        return self.stream(stream, chunk_size=chunk_size, request=request)


class TorrentDownloader(Response):
    """Class representing a torrent downloader"""

    def download(
            self, request, db, chunk_size=DEFAULT_CHUNK_SIZE, attachment=True,
            download_filename=None):
        """
        Adapted from Response.download.

        request.vars.size: string, one of SIZES. If provided the image is
                streamed from a subdirectory with that name.
        """
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103

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
            creator = entity_to_row(db.creator, request.args(1))
            if not creator:
                raise HTTP(404)
            filename = creator.torrent
        else:
            book = entity_to_row(db.book, request.args(1))
            if not book:
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
