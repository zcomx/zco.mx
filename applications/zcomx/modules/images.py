#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to images.
"""
import glob
import imghdr
import logging
import os
import re
import shutil
import subprocess
from PIL import Image
from gluon import *
from gluon.globals import Response
from gluon.streamer import DEFAULT_CHUNK_SIZE
from gluon.contenttype import contenttype
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    set_owner

LOG = logging.getLogger('app')

SIZES = [
    'original',
    'cbz',
    'web',
    'tbn',
]


class Downloader(Response):
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


class ImageOptimizeError(Exception):
    """Exception class for an image optimize errors."""
    pass


class ImgTag(object):
    """Class representing an image TAG"""

    placeholder_tag = DIV

    def __init__(
            self,
            image,
            size='original',
            tag=None,
            components=None,
            attributes=None):
        """Constructor

        Args:
            image: string, name of image (as stored in db.field.image)
            size: string, the size of image to use.
            tag: XmlComponent class, default IMG
            components: list of XmlComponents for innerHTML of tag.
            attributes: dict of attributes for tag.
        """
        self.image = image
        self.size = size if size in SIZES else 'original'
        self.tag = tag
        self.components = components if components is not None else []
        self.attributes = attributes if attributes is not None else {}

    def __call__(self):
        """Return the TAG representing the image. """

        tag = self.tag if self.tag is not None \
            else IMG if self.image \
            else self.placeholder_tag

        if self.image:
            if '_src' not in self.attributes:
                self.attributes.update(dict(
                    _src=URL(
                        c='images',
                        f='download',
                        args=self.image,
                        vars={'size': self.size},
                    ),
                ))
        else:
            self.set_placeholder()

        return tag(*self.components, **self.attributes)

    def set_placeholder(self):
        """Set the attributes for the placeholder."""
        class_name = 'placeholder_170x170' \
            if self.size == 'tbn' else 'portrait_placeholder'
        if '_class' in self.attributes:
            self.attributes['_class'] = '{c1} {c2}'.format(
                c1=self.attributes['_class'],
                c2=class_name
            ).replace('img-responsive', '').strip()
        else:
            self.attributes['_class'] = class_name


class CreatorImgTag(ImgTag):
    """Class representing a creator image TAG"""

    def set_placeholder(self):
        """Set the attributes for the placeholder."""
        # Use a torso for the creator.
        self.components.append(TAG['i'](**{'_class': 'icon zc-torso'}))
        class_name = 'preview placeholder_torso'
        if '_class' in self.attributes:
            self.attributes['_class'] = '{c1} {c2}'.format(
                c1=self.attributes['_class'],
                c2=class_name
            ).replace('img-responsive', '').strip()
        else:
            self.attributes['_class'] = class_name


class ResizeImgError(Exception):
    """Exception class for ResizeImg errors."""
    pass


class ResizeImg(TempDirectoryMixin):
    """Class representing a handler for interaction with resize_img.sh"""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of original image file
        """
        self.filename = filename
        self.filenames = {'ori': None, 'cbz': None, 'web': None, 'tbn': None}

    def run(self, nice=False):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice.
        """
        resize_script = os.path.abspath(
            os.path.join(
                current.request.folder, 'private', 'bin', 'resize_img.sh')
        )

        real_filename = os.path.abspath(self.filename)

        args = []
        if nice:
            args.append('nice')
        args.append(resize_script)
        if self.filename:
            args.append(real_filename)
        # The images created by resize_img.sh are placed in the current
        # directory. Use cwd= to change to the temp directory so they are
        # created there.
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.temp_directory()
        )
        p_stdout, p_stderr = p.communicate()
        # Generally there should be no output. Log to help troubleshoot.
        if p_stdout:
            LOG.warn('ResizeImg run stdout: %s', p_stdout)
        if p_stderr:
            LOG.error('ResizeImg run stderr: %s', p_stderr)

        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        if p.returncode:
            raise ResizeImgError('Resize failed: {err}'.format(
                err=p_stderr or p_stdout))

        for prefix in ['ori', 'cbz', 'web', 'tbn']:
            path = os.path.join(
                self.temp_directory(),
                '{pfx}-*'.format(pfx=prefix)
            )
            matches = glob.glob(path)
            if matches:
                self.filenames[prefix] = matches[0]


class ResizeImgIndicia(ResizeImg):
    """Class representing a handler for interaction with resizing an indicia
    image.

    Features:
    * minimal resizing: 'ori' only
    * quick: uses convert command directly, resizes img to max 1600px
    """

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of original image file
        """
        ResizeImg.__init__(self, filename)
        self.filenames = {'ori': None}

    def run(self, nice=False):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice.
        """
        #  $ convert infile -quiet -filter catrom -resize 1600x1600> \
        #     -colorspace sRGB +repage outfile

        real_filename = os.path.abspath(self.filename)

        args = []
        if nice:
            args.append('nice')
        args.append('convert')
        if self.filename:
            args.append(real_filename)
        args.append('-quiet')
        args.extend('-filter catrom'.split())
        args.extend('-resize 1600x1600>'.split())
        args.extend('-colorspace sRGB'.split())
        args.append('+repage')

        outfile = os.path.abspath(os.path.join(
            self.temp_directory(),
            'ori-{n}'.format(n=os.path.basename(real_filename))
        ))
        args.append(outfile)

        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p_stdout, p_stderr = p.communicate()
        # Generally there should be no output. Log to help troubleshoot.
        if p_stdout:
            LOG.warn('ResizeImgIndicia run stdout: %s', p_stdout)
        if p_stderr:
            LOG.error('ResizeImgIndicia run stderr: %s', p_stderr)

        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        if p.returncode:
            raise ResizeImgError('Resize failed: {err}'.format(
                err=p_stderr or p_stdout))

        for prefix in ['ori']:
            path = os.path.join(
                self.temp_directory(),
                '{pfx}-*'.format(pfx=prefix)
            )
            matches = glob.glob(path)
            if matches:
                self.filenames[prefix] = matches[0]


class UploadImage(object):
    """Class representing an uploaded image.

    Uploaded images are stored in an uploads/original subdirectory.
    """

    def __init__(self, field, image_name):
        """Constructor

        Args:
            field: gluon.dal.Field instance, eg db.creator.image
            field, image_name: string, the name of the image.
                Eg creator.image.944cdb07605150ca. ...
                        636875636b5f666f72736d616e2e6a7067.jpg
        """
        self.field = field
        self.image_name = image_name
        self._images = {}               # {'size': Image instance}
        self._dimensions = {}           # {'size': (w, h)}

    def delete(self, size):
        """Delete a version of the image

        Args:
            size: string, name of size, must one of SIZES
        """
        fullname = self.fullname(size=size)
        if os.path.exists(fullname):
            os.unlink(fullname)

    def delete_all(self):
        """Delete all sizes."""
        for size in SIZES:
            self.delete(size)
        self.delete('original')

    def dimensions(self, size='original'):
        """Return the dimensions of the image of the indicated size.

        Args:
            size: string, name of size, must one of SIZES
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
        return filename_for_size(fullname, size)

    def pil_image(self, size='original'):
        """Return a PIL Image instance representing the image.

        Args:
            size: string, name of size, must one of SIZES
        """
        if not self._images or size not in self._images:
            filename = self.fullname(size=size)
            if os.path.exists(filename):
                self._images[size] = Image.open(filename)
            else:
                self._images[size] = None
        return self._images[size]


