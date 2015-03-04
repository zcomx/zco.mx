# -*- coding: utf-8 -*-
"""Creator login controller functions"""
import logging
import os
import shutil
import sys
from PIL import Image
from gluon.contrib.simplejson import dumps
from gluon.validators import urlify
from applications.zcomx.modules.book_upload import BookPageUploader
from applications.zcomx.modules.books import \
    book_pages_as_json, \
    defaults as book_defaults, \
    numbers_for_book_type, \
    optimize_book_images, \
    publication_year_range, \
    read_link, \
    release_barriers
from applications.zcomx.modules.creators import \
    image_as_json, \
    optimize_creator_images
from applications.zcomx.modules.images import \
    ResizeImgIndicia, \
    store
from applications.zcomx.modules.indicias import \
    CreatorIndiciaPage, \
    IndiciaUpdateInProgress, \
    PublicationMetadata, \
    cc_licence_by_code, \
    clear_creator_indicia, \
    update_creator_indicia
from applications.zcomx.modules.job_queue import \
    DeleteBookQueuer, \
    DeleteImgQueuer, \
    ReleaseBookQueuer, \
    UpdateIndiciaQueuer
from applications.zcomx.modules.links import CustomLinks
from applications.zcomx.modules.shell_utils import TemporaryDirectory
from applications.zcomx.modules.utils import \
    default_record, \
    entity_to_row, \
    reorder

LOG = logging.getLogger('app')


@auth.requires_login()
def account():
    """Account login controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))

    return dict(creator=creator_record)


@auth.requires_login()
def book_crud():
    """Handler for ajax book CRUD calls.

    request.vars._action: string, 'create', 'update', etc

    create:
    request.vars.name: string, book table field name ('name')
    request.vars.value: string, value of book table field.

    delete:
    request.vars.pk: integer, id of book record

    release:
    request.vars.pk: integer, id of book record

    update:
    request.vars.pk: integer, id of book record
    request.vars.name: string, book table field name
    request.vars.value: string, value of book table field.
    """
    # too-many-return-statements (R0911): *Too many return statements*
    # pylint: disable=R0911

    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    # W0212 (protected-access): *Access to a protected member
    # pylint: disable=W0212
    actions = ['create', 'delete', 'release', 'update']
    if not request.vars._action or request.vars._action not in actions:
        return do_error('Invalid data provided')
    action = request.vars._action

    book_record = None
    if action != 'create':
        try:
            book_id = int(request.vars.pk)
        except (TypeError, ValueError):
            return do_error('Invalid data provided')
        book_record = entity_to_row(db.book, book_id)
        if not book_record or (
                book_record and book_record.creator_id != creator_record.id):
            return do_error('Invalid data provided')

    if action == 'create':
        data = {}
        # Validate all fields.
        if request.vars.name is not None and request.vars.value is not None:
            book_name = request.vars.value.strip()
            data = book_defaults(db, book_name, creator_record)
            data[request.vars.name] = book_name

        ret = db.book.validate_and_insert(**data)
        db.commit()

        if ret.errors:
            if request.vars.name in ret.errors:
                return {
                    'status': 'error',
                    'msg': ret.errors[request.vars.name]
                }
            else:
                return {
                    'status': 'error',
                    'msg': ', '.join([
                        '{k}: {v}'.format(k=k, v=v)
                        for k, v in ret.errors.items()
                    ])
                }
        if ret.id:
            return {
                'id': ret.id,
                'status': 'ok',
            }
        return do_error('Unable to create book')

    if action == 'delete':
        # The process of deleting book can be slow, so queue a job to
        # take care of it. Flag the book status=False so it is hidden.
        db(db.book.id == book_record.id).update(status=False)
        db.commit()

        job = DeleteBookQueuer(
            db.job,
            cli_args=[str(book_record.id)],
        ).queue()
        if not job:
            return do_error(
                'Delete failed. The book cannot be deleted at this time.')

        return {'status': 'ok'}

    if action == 'release':
        if release_barriers(book_record):
            return do_error('This book cannot be released.')

        book_record.update_record(releasing=True)
        db.commit()
        job = ReleaseBookQueuer(
            db.job,
            cli_args=[str(book_record.id)],
        ).queue()
        if not job:
            return do_error(
                'Release failed. The book cannot be released at this time.')

        return {'status': 'ok'}

    if action == 'update':
        if request.vars.name is not None \
                and request.vars.name not in db.book.fields:
            return do_error('Invalid data provided')

        data = {}
        if request.vars.name == 'cc_licence_id' and request.vars.value is None:
            # Allow cc_licence_id=0
            data = {request.vars.name: 0}
        elif request.vars.name is not None and request.vars.value is not None:
            data = {request.vars.name: request.vars.value}
        if not data:
            return do_error('Invalid data provided')

        if 'name' in data:
            data['urlify_name'] = urlify(data['name'], maxlen=99999)

        query = (db.book.id == book_record.id)
        ret = db(query).validate_and_update(**data)
        db.commit()

        if ret.errors:
            if request.vars.name in ret.errors:
                return {
                    'status': 'error',
                    'msg': ret.errors[request.vars.name]
                }
            else:
                return {
                    'status': 'error',
                    'msg': ', '.join([
                        '{k}: {v}'.format(k=k, v=v)
                        for k, v in ret.errors.items()
                    ])
                }
        numbers = numbers_for_book_type(db, request.vars.value) \
            if request.vars.name == 'book_type_id' else None
        show_cc_licence_place = False
        cc0_licence_id = cc_licence_by_code('CC0', want='id', default=0)
        if request.vars.name == 'cc_licence_id' \
                and request.vars.value == str(cc0_licence_id):
            show_cc_licence_place = True
        return {
            'show_cc_licence_place': show_cc_licence_place,
            'numbers': numbers,
            'status': 'ok',
        }
    return {'status': 'ok'}


@auth.requires_login()
def book_delete():
    """Book delete controller for modal view.

    request.args(0): integer, id of book.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('modal_error', vars={'message': 'Permission denied'}))

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided'}))

    return dict(book=book_record)


