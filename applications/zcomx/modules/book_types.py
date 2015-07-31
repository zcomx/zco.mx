#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book types.
"""
from gluon import *
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.utils import ClassFactory


class BookType(Record):
    """Class representing a book_type record"""
    db_table = 'book_type'
    class_factory = ClassFactory('class_factory_id')

    @classmethod
    def by_name(cls, name):
        """Create instance from the given name.

        Args:
            name: str, book_type.name value.

        Returns:
            BookType subclass instance
        """
        book_type = cls.from_key({'name': name})
        return cls.class_factory(
            book_type.name,
            book_type.as_dict()
        )

    @classmethod
    def classified_from_id(cls, record_id):
        """Create instance of appropriate class from record id.

        Like Record.from_id but converts BookType instance to appropriate
        subclass instance

        Args:
            record_id: integer, id of record

        Returns:
            BookType subclass instance
        """
        book_type = cls.from_id(record_id)
        return cls.class_factory(
            book_type.name,
            book_type.as_dict()
        )

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


@BookType.class_factory.register
class MiniSeriesType(BookType):
    """Class representing a mini-series book type"""
    class_factory_id = 'mini-series'

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


@BookType.class_factory.register
class OneShotType(BookType):
    """Class representing a one-shot book type"""
    class_factory_id = 'one-shot'

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


@BookType.class_factory.register
class OngoingType(BookType):
    """Class representing an ongoing book type"""
    class_factory_id = 'ongoing'

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
