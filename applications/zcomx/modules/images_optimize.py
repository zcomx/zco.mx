#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to optimizing images.
"""
from gluon import *
from applications.zcomx.modules.job_queuers import \
    OptimizeCBZImgForReleaseQueuer, \
    OptimizeCBZImgQueuer, \
    OptimizeOriginalImgQueuer, \
    OptimizeWebImgQueuer
from applications.zcomx.modules.records import Record

LOG = current.app.logger


class OptimizeImgLog(Record):
    """Class representing a optimize_img_log record"""
    db_table = 'optimize_img_log'


class BaseSizedImage(object):
    """Base class representing an image of a specific size."""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, name of image
                eg 'book_page.image.801685b627e099e.300332e6a7067.jpg'
        """
        self.name = name

    def is_optimized(self):
        """Determine if the image size is optimized.

        Returns:
            True if the image is optimized, False otherwise
        """
        db = current.app.db
        query = (db.optimize_img_log.image == self.name) & \
                (db.optimize_img_log.size == self.size())
        return db(query).count() > 0

    def queuer(self):
        """Return the queuer to use for optimizing image.

        Returns:
            OptimizeImg subclass instance
        """
        db = current.app.db
        queuer = self.queuer_class()(db.job)
        queuer.cli_args.append(self.name)
        return queuer

    def queuer_class(self):
        """Return the class of queuer to use for optimizing image.

        Returns:
            OptimizeImg subclass
        """
        raise NotImplementedError()

    @classmethod
    def size(cls):
        """Return the size of the image.

        Returns:
            string, one of SIZES
        """
        raise NotImplementedError()


class CBZImage(BaseSizedImage):
    """Base class representing an image of cbz size."""

    def queuer_class(self):
        return OptimizeCBZImgQueuer

    @classmethod
    def size(cls):
        return 'cbz'


class CBZForReleaseImage(CBZImage):
    """Base class representing an image of cbz size for release."""

    def queuer_class(self):
        return OptimizeCBZImgForReleaseQueuer


class OriginalImage(BaseSizedImage):
    """Base class representing an image of original size."""

    def queuer_class(self):
        return OptimizeOriginalImgQueuer

    @classmethod
    def size(cls):
        return 'original'


class WebImage(BaseSizedImage):
    """Base class representing an image of web size."""

    def queuer_class(self):
        return OptimizeWebImgQueuer

    @classmethod
    def size(cls):
        return 'web'


class Image(object):
    """Class representing an image for optimizing."""

    def __init__(self, sized_images):
        """Constructor

        Args:
            sized_image: list of BaseSizedImage subclass instances
        """
        self.sized_images = sized_images

    def is_optimized(self):
        """Determin if the image is optimized.

        Returns:
            True if the image is optimized, False otherwise
        """
        for sized_image in self.sized_images:
            if not sized_image.is_optimized():
                return False
        return True

    def queue_optimize(self):
        """Queue an job to optimize the image.

        Returns:
            Job instance representing queued job
        """
        jobs = []
        for sized_image in self.sized_images:
            jobs.append(sized_image.queuer().queue())
        return jobs


class BaseImages(object):
    """Base class representing a set of images for optimizing."""

    def __init__(self, images):
        """Constructor

        Args:
            images: list of Image instances
        """
        self.images = images

    @classmethod
    def from_names(cls, names):
        """Return an Images instance from a list of image names.

        Args:
            names: list of strings, image names as required by Image

        Returns:
            Images instance
        """
        images = []
        size_classes = cls.sized_image_classes()
        for name in names:
            sized_images = [x(name) for x in size_classes]
            images.append(Image(sized_images))
        return cls(images)

    def has_unoptimized(self):
        """Return if at least one image is unoptimized.

        Returns:
            True if at least one image in the set is unoptimized,
                False otherwise.
        """
        for image in self.images:
            if not image.is_optimized():
                return True
        return False

    def optimize(self):
        """Optimize all images as necessary.

        Returns:
            jobs, list of Job instances of jobs created to optimize images.
        """
        jobs = []
        for image in self.images:
            if not image.is_optimized():
                jobs.extend(image.queue_optimize())
        return jobs

    @classmethod
    def sized_image_classes(cls):
        """Return a list of BaseSizedImage classes representing the sizes of
        images.

        Returns:
            List of BaseSizedImage subclasses
        """
        raise NotImplementedError()

    @classmethod
    def size_to_class_hash(cls):
        """Return a hash allowing size to class lookups.

        Returns:
            dict
        """
        size_to_class = {}
        for img_class in cls.sized_image_classes():
            size_to_class[img_class.size()] = img_class
        return size_to_class


class AllSizesImages(BaseImages):
    """Class representing a set of images (all sizes) for optimizing for
    release."""
    @classmethod
    def sized_image_classes(cls):
        return [CBZImage, OriginalImage, WebImage]


class CBZImagesForRelease(BaseImages):
    """Class representing a set of cbz images for optimizing for release."""

    @classmethod
    def sized_image_classes(cls):
        return [CBZForReleaseImage]
