#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Classes and functions related to names.
"""
from pydal.validators import urlify
from applications.zcomx.modules.files import \
    for_file, \
    for_title_file
from applications.zcomx.modules.strings import \
    camelcase, \
    replace_punctuation, \
    squeeze_whitespace


class BaseName(object):
    """Base class representing a name"""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, the name text
        """
        self.name = name

    def for_file(self):
        """Return the name suitable for file names."""
        raise NotImplementedError()

    def for_search(self):
        """Return the name suitable for use in search matching."""
        if self.name is None:
            return
        return urlify(self.name)

    def for_url(self):
        """Return the name suitable for use in urls."""
        if self.name is None:
            return
        if isinstance(self.name, bytes):
            name = self.name.decode('utf-8')
        else:
            name = self.name
        # Remove apostrophes
        # Otherwise "Fred's Smith" becomes 'FredSSmith' not 'FredsSmith'
        name = replace_punctuation(name, repl='', punctuation="""'""")
        # Replace punctuation with space
        name = replace_punctuation(name)
        name = squeeze_whitespace(name)
        name = camelcase(name)
        return name


class BookName(BaseName):
    """Class representing a book name"""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, the name text
        """
        BaseName.__init__(self, name)

    def for_file(self):
        if self.name is None:
            return
        name = squeeze_whitespace(self.name)
        return for_title_file(name)


class BookNumber(BookName):
    """Class representing a book number"""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, the book number as text, eg '01 (of 04)'
                Eg. as returned by BookType.formatted_number
        """
        BookName.__init__(self, name)

    def for_url(self):
        return BookName.for_url(self).lower()


class BookTitle(object):
    """Class representing a book title.

    A book title is a string representing the book name and number.
    Eg:   'My Book - 01 (of 04)'
    """

    def __init__(self, book_name, book_number):
        """Constructor

        Args:
            book_name: BookName instance
            book_number: BookNumber instance
        """
        self.book_name = book_name
        self.book_number = book_number

    def for_file(self):
        """Return the book title suitable for file names."""
        return ' '.join([
            self.book_name.for_file(),
            self.book_number.for_file(),
        ]).strip()

    def for_search(self):
        """Return the book title suitable for use in search matching."""
        return '-'.join([
            self.book_name.for_search(),
            self.book_number.for_search(),
        ]).strip('-')

    def for_url(self):
        """Return the book title suitable for use in urls."""
        return '-'.join([
            self.book_name.for_url(),
            self.book_number.for_url(),
        ]).strip('-')


class CreatorName(BaseName):
    """Class representing a creator name"""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, the name text
        """
        BaseName.__init__(self, name)

    def for_file(self):
        """Return the name suitable for file names."""
        if self.name is None:
            return
        name = self.name
        # Remove apostrophes
        # Otherwise "Fred's Smith" becomes 'FredSSmith' not 'FredsSmith'
        name = replace_punctuation(name, repl='', punctuation="""'""")
        # Replace punctuation with space
        name = replace_punctuation(name)
        name = squeeze_whitespace(name)
        name = camelcase(name)
        return for_file(name)


def names(name_instance, fields=None):
    """Return of dict of name variations for the name class.

    Args:
        name_instance: BaseName subclass instance
        fields: list, limit the returned dict to include only elements whose
            keys are in this list.

    Returns:
        dict, example
            {
                'name_for_file': 'File Name',
                'name_for_search': 'Search Name',
                'name_for_url': 'Url Name',
            }
    """
    name_dict = {
        'name_for_file': name_instance.for_file(),
        'name_for_search': name_instance.for_search(),
        'name_for_url': name_instance.for_url(),
    }
    if fields is not None:
        name_dict = dict(
            [(x, name_dict[x]) for x in list(name_dict.keys()) if x in fields])
    return name_dict
