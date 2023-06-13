#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes related to custom argparse actions.
"""
import argparse


class CallbackAndExitAction(argparse.Action):
    """Class representing an argparse action that calls a callback func
    and then exits. All positional and optional parameters are ignored.

    Adapted from argparse.py class _HelpAction.
    """
    # pylint: disable=redefined-builtin
    def __init__(
            self,
            option_strings,
            dest=argparse.SUPPRESS,
            default=argparse.SUPPRESS,
            help=None,
            callback=None):
        self.callback = callback
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help
        )

    def __call__(self, parser, namespace, values, option_string=None):
        if self.callback and callable(self.callback):
            self.callback(parser, namespace, values, option_string)
        parser.exit()


class ListAction(CallbackAndExitAction):
    """Class representing an argparse action for a list option."""
    def __call__(self, parser, namespace, values, option_string=None):
        if self.callback and callable(self.callback):
            self.callback()
        parser.exit()


class ManPageAction(CallbackAndExitAction):
    """Class representing an argparse action for a man page option."""

    def __call__(self, parser, namespace, values, option_string=None):
        if self.callback and callable(self.callback):
            self.callback()
        parser.exit()
