#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

stickon/sqlhtml.py

Classes extending functionality of gluon/sqlhtml.py particular to the zcomx
application.

"""
from gluon import *
from gluon.sqlhtml import \
    ExporterCSV, \
    ExporterTSV, \
    FormWidget, \
    UploadWidget

# E1101: *%s %r has no %r member*
# pylint: disable=E1101

LOG = current.app.logger


class InputWidget(FormWidget):
    """Custom input widget."""

    def __init__(self, attributes=None, class_extra=''):
        """Constructor.

        Args:
            attributes: dict, dictionary of custom attributes.
            class_extra: string, value appended to _class value.
        """
        # W0221: Arguments number differs from overridden method
        # W0231: __init__ method from base class FormWidget is not called
        # pylint: disable=W0221,W0231

        self.attributes = attributes if attributes else {}
        self.class_extra = class_extra

    def widget(self, field, value, **attributes):
        """Generate INPUT tag for custom widget.

        See gluon.sqlhtml FormWidget
        """
        # W0221: Arguments number differs from overridden method
        # pylint: disable=W0221

        new_attributes = dict(
            _type='text',
            _value=(value != None and str(value)) or '',
            )
        new_attributes.update(self.attributes)
        attr = self._attributes(field, new_attributes, **attributes)
        if self.class_extra:
            attr['_class'] = ' '.join([attr['_class'], self.class_extra])
        return INPUT(**attr)


class SimpleUploadWidget(UploadWidget):
    """Simplified upload widget.

    Modifications:
    * Remove the 'file' download link.
    * Remove the brackets
    * Position the buttons and checkbox to the right of the image.
    """

    @classmethod
    def widget(cls, field, value, download_url=None, **attributes):
        """
        generates a INPUT file tag.

        Optionally provides an A link to the file, including a checkbox so
        the file can be deleted.
        All is wrapped in a DIV.

        see also: :meth:`FormWidget.widget`

        :param download_url: Optional URL to link to the file (default = None)
        """

        default = dict(_type='file',)
        attr = cls._attributes(field, default, **attributes)

        inp = INPUT(**attr)

        if download_url and value:
            if callable(download_url):
                url = download_url(value)
            else:
                url = download_url + '/' + value
            (br, image) = ('', '')
            if UploadWidget.is_image(value):
                br = BR()
                image = IMG(_src=url, _width=cls.DEFAULT_WIDTH, _alt='')

            requires = attr["requires"]
            if requires == [] or isinstance(requires, IS_EMPTY_OR):
                inp = DIV(
                        DIV(
                            image,
                            _class='image_widget_img',
                            ),
                        DIV(
                            inp,
                            SPAN(INPUT(_type='checkbox',
                                         _name=field.name + cls.ID_DELETE_SUFFIX,
                                         _id=field.name + cls.ID_DELETE_SUFFIX),
                                LABEL(current.T(cls.DELETE_FILE),
                                         _for=field.name + cls.ID_DELETE_SUFFIX,
                                         _style='display:inline'),
                            _style='white-space:nowrap'),
                            _class='image_widget_buttons',
                            ),
                         SCRIPT("""
                         jQuery('.image_widget_buttons input[type=file]').change(function(e) {
                            $(this).closest('form').submit();
                         });
                         """ % dict(name=field.name + cls.ID_DELETE_SUFFIX)
                         ),
                        _class='image_widget_container row'
                        )
            else:
                inp = DIV(inp,
                          SPAN('[',
                               A(current.T(cls.GENERIC_DESCRIPTION),_href=url),
                               ']', _style='white-space:nowrap'),
                          br, image)
        return inp


class LocalSQLFORMExtender(type):
    """Auto extender for LocalSQLFORM.

    Permits updating the grid_defaults class property.
    """
    def __new__(mcs, name, bases, attrs):
        grid_defaults = {}
        for base in bases:
            try:
                grid_defaults.update(getattr(base, 'grid_defaults'))
            except AttributeError:
                pass
        try:
            grid_defaults.update(attrs.pop('grid_default_additions'))
        except KeyError:
            pass
        attrs['grid_defaults'] = grid_defaults
        return type.__new__(mcs, name, bases, attrs)


class LocalSQLFORM(SQLFORM):
    """Class representing a SQLFORM with preset defaults and customizations.
    """
    __metaclass__ = LocalSQLFORMExtender
    grid_default_additions = {
        'paginate': 35,
    }

    @classmethod
    def grid(cls, *args, **kwargs):
        """Override grid method and set ui defaults."""
        for k, v in cls.grid_defaults.items():
            if k not in kwargs:
                kwargs[k] = v
        return SQLFORM.grid(*args, **kwargs)


def formstyle_bootstrap3_custom(form, fields):
    """Modified version of gluon/sqlhtml.py def formstyle_bootstrap3

    Modifications:
        1. Replace col-lg-* with size specific settings
            col-sm-* col-md-* col-lg-*

    """
    form.add_class('form-horizontal')
    parent = FIELDSET()
    for id, label, controls, help in fields:

        # wrappers
        _help = SPAN(help, _class='help-block')
        # embed _help into _controls
        _controls = DIV(controls, _help, _class='col-sm-6 col-lg-4')
        # submit unflag by default
        _submit = False
        if isinstance(controls, INPUT):
            controls.add_class('col-sm-6 col-lg-4')

            if controls['_type'] == 'submit':
                # flag submit button
                _submit = True
                controls['_class'] = 'btn btn-primary'
            if controls['_type'] == 'button':
                controls['_class'] = 'btn btn-default'
            elif controls['_type'] == 'file':
                controls['_class'] = 'input-file'
            elif controls['_type'] == 'text':
                controls['_class'] = 'form-control'
            elif controls['_type'] == 'password':
                controls['_class'] = 'form-control'
            elif controls['_type'] == 'checkbox':
                controls['_class'] = 'checkbox'

        # For password fields, which are wrapped in a CAT object.
        if isinstance(controls, CAT) and isinstance(controls[0], INPUT):
            controls[0].add_class('col-sm-2')

        if isinstance(controls, SELECT):
            controls.add_class('form-control')

        if isinstance(controls, TEXTAREA):
            controls.add_class('form-control')

        if isinstance(label, LABEL):
            label['_class'] = 'col-sm-3 col-lg-2 control-label'

        if _submit:
            # submit button has unwrapped label and controls, different class
            parent.append(DIV(label, DIV(controls,_class="col-sm-6 col-sm-offset-3 col-lg-4 col-lg-offset-2"), _class='form-group', _id=id))
            # unflag submit (possible side effect)
            _submit = False
        else:
            # unwrapped label
            parent.append(DIV(label, _controls, _class='form-group', _id=id))
    return parent


def formstyle_bootstrap3_login(form, fields):
    """Modified version of gluon/sqlhtml.py def formstyle_bootstrap3

    Modifications:
        1. Replace col-lg-* with size specific settings
            col-xs-12
        2. Use inline checkbox adapted from formstyle_bootstrap3_inline_factory

    """
    form.add_class('form-horizontal')
    parent = FIELDSET()
    for id, label, controls, help in fields:
        # wrappers
        _help = SPAN(help, _class='help-block')
        # embed _help into _controls
        _controls = DIV(controls, _help, _class='col-xs-12')
        # submit unflag by default
        _submit = False
        if isinstance(controls, INPUT):
            if controls['_type'] == 'submit':
                # flag submit button
                _submit = True
                controls['_class'] = 'btn btn-primary btn-block'
            if controls['_type'] == 'button':
                controls['_class'] = 'btn btn-default'
            elif controls['_type'] == 'file':
                controls['_class'] = 'input-file'
            elif controls['_type'] == 'text':
                controls['_class'] = 'form-control'
            elif controls['_type'] == 'password':
                controls['_class'] = 'form-control'
            elif controls['_type'] == 'checkbox':
                label['_for'] = None
                label.insert(0, controls)
                _controls = DIV(
                    DIV(label, _help, _class="checkbox"),
                    _class='col-xs-12'
                )
                label = ''

        if current.request.args(0) == 'login' \
                and isinstance(controls, INPUT) \
                and controls['_type'] != 'checkbox':
            controls.add_class('align_center')

        if isinstance(controls, INPUT) and controls['_type'] != 'checkbox':
            controls.add_class('input-lg')

        # For password fields, which are wrapped in a CAT object.
        if isinstance(controls, CAT) and isinstance(controls[0], INPUT):
            controls[0].add_class('col-xs-12')

        if isinstance(controls, SELECT):
            controls.add_class('form-control')

        if isinstance(controls, TEXTAREA):
            controls.add_class('form-control')

        if isinstance(label, LABEL):
            label['_class'] = 'col-xs-12 control-label align_left'

        if current.request.args(0) != 'register':
            if isinstance(controls, INPUT) and controls['_type'] != 'checkbox':
                if isinstance(label, LABEL):
                    label.add_class('labels_hidden')

        if _submit:
            # submit button has unwrapped label and controls, different class
            parent.append(DIV(label, DIV(controls,_class="col-xs-12"), _class='form-group', _id=id))
            # unflag submit (possible side effect)
            _submit = False
        else:
            # unwrapped label
            parent.append(DIV(label, _controls, _class='form-group', _id=id))
    return parent


def make_grid_class(export=None, search=None, ui=None, **kwargs):
    """Test make grid class.

    Args:
        export: str, one of 'simple', 'none'. Determines the SQLFORM.grid csv
            and exportclasses parameters.
                simple: csv and tsv
                none: no export options
            If None the SQLFORM.grid default is used.
        search: str, one of 'simple', 'none'
                simple: single input
                none: no search
            If None the SQLFORM.grid default is used.
        ui: str, one of 'no_icon', 'icon', 'glyphicon'
            If None the SQLFORM.grid default is used.
        kwargs: dict, grid param defaults are updated with this
    """
    defaults = {}

    # Export classes
    export_keys = [
        'csv',
        'csv_with_hidden_cols',
        'html',
        'json',
        'tsv',
        'tsv_with_hidden_cols',
        'xml',
    ]

    no_exporters = dict([(x, False) for x in export_keys])
    simple_exporters = dict(no_exporters)
    simple_exporters.update(dict(
        csv=(ExporterCSV, 'CSV'),
        tsv=(ExporterTSV, 'TSV (Excel compatible)'),
    ))

    export_classes = {
        # export: (csv, exportclasses)
        'none': (False, no_exporters),
        'simple': (True, simple_exporters),
    }

    if export is not None:
        defaults['csv'] = export_classes[export][0]
        defaults['exportclasses'] = export_classes[export][1]


    # Search
    def _searchable(sfields, keywords):
        """Simple searchable callback."""
        # The default web2m searchable doesn't handle spaces well.
        queries = []
        for sfield in sfields:
            queries.append((sfield.like('%' + keywords + '%')))
        query = reduce(lambda x, y: x | y, queries) if queries else None
        return query

    searches = {
        'none': False,
        'simple': _searchable,
    }

    if search is not None:
        defaults['searchable'] = searches[search]

    # UI
    uis = {
        'no_icon': dict(
            widget='grid_widget',
            header='grid_header',
            content='',
            default='grid_default',
            cornerall='',
            cornertop='',
            cornerbottom='',
            button='button btn',
            buttontext='buttontext button',
            buttonadd='',
            buttonback='',
            buttonexport='',
            buttondelete='',
            buttonedit='',
            buttontable='',
            buttonview='',
        ),
        'icon': dict(
            widget='grid_widget',
            header='grid_header',
            content='',
            default='grid_default',
            cornerall='',
            cornertop='',
            cornerbottom='',
            button='button btn',
            buttontext='buttontext button',
            buttonadd='icon plus icon-plus',
            buttonback='icon leftarrow icon-arrow-left',
            buttonexport='icon downarrow icon-download',
            buttondelete='icon trash icon-trash',
            buttonedit='icon pen icon-pencil',
            buttontable='icon rightarrow icon-arrow-right',
            buttonview='icon magnifier icon-zoom-in',
        ),
        'glyphicon': dict(
            widget='grid_widget',
            header='grid_header',
            content='',
            default='grid_default',
            cornerall='',
            cornertop='',
            cornerbottom='',
            button='button btn btn-default',
            buttontext='buttontext button',
            buttonadd='glyphicon glyphicon-plus',
            buttonback='glyphicon glyphicon-arrow-left',
            buttonexport='glyphicon glyphicon-download',
            buttondelete='glyphicon glyphicon-trash',
            buttonedit='glyphicon glyphicon-pencil',
            buttontable='glyphicon glyphicon-arrow-right',
            buttonview='glyphicon glyphicon-zoom-in',
        ),
    }

    if ui is not None:
        defaults['ui'] = uis[ui]

    if kwargs:
        defaults.update(kwargs)

    class PseudoLocalSQLFORM(LocalSQLFORM):
        """LocalSQLFORM class with updated grid_default class property."""
        grid_default_additions = defaults
    return PseudoLocalSQLFORM


plain_grid = make_grid_class(export='none', search='none', ui='no_icon').grid
simple_grid = make_grid_class(export='simple', search='none', ui='no_icon').grid
searchable_grid = make_grid_class(export='simple', search='simple', ui='no_icon').grid
