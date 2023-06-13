#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for shared/modules/argparse/actions.py
"""
import argparse
import unittest
from applications.zcomx.modules.argparse.actions import (
    CallbackAndExitAction,
    ListAction,
    ManPageAction,
)
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring

CALL_COUNT = 0


class TestCallbackAndExitAction(LocalTestCase):

    def test____init__(self):
        action = CallbackAndExitAction(['a', '--foo'])
        self.assertTrue(action)

    def test____call__(self):
        # pylint: disable=global-variable-undefined

        def a_callback(parser, namespace, values, option_string):
            # pylint: disable=unused-argument
            # pylint: disable=global-statement
            global CALL_COUNT
            CALL_COUNT = CALL_COUNT + 1

        parser = argparse.ArgumentParser(prog='test_actions.py')

        parser.add_argument(
            'pos_arg',
            help='Display help and exit.',
        )

        parser.add_argument(
            '--opt-arg',
            action='store_true',
            help='Display help and exit.',
        )

        parser.add_argument(
            '--callback-and-exit',
            action=CallbackAndExitAction,
            callback=a_callback,
            help='Display help and exit.',
        )

        tests = [
            # (cli args, incr call_count)
            (['a'], False),
            (['a', '--opt-arg'], False),
            (['--callback-and-exit'], True),
            (['a', '--opt-arg', '--callback-and-exit'], True),
            (['--callback-and-exit', 'a', '--opt-arg'], True),
        ]
        for t in tests:
            cli_args, increment = t
            old_call_count = CALL_COUNT

            try:
                parser.parse_args(cli_args)
            except SystemExit:
                pass
            if increment:
                self.assertEqual(CALL_COUNT, old_call_count + 1)
            else:
                self.assertEqual(CALL_COUNT, old_call_count)


class TestListAction(LocalTestCase):

    def test____call__(self):
        # pylint: disable=global-statement
        global CALL_COUNT
        CALL_COUNT = 0

        def a_callback():
            global CALL_COUNT
            CALL_COUNT = CALL_COUNT + 1

        parser = argparse.ArgumentParser(prog='test_actions.py')

        parser.add_argument(
            '--list',
            action=ListAction,
            callback=a_callback,
            help='Display help and exit.',
        )

        try:
            parser.parse_args(['--list'])
        except SystemExit:
            pass
        else:
            self.fail('SystemExit not raised.')


class TestManPageAction(LocalTestCase):

    def test____call__(self):
        # pylint: disable=global-statement
        global CALL_COUNT
        CALL_COUNT = 0

        def a_callback():
            global CALL_COUNT
            CALL_COUNT = CALL_COUNT + 1

        parser = argparse.ArgumentParser(prog='test_actions.py')

        parser.add_argument(
            '--man',
            action=ManPageAction,
            callback=a_callback,
            help='Display help and exit.',
        )

        try:
            parser.parse_args(['--man'])
        except SystemExit:
            pass
        else:
            self.fail('SystemExit not raised.')


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
