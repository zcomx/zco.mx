#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
process_img.py

Script to process an image.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
import os
from optparse import OptionParser
from applications.zcomx.modules.images import \
    SIZES, \
    UploadImage, \
    is_optimized, \
    optimize
from applications.zcomx.modules.utils import NotFoundError

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def run_delete(image, options):
    """Delete an image.

    Args:
        image: string, name of image. eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
        options: dict, OptionParser options
    """
    try:
        table, field, _ = image.split('.', 2)
    except ValueError:
        raise NotFoundError('Invalid image {i}'.format(i=image))
    if table not in db.tables or field not in db[table]:
        raise NotFoundError('Invalid image {i}'.format(i=image))

    upload_image = UploadImage(db[table][field], image)
    upload_image.delete_all()

    query = (db.optimize_img_log.image == image)
    db(query).delete()
    db.commit()


def run_optimize(image, options):
    """Optimize an image.

    Args:
        image: string, name of image. eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
        options: dict, OptionParser options
    """
    if not options.force and is_optimized(image):
        LOG.debug(
            'Not necessary, already optimized: %s', image)
        return

    try:
        table, field, _ = image.split('.', 2)
    except ValueError:
        raise NotFoundError('Invalid image {i}'.format(i=image))
    if table not in db.tables or field not in db[table]:
        raise NotFoundError('Invalid image {i}'.format(i=image))

    upload_image = UploadImage(db[table][field], image)

    up_folder = db[table][field].uploadfolder.rstrip('/').rstrip('original')

    LOG.debug('Optimizing: %s', image)

    for size in SIZES:
        fullname = upload_image.fullname(size=size)
        if options.uploads and fullname.startswith(up_folder):
            filename = os.path.join(
                options.uploads,
                fullname.replace(up_folder, '', 1)
            )
        else:
            filename = fullname

        if os.path.exists(os.path.abspath(filename)):
            LOG.debug('Optimizing filename: %s', filename)
            optimize(filename)

    db.optimize_img_log.insert(image=image)
    db.commit()


def man_page():
    """Print manual page-like help"""
    print """

USAGE
    process_img.py [OPTIONS] image
    process_img.py [OPTIONS] image_1 image_2 image_3
    process_img.py [OPTIONS] --delete image_1 image_2 image_3

EXAMPLE
    # optimize an image
    process_img.py book_page.image.801685b627e099e.300332e6a7067.jpg

    # delete an image
    process_img.py --delete book_page.image.801685b627e099e.300332e6a7067.jpg

OPTIONS
    -d, --delete
        With this option, the image is deleted.

    -f, --force
        By default, if the image(s) associated with the field(s) have already
        been optimized, (indicated by a optimize_img_log record), the optimize
        is not run. With the --force option, it is optimized regardless.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -p PRIORITY --priority=PRIORITY
        Queue jobs at this priority. Must be one of PRIORITIES.
        Default 'optimize_img'.

    -u PATH --uploads-path=PATH
        Use this option to indicate the path of the directory the upload images
        are stored in. Default: application/zcomx/uploads

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] image [image_2 image_3 ...]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-d', '--delete',
        action='store_true', dest='delete', default=False,
        help='Delete the image(s).',
    )
    parser.add_option(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Force optimize regardless of optimize_img_log record.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-p', '--priority',
        dest='priority', default='optimize_img',
        help='Queue jobs at this priority.',
    )
    parser.add_option(
        '-u', '--uploads-path',
        dest='uploads', default=None,
        help='Path of directory upload images are stored in.',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
    )

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    LOG.debug('Starting')
    for image in args:
        if options.delete:
            run_delete(image, options)
        else:
            run_optimize(image, options)
    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)