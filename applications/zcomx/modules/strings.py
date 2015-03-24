#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

String classes and functions.
"""
import re
import string


def camelcase(text):
    """Convert text to camel case

    Notes:
        The algorithm sets the first letter of each word to uppercase.
        Existing uppercase letters are left unchanged.
        Words are split on whitespace.

    Args:
        text: string, text to convert

    Returns:
        string, converted text.
    """
    if text is None:
        return
    if not text:
        return text
    words = [x[0].upper() + x[1:] for x in text.split() if x]
    return ''.join(words)


def replace_punctuation(text, repl=' ', punctuation=None):
    """Replace all punctuation in text.

    Args:
        text: string, text to convert
        repl: string, each punctuation character is replaced with this
            string.
        punctuation: string of punctuation characters to replace.
            If None, string.punctuation is used.

    Returns:
        string, converted text.
    """
    if text is None:
        return
    if not text:
        return text
    if punctuation is None:
        punctuation = string.punctuation
    for char in punctuation:
        text = text.replace(char, repl)
    return text


def squeeze_whitespace(text):
    """Squeeze multiple whitespace in text to single whitespace.

    Args:
        text: string, text to convert

    Returns:
        string, converted text.
    """
    if text is None:
        return
    if not text:
        return text
    return re.sub(r'\s+', ' ', text)
