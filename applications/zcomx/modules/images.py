#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Classes and functions related to images.
"""
import glob
import imghdr
import os
import re
import shutil
import subprocess
from PIL import Image
from gluon import *
from pydal.helpers.regex import REGEX_UPLOAD_EXTENSION
from applications.zcomx.modules.job_queuers import DeleteImgQueuer
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    TemporaryDirectory, \
    os_nice, \
    set_owner
from applications.zcomx.modules.zco import NICES

LOG = current.app.logger

SIZES = [
    'original',
    'cbz',
    'web',
]


class ImageDescriptor(object):
    """Class representing an image descriptor. The class can be used
    to access attributes of an image file.

    Attributes:
        filename: string, name of the file including path.

    """
    def __init__(self, filename):
        """Initializer"""
        self.filename = filename
        self._dimensions = None  # (w, h)
        self._size_bytes = None  # kb
        self._number_of_colours = None  # integer
        self._pil = None  # PIL Image instance

    def dimensions(self):
        """Return the dimensions of the image.

        Returns:
            tuple, (width, height) in pixels
        """
        if self._dimensions is None:
            im = self.pil_image()
            self._dimensions = im.size
        return self._dimensions

    def number_of_colours(self):
        """Return the number of colours in the image.

        Returns:
            integer, the number of colours in the image.
        """
        if self._number_of_colours is None:
            im = self.pil_image()
            self._number_of_colours = len(im.getcolors(maxcolors=99999))
        return self._number_of_colours

    def orientation(self):
        """Return the orientation of the image.

        Returns:
            string, one of 'portrait', 'landscape', 'square'
        """
        width, height = self.dimensions()
        if width == height:
            return 'square'
        if width > height:
            return 'landscape'
        return 'portrait'

    def pil_image(self):
        """Return a PIL Image instance representing the image.

        Returns:
            PIL Image instance.
        """
        if not self._pil:
            self._pil = Image.open(self.filename)
        return self._pil

    def size_bytes(self):
        """Return the size (in bytes) of the image.

        Returns:
            integer, number of kb
        """
        if self._size_bytes is None:
            try:
                num_bytes = os.stat(self.filename).st_size
            except (KeyError, OSError):
                num_bytes = 0
            self._size_bytes = num_bytes
        return self._size_bytes


class ImageOptimizeError(Exception):
    """Exception class for an image optimize errors."""


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
                        vars=self.url_vars(),
                    ),
                ))
        else:
            self.set_placeholder()

        return tag(*self.components, **self.attributes)

    def set_placeholder(self):
        """Set the attributes for the placeholder."""
        class_name = 'portrait_placeholder'
        if '_class' in self.attributes:
            self.attributes['_class'] = '{c1} {c2}'.format(
                c1=self.attributes['_class'],
                c2=class_name
            ).replace('img-responsive', '').strip()
        else:
            self.attributes['_class'] = class_name

    def url_vars(self):
        """Return the URL(..., vars=?) value."""
        return {'size': self.size}


class CachedImgTag(ImgTag):
    """Class representing a cached image TAG"""

    def url_vars(self):
        """Return the URL(..., vars=?) value."""
        cached_vars = super().url_vars()
        cached_vars['cache'] = 1
        return cached_vars


class CreatorImgTag(CachedImgTag):
    """Class representing a creator image TAG"""
    placeholder_tag = IMG

    def set_placeholder(self):
        """Set the attributes for the placeholder."""
        try:
            creator_id = self.attributes['_data-creator_id']
        except KeyError:
            creator_id = 0

        num_of_imgs = 4     # static/images/placeholders/creator/0*.png
        img_no = int(creator_id % num_of_imgs) + 1
        filename = '{n:02d}.png'.format(n=img_no)
        if '_src' not in self.attributes:
            self.attributes.update(dict(
                _src=URL(
                    c='static',
                    f='images',
                    args=['placeholders', 'creator', filename]
                ),
            ))

        additional_classes = ['preview', 'img-responsive']
        attr_classes = []
        if '_class' in self.attributes:
            attr_classes.extend(self.attributes['_class'].split())
        attr_classes.extend(additional_classes)
        self.attributes['_class'] = ' '.join(attr_classes)


class ResizeImgError(Exception):
    """Exception class for ResizeImg errors."""


class ResizeImg(TempDirectoryMixin):
    """Class representing a handler for interaction with resize_img.sh"""

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of original image file
        """
        self.filename = filename
        self.filenames = {'ori': None, 'cbz': None, 'web': None}

    def run(self, nice=NICES['resize']):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice. See os_nice for
                acceptable values.
        """
        resize_script = os.path.abspath(
            os.path.join(
                current.request.folder, 'private', 'bin', 'resize_img.sh')
        )

        real_filename = os.path.abspath(self.filename)

        args = []
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
            cwd=self.temp_directory(),
            preexec_fn=os_nice(nice),
        )
        p_stdout, p_stderr = p.communicate()
        # Generally there should be no output. Log to help troubleshoot.
        if p_stdout:
            LOG.warning('ResizeImg run stdout: %s', p_stdout)
        if p_stderr:
            LOG.error('ResizeImg run stderr: %s', p_stderr)

        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        if p.returncode:
            raise ResizeImgError('Resize failed: {err}'.format(
                err=p_stderr or p_stdout))

        for prefix in ['ori', 'cbz', 'web']:
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

    This is used for creator.indicia_image
    Not used for creator.indicia_landscape and creator.indicia_portrait.
    """

    def __init__(self, filename):
        """Constructor

        Args:
            filename: string, name of original image file
        """
        ResizeImg.__init__(self, filename)
        self.filenames = {'ori': None}

    def run(self, nice=NICES['resize']):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice. See os_nice for
                acceptable values.
        """
        #  $ convert infile -quiet -filter catrom -resize 1600x1600> \
        #     -colorspace sRGB +repage outfile

        real_filename = os.path.abspath(self.filename)

        args = []
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
            preexec_fn=os_nice(nice),
        )
        p_stdout, p_stderr = p.communicate()
        # Generally there should be no output. Log to help troubleshoot.
        if p_stdout:
            LOG.warning('ResizeImgIndicia run stdout: %s', p_stdout)
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
        self._full_name = None          # eg applications/zcomx/uploads/...
        self._original_name = None

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

    def fullname(self, size='original'):
        """Return the fullname of the image."""
        self.retrieve()
        return filename_for_size(self._full_name, size)

    def original_name(self):
        """Return the original name of the image.

        Returns:
            string: name of file.
        """
        self.retrieve()
        return self._original_name

    def retrieve(self):
        """Retrieve the names of the image.

        Returns:
            tuple: (original filename, full name)
        """
        if not self._full_name or not self._original_name:
            self._original_name, self._full_name = self.field.retrieve(
                self.image_name,
                nameonly=True,
            )
        return (self._original_name, self._full_name)


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


def on_delete_image(image):
    """Handle all processing required when an image is deleted.

    Args:
        image: string, name of image eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
    Returns:
        Row instance representing a queued job to delete image
    """
    if not image:
        return

    db = current.app.db
    job = DeleteImgQueuer(
        db.job,
        cli_args=[image],
    ).queue()
    if not job:
        LOG.error(
            'Failed to create job to delete img: %s', image)
    return job


def optimize(filename, nice=NICES['optimize'], quick=False):
    """Optimize an image file in place.

    Args:
        filename: string, name of file.
        nice: If True, run resize script with nice. See os_nice for
            acceptable values.
        quick: Use quick optimize routine (png only)
    """
    optimize_script = os.path.abspath(
        os.path.join(
            current.request.folder, 'private', 'bin', 'optimize_img.sh')
    )
    args = []
    args.append(optimize_script)
    if quick:
        args.append('--quick')
    args.append(os.path.abspath(filename))

    # optimize_img.sh creates temporary files in the current directory.
    # Use a temporary directory and cwd so processes are completed in
    # a safe place.
    with TemporaryDirectory() as tmp_dir:
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmp_dir,
            preexec_fn=os_nice(nice),
        )

        p_stdout, p_stderr = p.communicate()
        # Generally there should be no output. Log to help troubleshoot.
        if p_stdout:
            LOG.warning('optimize_img.sh run stdout: %s', p_stdout)
        if p_stderr:
            LOG.error('optimize_img.sh run stderr: %s', p_stderr)

        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        if p.returncode:
            raise ImageOptimizeError('Optimize failed: {err}'.format(
                err=p_stderr or p_stdout))


def rename(old_fullname, field, new_filename):
    """Rename a upload image. This will rename all sizes of the image file.

    Args:
        old_fullname: str, name of file to rename including path.
            eg applications/zcomx/uploads/original/book_page.image/8f/8f...
        field: gluon.dal.Field instance (field type 'upload')
        new_filename: str, new name of file, eg 'myfile.jpg'
            The new filename should not contain a path. The path is determined
            by the web2py upload store() function.

    Returns:
        dict, {size: stored filename, ...}
        Eg {
            'cbz': applications/zcomx/uploads/cbz/book_page.image...,
            'original': applications/zcomx/uploads/original/book_page.image...,
            'web': applications/zcomx/uploads/web/book_page.image...,
        }
    """
    stored_filenames = {}
    stored_filename = None
    with open(old_fullname, 'rb') as f:
        stored_filename = field.store(f, new_filename)
    _, new_fullname = field.retrieve(stored_filename, nameonly=True)
    stored_filenames['original'] = new_fullname
    for size in SIZES:
        old_sized_filename = filename_for_size(old_fullname, size)
        new_sized_filename = filename_for_size(new_fullname, size)
        if size not in stored_filenames:
            sized_path = os.path.dirname(new_sized_filename)
            if not os.path.exists(sized_path):
                os.makedirs(sized_path)
            if os.path.exists(old_sized_filename):
                shutil.move(old_sized_filename, new_sized_filename)
                stored_filenames[size] = new_sized_filename
        if os.path.exists(old_sized_filename):
            os.unlink(old_sized_filename)
    return stored_filenames


def scrub_extension_for_store(filename):
    """Return the filename with extension scrubbed so filename is suitable for
    store().
    The Field.store() method stores the file in an uploads folder with the same
    extension as the original filename. Some extensions are invalid
    and cause problem when optimizing. This function cleans up the extension.
    """
    if not filename:
        return filename

    translates = {
        'gif': 'png',
        'jpeg': 'jpg',
    }
    m = re.search(REGEX_UPLOAD_EXTENSION, filename)
    extension = m.group(1) if m else 'txt'
    if extension not in translates:
        return filename
    return filename[:(len(filename) - 1 - len(extension))] \
        + '.' + translates[extension]


def square_image(filename, offset=None, nice=NICES['resize']):
    """Square the image with name filename.

    Notes: image is squared in-place. Original image is modified.

    Args:
        filename: name of file to square.
        offset: str, used for -f option to square_image.sh
            Examples:
                offset='10'     offset is 10px
                offset='10%'    offset is 10 percent
        nice: If True, run resize script with nice. See os_nice for
            acceptable values.
    """
    if not os.path.exists(filename):
        raise LookupError('File not found: {f}'.format(f=filename))

    square_script = os.path.abspath(
        os.path.join(
            current.request.folder, 'private', 'bin', 'square_image.sh')
    )

    args = []
    args.append(square_script)
    args.append(filename)
    if offset:
        args.append('-f')
        args.append(offset)

    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os_nice(nice),
    )
    p_stdout, p_stderr = p.communicate()
    if p_stdout:
        LOG.error('square_image stdout: %s', p_stdout.decode())
    if p_stderr:
        LOG.error('square_image stderr: %s', p_stderr.decode())


def store(field, filename, resize=True, resizer=None):
    """Store an image file in an uploads directory.
    This will create all sizes of the image file.

    Args:
        field: gluon.dal.Field instance (field type 'upload')
        filename: name of file to store.
        resize: If True, the image is resized to SIZES sizes
        resizer: class, name of class to use for resizing. Default: ResizeImg
            Class must define a filenames dict property and a run() method.

    Return:
        string, the name of the file in storage.
    """
    scrubbed_filename = scrub_extension_for_store(filename)
    obj_class = resizer if resizer is not None else ResizeImg
    resize_img = obj_class(filename)
    if resize:
        resize_img.run()
    else:
        # Copy the files as is
        for size in list(resize_img.filenames.keys()):
            resize_img.filenames[size] = scrubbed_filename
    original_filename = resize_img.filenames['ori']
    with open(original_filename, 'r+b') as f:
        stored_filename = field.store(f, filename=scrubbed_filename)
    # stored_filename doesn't have a full path. Use retreive to get
    # file name will full path.
    unused_name, fullname = field.retrieve(stored_filename, nameonly=True)
    set_owner(os.path.dirname(fullname))                # store creates subdir
    set_owner(fullname)
    for size, name in list(resize_img.filenames.items()):
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

    resize_img.cleanup()
    return stored_filename
