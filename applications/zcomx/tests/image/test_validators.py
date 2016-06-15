#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/image/validators.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.image.validators import \
    InvalidImageError, \
    ImageValidator, \
    CBZValidator, \
    WebValidator
from applications.zcomx.modules.images import ImageDescriptor
from applications.zcomx.modules.tests.helpers import ImageTestCase
from applications.zcomx.modules.tests.runner import \
    LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
# pylint: disable=W0212


class ValidatorTestCase(ImageTestCase):
    """Base class for test cases that need access to test data directory."""

    def _test_validate(self, validator_class, dimensions, expect_valid):
        filename = self._create_image('file.jpg', dimensions)
        validator = validator_class(filename)
        if expect_valid:
            self.assertTrue(
                validator.validate(image_descriptor=ImageDescriptor)
            )
        else:
            self.assertRaises(
                InvalidImageError,
                validator.validate,
                image_descriptor=ImageDescriptor
            )


class TestCBZValidator(ValidatorTestCase):

    def test__minimum_widths(self):
        validator = CBZValidator('path/to/file.jpg')
        self.assertEqual(
            validator.minimum_widths,
            {
                'landscape': 2560,
                'portrait': 1600,
                'square': 1600,
            }
        )

    def test_parent_validate(self):
        tests = [
            # ((width, height), expect)
            # landscape
            ((2559, 1000), False),
            ((2560, 1000), True),
            ((2561, 1000), True),
            # portrait
            ((1599, 2000), False),
            ((1600, 2000), True),
            ((1601, 2000), True),
            # square
            ((1599, 1599), False),
            ((1600, 1600), True),
            ((1601, 1601), True),
        ]

        for t in tests:
            self._test_validate(CBZValidator, t[0], t[1])


class TestImageValidator(ValidatorTestCase):

    def test____init__(self):
        validator = ImageValidator('path/to/file.jpg')
        self.assertTrue(validator)

    def test__minimum_widths(self):
        validator = ImageValidator('path/to/file.jpg')
        self.assertEqual(
            validator.minimum_widths,
            {
                'landscape': 0,
                'portrait': 0,
                'square': 0,
            }
        )

    def test__validate(self):
        tests = [
            # ((width, height), expect)
            ((100, 100), True),
            ((999, 100), True),
            ((100, 999), True),
        ]

        for t in tests:
            self._test_validate(ImageValidator, t[0], t[1])


class TestInvalidImageError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise InvalidImageError(msg)
        except InvalidImageError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('InvalidImageError not raised')


class TestWebValidator(ValidatorTestCase):

    def test__minimum_widths(self):
        validator = WebValidator('path/to/file.jpg')
        self.assertEqual(
            validator.minimum_widths,
            {
                'landscape': 1200,
                'portrait': 750,
                'square': 750,
            }
        )

    def test_parent_validate(self):
        tests = [
            # ((width, height), expect)
            # landscape
            ((1199, 1000), False),
            ((1200, 1000), True),
            ((1201, 1000), True),
            # portrait
            ((749, 2000), False),
            ((750, 2000), True),
            ((751, 2000), True),
            # square
            ((749, 749), False),
            ((750, 750), True),
            ((751, 751), True),
        ]

        for t in tests:
            self._test_validate(WebValidator, t[0], t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
