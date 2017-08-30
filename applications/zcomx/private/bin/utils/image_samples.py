#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
image_samples.py

Script to create image samples.
"""
from __future__ import print_function
import os
import subprocess
import sys
from optparse import OptionParser
from PIL import Image, ImageDraw, ImageFont
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

FIELDS = [
    'creator.image',
    'book_page.image',
]


class ImageCreator(object):
    """Class representing a handler for creating image."""

    def __init__(
            self,
            path,
            extension='jpg',
            size=170,
            min_size=70,
            color='black',
            increment=0,
            font_ttf=None,
            font_size=10,
            dry_run=False):
        """Constructor

        Args:
            path: string, directory path where images are stored.
            extension: string, extension of image files, indicates the type of
                image.
            size: integer, image width and height in pixels.
            min_size: integer, the minimum image width/height in pixels.
            color: string, image colour, #rrggbb,
            increment: integer, amount the width and height will be incremented
                to create size variations.
            font_ttf: string, ttf font filename
            font_size: integer, ttf font size
            dry_run: If True, report what would be done but make no images.
        """
        self.path = path
        self.extension = extension
        self.size = size
        self.min_size = min_size
        self.color = color
        self.increment = increment
        self.font_ttf = font_ttf
        self.font_size = font_size
        self.dry_run = dry_run

    def run(self):
        """Create images"""
        for size in self.size_generator():
            action = 'Dry run' if self.dry_run else 'Creating'
            name = 'img_{w:03d}x{h:03d}.{e}'.format(
                w=size[0],
                h=size[1],
                e=self.extension
            )
            image_filename = os.path.join(self.path, name)
            LOG.info('{action}: {name}'.format(
                action=action, name=image_filename))
            if not self.dry_run:
                im = Image.new('RGB', size, color=self.color)
                font = None
                if self.font_ttf:
                    font = ImageFont.truetype(self.font_ttf, self.font_size)
                with open(image_filename, 'wb') as f:
                    draw = ImageDraw.Draw(im)
                    draw.text([10, 10], name, font=font)
                    im.save(f)

    def size_generator(self):
        """Generator of image sizes.

        Returns:
            tuple: (width, height)
        """
        if not self.increment:
            yield (self.size, self.size)
            return

        h = self.size
        increments = range(self.size, self.min_size - 1, -1 * self.increment)
        for w in increments:
            yield (w, h)
        w = self.size
        for h in increments:
            yield (w, h)


def list_ttf():
    """List ttf files on system."""
    args = ['find', '/', '-name', "'*.ttf'"]
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    p_stdout, p_stderr = p.communicate()
    if p_stderr:
        print('ERROR: {err}'.format(err=p_stderr), file=sys.stderr)
        exit(1)
    print(p_stdout)


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    image_samples.py [OPTIONS] /path/to/images


OPTIONS
    -c COLOR, --color=COLOR
        Image background color. Examples, 'black', '#000000'

    -d, --dry-run
        Do not create images, only report what would be done.

    -e EXT, --extension=EXT
        Image file extension. Determines the file type. Examples: 'jpg', 'png'.

    --font-size=TTF
        TrueType font size. Use this with --font-ttf option. Default 10.

    --font-ttf=TTF
        Name of TrueType font file. This font is used for image label.

    -h, --help
        Print a brief help.

    -i INCR, --increment=INCR
        Various sizes of images are created. The width and height are varied
        by this number of increments. Set to 0 for no variations.

    --list-ttf
        List available TTF fonts and exit.

    -s SIZE, --size=SIZE
        By default, images are resized to each of the standard sizes. With
        this option, images are resized to SIZE only. Use --sizes option to
        list valid values for SIZE.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """)


def main():
    """Main processing."""

    usage = '%prog [options] [path/for/images]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-c', '--color', type='string',
        dest='color', default='black',
        help='Image background color. Default: black',
    )
    parser.add_option(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not create images. Only report what would be done.',
    )
    parser.add_option(
        '-e', '--extension', type='string',
        dest='extension', default='jpg',
        help='Image file extension. Default: jpg',
    )
    parser.add_option(
        '--font-size', type='int',
        dest='font_size', default=10,
        help='TrueType font size. Default 10',
    )
    parser.add_option(
        '--font-ttf', type='string',
        dest='font_ttf', default=None,
        help='TrueType font file.',
    )
    parser.add_option(
        '-i', '--increment', type='int',
        dest='increment', default=0,
        help='Increment in pixels to vary width and hieght by. Default 0',
    )
    parser.add_option(
        '--list-ttf',
        action='store_true', dest='list_ttf', default=False,
        help='List TTF files available on system and exit.',
    )
    parser.add_option(
        '-m', '--min-size', type='int',
        dest='min_size', default=70,
        help='Minimum image size in pixels. Default 70',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-s', '--size', type='int',
        dest='size', default=170,
        help='Default image size in pixels. Default 170',
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

    if options.list_ttf:
        list_ttf()
        quit(0)

    if len(args) > 1:
        print(parser.print_help())
        quit(1)

    path = os.getcwd()
    if args:
        path = args[0]

    if not os.path.exists(path):
        LOG.error('Directory not found: {path}'.format(path=path))
        exit(1)

    if options.font_ttf and not os.path.exists(options.font_ttf):
        LOG.error('TrueType font file not found: {path}'.format(
            path=options.font_ttf))
        exit(1)

    LOG.debug('path: {var}'.format(var=path))

    LOG.info('Started.')
    creator = ImageCreator(
        path,
        extension=options.extension,
        size=options.size,
        min_size=options.min_size,
        color=options.color,
        increment=options.increment,
        font_ttf=options.font_ttf,
        font_size=options.font_size,
        dry_run=options.dry_run,
    )
    creator.run()
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
