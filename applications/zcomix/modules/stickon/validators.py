#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
stickon/validators.py

Classes extending functionality of gluon/validators.py.

"""
import logging
from gluon.validators import \
    IS_NOT_IN_DB, \
    translate

# C0103: Invalid name
# pylint: disable=C0103

LOG = logging.getLogger('app')


class IS_NOT_IN_DB_ANYCASE(IS_NOT_IN_DB):
    """Class representing a validator similar to IS_NOT_IN_DB except matching
        is explicitly case insensitive. IN_NOT_IN_DB is not explicitly case
        sensitive, it depends on the db.
    """
    def __init__(
        self,
        dbset,
        field,
        error_message='value already in database or empty',
        allowed_override=None,
        ignore_common_filters=False,
    ):
        if allowed_override is None:
            allowed_override = []
        IS_NOT_IN_DB.__init__(
            self,
            dbset,
            field,
            error_message,
            allowed_override,
            ignore_common_filters
        )

    def __call__(self, value):
        if isinstance(value,unicode):
            value = value.encode('utf8')
        else:
            value = str(value)
        if not value.strip():
            return (value, translate(self.error_message))
        if value in self.allowed_override:
            return (value, None)
        (tablename, fieldname) = str(self.field).split('.')
        table = self.dbset.db[tablename]
        field = table[fieldname]
        # custom \\
        # subset = self.dbset(field == value,
        #                    ignore_common_filters=self.ignore_common_filters)
        subset = self.dbset(field.lower().like(value),
                            ignore_common_filters=self.ignore_common_filters)
        # custom ///

        id = self.record_id
        if isinstance(id, dict):
            fields = [table[f] for f in id]
            row = subset.select(*fields, **dict(limitby=(0, 1), orderby_on_limitby=False)).first()
            if row and any(str(row[f]) != str(id[f]) for f in id):
                return (value, translate(self.error_message))
        else:
            row = subset.select(table._id, field, limitby=(0, 1), orderby_on_limitby=False).first()
            if row and str(row.id) != str(id):
                return (value, translate(self.error_message))
        return (value, None)


class IS_NOT_IN_DB_SCRUBBED(IS_NOT_IN_DB_ANYCASE):
    """Class representing a validator similar to IS_NOT_IN_DB_ANYCASE except the
        value is scrubbed by a callback function before it is looked up in
        the database. If scrub_callback is None or not callable, the validator
        behaves exactly like IS_NOT_IN_DB.
    """
    def __init__(
        self,
        dbset,
        field,
        error_message='value already in database or empty',
        allowed_override=None,
        ignore_common_filters=False,
        scrub_callback=None,
    ):
        if allowed_override is None:
            allowed_override = []
        IS_NOT_IN_DB_ANYCASE.__init__(
            self,
            dbset,
            field,
            error_message,
            allowed_override,
            ignore_common_filters
        )
        self.scrub_callback = scrub_callback

    def __call__(self, value):
        test_value = value
        if self.scrub_callback and callable(self.scrub_callback):
            test_value = self.scrub_callback(value)
        (unused_value, error) = IS_NOT_IN_DB_ANYCASE.__call__(self, test_value)
        return (value, error)
