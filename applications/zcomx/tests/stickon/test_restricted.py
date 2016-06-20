#!/usr/bin/python
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


# R0904: *Too many public methods (%%s/%%s)*
# pylint: disable=R0904
# C0111: *Missing docstring*
# pylint: disable=C0111

class DubLogger(object):
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
        # This method is not practically testable.

        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201

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

        # This will create a ticket
        errors_path = os.path.join(request.folder, 'errors')
        errors_before = os.listdir(errors_path)
        self.assertWebTest(
            '/errors/test_exception', match_page_key='/errors/index')
        errors_after = os.listdir(errors_path)
        self.assertEqual(len(errors_after), len(errors_before) + 1)

        ticket_re = re.compile(
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.\d{4}-\d{2}-\d{2}.*$')

        ticket = None
        for unused_root, unused_dirs, files in os.walk(errors_path):
            for filename in files:
                if ticket_re.match(filename):
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
            for word in words_found_status.keys():
                if error.startswith(word):
                    words_found_status[word] = True
        for word in words_found_status.keys():
            self.assertTrue(words_found_status[word])

        # Cleanup
        new_files = set(errors_after).difference(set(errors_before))
        for new_file in new_files:
            filename = os.path.join(errors_path, new_file)
            if os.path.exists(filename):
                os.unlink(filename)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
