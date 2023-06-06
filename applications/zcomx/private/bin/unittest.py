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
from unittest.main import TestProgram
from applications.zcomx.modules.tests.runner import (
    LocalTestCase,
    LocalTextTestRunner,
    count_diff,
)


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

    # Note: TestProgram has its own cli options parser.
    __unittest = True
    verbosity = 2

    if '--max-diff' in sys.argv:
        LocalTestCase.maxDiff = None
        sys.argv[:] = [x for x in sys.argv if x != '--max-diff']

    options = {}
    opt_args = {
        # cli option: option key
        '--frce': 'force',
        '--no-count': 'no_count',
        '--quick': 'quick',
        '--dump': 'dump',
    }
    for cli_opt, opt_key in opt_args.items():
        if cli_opt in sys.argv:
            options[opt_key] = True
            # Remove the option from sys.argv so it is not passed to
            # web2py.py.
            sys.argv[:] = [x for x in sys.argv if x != cli_opt]

    # pylint: disable=protected-access
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
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
