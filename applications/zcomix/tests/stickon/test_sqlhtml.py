#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for igeejo/modules/stickon/sqlhtml.py

"""
import unittest
from applications.zcomix.modules.stickon.sqlhtml import \
    InputWidget, \
    LocalSQLFORM
from applications.zcomix.modules.test_runner import LocalTestCase
from BeautifulSoup import BeautifulSoup


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
        soup = BeautifulSoup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        # Example:
        # <input class="generic-widget" id="account_number" name="number"
        #   type="text" value="_some_fake_value__" />
        self.assertEqual(w_input['class'], 'generic-widget')
        self.assertEqual(w_input['id'], 'book_name')
        self.assertEqual(w_input['name'], 'name')
        self.assertEqual(w_input['type'], 'text')
        self.assertEqual(w_input['value'], value)

        widget = InputWidget(
            attributes=dict(_type='hidden', _id='my_fake_id'),
            class_extra='id_widget'
        )
        soup = BeautifulSoup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        self.assertEqual(w_input['class'], 'generic-widget id_widget')
        self.assertEqual(w_input['id'], 'my_fake_id')
        self.assertEqual(w_input['name'], 'name')
        self.assertEqual(w_input['type'], 'hidden')
        self.assertEqual(w_input['value'], value)

        widget = InputWidget(attributes=dict(_type='submit'))
        soup = BeautifulSoup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        self.assertEqual(w_input['class'], 'generic-widget')
        self.assertEqual(w_input['id'], 'book_name')
        self.assertEqual(w_input['name'], 'name')
        self.assertEqual(w_input['type'], 'submit')
        self.assertEqual(w_input['value'], value)


class TestLocalSQLFORM(LocalTestCase):

    def test_parent__init__(self):
        form = LocalSQLFORM(db.book)
        self.assertTrue(form)
        self.assertTrue('paginate' in form.grid_defaults)
        self.assertTrue('ui' in form.grid_defaults)

    def test__grid(self):
        # Use table with many records so pagination is required.
        form = LocalSQLFORM(db.contribution)
        grid = form.grid(db.contribution)
        soup = BeautifulSoup(str(grid))
        # Sample outer div's of soup
        # <div class="web2py_grid grid_widget">
        #  <div class="web2py_console grid_header ">
        #  ...
        #  <div class="web2py_table">
        #   <div class="web2py_htmltable" style="width:100%;overflow-x:auto;-ms-overflow-x:scroll">
        #    <table>
        #     <thead>
        #      <tr class="grid_header">
        #       <th class="grid_default">
        div_1 = soup.div
        self.assertEqual(div_1['class'], 'web2py_grid grid_widget')
        div_2 = div_1.div
        self.assertEqual(div_2['class'], 'web2py_console grid_header ')
        div_3 = soup.find('div', {'class': 'web2py_table'})
        ths = div_3.findAll('th')
        for th in ths:
            self.assertEqual(th['class'], 'grid_default')

        # Test paginator
        div_paginator = soup.find('div', {'class': 'web2py_paginator grid_header '})
        lis = div_paginator.findAll('li')
        self.assertTrue(len(lis) > 5)
        last_page = lis[-1]
        # Example last page li
        # <li><a class="w2p_trap" href="/igeejo/default/index?page=797">&gt;&gt;</a></li>
        count = db.contribution.id.count()
        num_contribution = db(db.contribution).select(count).first()[count]
        pages = int(num_contribution / 35)
        if num_contribution % pages != 0:
            pages += 1
        href = last_page.a['href']
        self.assertTrue('page={pgs}'.format(pgs=pages) in href)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