@auth.requires_login()
def book_edit():
    """Book edit controller for modal view.

    request.args(0): integer, id of book
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('modal_error', vars={'message': 'Permission denied'}))

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))

    book_type_id = book_record.book_type_id if book_record else 0
    numbers = numbers_for_book_type(db, book_type_id)

    show_cc_licence_place = False
    meta = None
    if book_record:
        cc0_licence_id = cc_licence_by_code('CC0', want='id', default=0)
        if book_record.cc_licence_id == cc0_licence_id:
            show_cc_licence_place = True

        meta = PublicationMetadata(book_record)
        meta.load()

    return dict(
        book=book_record,
        metadata=str(meta) if meta else '',
        numbers=dumps(numbers),
        show_cc_licence_place=dumps(show_cc_licence_place),
    )


@auth.requires_login()
def book_list():
    """Book list component controller.

    request.args(0): string, optional, one of 'released', 'ongoing', 'disabled'
    """
    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return dict()

    if not request.args(0) or \
            request.args(0) not in ['released', 'ongoing', 'disabled']:
        return dict()

    creator_query = (db.book.creator_id == creator_record.id)
    active_query = (db.book.status == True)

    book_records = None
    if request.args(0) == 'released':
        query = creator_query & active_query & (db.book.release_date != None)
    elif request.args(0) == 'ongoing':
        query = creator_query & active_query & (db.book.release_date == None)
    elif request.args(0) == 'disabled':
        query = creator_query & (db.book.status == False)
    if query:
        book_records = db(query).select(
            db.book.ALL, orderby=[db.book.name, db.book.number])
    return dict(books=book_records)


@auth.requires_login()
def book_pages():
    """Book pages (image upload) controller for modal view.

    request.args(0): integer, id of book.
    """
    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('modal_error', vars={'message': 'Permission denied'}))

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided'}))

    read_button = read_link(
        db,
        book_record,
        **dict(
            _class='btn btn-default btn-lg',
            _target='_blank',
        )
    )

    return dict(
        book=book_record,
        read_button=read_button,
    )


@auth.requires_login()
def book_pages_handler():
    """Callback function for the jQuery-File-Upload plugin.

    request.args(0): integer, id of book.

    # Add
    request.vars.up_files: list of files representing pages to add to book.

    # Delete
    request.vars.book_page_id: integer, id of book_page to delete

    """
    # too-many-return-statements (R0911): *Too many return statements*
    # pylint: disable=R0911

    def do_error(msg, files=None):
        """Error handler."""
        if files == None:
            files = ['']
        messages = [{'name': x, 'error': msg} for x in files]
        return dumps({'files': messages})

    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Upload service unavailable')

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record or book_record.creator_id != creator_record.id:
        return do_error('Upload service unavailable')

    if request.env.request_method == 'POST':
        # Create a book_page record for each upload.
        files = request.vars['up_files[]']
        if not isinstance(files, list):
            files = [files]
        # Catching too general exception (W0703)
        # pylint: disable=W0703
        try:
            result = BookPageUploader(book_record.id, files).upload()
        except Exception as err:
            print >> sys.stderr, 'Upload failed, err: {err}'.format(err=err)
            return do_error(
                'The upload was not successful.',
                files=[x.filename for x in files]
            )
        return result
    elif request.env.request_method == 'DELETE':
        book_page = entity_to_row(db.book_page, request.vars.book_page_id)
        if not book_page:
            return do_error('Unable to delete page')

        # retrieve real file name
        filename, _ = db.book_page.image.retrieve(
            book_page.image,
            nameonly=True,
        )

        job = DeleteImgQueuer(
            db.job,
            cli_args=[book_page.image],
        ).queue()
        if not job:
            # This isn't critical, just log a message.
            LOG.error(
                'Failed to create job to delete img: %s', book_page.image)
        book_page.delete_record()
        db.commit()
        return dumps({"files": [{filename: True}]})
    else:
        # GET
        return book_pages_as_json(db, book_record.id)


@auth.requires_login()
def book_post_image_upload():
    """Callback function for handling processing to run after images have been
        uploaded.

        * optimize book page images
        * reorder book pages

    request.args(0): integer, id of book.
    request.vars.book_page_ids[], list of book page ids.
    """
    def do_error(msg):
        """Error handler."""
        return dumps({'success': False, 'error': msg})

    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Reorder service unavailable')

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record or book_record.creator_id != creator_record.id:
        return do_error('Reorder service unavailable')

    # Step 1:  Trigger optimization of book images
    optimize_book_images(book_record)

    # Step 2: Reorder book pages
    if 'book_page_ids[]' not in request.vars:
        # Nothing more to do
        return dumps({'success': True})

    page_ids = []
    for page_id in request.vars['book_page_ids[]']:
        try:
            page_ids.append(int(page_id))
        except (TypeError, ValueError):
            # reordering pages isn't critical, if page is not valid, just move
            # on
            continue

    for count, page_id in enumerate(page_ids):
        page_record = entity_to_row(db.book_page, page_id)
        if page_record and page_record.book_id == book_record.id:
            page_record.update_record(page_no=(count + 1))
            db.commit()
    return dumps({'success': True})


@auth.requires_login()
def book_release():
    """Book release controller for modal view.

    request.args(0): integer, id of book.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('modal_error', vars={'message': 'Permission denied'}))

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided'}))

    return dict(
        book=book_record,
        barriers=release_barriers(book_record),
    )


