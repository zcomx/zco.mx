#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
logger.py

Classes and functions related to logging.

"""
import logging


def set_cli_logging(
        logger,
        verbose,
        more_verbose,
        quiet=False,
        with_time=False):
    """Set logging for cli scripts.

    Args:
        logger: logging.Logger instance
        verbose: if True, level is set to logging.INFO
        more_verbose: if True, level is set to logging.DEBUG
        quiet: if True, level is set to logging.critical
        with_time: if True formatter includes a timestamp.

    Notes:
        Order of precedence
            more_verbose            highest
            verbose
            quiet                   lowest
    """
    level = logging.DEBUG if more_verbose \
        else logging.INFO if verbose \
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
