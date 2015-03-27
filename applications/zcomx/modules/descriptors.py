#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to descriptors.
"""
import logging
from gluon import *

_GLOBALS = {}
LOG = logging.getLogger('app')


class Bank(object):
    """A data descriptor bank."""

    def __init__(self, vault, key, init_val=None):
        self.vault = vault
        self.key = key
        self.vault[self.key] = init_val

    def __get__(self, obj, objtype):
        LOG.debug('FIXME Bank __get__ self.key: %s', self.key)
        return self.vault[self.key]

    def __set__(self, obj, value):
        LOG.debug('FIXME Bank __set__ self.key: %s', self.key)
        LOG.debug('FIXME Bank __set__ value: %s', value)
        self.vault[self.key] = value

    def __delete__(self, obj):
        self.vault[self.key] = None


class ReadOnlyBank(Bank):
    """Read only bank."""

    def __set__(self, obj, value):
        raise AttributeError('Unable to set read only variable.')

    def __delete__(self, obj):
        raise AttributeError('Unable to delete read only variable.')


class GlobalBank(ReadOnlyBank):
    """A global variable bank."""

    def __init__(self, key, init_val=None):
        super(GlobalBank, self).__init__(_GLOBALS, key, init_val=init_val)


class SessionBank(Bank):
    """A session variable bank."""

    def __init__(self, key, init_val=None):
        if current.session.zco is None:
            LOG.debug('FIXME initializing current.session.zco')
            current.session.zco = {}
        super(SessionBank, self).__init__(
            current.session.zco, key, init_val=init_val)
