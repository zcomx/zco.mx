#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

stickon/sqlhtml.py

Classes extending functionality of gluon/sqlhtml.py particular to the zcomx
application.

"""
import logging
from gluon import *
from gluon.sqlhtml import FormWidget, UploadWidget

# E1101: *%s %r has no %r member*
# pylint: disable=E1101

LOG = logging.getLogger('app')


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
                image = IMG(_src=url, _width=cls.DEFAULT_WIDTH)

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


class LocalSQLFORM(SQLFORM):
    """Class representing a SQLFORM with preset defaults and customizations.
    """
    grid_defaults = {
            'paginate': 35,
            'ui': dict(widget='grid_widget',
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

    @staticmethod
    def grid(*args, **kwargs):
        """Override grid method and set ui defaults."""
        for k, v in LocalSQLFORM.grid_defaults.items():
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
            controls.add_class('col-xs-12')

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
            controls[0].add_class('col-xs-12')

        if isinstance(controls, SELECT):
            controls.add_class('form-control')

        if isinstance(controls, TEXTAREA):
            controls.add_class('form-control')

        if isinstance(label, LABEL):
            label['_class'] = 'col-xs-12 control-label'

        if _submit:
            # submit button has unwrapped label and controls, different class
            parent.append(DIV(label, DIV(controls,_class="col-xs-12"), _class='form-group', _id=id))
            # unflag submit (possible side effect)
            _submit = False
        else:
            # unwrapped label
            parent.append(DIV(label, _controls, _class='form-group', _id=id))
    return parent
