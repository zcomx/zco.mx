#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Class and functions relatedo database records.
"""
import traceback
from gluon import *
from pydal.objects import Row
from functools import reduce

LOG = current.app.logger


class Record(Row):
    """Base class representing a database record."""

    db_table = None

    def __init__(self, *args, **kwargs):
        """Initializer"""
        Row.__init__(self, *args, **kwargs)

    def as_one(self, record_class, key_fields=None):
        """Return a Record instance representing a referenced attribute of the
        record.

        Args:
            record_class: Record subclass, the class of the referenced
                attribute.
            key_fields: dict of field pairings
                Eg {field of record_class: field of self}
                If None, {'id': <db_table>_id} where db_table is
                record_class.db_table
        """
        if not key_fields:
            key_fields = {'id': '{t}_id'.format(t=record_class.db_table)}
        key = {}
        for record_field, self_field in key_fields.items():
            key[record_field] = self[self_field]
        return record_class.from_key(key)

    def delete(self):
        """Delete the record from the db"""
        db = current.app.db
        db(db[self.db_table].id == self.id).delete()
        db.commit()

    def delete_record(self):
        """DEPRECATED use delete()."""
        for line in traceback.format_stack():
            LOG.error(line)
        LOG.error('Record.delete_record called')
        return self.delete()

    @classmethod
    def from_add(cls, data, validate=True):
        """Add a db record from the given data and return the instance
        associateted with it.

        Args:
            data: dict, {field: value, ...}
            validate: if True, data is validated before adding.

        Returns:
            cls instance
        """
        record_id = 0
        db = current.app.db
        if validate:
            ret = db[cls.db_table].validate_and_insert(**data)
            db.commit()
            if ret.errors:
                msg = ', '.join([
                    '{k}: {v}'.format(k=k, v=v)
                    for k, v in list(ret.errors.items())
                ])
                raise SyntaxError(msg)
            record_id = ret.id
        else:
            record_id = db[cls.db_table].insert(**data)
            db.commit()
        return cls.from_id(record_id)

    @classmethod
    def from_id(cls, record_id):
        """Create instance from record id.

        Args:
            record_id: integer, id of record

        Returns:
            cls instance
        """
        try:
            record_id = int(record_id)
        except (TypeError, ValueError) as err:
            raise LookupError('Record not found, table {t}, id {i}'.format(
                t=cls.db_table, i=record_id))
        db = current.app.db
        query = (db[cls.db_table].id == record_id)
        record = db(query).select(limitby=(0, 1)).first()
        if not record:
            raise LookupError('Record not found, table {t}, id {i}'.format(
                t=cls.db_table, i=record_id))
        return cls(record.as_dict())

    @classmethod
    def from_key(cls, key):
        """Create instance from key

        Args:
            key: dict, {field: value, ...}

        Returns:
            cls instance
        """
        db = current.app.db
        queries = []
        for k, v in key.items():
            queries.append((db[cls.db_table][k] == v))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        return cls.from_query(query)

    @classmethod
    def from_query(cls, query):
        """Create instance from query

        Args:
            query: pydal.objects.Expression instance.

        Returns:
            cls instance
        """
        db = current.app.db
        record = db(query).select(limitby=(0, 1)).first()
        if not record:
            raise LookupError('Record not found, table {t}, query {q}'.format(
                t=cls.db_table, q=query))
        return cls(record.as_dict())

    @classmethod
    def from_updated(cls, record, data, validate=True):
        """Update a db record and return a instance representing the
        updated record.

        Args:
            record: Record (or subclass) instance
            data: dict, {field: value, ...}
            validate: if True, data is validated before updating.

        Returns:
            cls instance

        Raises:
            SyntaxError if validate=True and data is invalid.
        """
        if not record.id:
            msg = 'Unable to update record with out id.'
            raise SyntaxError(msg)

        db = current.app.db
        query = (db[record.db_table].id == record.id)
        if validate:
            validate_data = dict(data)
            if 'id' not in validate_data:
                validate_data['id'] = record.id
            ret = db(query).validate_and_update(**validate_data)
            db.commit()
            if ret.errors:
                msg = ', '.join([
                    '{k}: {v}'.format(k=k, v=v)
                    for k, v in list(ret.errors.items())
                ])
                raise SyntaxError(msg)
        else:
            db(query).update(**data)
            db.commit()
        return cls.from_id(record.id)

    def update_record(self, **data):
        """DEPRECATED do not use. Use from_updated()."""
        for line in traceback.format_stack():
            LOG.error(line)
        LOG.error('Record.update_record called')
        db = current.app.db
        db(db[self.db_table].id == self.id).update(**data)
        db.commit()


class Records(object):
    """Class representing a list of Record instances"""

    def __init__(self, records):
        """Initializer

        Args:
            records: list, list of Record instances
        """
        self.records = records

    def __getitem__(self, i):
        """Permits access of records using self[key] where key is integer or
        slice.
        """
        return self.records[i]

    def __iter__(self):
        """Permits the object to be used as an iterator."""
        for obj in self.records:
            yield obj

    def __len__(self):
        """Return length of object."""
        return len(self.records)

    def __bool__(self):
        """Return truth value of object."""
        if len(self.records):
            return True
        return False

    def first(self):
        """Return the first of the records."""
        if not self.records:
            return None
        return self.records[0]

    @classmethod
    def from_key(cls, record_class, key, orderby=None, limitby=None):
        """Create instance from key

        Args:
            records_class: Record subclass.
            key: dict, {field: value, ...}
            orderby: orderby expression, see select()
            limitby: limitby expression, see seelct()

        Returns:
            cls instance
        """
        db = current.app.db
        queries = []
        for k, v in key.items():
            queries.append((db[record_class.db_table][k] == v))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        return cls.from_query(record_class, query, orderby=orderby, limitby=limitby)

    @classmethod
    def from_query(cls, record_class, query, orderby=None, limitby=None):
        """Create instance from query

        Args:
            records_class: Record subclass.
            query: pydal.objects.Expression instance.
            orderby: orderby expression, see select()
            limitby: limitby expression, see seelct()

        Returns:
            cls instance
        """
        db = current.app.db
        records = []
        for r in db(query).select(orderby=orderby, limitby=limitby):
            record = record_class(r.as_dict())
            records.append(record)
        return cls(records)
