#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to autocompletion.
"""
import functools
import json
import os
import shutil
from pydal.validators import urlify
from gluon import *
from applications.zcomx.modules.books import (
    Book,
    formatted_name as formatted_book_name,
)
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.shell_utils import TemporaryDirectory
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE


class BaseAutocompleter():
    """Base class representing a autocompleter"""

    def __init__(self, table, keyword=''):
        """Constructor

        Args:
            table: gluon.dal.Table instance, eg db.book
            keyword: string, keyword text to filter results on
        """
        self.table = table
        self.keyword = keyword

    def dump(self, output):
        """Dump search results to file.

        Args:
            output: string, name of output file.
        """
        items = self.search()
        with TemporaryDirectory() as tmp_dir:
            out_file = os.path.join(tmp_dir, 'output.json')
            with open(out_file, 'w', encoding='utf-8') as outfile:
                outfile.write(json.dumps(items))
            shutil.move(out_file, output)

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        queries = []
        if self.keyword:
            url_kw = urlify(self.keyword)
            queries.append((self.search_field().contains(url_kw)))
        return queries

    def formatted_value(self, record_id):
        """Return the formatted value for the record.

        Returns:
            string
        """
        return str(record_id)

    def id_field(self):
        """Table field to use for record id.

        Returns:
            gluon.dal.Field instance
        """
        return self.table['id']

    def left_join(self):
        """Dal expression to use for left join in results query.

        Returns:
            gluon.dal.Expr instance
        """
        return None

    def orderby(self):
        """Dal expression to use for ordering results.

        Returns:
            gluon.dal.Expr instance
        """
        return self.table['name_for_search']

    def row_to_json(self, row):
        """Return the row formatted for json.

        Args
            row: Row instance

        Returns:
            dict, {'id': <id>, 'table': <table>, 'value': <value>}
        """
        return {
            'id': row.id,
            'table': str(self.table),
            'value': self.formatted_value(row.id),
        }

    def search(self):
        """Return search results."""
        return [self.row_to_json(x) for x in self.search_rows()]

    def search_rows(self):
        """Return rows representing search results."""
        db = current.app.db
        queries = self.filters()
        query = functools.reduce(lambda x, y: x & y, queries) \
            if queries else None
        rows = db(query).select(
            self.id_field(),
            left=self.left_join(),
            orderby=self.orderby(),
            distinct=True,
        )
        return rows

    def search_field(self):
        """Table field to search for keyword.

        Returns:
            gluon.dal.Field instance
        """
        return self.table['name_for_search']


class BookAutocompleter(BaseAutocompleter):
    """Class representing a book autocompleter"""

    def __init__(self, keyword=''):
        db = current.app.db
        super().__init__(db.book, keyword=keyword)

    def filters(self):
        db = current.app.db
        queries = super().filters()
        queries.append((db.book.status == BOOK_STATUS_ACTIVE))
        return queries

    def formatted_value(self, record_id):
        book = Book.from_id(record_id)
        return formatted_book_name(book, include_publication_year=False)

    def orderby(self):
        return self.table['name']


class CreatorAutocompleter(BaseAutocompleter):
    """Class representing a creator autocompleter"""

    def __init__(self, keyword=''):
        db = current.app.db
        super().__init__(db.creator, keyword=keyword)

    def filters(self):
        db = current.app.db
        queries = []
        queries = super().filters()
        # Creators must have at least one book
        queries.append((db.book.id != None))
        return queries

    def formatted_value(self, record_id):
        creator = Creator.from_id(record_id)
        return creator.name

    def left_join(self):
        db = current.app.db
        return [db.book.on(db.book.creator_id == db.creator.id)]


def autocompleter_class(table):
    """Return BaseAutocompleter subclass for the table."""
    if table == 'book':
        return BookAutocompleter
    if table == 'creator':
        return CreatorAutocompleter
    return None