def filename_for_size(original_filename, size):
    """Return the name of the file that is a resized version of
    original_filename.

    Args:
        original_filename: string, name of original file. eg
            /path/to/uploads/original/book_page.image/bf/bf1234.jpg
        size: string, size of file
    """
    new_name = original_filename
    if size != 'original' and '/original/' in original_filename:
        new_name = new_name.replace('/original/', '/{s}/'.format(s=size))

        # Resized gif files are png's
        name, ext = os.path.splitext(new_name)
        if ext == '.gif':
            new_name = name + '.png'
    return new_name


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


def optimize(filename, nice=False):
    """Optimize an image file in place.

    Args:
        filename: string, name of file.
        nice: If True, run optimize script with nice.
    """
    optimize_script = os.path.abspath(
        os.path.join(
            current.request.folder, 'private', 'bin', 'optimize_img.sh')
    )
    args = []
    if nice:
        args.append('nice')
    args.append(optimize_script)
    args.append(os.path.abspath(filename))

    # Background the process
    subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def set_thumb_dimensions(db, book_page_id, dimensions):
    """Set the db.book_page.thumb_* dimension values for a page.

    Args:
        db: gluon.dal.Dal instance.
        book_page_id: integer, id of book_page record
        dimensions: tuple (w, h), dimensions of thumb image.
    """
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    if not dimensions:
        return
    w = dimensions[0]
    h = dimensions[1]

    db(db.book_page.id == book_page_id).update(
        thumb_w=w,
        thumb_h=h,
    )
    db.commit()


def store(field, filename, resize=True, resizer=None, run_optimize=True):
    """Store an image file in an uploads directory.
    This will create all sizes of the image file.

    Args:
        field: gluon.dal.Field instance (field type 'upload')
        filename: name of file to store.

    Return:
        string, the name of the file in storage.
    """
    obj_class = resizer if resizer is not None else ResizeImg
    resize_img = obj_class(filename)
    if resize:
        resize_img.run(nice=True)
    else:
        # Copy the files as is
        for size in resize_img.filenames.keys():
            resize_img.filenames[size] = filename
    original_filename = resize_img.filenames['ori']
    with open(original_filename, 'r+b') as f:
        stored_filename = field.store(f, filename=filename)
    # stored_filename doesn't have a full path. Use retreive to get
    # file name will full path.
    unused_name, fullname = field.retrieve(stored_filename, nameonly=True)
    set_owner(os.path.dirname(fullname))                # store creates subdir
    set_owner(fullname)
    for size, name in resize_img.filenames.items():
        if size == 'ori':
            continue
        if name is None:
            continue
        sized_filename = filename_for_size(fullname, size)
        sized_path = os.path.dirname(sized_filename)
        if not os.path.exists(sized_path):
            os.makedirs(sized_path)
        set_owner(sized_path)
        if resize:
            # $ mv name sized_filename
            shutil.move(name, sized_filename)
        else:
            shutil.copy(name, sized_filename)
        set_owner(sized_filename)
        if run_optimize:
            optimize(sized_filename, nice=True)

    resize_img.cleanup()
    return stored_filename
