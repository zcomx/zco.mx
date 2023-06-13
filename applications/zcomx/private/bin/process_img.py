#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
process_img.py

Script to process an image.
"""
import argparse
import os
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.images import (
    SIZES,
    UploadImage,
    optimize,
)
from applications.zcomx.modules.images_optimize import AllSizesImages
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def run_delete(image, args):
    """Delete an image.

    Args:
        image: string, name of image. eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
        args: dict, argparse args
    """
    try:
        table, field, _ = image.split('.', 2)
    except ValueError as exc:
        raise LookupError('Invalid image {i}'.format(i=image)) from exc
    if table not in db.tables or field not in db[table]:
        raise LookupError('Invalid image {i}'.format(i=image))

    LOG.debug('Deleting: %s', image)

    upload_image = UploadImage(db[table][field], image)
    if args.size:
        upload_image.delete(size=args.size)
    else:
        upload_image.delete_all()

    query = (db.optimize_img_log.image == image)
    if args.size:
        query = query & (db.optimize_img_log.size == args.size)
    db(query).delete()
    db.commit()


def run_optimize(image, args):
    """Optimize an image.

    Args:
        image: string, name of image. eg
            book_page.image.801685b627e099e.300332e6a7067.jpg
        args: dict, argparse args
    """
    try:
        table, field, _ = image.split('.', 2)
    except ValueError as exc:
        raise LookupError('Invalid image {i}'.format(i=image)) from exc
    if table not in db.tables or field not in db[table]:
        raise LookupError('Invalid image {i}'.format(i=image))

    upload_image = UploadImage(db[table][field], image)
    up_folder = db[table][field].uploadfolder.rstrip('/').rstrip('original')

    LOG.debug('Optimizing: %s', image)

    size_to_classes = AllSizesImages.size_to_class_hash()
    sizes = [args.size] if args.size else SIZES
    for size in sizes:
        img_class = size_to_classes[size]
        if not args.force and img_class(image).is_optimized():
            LOG.debug(
                'Not necessary, already optimized (size: %s): %s', size, image)
            continue

        fullname = upload_image.fullname(size=size)
        if args.uploads and fullname.startswith(up_folder):
            filename = os.path.join(
                args.uploads,
                fullname.replace(up_folder, '', 1)
            )
        else:
            filename = fullname

        if os.path.exists(os.path.abspath(filename)):
            LOG.debug('Optimizing filename: %s', filename)
            optimize(filename, quick=DEBUG)

        db.optimize_img_log.insert(image=image, size=size)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print("""

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

    -s SIZE, --size=SIZE
        By default all sizes of the image are processed. With this option,
        only the SIZE size is processed.

    -u PATH --uploads-path=PATH
        Use this option to indicate the path of the directory the upload images
        are stored in. Default: application/zcomx/uploads

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='process_img.py')

    parser.add_argument(
        'image_names',
        nargs='+',
        metavar='image_name [image_name ...]',
    )

    parser.add_argument(
        '-d', '--delete',
        action='store_true', dest='delete', default=False,
        help='Delete the image(s).',
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Force optimize regardless of optimize_img_log record.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-s', '--size',
        choices=SIZES,
        dest='size', default=None,
        help='Process this size only.',
    )
    parser.add_argument(
        '-u', '--uploads-path',
        dest='uploads', default=None,
        help='Path of directory upload images are stored in.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    LOG.debug('Starting')
    for image in args.image_names:
        if args.delete:
            run_delete(image, args)
        else:
            run_optimize(image, args)
    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
