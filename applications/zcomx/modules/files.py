#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Utilty classes and functions.
"""
import re


class FileName(str):
    """Class representing a filename"""
    # R0904 (too-many-public-methods): *Too many public methods (%%s/%%s)*
    # pylint: disable=R0904

    allowed_in_inputs = [
        # ('char', 'name')
        ('?', 'question mark'),
        (':', 'colon'),
        ('"', 'double quote'),
    ]

    not_allowed_in_inputs = [
        # ('char', 'name')
        (r'/', 'slash'),
        ('\\', 'backslash'),
        ('%', 'percent'),
        ('*', 'asterisk'),
        ('|', 'pipe'),
        ('<', 'less than'),
        ('>', 'greater than'),
    ]

    invalid_chars = allowed_in_inputs + not_allowed_in_inputs

    def pre_scrub(self):
        """Overridable method to implement pre-scrub formatting."""
        return self

    def scrubbed(self):
        """Return the filename scrubbed.

        Return:
            string
        """
        clean = self.pre_scrub()
        # Characters reserved and not allowed in filenames
        # http://en.wikipedia.org/wiki/Filenames#Reserved_characters_and_words
        return ''.join(
            c for c in clean if c not in [x[0] for x in self.invalid_chars]
        ).strip()


class TitleFileName(FileName):
    """Class representing a title filename.

    Differences from FileName:
    * Colons are replaced with a spaced hyphen.
        Eg Bubbles: A Comic Odyssey => Bubbles - A Comic Odyssey
    """
    # R0904 (too-many-public-methods): *Too many public methods (%%s/%%s)*
    # pylint: disable=R0904

    def pre_scrub(self):
        """Return the filename scrubbed.

        Return:
            string
        """
        # Replace colon wrapped in optional space with space hyphen space
        return re.sub(r'\s*:\s*', ':', self).replace(':', ' - ')


def for_file(text):
    """Convenience function to convert text so it is suitable for a file name.

    Args:
        text: string, text to convert

    Returns:
        string
    """
    return FileName(text).scrubbed()


def for_title_file(text):
    """Convenience function to convert text so it is suitable for a title file
    name.

    Args:
        text: string, text to convert

    Returns:
        string
    """
    return TitleFileName(text).scrubbed()
