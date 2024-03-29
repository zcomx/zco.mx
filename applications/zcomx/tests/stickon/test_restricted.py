#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for modules/stickon/restricted.py
"""
import os
import re
import unittest
from applications.zcomx.modules.stickon.restricted import log_ticket
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.tests.helpers import WebTestCase
# pylint: disable=missing-docstring


class DubLogger():
    def __init__(self):
        self.warns = []
        self.errors = []

    @staticmethod
    def log(repo, *args):
        if not args:
            return
        if len(args) == 1:
            msg = args[0]
        else:
            msg = args[0] % tuple(args[1:])
        repo.append(msg)

    def error(self, *args):
        self.log(self.errors, *args)

    def warn(self, *args):
        self.log(self.warns, *args)


class TestFunctions(WebTestCase):

    def test__log_ticket(self):

        # Test variation on no ticket, should be handled gracefully
        log_ticket(None)

        tests = [
            # (ticket, expect)
            (None, None),
            ('zcomx', None),
            ('zcomx/_invalid_', None),
        ]
        for t in tests:
            self.assertEqual(log_ticket(t[0]), t[1])

        def get_files(path):
            """Return a list of files in a directory"""
            for unused_root, unused_dirs, files in os.walk(path):
                return files

        errors_path = os.path.join(request.folder, 'errors')
        error_files_bef = get_files(errors_path)

        # The next call will create an error ticket
        self.assertRaisesHTTPError(
            406,
            self.assertWebTest,
            '/errors/test_exception',
            match_page_key='/errors/index',
        )

        error_files_aft = get_files(errors_path)
        self.assertEqual(len(error_files_aft), len(error_files_bef) + 1)

        ticket_re = re.compile(
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.\d{4}-\d{2}-\d{2}.*$')

        ticket = None
        for filename in error_files_aft:
            if filename not in error_files_bef and ticket_re.match(filename):
                ticket = filename
                break

        if not ticket:
            self.fail('Ticket not found.')

        logger = DubLogger()
        log_ticket(ticket, logger=logger)
        self.assertTrue(len(logger.errors) > 8)
        expect_words = ['Traceback', 'SyntaxError']
        words_found_status = {}
        for word in expect_words:
            words_found_status[word] = False

        for error in logger.errors:
            for word in words_found_status:
                if error.startswith(word):
                    words_found_status[word] = True
        for status in words_found_status.values():
            self.assertTrue(status)

        # Cleanup
        new_files = set(error_files_aft).difference(set(error_files_bef))
        for new_file in new_files:
            filename = os.path.join(errors_path, new_file)
            if os.path.exists(filename):
                os.unlink(filename)


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
