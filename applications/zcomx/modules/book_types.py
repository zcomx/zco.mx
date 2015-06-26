#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book types.
"""
import collections
from gluon import *
from applications.zcomx.modules.utils import \
    entity_to_row


class BaseBookType(object):
    """Base class representing a book type"""

    def __init__(self, name, description, sequence):
        """Constructor

        Args:
            name: string, the name of the book type
            description: string, the description of the book type
            sequence: integer, the order sequence of the book type
        """
        self.name = name
        self.description = description
        self.sequence = sequence

    def formatted_number(self, number, of_number):
        """Return the number of the book formatted.

        Args:
            number: integer, the book number
            of_number: integer, the number of books in a series

        Returns:
            string: formatted number, eg '01 (of 04)'
        """
        raise NotImplementedError()

    def is_series(self):
        """Return whether the book type is a series.

        Returns:
            True if the type is a series.
        """
        statuses = self.number_field_statuses()
        return statuses['number']

    @staticmethod
    def number_field_statuses():
        """Return the use statuses of number related fields."""
        raise NotImplementedError()


class MiniSeriesType(BaseBookType):
    """Class representing a mini-series book type"""

    def formatted_number(self, number, of_number):
        """Return the number of the book formatted.

        Args:
            number: integer, the book number
            of_number: integer, the number of books in a series

        Returns:
            string: formatted number, eg '01 (of 04)'
        """
        return '{num:02d} (of {of:02d})'.format(num=number, of=of_number)

    @staticmethod
    def number_field_statuses():
        """Return the use statuses of number related fields."""
        return {
            'number': True,
            'of_number': True,
        }


class OneShotType(BaseBookType):
    """Class representing a one-shot book type"""

    def formatted_number(self, number, of_number):
        """Return the number of the book formatted.

        Args:
            number: integer, the book number
            of_number: integer, the number of books in a series

        Returns:
            string: formatted number, eg '01 (of 04)'
        """
        return ''

    @staticmethod
    def number_field_statuses():
        """Return the use statuses of number related fields."""
        return {
            'number': False,
            'of_number': False,
        }


class OngoingType(BaseBookType):
    """Class representing an ongoing book type"""

    def formatted_number(self, number, of_number):
        """Return the number of the book formatted.

        Args:
            number: integer, the book number
            of_number: integer, the number of books in a series

        Returns:
            string: formatted number, eg '01 (of 04)'
        """
        return '{num:03d}'.format(num=number)

    @staticmethod
    def number_field_statuses():
        """Return the use statuses of number related fields."""
        return {
            'number': True,
            'of_number': False,
        }


CLASS_BY_NAME = collections.defaultdict(
    lambda: OneShotType,
    {
        'one-shot': OneShotType,
        'ongoing': OngoingType,
        'mini-series': MiniSeriesType,
    }
)


def by_name(type_name, default='one-shot'):
    """Factory to return Row instance representing book_type record with the
    given name.

    Args:
        type_name: string, name of book_type
        default: default book_type name if book_type record not found.
            If None and book_type record not found, raises LookupError.
    Returns:
        Row instance representing a book_type record
    """
    db = current.app.db
    query = (db.book_type.name == type_name)
    book_type = db(query).select().first()
    if not book_type and default is None:
        raise LookupError('Book type not found, name: {n}'.format(
            n=type_name))
    if not book_type:
        query = (db.book_type.name == default)
        book_type = db(query).select().first()
        if not book_type:
            raise LookupError('Book type not found, name: {n}'.format(
                n=default))
    return book_type


def from_id(book_type_id, default='one-shot'):
    """Factory to return a subclass instance associated with the book type id.

    Args:
        book_type_id: integer, id of book_type record
        default: default book_type name if book_type record not found.
            If None and book_type record not found, raises LookupError.
    Returns:
        BaseBookType subclass instance
    """
    db = current.app.db
    book_type = entity_to_row(db.book_type, book_type_id)
    if not book_type and default is None:
        raise LookupError('Book type not found, id: {i}'.format(
            i=book_type_id))
    if not book_type:
        query = (db.book_type.name == default)
        book_type = db(query).select().first()
        if not book_type:
            raise LookupError('Book type not found, name: {n}'.format(
                n=default))
    return CLASS_BY_NAME[book_type.name](
        book_type.name,
        book_type.description,
        book_type.sequence
    )
