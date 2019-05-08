#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
stickon/validators.py

Classes extending functionality of gluon/validators.py.
"""
import urlparse
from gluon.sqlhtml import safe_float, safe_int
from gluon.validators import (
    IS_MATCH,
    IS_NOT_IN_DB,
    IS_URL,
    Validator,
    ValidationError,
)

# C0103: Invalid name
# pylint: disable=C0103


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

    def validate(self, value):
        """Validate."""
        found = []
        for c in self.not_allowed:
            if c[0] in value:
                found.append(c)
        if not found:
            return value

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
        raise ValidationError(self.translator(msg))


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
            ignore_common_filters=False):
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

    def validate(self, value):
        """Validate"""
        # W0622 (redefined-builtin): *Redefining built-in %%r*          # id
        # pylint: disable=W0622
        # W0212 : *Access to a protected member %%s of a client class*
        # pylint: disable=W0212

        if isinstance(value, unicode):
            value = value.encode('utf8')
        else:
            value = str(value)
        if not value.strip():
            raise ValidationError(self.translator(self.error_message))
        if value in self.allowed_override:
            return value
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
                raise ValidationError(self.error_message)
        else:
            row = subset.select(
                table._id,
                field,
                limitby=(0, 1),
                orderby_on_limitby=False
            ).first()
            if row and str(row.id) != str(id):
                # Do not translate so HTML can be included in error message
                raise ValidationError(self.error_message)
        return value


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
            scrub_callback=None):
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

    def validate(self, value):
        test_value = value
        if self.scrub_callback and callable(self.scrub_callback):
            test_value = self.scrub_callback(value)
        return IS_NOT_IN_DB_ANYCASE.validate(self, test_value)


class IS_TWITTER_HANDLE(IS_MATCH):
    """Class representing a validator for twitter handles.
    """
    def __init__(
            self,
            error_message=None):
        """Constructor
        Args:
            error_message: see IS_MATCH
        """
        # twitter handles: @username
        # * Starts with '@'
        # * from 1 to 15 alphanumeric characters.
        if error_message is None:
            error_message = 'Enter a valid twitter handle, eg @username'
        IS_MATCH.__init__(self, r'^@[\w]{1,15}$', error_message)


class IS_URL_FOR_DOMAIN(IS_URL):
    """Class representing a validator like IS_URL but rejects a URL string if
    it is not from a specific domain.
    """
    def __init__(
            self,
            domain,
            error_message=None,
            mode='http',
            allowed_schemes=None,
            prepend_scheme='http'):
        """Constructor
        Args:
            domain: string, eg example.com
            error_message: see IS_URL
            mode: see IS_URL
            allowed_schemes: see IS_URL
            prepend_scheme: see IS_URL

        """
        if error_message is None:
            error_message = 'Enter a valid {domain} URL'.format(domain=domain)
        IS_URL.__init__(
            self,
            error_message=error_message,
            mode=mode,
            allowed_schemes=allowed_schemes,
            prepend_scheme=prepend_scheme,
        )
        self.domain = domain

    def validate(self, value):
        """Validate."""
        try:
            result = IS_URL().validate(value)
        except ValidationError:
            raise ValidationError(self.translator(self.error_message))

        o = urlparse.urlparse(result)
        if not o.hostname:
            raise ValidationError(self.translator(self.error_message))
        if not o.hostname == self.domain and \
                not o.hostname.endswith('.{d}'.format(d=self.domain)):
            raise ValidationError(self.translator(self.error_message))
        return result


def as_per_type(table, data):
    """Return data with all values set as per the field type.
    Useful for converting request.vars values.

    Notes: If data is invalid for a specific field, it is left as is.


    Args:
        table: gluon.dal.Table instance
        data: dict of data representing a record from table

    Returns:
        dict: dict of data representing a record from table
    """
    for field, value in data.items():
        if field not in table.fields:
            continue
        if value is None:
            continue
        if table[field].type == 'integer':
            data[field] = safe_int(data[field])
        elif table[field].type == 'boolean':
            if value in ['T', 'True', True]:
                data[field] = True
            elif value in ['F', 'False', False]:
                data[field] = False
        elif table[field].type == 'double':
            data[field] = safe_float(data[field])
    return data
