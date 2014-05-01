#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to images.
"""
import imghdr
import math
import os
import re
from PIL import Image
from gluon import *
from gluon.globals import Response
from gluon.streamer import DEFAULT_CHUNK_SIZE
from gluon.contenttype import contenttype


class Downloader(Response):
    """Class representing an image downloader"""

    def download(self, request, db, chunk_size=DEFAULT_CHUNK_SIZE, attachment=True, download_filename=None):
        """
        Adapted from Response.download.

        request.vars.size: string, one of 'original' (default), 'medium', or
                'thumb'. If provided the image is streamed from a subdirectory
                 with that name.
        """
        current.session.forget(current.response)

        if not request.args:
            raise HTTP(404)
        name = request.args[-1]
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
        if request.vars.size and request.vars.size in SIZERS.keys():
            resized = stream.replace('/original/', '/{s}/'.format(s=request.vars.size))
            if os.path.exists(resized):
                stream = resized
        # Customization: end

        headers = self.headers
        headers['Content-Type'] = contenttype(name)
        if download_filename is None:
            download_filename = filename
        if attachment:
            headers['Content-Disposition'] = \
                'attachment; filename="%s"' % download_filename.replace('"', '\"')
        return self.stream(stream, chunk_size=chunk_size, request=request)


class Sizer(object):
    """Base class representing an image Sizer"""

    def __init__(self, im):
        """Constructor

        Args:
            im: Image instance.
        """
        self.im = im

    def size(self):
        """Return (w, h) tuple representing max width and max height size of
        image.

        Returns:
            tuple (w integer, h integer)
        """
        return self.im.size


class LargeSizer(Sizer):
    """Class representing a sizer for large images."""

    _max_area = 900000          # in pixels, 1200w x 750h

    def __init__(self, im):
        """Constructor """
        Sizer.__init__(self, im)

    def size(self):
        """Return (w, h) tuple representing max width and max height size of
        image.

        Returns:
            tuple (w integer, h integer)
        """
        w, h = self.im.size
        area = w * h
        new_w, new_h = w, h
        if area > self._max_area:
            new_w = int(math.sqrt(1.0 * w * self._max_area / h))
            new_h = int(math.sqrt(1.0 * h * self._max_area / w))
        return (new_w, new_h)


class MediumSizer(Sizer):
    """Class representing a sizer for medium images."""
    dimensions = (500, 500)

    def __init__(self, im):
        """Constructor """
        Sizer.__init__(self, im)

    def size(self):
        """Return (w, h) tuple representing max width and max height size of
        image.

        Returns:
            tuple (w integer, h integer)
        """
        return self.dimensions


class ThumbnailSizer(Sizer):
    """Class representing a sizer for thumbnail images."""
    dimensions = (170, 170)
    shrink_threshold = 120
    shrink_multiplier = 0.80

    def __init__(self, im):
        """Constructor """
        Sizer.__init__(self, im)

    def size(self):
        """Return (w, h) tuple representing max width and max height size of
        image.

        Returns:
            tuple (w integer, h integer)
        """
        return self.dimensions


SIZERS = {
    'large': LargeSizer,
    'medium': MediumSizer,
    'thumb': ThumbnailSizer,
}


class UploadImage(object):
    """Class representing an image resizer"""

    def __init__(self, field, image_name):
        """Constructor

        Args:
            field: gluon.dal.Field instance, eg db.creator.image
            field, image_name: string, the name of the image.
                Eg creator.image.944cdb07605150ca.636875636b5f666f72736d616e2e6a7067.jpg
        """
        self.field = field
        self.image_name = image_name
        self._images = {}               # {'size': Image instance}
        self._dimensions = {}           # {'size': (w, h)}

    def delete(self, size):
        """Delete a version of the image

        Args:
            size: string, name of size, must one of the keys of the SIZERS
                    dict
        """
        fullname = self.fullname(size=size)
        if os.path.exists(fullname):
            os.unlink(fullname)

    def delete_all(self):
        """Delete all sizes."""
        for size in SIZERS.keys():
            self.delete(size)
        self.delete('original')

    def dimensions(self, size='original'):
        """Return the dimensions of the image of the indicated size.

        Args:
            size: string, name of size, must one of the keys of the SIZERS
                    dict
        """
        if not self._dimensions or size not in self._dimensions:
            im = self.pil_image(size=size)
            if im:
                self._dimensions[size] = im.size
            else:
                self._dimensions[size] = None
        return self._dimensions[size]

    def fullname(self, size='original'):
        """Return the fullname of the image."""
        unused_file_name, fullname = self.field.retrieve(
            self.image_name,
            nameonly=True,
        )
        if size != 'original':
            fullname = fullname.replace('/original/', '/{s}/'.format(s=size))
        return fullname

    def pil_image(self, size='original'):
        """Return a PIL Image instance representing the image.

        Args:
            size: string, name of size, must one of the keys of the SIZERS
                    dict
        """
        if not self._images or size not in self._images:
            filename = self.fullname(size=size)
            if os.path.exists(filename):
                self._images[size] = Image.open(filename)
            else:
                self._images[size] = None
        return self._images[size]

    def resize(self, size):
        """Resize the image.

        Args:
            size: string, name of size, must one of the keys of the SIZERS
                    dict
        """
        original_filename = self.fullname(size='original')
        sized_filename = self.fullname(size=size)
        sized_path = os.path.dirname(sized_filename)
        if not os.path.exists(sized_path):
            os.makedirs(sized_path)
        im = Image.open(original_filename)
        sizer = classified_sizer(size)
        im.thumbnail(sizer(im).size(), Image.ANTIALIAS)
        im.save(sized_filename)
        # self.dimensions[size] = im.size
        return sized_filename

    def resize_all(self):
        """Resize all sizes."""
        for size in SIZERS.keys():
            self.resize(size)


def classified_sizer(size):
    """Return the approapriate class for the given size.

    Args:
        size: string, eg 'medium', 'large', 'thumb'

    Returns:
        Sizer class or subclass
    """
    if size in SIZERS:
        return SIZERS[size]
    return Sizer


def img_tag(field, size='original', img_attributes=None):
    """Return an image HTML tag suitable for an resizeable image.

    Args:
        field: gluon.dal.Field instance, eg db.creator.image
        size: string, the image size
        img_attributes: dict, passed on as IMG(**img_attributes)
    """
    attributes = {}

    if field:
        tag = IMG
        if size != 'original' and size not in SIZERS.keys():
            size = 'original'

        attributes.update(dict(
            _src=URL(
                c='images',
                f='download',
                args=field,
                vars={'size': size},
            ),
        ))
    else:
        tag = DIV

    if img_attributes:
        attributes.update(img_attributes)

    if not field:
        class_name = 'placeholder_170x170' \
            if size == 'thumb' else 'portrait_placeholder'
        if '_class' in attributes:
            attributes['_class'] = '{c1} {c2}'.format(
                c1=attributes['_class'],
                c2=class_name
            ).replace('img-responsive', '').strip()
        else:
            attributes['_class'] = class_name

    return tag(**attributes)


def is_image(filename, image_types=None):
    """Determine if a file is an image.

    Args:
        filename: string, name of file.
        image_types: list of image types as returned by imghdr

    Returns:
        True if file is an image.
    """
    if image_types is None:
        # image types recognized by imghdr
        image_types = [
            'rgb',   # SGI ImgLib Files
            'gif',   # GIF 87a and 89a Files
            'pbm',   # Portable Bitmap Files
            'pgm',   # Portable Graymap Files
            'ppm',   # Portable Pixmap Files
            'tiff',  # TIFF Files
            'rast',  # Sun Raster Files
            'xbm',   # X Bitmap Files
            'jpeg',  # JPEG data in JFIF or Exif formats
            'bmp',   # BMP files
            'png',   # Portable Network Graphics
        ]

    if imghdr.what(filename) not in image_types:
        return False
    return True


def set_thumb_dimensions(db, book_page_id, dimensions):
    """Set the db.book_page.thumb_* dimension values for a page.

    Args:
        db: gluon.dal.Dal instance.
        book_page_id: integer, id of book_page record
        dimensions: tuple (w, h), dimensions of thumb image.
    """
    if not dimensions:
        return
    w = dimensions[0]
    h = dimensions[1]
    shrink = True if h > ThumbnailSizer.shrink_threshold \
        and w > ThumbnailSizer.shrink_threshold \
        else False

    thumb_shrink = ThumbnailSizer.shrink_multiplier if shrink else 1

    db(db.book_page.id == book_page_id).update(
        thumb_w=w,
        thumb_h=h,
        thumb_shrink=thumb_shrink
    )
    db.commit()
