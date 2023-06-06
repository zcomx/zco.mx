#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_logger.py

Test suite for zcomx/modules/logger.py
"""
import logging
import unittest
from gluon import *
from applications.zcomx.modules.logger import (
    set_cli_logging,
    set_stream_logging,
)
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestFunctions(LocalTestCase):

    def test__set_cli_logging(self):
        logger = current.app.logger

        # Test: verbose and more_verbose
        tests = [
            # (verbose, more_verbose, quiet, expect)
            (False, False, False, logging.WARNING),
            (False, True, False, logging.DEBUG),
            (True, False, False, logging.INFO),
            (True, True, False, logging.DEBUG),
            (False, False, True, logging.CRITICAL),
            (False, True, True, logging.DEBUG),
            (True, False, True, logging.INFO),
            (True, True, True, logging.DEBUG),
        ]

        for t in tests:
            self.assertEqual(len(logger.handlers), 0)
            set_cli_logging(logger, t[0], t[1], quiet=t[2])
            self.assertEqual(len(logger.handlers), 1)
            handler = logger.handlers[0]
            self.assertEqual(handler.level, t[3])
            logger.removeHandler(handler)
            self.assertEqual(len(logger.handlers), 0)

        formats = {
            'default': '%(levelname)s - %(message)s',
            'with_time': '%(asctime)s - %(levelname)s - %(message)s',
        }

        # Test: with_time
        tests = [
            # (with_time, expect)
            (False, formats['default']),
            (True, formats['with_time']),
        ]

        for t in tests:
            set_cli_logging(logger, True, True, with_time=t[0])
            handler = logger.handlers[0]
            formatter = handler.formatter
            # pylint: disable=protected-access
            self.assertEqual(formatter._fmt, t[1])
            logger.removeHandler(handler)

    def test__set_stream_logging(self):
        logger = current.app.logger
        self.assertEqual(len(logger.handlers), 0)
        fmt = '_test_ %(message)s'
        formatter = logging.Formatter(fmt)
        set_stream_logging(logger, logging.DEBUG, formatter)

        self.assertEqual(len(logger.handlers), 1)
        # pylint: disable=protected-access
        self.assertEqual(logger.handlers[0].formatter._fmt, fmt)
        self.assertEqual(logger.handlers[0].level, logging.DEBUG)

        # cleanup
        logger.removeHandler(logger.handlers[0])


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
