#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
set_creator_indicia.py

Script to set the creator indicia image.
This is used for testing.
* Stores the image in the uploads directory
* Sets the creator.indicia_image field.
The update_creator_indicia is not queued.

"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import os
import shutil
import sys
from optparse import OptionParser
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.images import \
    ResizeImgIndicia, \
    store

VERSION = 'Version 0.1'
from applications.zcomx.modules.logger import set_cli_logging


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    set_creator_indicia.py [OPTIONS] id|name file.png

    set_creator_indicia.py 101 file.png                   # Set indicia by id
    set_creator_indicia.py 'Charles Forsman' file.png     # Set indicia by name

OPTIONS

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] id|name file.png'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
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

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) != 2:
        parser.print_help()
        exit(1)

    record_id = None
    name = None
    try:
        record_id = int(args[0])
    except (TypeError, ValueError):
        name = args[0]

    if record_id is None:
        query = (db.auth_user.name == name)
        rows = db(query).select(
            left=db.creator.on(
                db.creator.auth_user_id == db.auth_user.id),
        )
        if not rows:
            print 'No creator found, name: {n}'.format(n=name)
            quit(1)
        if len(rows) > 1:
            print 'Multiple creator matches, use creator id:'
            for r in rows:
                print 'id: {i}'.format(i=r.id)
            quit(1)
        record_id = rows[0].creator.id

    creator = Creator.from_id(record_id)

    if not os.path.exists(args[1]):
        print 'File not found: {n}'.format(n=args[1])
        quit(1)

    image_fullname = args[1]

    # Cp the file to a tmp directory so it is not deleted.
    tmp_dir = '/tmp/set_creator_indicia'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    local_filename = os.path.join(tmp_dir, os.path.basename(image_fullname))

    # Copy file name so original is not touched
    shutil.copy(image_fullname, local_filename)

    LOG.debug('Storing image')
    img_field = 'indicia_image'
    # This code copied/adapted from controllers/login.py def
    # creator_img_handler.
    resizer = ResizeImgIndicia if img_field == 'indicia_image' else None
    try:
        stored_filename = store(
            db.creator[img_field], local_filename, resizer=resizer)
    except Exception as err:
        print >> sys.stderr, \
            'Creator image upload error: {err}'.format(err=err)
        stored_filename = None

    if not stored_filename:
        print >> sys.stderr, \
            'Stored filename not returned. Aborting.'
        quit(1)

    LOG.debug('stored_filename: %s', stored_filename)
    LOG.debug('Updating creator.indicia_image')
    data = {img_field: stored_filename}
    creator = Creator.from_updated(creator, data)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
