# -*- coding: utf-8 -*-
"""Creator profile controller functions"""
import os
import shutil
import datetime
from gluon.contrib.simplejson import dumps
from applications.zcomix.modules.book_upload import BookPageUploader
from applications.zcomix.modules.books import \
    book_pages_as_json, \
    defaults as book_defaults, \
    is_releasable, \
    numbers_for_book_type, \
    read_link
from applications.zcomix.modules.creators import image_as_json
from applications.zcomix.modules.images import \
    UploadImage, \
    store
from applications.zcomix.modules.links import CustomLinks
from applications.zcomix.modules.shell_utils import \
    TemporaryDirectory
from applications.zcomix.modules.utils import \
    markmin_content, \
    reorder


@auth.requires_login()
def account():
    """Account profile controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))

    return dict(creator=creator_record)


@auth.requires_login()
def book_crud():
    """Handler for ajax book CRUD calls.

    request.args(0): integer, id of book

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
    response.generic_patterns = ['json']

    def do_error(msg=None):
        return {'status': 'error', 'msg': msg or 'Server request failed.'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied.')

    # W0212 (protected-access): *Access to a protected member %%s of a client class*
    # pylint: disable=W0212
    actions = ['create', 'delete', 'release', 'update']
    if not request.vars._action or request.vars._action not in actions:
        return do_error('Invalid data provided.')
    action = request.vars._action

    book_record = None
    if action != 'create':
        try:
            book_id = int(request.vars.pk)
        except (TypeError, ValueError):
            return do_error('Invalid data provided.')
        book_record = db(db.book.id == book_id).select(
            db.book.ALL
        ).first()
        if not book_record or \
            (book_record and book_record.creator_id != creator_record.id):
            return do_error('Invalid data provided.')

    if action == 'create':
        data = {}
        # Validate all fields.
        if request.vars.name is not None and request.vars.value is not None:
            book_name = request.vars.value.strip()
            data = book_defaults(db, book_name, creator_record)
            data[request.vars.name] = book_name
        ret = db.book.validate_and_insert(**data)

        if ret.errors:
            if request.vars.name in ret.errors:
                return {'status': 'error', 'msg': ret.errors[request.vars.name]}
            else:
                return {
                    'status': 'error',
                    'msg': ', '.join(['{k}: {v}'.format(k=k, v=v) for k, v in ret.errors.items()])
                }
        if ret.id:
            return {
                'id': ret.id,
                'status': 'ok',
            }
        return do_error('Unable to create book.')

    if action == 'delete':
        # FIXME delete torrent
        # FIXME remove book from creator torrent
        # FIXME remove book from ALL torrent

        # Delete all records associated with the book.
        for t in ['book_page', 'book_view', 'contribution', 'rating']:
            db(db[t].book_id == book_record.id).delete()

        # Delete all links associated with the book.
        query = db.book_to_link.book_id == book_record.id
        for row in db(query).select(db.book_to_link.link_id):
            db(db.link.id == row['link_id']).delete()
        db(db.book_to_link.book_id == book_record.id).delete()

        # Delete the book
        db(db.book.id == book_record.id).delete()
        db.commit()
        return {'status': 'ok'}

    if action == 'release':
        if not is_releasable(db, book_record):
            return do_error('This book cannot be released.')

        book_record.update_record(
            release_date=datetime.datetime.today()
        )
        db.commit()
        # FIXME create torrent
        # FIXME add book to creator torrent
        # FIXME add book to ALL torrent
        return {'status': 'ok'}

    if action == 'update':
        if request.vars.name is not None and request.vars.name not in db.book.fields:
            return do_error('Invalid data provided.')

        data = {}
        if request.vars.name is not None and request.vars.value is not None:
            data = {request.vars.name: request.vars.value}
        if not data:
            return do_error('Invalid data provided.')

        query = (db.book.id == book_record.id)
        ret = db(query).validate_and_update(**data)
        db.commit()

        if ret.errors:
            if request.vars.name in ret.errors:
                return {'status': 'error', 'msg': ret.errors[request.vars.name]}
            else:
                return {
                    'status': 'error',
                    'msg': ', '.join(['{k}: {v}'.format(k=k, v=v) for k, v in ret.errors.items()])
                }
        numbers = numbers_for_book_type(db, request.vars.value) \
                if request.vars.name == 'book_type_id' else None
        return {'status': 'ok', 'numbers': numbers}
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
        redirect(URL('modal_error', vars={'message': 'Permission denied.'}))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided.'}))

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
        redirect(URL('modal_error', vars={'message': 'Permission denied.'}))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()

    book_type_id = book_record.book_type_id if book_record else 0
    numbers = numbers_for_book_type(db, book_type_id)

    return dict(book=book_record, numbers=dumps(numbers))


@auth.requires_login()
def book_list():
    """Book list component controller."""


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
        book_records = db(query).select(db.book.ALL, orderby=[db.book.name, db.book.number])
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
        redirect(URL('modal_error', vars={'message': 'Permission denied.'}))

    book_record = None
    if request.args(0):
        query = (db.book.id == request.args(0))
        book_record = db(query).select(db.book.ALL).first()
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided.'}))

    read_button = read_link(
        db,
        book_record,
        **dict(
            _class='btn btn-default btn-lg',
            _type='button',
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
    def do_error(msg):
        return dumps({'files': [{'error': msg}]})

    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Upload service unavailable.')

    book_record = None
    if request.args(0):
        query = (db.book.id == request.args(0))
        book_record = db(query).select(db.book.ALL).first()
    if not book_record or book_record.creator_id != creator_record.id:
        return do_error('Upload service unavailable.')

    if request.env.request_method == 'POST':
        # Create a book_page record for each upload.
        files = request.vars['up_files[]']
        if not isinstance(files, list):
            files = [files]
        return BookPageUploader(book_record.id, files).upload()
    elif request.env.request_method == 'DELETE':
        book_page_id = request.vars.book_page_id
        book_page = db(db.book_page.id == book_page_id).select().first()
        if not book_page:
            return do_error('Unable to delete page.')

        # retrieve real file name
        filename, _ = db.book_page.image.retrieve(
            book_page.image,
            nameonly=True,
        )
        up_image = UploadImage(db.book_page.image, book_page.image)
        up_image.delete_all()
        book_page.delete_record()
        return dumps({"files": [{filename: True}]})
    else:
        # GET
        return book_pages_as_json(db, book_record.id)


@auth.requires_login()
def book_pages_reorder():
    """Callback function for reordering book pages.

    request.args(0): integer, id of book.
    request.vars.book_page_ids[], list of book page ids.
    """
    def do_error(msg):
        return dumps({'success': False, 'error': msg})

    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Reorder service unavailable.')

    book_record = None
    if request.args(0):
        query = (db.book.id == request.args(0))
        book_record = db(query).select(db.book.ALL).first()
    if not book_record or book_record.creator_id != creator_record.id:
        return do_error('Reorder service unavailable.')

    if not 'book_page_ids[]' in request.vars:
        # Nothing to do
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
        query = (db.book_page.id == page_id)
        page_record = db(query).select(db.book_page.ALL).first()
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
        redirect(URL('modal_error', vars={'message': 'Permission denied.'}))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided.'}))

    return dict(
        book=book_record,
        releasable=is_releasable(db, book_record),
    )


@auth.requires_login()
def books():
    """Books controller.

    request.vars.can_release: mixed, if set, released books are displayed.
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
        URL('static', 'x-editable/bootstrap3-editable/css/bootstrap-editable.css')
    )

    query = (db.book.creator_id == creator_record.id) & \
            (db.book.status == False)
    has_disabled = db(query).count()

    return dict(has_disabled=has_disabled)


@auth.requires_login()
def creator():
    """Creator controller."""
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
        URL('static', 'x-editable/bootstrap3-editable/css/bootstrap-editable.css')
    )

    return dict(creator=creator_record)


@auth.requires_login()
def creator_crud():
    """Handler for ajax creator CRUD calls.

    request.vars.name: string, creator table field name
    request.vars.value: string, value of creator table field.
    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        errors = {'url': msg or 'Server request failed.'}
        return {'errors': errors}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied.')

    if request.vars.name is not None and request.vars.name not in db.creator.fields:
        return do_error('Invalid data provided.')

    data = {}
    if request.vars.name is not None and request.vars.value is not None:
        data = {request.vars.name: request.vars.value}
    if not data:
        return do_error('Invalid data provided.')

    query = (db.creator.id == creator_record.id)
    ret = db(query).validate_and_update(**data)
    db.commit()

    if ret.errors:
        if request.vars.name in ret.errors:
            return {'status': 'error', 'msg': ret.errors[request.vars.name]}
        else:
            return {
                'status': 'error',
                'msg': ', '.join(['{k}: {v}'.format(k=k, v=v) for k, v in ret.errors.items()])
            }
    return {'status': 'ok'}


@auth.requires_login()
def creator_img_handler():
    """Callback function for the jQuery-File-Upload plugin.

    # POST
    request.vars.up_files: list of files representing creator image.
    """
    def do_error(msg):
        return dumps({'files': [{'error': msg}]})

    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Upload service unavailable.')

    if request.env.request_method == 'POST':
        # Create a book_page record for each upload.
        files = request.vars.up_files
        if not isinstance(files, list):
            files = [files]
        file = files[0]

        with TemporaryDirectory() as tmp_dir:
            local_filename = os.path.join(tmp_dir, file.filename)
            with open(local_filename, 'w+b') as lf:
                # This will convert cgi.FieldStorage to a regular file.
                shutil.copyfileobj(file.file, lf)

            try:
                stored_filename = store(db.creator.image, local_filename)
            except:
                stored_filename = None

        if not stored_filename:
            return do_error('File upload failed.')

        if creator_record.image and creator_record.image != stored_filename:
            filename, _ = db.creator.image.retrieve(
                creator_record.image,
                nameonly=True,
            )
            db(db.creator.id == creator_record.id).update(image=None)
            db.commit()
            up_image = UploadImage(db.creator.image, creator_record.image)
            up_image.delete_all()

        db(db.creator.id == creator_record.id).update(
            image=stored_filename,
        )
        db.commit()
        return image_as_json(db, creator_record.id)

    elif request.env.request_method == 'DELETE':
        # retrieve real file name
        if not creator_record.image:
            return do_error('')

        filename, _ = db.creator.image.retrieve(
            creator_record.image,
            nameonly=True,
        )
        db(db.creator.id == creator_record.id).update(image=None)
        db.commit()
        up_image = UploadImage(db.creator.image, creator_record.image)
        up_image.delete_all()
        return dumps({"files": [{filename: 'true'}]})

    # GET
    return image_as_json(db, creator_record.id)


@auth.requires_login()
def faq():
    """FAQ profile controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))

    return dict(text=markmin_content('faq.mkd'))


@auth.requires_login()
def faqc():
    """Creator FAQ profile controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))

    return dict(text=markmin_content('faqc.mkd'))


@auth.requires_login()
def index():
    """Creator profile controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))
    redirect(URL(c='profile', f='books'))


@auth.requires_login()
def link_crud():
    """Handler for ajax link CRUD calls.
    request.args(0): integer, optional, if provided, id of book record. All
        actions are done on book links. If not provided, actions are done on
        creator links.

    request.vars.action: string, one of 'get', 'create', 'update', 'delete', 'move'

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
    response.generic_patterns = ['json']

    def do_error(msg=None):
        return {'status': 'error', 'msg': msg or 'Server request failed.'}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    record_id = 0
    rows = []
    errors = {}     # Row() or dict

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
        if not book_record:
            return do_error('Invalid data provided.')

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
        link_record = db(db.link.id == link_id).select(db.link.ALL).first()
        if not link_record:
            return do_error('Invalid data provided.')

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
            if request.vars.field is not None and request.vars.value is not None:
                data = {request.vars.field: request.vars.value}
            if data:
                query = (db.link.id == link_id)
                ret = db(query).validate_and_update(**data)
                db.commit()
                record_id = link_id
                if ret.errors:
                    if request.vars.field in ret.errors:
                        return {'status': 'error', 'msg': ret.errors[request.vars.field]}
                    else:
                        return {
                            'status': 'error',
                            'msg': ', '.join(['{k}: {v}'.format(k=k, v=v) for k, v in ret.errors.items()])
                        }
                do_reorder = True
        else:
            return do_error('Invalid data provided.')
    elif action == 'create':
        ret = db.link.validate_and_insert(
            url=request.vars.url,
            name=request.vars.name,
        )
        db.commit()
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
            return do_error('Invalid data provided.')
    elif action == 'move':
        if link_id:
            filter_field = to_link_join_field.name
            to_link_record = db(to_link_table.link_id == link_id).select(to_link_table.ALL).first()
            links = CustomLinks(entity_table, record.id)
            links.move_link(to_link_record.id, direction=request.vars.dir)
            record_id = link_id
        else:
            return do_error('Invalid data provided.')
    if do_reorder:
        reorder_query = (to_link_join_field == record.id)
        reorder(
            to_link_table.order_no,
            query=reorder_query,
        )
    return {
        'id': record_id,
        'rows': rows,
        'errors': errors,
    }


@auth.requires_login()
def modal_error():
    """Controller for displaying error messages within modal.

    request.vars.message: string, error message
    """
    return dict(message=request.vars.message)