@auth.requires_login()
def books():
    """Books controller.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    response.files.append(
        URL('static', 'bgrins-spectrum/spectrum.css')
    )

    response.files.append(
        URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
    )

    response.files.append(
        URL('static', 'blueimp/jQuery-File-Upload/css/jquery.fileupload.css')
    )

    response.files.append(
        URL(
            'static',
            'blueimp/jQuery-File-Upload/css/jquery.fileupload-ui.css'
        )
    )
    response.files.append(
        URL(
            'static',
            'x-editable/bootstrap3-editable/css/bootstrap-editable.css'
        )
    )

    query = (db.book.creator_id == creator_record.id) & \
            (db.book.status == False)
    has_disabled = db(query).count()

    return dict(has_disabled=has_disabled)


@auth.requires_login()
def creator_crud():
    """Handler for ajax creator CRUD calls.

    request.vars.name: string, creator table field name
    request.vars.value: string, value of creator table field.
    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    if request.vars.name is not None \
            and request.vars.name not in db.creator.fields:
        return do_error('Invalid data provided')

    data = {}
    if request.vars.name is not None and request.vars.value is not None:
        data = {request.vars.name: request.vars.value}
    if not data:
        return do_error('Invalid data provided')

    # Strip trailing slash from urls
    for f in ['website', 'shop', 'tumblr']:
        if f in data:
            data[f] = data[f].rstrip('/')

    query = (db.creator.id == creator_record.id)
    ret = db(query).validate_and_update(**data)
    db.commit()

    if ret.errors:
        if request.vars.name in ret.errors:
            return {'status': 'error', 'msg': ret.errors[request.vars.name]}
        else:
            return {
                'status': 'error',
                'msg': ', '.join([
                    '{k}: {v}'.format(k=k, v=v)
                    for k, v in ret.errors.items()
                ])
            }
    result = {'status': 'ok'}
    if request.vars.name in data \
            and data[request.vars.name] != request.vars.value:
        result['newValue'] = data[request.vars.name]
    return result


