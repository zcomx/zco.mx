#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unittest wrapper. Allows unittest discovery in web2py.

# Normal unittest test
python -m unittest discover path/to/tests
python -m unittest path.to.test.module

# web2py
python web2py.py -S app -M -R path/to/unittest.py discover path/to/tests
python web2py.py -S app -M -R path/to/unittest.py path.to.test.module

"""
import logging
import sys
import traceback
# E0611: *No name %%r in module %%r*
# pylint: disable=E0611
# F0401: *Unable to import %%r*
# pylint: disable=F0401
from unittest.main import TestProgram, USAGE_AS_MAIN
from applications.zcomx.modules.tests.runner import \
        LocalTestCase, \
        LocalTextTestRunner, \
        count_diff


@count_diff
def main():
    """Main processing."""

    # Set up logging so noise isn't printed to stdout.

    # Capture warnings printed to stdout, eg by MySQLdb
    logging.captureWarnings(True)

    # Replicate logging to local7
    formatter = logging.Formatter(
            fmt='%(name)s [%(levelname)s %(filename)s %(lineno)d] %(message)s')
    handler = logging.handlers.SysLogHandler(
        "/dev/log", logging.handlers.SysLogHandler.LOG_LOCAL7)
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    logger.addHandler(handler)

    # Note: TestProgam has its own cli options parser.
    __unittest = True
    TestProgram.USAGE = USAGE_AS_MAIN
    verbosity = 2

    if '--max-diff' in sys.argv:
        LocalTestCase.maxDiff = None
        sys.argv[:] = [x for x in sys.argv if x != '--max-diff']

    options = {}
    if '--force' in sys.argv:
        options['force'] = True
        sys.argv[:] = [x for x in sys.argv if x != '--force']
    if '--quick' in sys.argv:
        options['quick'] = True
        sys.argv[:] = [x for x in sys.argv if x != '--quick']
    if '--dump' in sys.argv:
        options['dump'] = True
        sys.argv[:] = [x for x in sys.argv if x != '--dump']

    # W0212: *Access to a protected member %%s of a client class*
    # pylint: disable=W0212
    LocalTestCase._opts.update(options)

    try:
        TestProgram(
                argv=sys.argv,
                module=None,
                testRunner=LocalTextTestRunner(verbosity=verbosity),
                verbosity=verbosity,
                )
    except AttributeError:
        # If a module produces an error on import, unittest traps the
        # ImportError exception and raises an AttributeError instead. The
        # message from the AttributeError isn't useful. It's the
        # ImportError message we want. Import the module again so
        # ImportError is raised with its message reported in all its glory.
        # (See mod 11898)
        __import__(sys.argv[-1])


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
