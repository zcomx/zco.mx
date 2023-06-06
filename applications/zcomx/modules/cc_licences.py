#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to CC (Creative Commons) licences.
"""
from applications.zcomx.modules.records import Record


class CCLicence(Record):
    """Class representing a cc_licence record."""
    db_table = 'cc_licence'
    default_code = 'All Rights Reserved'

    @classmethod
    def by_code(cls, code):
        """Return a CCLicence instance for the code.

        Args:
            code: string, cc_licence.code

        Returns:
            CCLicence instance.
        """
        return cls.from_key({'code': code})

    @classmethod
    def default(cls):
        """Return the default CCLicence instance.

        Returns:
            CCLicence instance.
        """
        return cls.by_code(cls.default_code)
