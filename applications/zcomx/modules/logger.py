#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
logger.py

Classes and functions related to logging.
"""
import logging


def set_cli_logging(
        logger,
        verbose,
        more_verbose=False,
        quiet=False,
        with_time=False):
    """Set logging for cli scripts.

    Args:
        logger: logging.Logger instance
        verbose: bool or int
            if bool, if True, level is set to logging.INFO
            if int,
                verbose = 0         logging.WARN
                verbose = 1         logging.INFO
                verbose = 2         logging.DEBUG
        more_verbose: if True, level is set to logging.DEBUG
            This is ignored if verbose is int.
        quiet: if True, level is set to logging.critical
        with_time: if True formatter includes a timestamp.

    Notes:
        Order of precedence
            more_verbose            highest
            verbose
            quiet                   lowest
    """
    do_verbose = verbose
    do_more_verbose = more_verbose

    if verbose is not None and not isinstance(verbose, bool):
        do_verbose = verbose > 0
        do_more_verbose = verbose > 1

    level = logging.DEBUG if do_more_verbose \
        else logging.INFO if do_verbose \
        else logging.CRITICAL if quiet \
        else logging.WARNING

    formats = {
        'default': '%(levelname)s - %(message)s',
        'with_time': '%(asctime)s - %(levelname)s - %(message)s',
    }

    format_key = 'with_time' if with_time else 'default'
    formatter = logging.Formatter(formats[format_key])
    set_stream_logging(logger, level, formatter)


def set_stream_logging(logger, level, formatter):
    """Set stream logging

    Args:
        logger: logging.Logger instance
        level: integer, logging level, eg logging.INFO
        formatter: logging.Formatter instance
    """
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
