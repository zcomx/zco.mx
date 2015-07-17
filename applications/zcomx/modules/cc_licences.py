#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to CC (Creative Commons) licences.
"""
import logging
from gluon import *

from applications.zcomx.modules.records import Record

LOG = logging.getLogger('app')


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
        db = current.app.db
        query = (db.cc_licence.code == code)
        cc_licence_id = db(query).select(db.cc_licence.id).first()
        return cls.from_id(cc_licence_id)

    @classmethod
    def default(cls):
        """Return the default CCLicence instance.

        Returns:
            CCLicence instance.
        """
        return cls.by_code(cls.default_code)
