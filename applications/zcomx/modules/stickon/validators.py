#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
stickon/validators.py

Classes extending functionality of gluon/validators.py.

"""
import logging
from gluon.html import \
    DIV, \
    SPAN, \
    UL, \
    XML
from gluon.validators import \
    IS_NOT_IN_DB, \
    Validator, \
    translate

# C0103: Invalid name
# pylint: disable=C0103

LOG = logging.getLogger('app')


class IS_ALLOWED_CHARS(Validator):
    """Class representing a validator for text inputs that produces an error
    message if there are any characters in the set of not allowed.
    """
    def __init__(self, not_allowed=None, error_message='Invalid characters.'):
        """Constructor
        Args:
            not_allowed: sequence of individual characters or tuples of
                ('char', 'name') of characters that are not allowed.
                Characters are case sensitive. Eg the following all represent
                the same set of characters.
                    string: '@#$%^'
                    list: ['@', '#', '$', '%', '^']
                    tuples: [
                        ('@', 'at'),
                        ('#', 'number'),
                        ('$', 'dollar sign'),
                        ('%', 'percent'),
                        ('^', 'caret'),
                    ]

        """
        self.not_allowed = not_allowed or []
        self.error_message = error_message

    def __call__(self, value):
        found = []
        for c in self.not_allowed:
            if c[0] in value:
                found.append(c)
        if not found:
            return (value, None)

        list_items = []
        for c in found:
            if len(c) > 1:
                list_items.append(
                    '{char} ({name})'.format(char=c[0], name=c[1])
                )
            else:
                list_items.append(c)
        # Format error message.
        msg = ' '.join([
                self.error_message,
                'Please remove or replace the following characters:',
                ', '.join(list_items),
                ])
        return (value, msg)


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
        # W0622 (redefined-builtin): *Redefining built-in %%r*          # id
        # pylint: disable=W0622
        # W0212 : *Access to a protected member %%s of a client class*
        # pylint: disable=W0212

        if isinstance(value, unicode):
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
            row = subset.select(
                *fields,
                **dict(limitby=(0, 1), orderby_on_limitby=False)
            ).first()
            if row and any(str(row[f]) != str(id[f]) for f in id):
                # Do not translate so HTML can be included in error message
                # return (value, translate(self.error_message))
                return (value, self.error_message)
        else:
            row = subset.select(
                table._id,
                field,
                limitby=(0, 1),
                orderby_on_limitby=False
            ).first()
            if row and str(row.id) != str(id):
                # Do not translate so HTML can be included in error message
                # return (value, translate(self.error_message))
                return (value, self.error_message)
        return (value, None)


class IS_NOT_IN_DB_SCRUBBED(IS_NOT_IN_DB_ANYCASE):
    """Class representing a validator similar to IS_NOT_IN_DB_ANYCASE except
    the value is scrubbed by a callback function before it is looked up in the
    database. If scrub_callback is None or not callable, the validator behaves
    exactly like IS_NOT_IN_DB.
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