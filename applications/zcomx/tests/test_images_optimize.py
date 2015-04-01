#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/images_optimize.py

"""
import collections
import unittest
from gluon import *
from applications.zcomx.modules.job_queue import \
    OptimizeCBZImgForReleaseQueuer, \
    OptimizeCBZImgQueuer, \
    OptimizeOriginalImgQueuer, \
    OptimizeWebImgQueuer
from applications.zcomx.modules.images_optimize import \
    AllSizesImages, \
    BaseImages, \
    BaseSizedImage, \
    CBZForReleaseImage, \
    CBZImage, \
    CBZImagesForRelease, \
    Image, \
    OriginalImage, \
    WebImage
from applications.zcomx.modules.tests.runner import \
    LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
# pylint: disable=W0212


class DubQueuer(object):

    def __init__(self, tbl):
        self.tbl = tbl
        self.cli_args = []
        self.queued = {}

    def queue(self):
        self.queued = {
            'result': True,
            'args': self.cli_args,
        }
        return self.queued


class DubOptimizedImage(Image):
    def is_optimized(self):
        return True

    def queue_optimize(self):
        return ['optimized']


class DubUnOptimizedImage(DubOptimizedImage):
    def is_optimized(self):
        return False


class DubSizedImage(BaseSizedImage):
    def queuer_class(self):
        return DubQueuer

    @classmethod
    def size(cls):
        return 'dub'


class DubSizedImage2(BaseSizedImage):
    def queuer_class(self):
        return DubQueuer

    @classmethod
    def size(cls):
        return 'dub2'


class DubImages(BaseImages):
    @classmethod
    def sized_image_classes(cls):
        return [DubSizedImage, DubSizedImage2]


class TestAllSizesImages(LocalTestCase):

    def test__sized_image_classes(self):
        self.assertEqual(
            AllSizesImages.sized_image_classes(),
            [CBZImage, OriginalImage, WebImage]
        )


class TestBaseImages(LocalTestCase):

    optimized_images = None
    unoptimized_images = None
    mixed_images = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        sized_images = [DubSizedImage(x) for x in ['a', 'b', 'c']]
        cls.optimized_images = [DubOptimizedImage(sized_images)]
        cls.unoptimized_images = [DubUnOptimizedImage(sized_images)]
        cls.mixed_images = cls.optimized_images + cls.unoptimized_images

    def test____init__(self):
        image = Image('name.jpg')
        image_set = DubImages([image])
        self.assertTrue(image_set)

    def test__from_names(self):
        names = ['aaa.jpg', 'bbb.png', 'ccc.jpg']
        expect_sizes = ['dub', 'dub2']
        image_set = DubImages.from_names(names)
        self.assertEqual(len(image_set.images), 3)
        name_sizes = collections.defaultdict(lambda: [])
        for image in image_set.images:
            self.assertEqual(len(image.sized_images), len(expect_sizes))
            for sized_image in image.sized_images:
                size = sized_image.size()
                name_sizes[sized_image.name].append(size)
        self.assertEqual(
            name_sizes,
            {
                'aaa.jpg': expect_sizes,
                'bbb.png': expect_sizes,
                'ccc.jpg': expect_sizes,
            }
        )

    def test__has_unoptimized(self):

        tests = [
            # (images, expect)
            ([], False),
            (self.optimized_images, False),
            (self.unoptimized_images, True),
            (self.mixed_images, True),
        ]
        for t in tests:
            image_set = DubImages(t[0])
            self.assertEqual(image_set.has_unoptimized(), t[1])

    def test__optimize(self):

        tests = [
            # (images, expect number of jobs)
            ([], 0),
            (self.optimized_images, 0),
            (self.unoptimized_images, 1),
            (self.mixed_images, 1),
        ]
        for t in tests:
            image_set = DubImages(t[0])
            jobs = image_set.optimize()
            self.assertEqual(len(jobs), t[1])

    def test__sized_image_classes(self):
        self.assertRaises(NotImplementedError, BaseImages.sized_image_classes)
        self.assertEqual(
            DubImages.sized_image_classes(),
            [DubSizedImage, DubSizedImage2]
        )

    def test__size_to_class_hash(self):
        self.assertRaises(NotImplementedError, BaseImages.sized_image_classes)
        self.assertEqual(
            DubImages.size_to_class_hash(),
            {
                'dub': DubSizedImage,
                'dub2': DubSizedImage2,
            }
        )


class TestBaseSizedImage(LocalTestCase):

    def test____init__(self):
        image = BaseSizedImage('name.jpg')
        self.assertTrue(image)

    def test__is_optimized(self):
        image_name = 'name.jpg'
        image = DubSizedImage(image_name)

        self.assertFalse(image.is_optimized())

        self.add(db.optimize_img_log, dict(
            image=image_name,
            size='web',             # mismatching size
        ))

        self.assertFalse(image.is_optimized())

        self.add(db.optimize_img_log, dict(
            image=image_name,
            size='dub',
        ))
        self.assertTrue(image.is_optimized())

    def test__queuer(self):
        image = DubSizedImage('name.jpg')
        queuer = image.queuer()
        self.assertEqual(str(queuer.tbl), 'job')
        self.assertEqual(queuer.cli_args, ['name.jpg'])

    def test__queuer_class(self):
        image = BaseSizedImage('name.jpg')
        self.assertRaises(NotImplementedError, image.queuer_class)

    def test__size(self):
        image = BaseSizedImage('name.jpg')
        self.assertRaises(NotImplementedError, image.size)


class TestCBZForReleaseImage(LocalTestCase):

    def test__queuer_class(self):
        image = CBZForReleaseImage('name.jpg')
        self.assertEqual(image.queuer_class(), OptimizeCBZImgForReleaseQueuer)


class TestCBZImage(LocalTestCase):

    def test__queuer_class(self):
        image = CBZImage('name.jpg')
        self.assertEqual(image.queuer_class(), OptimizeCBZImgQueuer)

    def test__size(self):
        image = CBZImage('name.jpg')
        self.assertEqual(image.size(), 'cbz')


class TestCBZImagesForRelease(LocalTestCase):

    def test__sized_image_classes(self):
        self.assertEqual(
            CBZImagesForRelease.sized_image_classes(),
            [CBZForReleaseImage]
        )


class TestImage(LocalTestCase):

    def test____init__(self):
        sized_images = [CBZImage('name.jpg'), WebImage('name.jpg')]
        image = Image(sized_images)
        self.assertTrue(image)

    def test__is_optimized(self):
        image_name = 'name.jpg'
        sized_images = [CBZImage(image_name), WebImage(image_name)]
        image = Image(sized_images)

        self.assertFalse(image.is_optimized())

        self.add(db.optimize_img_log, dict(
            image=image_name,
            size='original',            # mismatch size
        ))

        self.assertFalse(image.is_optimized())

        self.add(db.optimize_img_log, dict(
            image=image_name,
            size='cbz'
        ))
        self.assertFalse(image.is_optimized())      # not all images logged

        self.add(db.optimize_img_log, dict(
            image=image_name,
            size='web'
        ))
        self.assertTrue(image.is_optimized())

    def test__queue_optimize(self):
        image_name = 'name.jpg'
        sized_images = [DubSizedImage(image_name), DubSizedImage(image_name)]
        image = Image(sized_images)

        jobs = image.queue_optimize()
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(
                job,
                {
                    'result': True,
                    'args': [image_name],
                }
            )


class TestOriginalImage(LocalTestCase):

    def test__queuer_class(self):
        image = OriginalImage('name.jpg')
        self.assertEqual(image.queuer_class(), OptimizeOriginalImgQueuer)

    def test__size(self):
        image = OriginalImage('name.jpg')
        self.assertEqual(image.size(), 'original')


class TestWebImage(LocalTestCase):

    def test__queuer_class(self):
        image = WebImage('name.jpg')
        self.assertEqual(image.queuer_class(), OptimizeWebImgQueuer)

    def test__size(self):
        image = WebImage('name.jpg')
        self.assertEqual(image.size(), 'web')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
