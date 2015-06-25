#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for modules/stickon/restricted.py

"""
import unittest
from applications.zcomx.modules.stickon.restricted import log_ticket
from applications.zcomx.modules.tests.runner import LocalTestCase


# R0904: *Too many public methods (%%s/%%s)*
# pylint: disable=R0904
# C0111: *Missing docstring*
# pylint: disable=C0111


class TestFunctions(LocalTestCase):

    def test__log_ticket(self):
        # This method is not practically testable.

        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201

        # Test variation on no ticket, should be handled gracefully
        log_ticket(None)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