@auth.requires_login()
def creator_img_handler():
    """Callback function for the jQuery-File-Upload plugin.

    # POST
    request.args(0): string, name if creator field to update.
            Optional, if not set, update creator.image
            Eg 'indicia_image': update creator.indicia_image
    request.vars.up_files: list of files representing creator image.
    """
    # too-many-return-statements (R0911): *Too many return statements*
    # pylint: disable=R0911

    def do_error(msg, files=None):
        """Error handler."""
        if files == None:
            files = ['']
        messages = [{'name': x, 'error': msg} for x in files]
        return dumps({'files': messages})

    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Upload service unavailable')

    img_field = 'image'
    if request.args(0):
        if request.args(0) not in db.creator.fields:
            print >> sys.stderr, \
                'creator_img_handler invalid field: {fld}'.format(
                    fld=request.vargs(0))
            return do_error('Upload service unavailable')
        img_field = request.args(0)

    minimum_widths = {
        # 'field': width in px
        'image': 263,
        'indicia_image': 600,
    }

    if request.env.request_method == 'POST':
        # Create a book_page record for each upload.
        files = request.vars.up_files
        if not isinstance(files, list):
            files = [files]
        up_file = files[0]

        with TemporaryDirectory() as tmp_dir:
            local_filename = os.path.join(tmp_dir, up_file.filename)
            with open(local_filename, 'w+b') as lf:
                # This will convert cgi.FieldStorage to a regular file.
                shutil.copyfileobj(up_file.file, lf)

            with open(local_filename, 'r') as lf:
                try:
                    im = Image.open(lf)
                except IOError as err:
                    return do_error(str(err))

                if im.size[0] < minimum_widths[img_field]:
                    fmt = 'Image is too small. Minimum image width: {min}px'
                    return do_error(
                        fmt.format(min=minimum_widths[img_field]),
                        files=[up_file.filename]
                    )
            # Catching too general exception (W0703)
            # pylint: disable=W0703
            resizer = ResizeImgIndicia if img_field == 'indicia_image' \
                else None
            try:
                stored_filename = store(
                    db.creator[img_field], local_filename, resizer=resizer)
            except Exception as err:
                print >> sys.stderr, \
                    'Creator image upload error: {err}'.format(err=err)
                stored_filename = None

        if not stored_filename:
            return do_error(
                'File upload failed',
                files=[up_file.filename]
            )

        img_changed = creator_record[img_field] != stored_filename
        if img_changed:
            if creator_record[img_field] is not None:
                # Delete an existing image before it is replaced
                job = DeleteImgQueuer(
                    db.job,
                    cli_args=[creator_record[img_field]],
                ).queue()
                if not job:
                    # This isn't critical, just log a message.
                    LOG.error(
                        'Failed to create job to delete img: %s',
                        creator_record[img_field]
                    )
                data = {img_field: None}
                creator_record.update_record(**data)
                db.commit()
            if img_field == 'indicia_image':
                # Clear the indicia png fields. This will trigger a rebuild
                # in indicia_preview_urls
                for f in ['indicia_portrait', 'indicia_landscape']:
                    if creator_record[f] is not None:
                        clear_creator_indicia(creator_record, field=f)
                job = UpdateIndiciaQueuer(
                    db.job,
                    cli_args=[str(creator_record.id)],
                ).queue()
                if not job:
                    # This isn't critical, just log a message.
                    LOG.error(
                        'Failed to create job to update indicia: %s',
                        creator_record.id
                    )

        data = {img_field: stored_filename}
        creator_record.update_record(**data)
        db.commit()
        if img_changed:
            optimize_creator_images(creator_record)
        return image_as_json(db, creator_record.id, field=img_field)

    elif request.env.request_method == 'DELETE':
        # retrieve real file name
        if not creator_record[img_field]:
            return do_error('')

        filename, _ = db.creator[img_field].retrieve(
            creator_record[img_field],
            nameonly=True,
        )
        # Clear the images from the record
        data = {img_field: None}

        job = DeleteImgQueuer(
            db.job,
            cli_args=[creator_record[img_field]],
        ).queue()
        if not job:
            # This isn't critical, just log a message.
            LOG.error(
                'Failed to create job to delete img: %s',
                creator_record[img_field]
            )

        if img_field == 'indicia_image':
            for f in ['indicia_portrait', 'indicia_landscape']:
                if creator_record[f] is not None:
                    clear_creator_indicia(creator_record, field=f)
            job = UpdateIndiciaQueuer(
                db.job,
                cli_args=[str(creator_record.id)],
            ).queue()
            if not job:
                # This isn't critical, just log a message.
                LOG.error(
                    'Failed to create job to update indicia: %s',
                    creator_record.id
                )
        db(db.creator.id == creator_record.id).update(**data)
        db.commit()
        return dumps({"files": [{filename: 'true'}]})

    # GET
    return image_as_json(db, creator_record.id, field=img_field)


