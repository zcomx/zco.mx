#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/my/constants.py

"""

import unittest
from applications.zcomx.modules.my.constants import \
        ASCII_CHARACTER, \
        ASCII_DESCRIPTION, \
        ASCII_FRIENDLY_CODE, \
        ASCII_HEX_CODE, \
        ASCII_NUMERICAL_CODE, \
        CM_PER_INCH, \
        CM_PER_M, \
        HOURS_PER_DAY, \
        KG_PER_LB, \
        KG_PER_TONNE, \
        LB_PER_KG, \
        LB_PER_TON, \
        MINUTES_PER_DAY, \
        MINUTES_PER_HOUR, \
        MM_PER_CM, \
        MM_PER_INCH, \
        MM_PER_M, \
        M_PER_INCH, \
        OZ_PER_KG, \
        OZ_PER_LB, \
        SECONDS_PER_DAY, \
        SECONDS_PER_HOUR, \
        SECONDS_PER_MINUTE, \
        ascii_lookup
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: *Missing docstring*
# pylint: disable=C0111
# R0904: *Too many public methods (%%s/%%s)*
# pylint: disable=R0904


class TestConstants(LocalTestCase):

    def test_constants(self):
        # Time
        self.assertEqual(SECONDS_PER_MINUTE, 60)
        self.assertEqual(MINUTES_PER_HOUR, 60)
        self.assertEqual(HOURS_PER_DAY, 24)
        self.assertEqual(MINUTES_PER_DAY, 1440)
        self.assertEqual(SECONDS_PER_HOUR, 3600)
        self.assertEqual(SECONDS_PER_DAY, 86400)

        # Length
        self.assertEqual(MM_PER_CM, 10)
        self.assertEqual(CM_PER_M, 100)
        self.assertEqual(MM_PER_M, 1000)
        self.assertEqual(MM_PER_INCH, 25.4)
        self.assertEqual(CM_PER_INCH, 2.54)
        self.assertEqual(M_PER_INCH, 0.0254)

        # Weight
        self.assertEqual(LB_PER_KG, 2.205)
        self.assertEqual(LB_PER_TON, 2000)
        self.assertEqual(OZ_PER_LB, 16)
        self.assertEqual(OZ_PER_KG, 35.28)
        self.assertEqual(KG_PER_LB, 0.454)
        self.assertEqual(KG_PER_TONNE, 1000)

        # ASCII
        self.assertEqual(ASCII_CHARACTER, 0)
        self.assertEqual(ASCII_DESCRIPTION, 4)


class TestFunctions(LocalTestCase):

    def test__ascii_lookup(self):
        self.assertEqual(ascii_lookup("$", ASCII_CHARACTER), "$")
        self.assertEqual(ascii_lookup("$", ASCII_FRIENDLY_CODE), "")
        self.assertEqual(ascii_lookup("$", ASCII_NUMERICAL_CODE), "&#36;")
        self.assertEqual(ascii_lookup("$", ASCII_HEX_CODE), "&#x24;")
        self.assertEqual(ascii_lookup("$", ASCII_DESCRIPTION), "Dollar sign")


if __name__ == '__main__':
    unittest.main()
