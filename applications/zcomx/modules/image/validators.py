#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Classes and functions related to validating images.
"""
from gluon import *
from applications.zcomx.modules.images import ImageDescriptor

LOG = current.app.logger


class InvalidImageError(Exception):
    """Exception class for invalid image errors."""
    pass


class ImageValidator(object):
    """Class representing an image validator"""

    def __init__(self, filename):
        """Initializer

        Args:
            filename: str, name of image file
        """
        self.filename = filename

    @property
    def minimum_widths(self):
        """Return the minimum widths in pixels for the image orientations

        Returns:
            dict
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return {
            'landscape': 0,
            'portrait': 0,
            'square': 0,
        }

    def validate(self, image_descriptor=ImageDescriptor):
        """Validate the image."""
        descriptor = image_descriptor(self.filename)
        dimensions = descriptor.dimensions()
        width = dimensions[0]
        orientation = descriptor.orientation()
        minimum_width = self.minimum_widths[orientation]
        if width < minimum_width:
            msg = 'Minimum width for {o} image is {w}px'.format(
                o=orientation, w=minimum_width)
            raise InvalidImageError(msg)
        return True


class CBZValidator(ImageValidator):
    """Class representing a CBZ image validator"""

    @property
    def minimum_widths(self):
        # These values should match those in resize_img.sh variable d1
        return {
            'landscape': 2560,
            'portrait': 1600,
            'square': 1600,
        }


class WebValidator(ImageValidator):
    """Class representing a Web image validator"""

    @property
    def minimum_widths(self):
        # These values should match those in resize_img.sh variable d1
        return {
            'landscape': 1200,
            'portrait': 750,
            'square': 750,
        }
