#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to unix files.
"""
import subprocess


class UnixFile(object):
    """Class representing a Unix file."""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, name of file including path.
        """
        self.name = name

    def file(self):
        """Return output of the unix 'file' command

        Returns:
            tuple: (output, errors)
        """
        p = subprocess.Popen(
            ['file', self.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return p.communicate()
