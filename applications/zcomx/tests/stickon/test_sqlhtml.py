#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for modules/stickon/sqlhtml.py

"""
import unittest
from BeautifulSoup import BeautifulSoup
from gluon.sqlhtml import StringWidget
from applications.zcomx.modules.stickon.sqlhtml import \
    InputWidget, \
    SimpleUploadWidget, \
    LocalSQLFORM, \
    formstyle_bootstrap3_custom, \
    formstyle_bootstrap3_login
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


class TestSimpleUploadWidget(LocalTestCase):

    def test_init(self):
        widget = SimpleUploadWidget()
        self.assertTrue(widget)

    def test__widget(self):
        field = db.creator.image
        value = None

        widget = SimpleUploadWidget()
        soup = BeautifulSoup(str(widget.widget(field, value)))
        w_input = soup.find('input')
        if not w_input:
            self.fail('Input tag not returned')
        # Example:
        # <input class="upload" id="creator_image" name="image" type="file" />
        self.assertEqual(w_input['class'], 'upload')
        self.assertEqual(w_input['id'], 'creator_image')
        self.assertEqual(w_input['name'], 'image')
        self.assertEqual(w_input['type'], 'file')

        value = 'test_image.jpg'
        url = 'http://www.download.com'

        widget = SimpleUploadWidget()
        soup = BeautifulSoup(
            str(widget.widget(field, value, download_url=url)))
        # Example:
        # <div class="image_widget_container row">
        # <div class="image_widget_img">
        #     <img src="http://www.download.com/test_image.jpg" width="150px" />
        # </div>
        # <div class="image_widget_buttons">
        #     <input class="upload" id="creator_image" name="image" type="file" />
        #     <span style="white-space:nowrap">
        #         <input id="image__delete" name="image__delete" type="checkbox" value="on" />
        #         <label for="image__delete" style="display:inline">
        #             delete
        #         </label>
        #     </span>
        # </div>
        # <script>
        # &lt;!--
        #
        # jQuery('.image_widget_buttons input[type=file]').change(function(e) {
        # $(this).closest('form').submit();
        # });
        #
        # //--&gt;
        # </script>
        # </div>

        container_div = soup.find('div')
        if not container_div:
            self.fail('DIV tag not returned')
        self.assertEqual(container_div['class'], 'image_widget_container row')
        divs = container_div.findAll('div')
        img_div = divs[0]
        if not img_div:
            self.fail('Image DIV tag not returned')

        img = img_div.img
        if not img:
            self.fail('IMG tag not returned')
        self.assertEqual(img['src'], 'http://www.download.com/test_image.jpg')

        buttons_div = divs[1]
        if not buttons_div:
            self.fail('Buttons DIV tag not returned')

        up_input = buttons_div.input
        if not up_input:
            self.fail('Upload input tag not returned')
        self.assertEqual(up_input['class'], 'upload')
        self.assertEqual(up_input['id'], 'creator_image')
        self.assertEqual(up_input['name'], 'image')
        self.assertEqual(up_input['type'], 'file')

        span = buttons_div.span
        if not span:
            self.fail('SPAN tag not returned')

        del_input = span.input
        if not del_input:
            self.fail('Delete input tag not returned')
        self.assertEqual(del_input['id'], 'image__delete')
        self.assertEqual(del_input['name'], 'image__delete')
        self.assertEqual(del_input['type'], 'checkbox')
        self.assertEqual(del_input['value'], 'on')

        label = span.label
        if not label:
            self.fail('Delete input label tag not returned')
        self.assertEqual(label['for'], 'image__delete')
        self.assertEqual(label.string, 'delete')


class TestLocalSQLFORM(LocalTestCase):

    def test_parent__init__(self):
        form = LocalSQLFORM(db.book)
        self.assertTrue(form)
        self.assertTrue('paginate' in form.grid_defaults)
        self.assertTrue('ui' in form.grid_defaults)

    def test__grid(self):
        # Use table with many records so pagination is required.
        table = db.book_page

        form = LocalSQLFORM(table)
        grid = form.grid(table)
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
        self.assertTrue(len(lis) >= 5)
        next_page = lis[-1]
        # Example next page li
        # <li><a href="/?page=7">&gt;&gt;</a></li>
        href = next_page.a['href']
        count = db(db.book_page).count()
        rows_per_page = LocalSQLFORM.grid_defaults['paginate']
        pages = int(count / rows_per_page)
        if count % rows_per_page != 0:
            pages = pages + 1
        self.assertTrue('page={p}'.format(p=pages) in href)


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
                StringWidget.widget(db.creator.paypal_email, 'paypal.username@gmail.com'),
                db.creator.paypal_email.comment
            ),
        ]

    def test__formstyle_bootstrap3_custom(self):
        form = LocalSQLFORM(self._table)
        bootstrap_form = formstyle_bootstrap3_custom(form, self._fields)
        soup = BeautifulSoup(str(bootstrap_form))
        fieldset = soup.find('fieldset')
        div = fieldset.div.div
        self.assertEqual(div['class'], 'col-sm-6 col-lg-4')

    def test__formstyle_bootstrap3_login(self):
        form = LocalSQLFORM(self._table)
        bootstrap_form = formstyle_bootstrap3_login(form, self._fields)
        soup = BeautifulSoup(str(bootstrap_form))
        fieldset = soup.find('fieldset')
        div = fieldset.div.div
        self.assertEqual(div['class'], 'col-xs-12')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
