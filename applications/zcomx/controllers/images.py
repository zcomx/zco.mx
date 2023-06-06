# -*- coding: utf-8 -*-
"""Image controller functions"""
import os
import shutil
from applications.zcomx.modules.downloaders import ImageDownloader
from applications.zcomx.modules.images import ResizeImg


def download():
    """Download image function.

    Adapted from Response.download. Handles image files stored in multiple
    subdirectores.

    request.args(0)
    """
    return ImageDownloader().download(request, db)


def resize():
    """Resize an image.

    This controller is used primarily for performance tests.
    """
    response.generic_patterns = ['html']
    fields = [
        Field(
            'filename',
            default='/tmp/file.jpg',
            type='string',
            requires=IS_NOT_EMPTY(),
            comment=(
                'File must be in /tmp or'
                ' in subdirectory of applications/zcomx'
            ),
        ),
    ]

    form = SQLFORM.factory(
        *fields,
        formstyle='table2cols',
        submit_button='Submit'
    )

    if form.process(keepvalues=True, message_onsuccess='').accepted:
        response.flash = 'Resizing {f}'.format(f=form.vars.filename)
        if not os.path.exists(form.vars.filename):
            response.flash = 'Unable to read file {f}'.format(
                f=form.vars.filename)
        else:
            tmp_dir = '/tmp/resize_img_py_web'
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            base = os.path.basename(form.vars.filename)
            dest_filename = os.path.join(tmp_dir, base)
            shutil.copy(form.vars.filename, dest_filename)
            resize_img = ResizeImg(dest_filename)
            resize_img.run()
            session.flash = 'Done'
            redirect(URL('resize'))
    elif form.errors:
        response.flash = 'Form could not be submitted.' + \
            ' Please make corrections.'

    return dict(form=form)
