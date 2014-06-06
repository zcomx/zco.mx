#!/usr/bin/python
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

    def __init__(self, raw):
        """Constructor

        Args:
            raw: string, the raw name of the file
        """
        self.raw = raw
        str.__init__(self, self.raw)

    def pre_scrub(self):
        """Overridable method to implement pre-scrub formatting."""
        return self.raw

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
    """Class representing a title filename. """
    # R0904 (too-many-public-methods): *Too many public methods (%%s/%%s)*
    # pylint: disable=R0904

    def __init__(self, raw):
        """Constructor

        Args:
            raw: string, the raw name of the file
        """
        FileName.__init__(self, raw)

    def pre_scrub(self):
        """Return the filename scrubbed.

        Return:
            string
        """
        # Replace colon wrapped in optional space with space hyphen space
        return re.sub(r'\s*:\s*', ':', self.raw).replace(':', ' - ')