@auth.requires_login()
def index():
    """Default login controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))
    redirect(URL(c='login', f='books'))


@auth.requires_login()
def indicia():
    """Indicia controller.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    response.files.append(
        URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
    )

    response.files.append(
        URL('static', 'blueimp/jQuery-File-Upload/css/jquery.fileupload.css')
    )

    response.files.append(
        URL(
            'static',
            'blueimp/jQuery-File-Upload/css/jquery.fileupload-ui.css'
        )
    )

    return dict(creator=creator_record)


@auth.requires_login()
def indicia_preview_urls():
    """Handler for ajax link CRUD calls.
    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    # If indicias are blank, create them.
    if not creator_record.indicia_portrait \
            or not creator_record.indicia_landscape:
        try:
            # Run quickly in foreground
            update_creator_indicia(
                creator_record,
                background=False,
                resize=False,
                optimize=False
            )
        except IndiciaUpdateInProgress as err:
            print >> sys.stderr, 'IndiciaUpdateInProgress: ', err

    urls = {
        'portrait': None,
        'landscape': None,
    }

    for orientation in urls.keys():
        field = 'indicia_{o}'.format(o=orientation)
        if creator_record[field]:
            urls[orientation] = URL(
                c='images',
                f='download',
                args=creator_record[field],
                vars={'size': 'web'},
            )
        else:
            # Use generic images if creator indicias not set.
            urls[orientation] = URL(
                c='static',
                f='images/generic_indicia_{o}.png'.format(o=orientation),
            )

    return dumps({
        'status': 'ok',
        'urls': urls,
    })


@auth.requires_login()
def link_crud():
    """Handler for ajax link CRUD calls.
    request.args(0): integer, optional, if provided, id of book record. All
        actions are done on book links. If not provided, actions are done on
        creator links.

    request.vars.action: string, one of
        'get', 'create', 'update', 'delete', 'move'

    # action = 'update', 'delete', 'move'
    request.vars.link_id: integer, id of link record

    # action = 'update'
    request.vars.field: string, link table field name
    request.vars.value: string, value of link field

    # action = 'create'
    request.vars.name: string, name of link
    request.vars.url: string, url of link

    # action = 'move'
    request.vars.dir: string, 'up' or 'down'
    """
    # too-many-return-statements (R0911): *Too many return statements*
    # pylint: disable=R0911
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    record_id = 0
    rows = []
    errors = {}     # Row() or dict
    new_value = None

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
        if not book_record:
            return do_error('Invalid data provided')

    if book_record:
        entity_table = db.book
        to_link_table = db.book_to_link
        to_link_join_field = db.book_to_link.book_id
        record = book_record
    else:
        entity_table = db.creator
        to_link_table = db.creator_to_link
        to_link_join_field = db.creator_to_link.creator_id
        record = creator_record

    action = request.vars.action if request.vars.action else 'get'

    link_id = None
    link_record = None
    if request.vars.link_id:
        try:
            link_id = int(request.vars.link_id)
        except (TypeError, ValueError):
            link_id = None

    if link_id:
        link_record = entity_to_row(db.link, link_id)
        if not link_record:
            return do_error('Invalid data provided')

    do_reorder = False
    if action == 'get':
        query = (to_link_join_field == record.id)
        if link_id:
            query = query & (db.link.id == link_id)
        rows = db(query=query).select(
            db.link.ALL,
            left=[
                to_link_table.on(
                    (to_link_table.link_id == db.link.id)
                )
            ],
            orderby=[to_link_table.order_no, to_link_table.id],
        ).as_list()
    elif action == 'update':
        if link_id:
            data = {}
            if request.vars.field is not None \
                    and request.vars.value is not None:
                data = {request.vars.field: request.vars.value}

            # Strip trailing slash from url
            for f in ['url']:
                if f in data:
                    data[f] = data[f].rstrip('/')
                    new_value = data[f]

            if data:
                query = (db.link.id == link_id)
                ret = db(query).validate_and_update(**data)
                db.commit()
                record_id = link_id
                if ret.errors:
                    if request.vars.field in ret.errors:
                        return {
                            'status': 'error',
                            'msg': ret.errors[request.vars.field]
                        }
                    else:
                        return {
                            'status': 'error',
                            'msg': ', '.join([
                                '{k}: {v}'.format(k=k, v=v)
                                for k, v in ret.errors.items()
                            ])
                        }
                do_reorder = True
        else:
            return do_error('Invalid data provided')
    elif action == 'create':
        url = request.vars.url.rstrip('/')
        ret = db.link.validate_and_insert(
            url=url,
            name=request.vars.name,
        )
        db.commit()
        if url != request.vars.url:
            new_value = url
        if ret.id:
            data = dict(
                link_id=ret.id,
                order_no=99999,
            )
            if book_record:
                data['book_id'] = book_record.id
            else:
                data['creator_id'] = creator_record.id
            to_link_table.insert(**data)
            db.commit()
            do_reorder = True
        record_id = ret.id
        if ret.errors:
            return {'status': 'error', 'msg': ret.errors}
    elif action == 'delete':
        if link_id:
            query = (to_link_table.link_id == link_id)
            db(query).delete()
            query = (db.link.id == link_id)
            db(query).delete()
            db.commit()
            record_id = link_id
            do_reorder = True
        else:
            return do_error('Invalid data provided')
    elif action == 'move':
        if link_id:
            to_link_record = db(to_link_table.link_id == link_id).select(
                to_link_table.ALL).first()
            links = CustomLinks(entity_table, record.id)
            links.move_link(to_link_record.id, direction=request.vars.dir)
            record_id = link_id
        else:
            return do_error('Invalid data provided')
    if do_reorder:
        reorder_query = (to_link_join_field == record.id)
        reorder(
            to_link_table.order_no,
            query=reorder_query,
        )
    result = {
        'id': record_id,
        'rows': rows,
        'errors': errors,
    }
    if new_value != None:
        result['newValue'] = new_value
    return result


@auth.requires_login()
def metadata_crud():
    """Handler for ajax metadata CRUD calls.

    request.args(0): integer, book id.

    request.vars._action: string, 'get', 'update'

        get: Return the metadata in json format.
        update: expect POST json data and create/update metadata records as
            necesary.
    """
    # too-many-return-statements (R0911): *Too many return statements*
    # pylint: disable=R0911
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    # W0212 (protected-access): *Access to a protected member
    # pylint: disable=W0212
    actions = ['get', 'update']
    if not request.vars._action or request.vars._action not in actions:
        return do_error('Invalid data provided')
    action = request.vars._action

    book_record = None
    try:
        book_id = int(request.args(0))
    except (TypeError, ValueError):
        return do_error('Invalid data provided')
    book_record = entity_to_row(db.book, book_id)
    if not book_record or (
            book_record and book_record.creator_id != creator_record.id):
        return do_error('Invalid data provided')

    if action == 'get':
        data = {
            'publication_metadata': {
                'fields': {},
                'record': {},
                'default': {},
            },
            'publication_serial': {
                'fields': {},
                'records': [],
                'default': {},
            },
            'derivative': {
                'fields': {},
                'record': {},
                'default': {},
            },
        }

        for f in db.publication_metadata.fields:
            data['publication_metadata']['fields'][f] = {
                'name': db.publication_metadata[f].name,
                'label': db.publication_metadata[f].label,
            }

        number_ddm = {
            'type': 'select',
            'source': [{'value': x, 'text': x or ''} for x in range(0, 101)]
        }

        published_format_ddm = {
            'type': 'select',
            'source': [
                {'value': 'digital', 'text': 'Digital'},
                {'value': 'paper', 'text': 'Paper'}
            ],
        }

        publisher_type_ddm = {
            'type': 'select',
            'source': [
                {'value': 'press', 'text': 'Press'},
                {'value': 'self', 'text': 'Self'}
            ],
        }

        year_ddm = {
            'type': 'select',
            'source': [
                {'value': x, 'text': x}
                for x in sorted(range(*publication_year_range()), reverse=True)
            ]
        }

        data['publication_metadata']['fields']['republished'].update({
            'type': 'select',
            'source': [
                {'value': '', 'text': ''},
                {'value': 'first', 'text': 'First publication'},
                {'value': 'repub', 'text': 'Republication'}
            ],
        })

        data['publication_metadata']['fields']['published_type'].update({
            'type': 'select',
            'source': [
                {'value': '', 'text': ''},
                {'value': 'whole', 'text': 'Republication - whole'},
                {'value': 'serial', 'text': 'Republication - serial'}
            ],
        })

        data['publication_metadata']['fields']['is_anthology'].update({
            'type': 'select',
            'source': [
                {'value': 'yes', 'text': 'Yes'},
                {'value': 'no', 'text': 'No'}
            ],
        })

        data['publication_metadata']['fields']['published_format'].update(
            published_format_ddm)
        data['publication_metadata']['fields']['publisher_type'].update(
            publisher_type_ddm)
        data['publication_metadata']['fields']['from_year'].update(year_ddm)
        data['publication_metadata']['fields']['to_year'].update(year_ddm)

        for f in db.publication_serial.fields:
            data['publication_serial']['fields'][f] = {
                'name': db.publication_serial[f].name,
                'label': db.publication_serial[f].label,
            }

        data['publication_serial']['fields']['serial_number'].update(
            number_ddm)
        data['publication_serial']['fields']['published_format'].update(
            published_format_ddm)
        data['publication_serial']['fields']['publisher_type'].update(
            publisher_type_ddm)
        data['publication_serial']['fields']['story_number'].update(
            number_ddm)
        data['publication_serial']['fields']['from_year'].update(year_ddm)
        data['publication_serial']['fields']['to_year'].update(year_ddm)

        for f in db.derivative.fields:
            data['derivative']['fields'][f] = {
                'name': db.derivative[f].name,
                'label': db.derivative[f].label,
            }
        data['derivative']['fields']['is_derivative'] = {
            'name': 'is_derivative',
            'label': 'Derivative Work',
            'type': 'select',
            'source': [
                {'value': 'no', 'text': 'No'},
                {'value': 'yes', 'text': 'Yes'}
            ],
        }
        data['derivative']['fields']['from_year'].update(year_ddm)
        data['derivative']['fields']['to_year'].update(year_ddm)

        # Exclude 'NoDerivs' licences
        query = (db.cc_licence.code.like('CC BY%')) & \
                (~db.cc_licence.code.like('%-ND'))
        licences = db(query).select(
            db.cc_licence.ALL,
            orderby=db.cc_licence.number
        )

        cc_licence_id = cc_licence_by_code(
            CreatorIndiciaPage.default_licence_code, want='id', default=0)

        data['derivative']['fields']['cc_licence_id'].update({
            'type': 'select',
            'source': [{'value': x.id, 'text': x.code} for x in licences]
        })

        for table in data.keys():
            data[table]['default'] = default_record(
                db[table], ignore_fields='common')

        data['publication_metadata']['default'].update({
            'published_name': book_record.name,
        })

        data['publication_serial']['default'].update({
            'published_name': book_record.name,
            'serial_title': book_record.name,
        })

        data['derivative']['default'].update({
            'is_derivative': 'no',
            'cc_licence_id': cc_licence_id,
        })

        query = (db.publication_metadata.book_id == book_record.id)
        metadata_record = db(query).select(
            orderby=[db.publication_metadata.id],
        ).first()
        if metadata_record:
            data['publication_metadata']['record'] = metadata_record.as_dict()
        else:
            data['publication_metadata']['record'] = \
                data['publication_metadata']['default']

        query = (db.publication_serial.book_id == book_record.id)
        data['publication_serial']['records'] = db(query).select(
            orderby=[
                db.publication_serial.sequence,
                db.publication_serial.id,
            ],
        ).as_list()

        query = (db.derivative.book_id == book_record.id)
        derivative_record = db(query).select().first()
        if derivative_record:
            data['derivative']['record'] = derivative_record.as_dict()
            data['derivative']['record']['is_derivative'] = 'yes'
        else:
            data['derivative']['record'] = data['derivative']['default']
        return {'status': 'ok', 'data': data}

    if action == 'update':
        meta = PublicationMetadata(book_record)
        meta.load_from_vars(dict(request.vars))
        meta.validate()
        if meta.errors:
            return {'status': 'error', 'fields': meta.errors}
        meta.update()
        return {'status': 'ok'}
    return do_error('Invalid data provided')


@auth.requires_login()
def metadata_poc():
    """Temporary controller for metadata POC. FIXME delete"""
    query = db.book.name == 'Test Do Not Delete'
    book = db(query).select().first()
    return dict(book=book)


@auth.requires_login()
def metadata_text():
    """Handler for ajax call to get metadata text.

    request.args(0): integer, book id.
    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    book_record = None
    try:
        book_id = int(request.args(0))
    except (TypeError, ValueError):
        return do_error('Invalid data provided')
    book_record = entity_to_row(db.book, book_id)
    if not book_record or (
            book_record and book_record.creator_id != creator_record.id):
        return do_error('Invalid data provided')

    meta = PublicationMetadata(book_record)
    if not meta:
        return do_error('Invalid data provided')
    meta.load()
    return {'status': 'ok', 'text': str(meta)}


@auth.requires_login()
def modal_error():
    """Controller for displaying error messages within modal.

    request.vars.message: string, error message
    """
    return dict(message=request.vars.message)


@auth.requires_login()
def profile():
    """Creator profile controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    response.files.append(
        URL('static', 'blueimp/jQuery-File-Upload/css/jquery.fileupload.css')
    )
    response.files.append(
        URL(
            'static',
            'blueimp/jQuery-File-Upload/css/jquery.fileupload-ui.css'
        )
    )
    response.files.append(
        URL(
            'static',
            'x-editable/bootstrap3-editable/css/bootstrap-editable.css'
        )
    )

    return dict(creator=creator_record)
