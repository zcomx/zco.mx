#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Test suite for modules/stickon/sqlhtml.py

"""
import unittest
from bs4 import BeautifulSoup
from gluon.sqlhtml import StringWidget
from applications.zcomx.modules.stickon.sqlhtml import (
    InputWidget,
    LocalSQLFORM,
    formstyle_bootstrap3_custom,
    formstyle_bootstrap3_login,
    make_grid_class,
    search_fields_grid
)

from applications.zcomx.modules.tests.runner import LocalTestCase


# R0904: *Too many public methods (%%s/%%s)*
# pylint: disable=R0904
# C0111: *Missing docstring*
# pylint: disable=C0111


class TestInputWidget(LocalTestCase):

    def test____init__(self):
        widget = InputWidget()
        self.assertTrue(widget)

    def test__widget(self):
        field = db.book.name
        value = '_some_fake_value__'

        widget = InputWidget()
        soup = as_soup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        # Example:
        # <input class="generic-widget" id="account_number" name="number"
        #   type="text" value="_some_fake_value__" />
        self.assertEqual(w_input['class'], ['generic-widget'])
        self.assertEqual(w_input['id'], 'book_name')
        self.assertEqual(w_input['name'], 'name')
        self.assertEqual(w_input['type'], 'text')
        self.assertEqual(w_input['value'], value)

        widget = InputWidget(
            attributes=dict(_type='hidden', _id='my_fake_id'),
            class_extra='id_widget'
        )
        soup = as_soup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        self.assertEqual(w_input['class'], ['generic-widget', 'id_widget'])
        self.assertEqual(w_input['id'], 'my_fake_id')
        self.assertEqual(w_input['name'], 'name')
        self.assertEqual(w_input['type'], 'hidden')
        self.assertEqual(w_input['value'], value)

        widget = InputWidget(attributes=dict(_type='submit'))
        soup = as_soup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        self.assertEqual(w_input['class'], ['generic-widget'])
        self.assertEqual(w_input['id'], 'book_name')
        self.assertEqual(w_input['name'], 'name')
        self.assertEqual(w_input['type'], 'submit')
        self.assertEqual(w_input['value'], value)


class TestLocalSQLFORM(LocalTestCase):

    def test_parent___init__(self):
        form = LocalSQLFORM(db.book_page)
        self.assertTrue(form)

    def test__grid(self):
        # No field_id should error.
        self.assertRaises(
            LookupError, LocalSQLFORM(db.book_page).grid, db.book_page)

        grid = LocalSQLFORM(db.book_page).grid(
            db.book_page, field_id=db.book_page.id)
        soup = as_soup(str(grid))
        # <div class="web2py_grid grid_widget">...</div>
        div = soup.find('div', {'class': 'web2py_grid '})
        self.assertTrue(div)


class TestLocalSQLFORMExtender(LocalTestCase):

    def test____new__(self):
        pass    # Test for LocalSQLFORM and make_grid_class test this


class TestFunctions(LocalTestCase):

    _table = None
    _fields = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._table = db.creator
        cls._fields = [
            (
                'creator.email',
                db.creator.email.label,
                StringWidget.widget(db.creator.email, 'username@gmail.com'),
                db.creator.email.comment
            ),
            (
                'creator.paypal_email',
                db.creator.paypal_email.label,
                StringWidget.widget(
                    db.creator.paypal_email, 'paypal.username@gmail.com'),
                db.creator.paypal_email.comment
            ),
        ]

    def test__formstyle_bootstrap3_custom(self):
        form = LocalSQLFORM(self._table)
        bootstrap_form = formstyle_bootstrap3_custom(form, self._fields)
        soup = as_soup(str(bootstrap_form))
        fieldset = soup.find('fieldset')
        div = fieldset.div.div
        self.assertEqual(div['class'], ['col-sm-6', 'col-lg-4'])

    def test__formstyle_bootstrap3_login(self):
        form = LocalSQLFORM(self._table)
        bootstrap_form = formstyle_bootstrap3_login(form, self._fields)
        soup = as_soup(str(bootstrap_form))
        fieldset = soup.find('fieldset')
        div = fieldset.div.div
        self.assertEqual(div['class'], ['col-xs-12'])

    def test__make_grid_class(self):

        # Text export parameter
        export_keys = [
            'csv',
            'csv_with_hidden_cols',
            'html',
            'json',
            'tsv',
            'tsv_with_hidden_cols',
            'xml',
        ]

        # Test export=None
        grid_class = make_grid_class(export=None)
        self.assertTrue('csv' not in grid_class.grid_defaults)
        self.assertTrue('exportclasses' not in grid_class.grid_defaults)

        # Test export='none'
        grid_class = make_grid_class(export='none')
        for key in export_keys:
            self.assertEqual(
                grid_class.grid_defaults['exportclasses'][key],
                False
            )

        # Test export='simple'
        expect_falses = list(export_keys)
        del expect_falses[expect_falses.index('csv')]
        del expect_falses[expect_falses.index('tsv')]
        grid_class = make_grid_class(export='simple')
        for key in export_keys:
            if key in expect_falses:
                self.assertEqual(
                    grid_class.grid_defaults['exportclasses'][key],
                    False
                )
            else:
                self.assertEqual(
                    len(grid_class.grid_defaults['exportclasses'][key]),
                    2
                )

        # Test search=None
        grid_class = make_grid_class(search=None)
        self.assertTrue('searchable' not in grid_class.grid_defaults)

        # Test search='none'
        grid_class = make_grid_class(search='none')
        self.assertEqual(grid_class.grid_defaults['searchable'], False)

        # Test search='simple'
        grid_class = make_grid_class(search='simple')
        self.assertTrue(callable(grid_class.grid_defaults['searchable']))

        # test ui=None
        grid_class = make_grid_class(ui=None)
        self.assertTrue('ui' not in grid_class.grid_defaults)

        # test ui='no_icon'
        grid_class = make_grid_class(ui='no_icon')
        self.assertEqual(
            grid_class.grid_defaults['ui']['buttonedit'],
            ''
        )

        # test ui='icon'
        grid_class = make_grid_class(ui='icon')
        self.assertEqual(
            grid_class.grid_defaults['ui']['buttonedit'],
            'icon pen icon-pencil'
        )

        # test ui='glyphicon'
        grid_class = make_grid_class(ui='glyphicon')
        self.assertEqual(
            grid_class.grid_defaults['ui']['buttonedit'],
            'glyphicon glyphicon-pencil'
        )

    def test__search_fields_grid(self):
        fields = [db.book.name]
        # No field_id should error.
        self.assertRaises(
            LookupError, search_fields_grid(fields), db.book)

        grid = search_fields_grid(fields)(db.book, field_id=db.book.id)
        self.assertTrue(grid)


def as_soup(html):
    return BeautifulSoup(html, 'html.parser')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
