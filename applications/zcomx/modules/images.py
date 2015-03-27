#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to images.
"""
import glob
import imghdr
import logging
import os
import shutil
import subprocess
from PIL import Image
from gluon import *
from applications.zcomx.modules.job_queue import \
    DeleteImgQueuer, \
    OptimizeImgQueuer, \
    OptimizeImgForReleaseQueuer
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    TemporaryDirectory, \
    os_nice, \
    set_owner
from applications.zcomx.modules.utils import NotFoundError

LOG = logging.getLogger('app')

SIZES = [
    'original',
    'cbz',
    'web',
    'tbn',
]


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
        self.filenames = {'ori': None, 'cbz': None, 'web': None}

    def run(self, nice='max'):
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
            LOG.warn('ResizeImg run stdout: %s', p_stdout)
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

    def run(self, nice='max'):
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
        self._sizes = {}                # {'size': x kb}
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
        self.retrieve()
        return filename_for_size(self._full_name, size)

    def orientation(self):
        """Return the orientation of the image.

        Returns:
            string, one of 'portrait', 'landscape', 'square'
        """
        width, height = self.dimensions()
        if width == height:
            return 'square'
        elif width > height:
            return 'landscape'
        else:
            return 'portrait'

    def original_name(self):
        """Return the original name of the image.

        Returns:
            string: name of file.
        """
        self.retrieve()
        return self._original_name

    def pil_image(self, size='original'):
        """Return a PIL Image instance representing the image.

        Args:
            size: string, name of size, must one of SIZES

        Returns:
            PIL Image instance.
        """
        if not self._images or size not in self._images:
            filename = self.fullname(size=size)
            if os.path.exists(filename):
                self._images[size] = Image.open(filename)
            else:
                self._images[size] = None
        return self._images[size]

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

    def size(self, size='original'):
        """Return the size (bytes) of the image.

        Args:
            size: string, name of size, must one of SIZES

        Returns:
            integer, size of image in bytes
        """
        if not self._sizes or size not in self._sizes:
            full_name = self.fullname(size=size)
            try:
                size_bytes = os.stat(full_name).st_size
            except (KeyError, OSError):
                size_bytes = 0
            self._sizes[size] = size_bytes
        return self._sizes[size]


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


def is_optimized(image):
    """Determined if the image is optimized.

    Args:
        image: string, name of image eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db
    query = (db.optimize_img_log.image == image)
    return db(query).count() > 0


def on_add_image(image):
    """Handle all processing required when an image is added.

    Args:
        image: string, name of image eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
    """
    if not image:
        return
    db = current.app.db
    job = OptimizeImgQueuer(
        db.job,
        cli_args=[image],
    ).queue()
    if not job:
        LOG.error(
            'Failed to create job to optimize img: %s', image)

    return job


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


def optimize(filename, nice='max'):
    """Optimize an image file in place.

    Args:
        filename: string, name of file.
        nice: If True, run resize script with nice. See os_nice for
            acceptable values.
    """
    optimize_script = os.path.abspath(
        os.path.join(
            current.request.folder, 'private', 'bin', 'optimize_img.sh')
    )
    args = []
    args.append(optimize_script)
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
            LOG.warn('optimize_img.sh run stdout: %s', p_stdout)
        if p_stderr:
            LOG.error('optimize_img.sh run stderr: %s', p_stderr)

        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        if p.returncode:
            raise ImageOptimizeError('Optimize failed: {err}'.format(
                err=p_stderr or p_stdout))


def queue_optimize(
        image,
        priority='optimize_img',
        job_options=None,
        cli_options=None):
    """Queue job to optimize images associated with a record field.

    Args:
        image: string, name of image eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
        priority: string, priority key, one of PROIRITIES
        job_options: dict, job record attributes used for JobQueuer property
        cli_options: dict, options for job command

    Returns:
        Row instance representing the queued job.
    """
    queuer_classes = {
        'optimize_img': OptimizeImgQueuer,
        'optimize_img_for_release': OptimizeImgForReleaseQueuer,
    }
    if priority not in queuer_classes:
        raise NotFoundError('Invalid priority: {p}'.format(p=priority))

    db = current.app.db
    queuer = queuer_classes[priority](
        db.job,
        job_options=job_options,
        cli_options=cli_options,
        cli_args=[image],
    )

    return queuer.queue()


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
    obj_class = resizer if resizer is not None else ResizeImg
    resize_img = obj_class(filename)
    if resize:
        resize_img.run()
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

    resize_img.cleanup()
    return stored_filename
