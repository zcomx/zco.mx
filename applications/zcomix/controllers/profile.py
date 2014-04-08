# -*- coding: utf-8 -*-
"""Creator profile controller functions"""

import datetime
from gluon.contrib.simplejson import dumps
from applications.zcomix.modules.books import \
    book_pages_as_json, \
    book_page_for_json, \
    read_link
from applications.zcomix.modules.creators import image_as_json
from applications.zcomix.modules.images import \
    UploadImage, \
    img_tag, \
    set_thumb_dimensions
from applications.zcomix.modules.links import \
    CustomLinks, \
    ReorderLink
from applications.zcomix.modules.utils import \
    move_record, \
    reorder
from applications.zcomix.modules.stickon.sqlhtml import \
    InputWidget, \
    SimpleUploadWidget, \
    LocalSQLFORM, \
    formstyle_bootstrap3_custom


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
def book_add():
    """Add a book and redirect to book_edit controller.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('books'))

    query = (db.book.creator_id == creator_record.id) &  \
            (db.book.name.like('__Untitled%__'))
    try:
        count = len(db(query).select(db.book.id)) + 1
    except TypeError:
        count = 1

    name = '__Untitled-{nn:02d}__'.format(nn=count)

    book_id = db.book.insert(
        name=name,
        creator_id=creator_record.id,
    )
    db.commit()

    book_record = db(db.book.id == book_id).select(
        db.book.ALL
    ).first()
    if (not book_record) or \
            (book_record and book_record.creator_id != creator_record.id):
        redirect(URL('books'))

    redirect(URL('book_edit', args=book_record.id))


@auth.requires_login()
def book_crud():
    """Handler for ajax book CRUD calls.

    request.args(0): integer, id of book
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

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if (request.args(0) and not book_record) or \
            (book_record and book_record.creator_id != creator_record.id):
        return do_error('Invalid data provided.')

    if request.vars.field is not None and request.vars.field not in db.book.fields:
        return do_error('Invalid data provided.')

    data = {}
    if request.vars.field is not None and request.vars.value is not None:
        data = {request.vars.field: request.vars.value}
    if not data:
        return do_error('Invalid data provided.')

    query = (db.book.id == book_record.id)
    ret = db(query).validate_and_update(**data)

    return {
        'errors': ret.errors,
    }


@auth.requires_login()
def book_delete():
    """Delete a book controller.

    request.args(0): integer, id of book.
    """
    import sys; print >> sys.stderr, 'FIXME request.args: {var}'.format(var=request.args)
    import sys; print >> sys.stderr, 'FIXME request.vars: {var}'.format(var=request.vars)
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('books'))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(URL('books'))

    form = SQLFORM.factory(
        Field('dummy'),
        _action=URL('book_delete', args=request.args),
    )

    success_msg = '{name} deleted.'.format(name=book_record.name)

    if form.process(
        keepvalues=True,
        formname='book_delete',
        message_onsuccess=success_msg
    ).accepted:
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

        redirect(URL('books'))
    elif form.errors:
        response.flash = 'Form could not be submitted.' + \
            ' Please make corrections.'

    return dict(
        book=book_record,
        form=form,
    )


@auth.requires_login()
def book_edit():
    """Book edit controller for modal view.

    request.args(0): integer, id of book
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('books'))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if not book_record or \
            (book_record and book_record.creator_id != creator_record.id):
        redirect(URL('books'))

    return dict(book=book_record)


@auth.requires_login()
def book_pages():
    """Creator profile book pages component. (Multiple file upload.)

    request.args(0): integer, id of book.
    """
    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('books'))

    book_record = None
    if request.args(0):
        query = (db.book.id == request.args(0))
        book_record = db(query).select(db.book.ALL).first()
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(URL('books'))

    response.files.append(
        URL('static', 'blueimp/jQuery-File-Upload/css/jquery.fileupload.css')
    )
    response.files.append(
        URL(
            'static',
            'blueimp/jQuery-File-Upload/css/jquery.fileupload-ui.css'
        )
    )

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
        files = request.vars.up_files
        if not isinstance(files, list):
            files = [files]
        max_page = db.book_page.page_no.max()
        page_no = db().select(max_page)[0][max_page]
        book_page_ids = []
        for file in files:
            stored_filename = db.book_page.image.store(file, file.filename)
            page_no = page_no + 1
            page_id = db.book_page.insert(
                book_id=book_record.id,
                page_no=page_no,
                image=stored_filename,
                thumb_shrink=1,
            )
            db.commit()
            resizer = UploadImage(db.book_page.image, stored_filename)
            resizer.resize_all()
            set_thumb_dimensions(db, page_id, resizer.dimensions(size='thumb'))
            book_page_ids.append(page_id)
        # Make sure page_no values are sequential
        reorder_query = (db.book_page.book_id == book_record.id)
        reorder(db.book_page.page_no, query=reorder_query)
        return book_pages_as_json(db, book_record.id, book_page_ids=book_page_ids)
    elif request.env.request_method == 'DELETE':
        book_page_id = request.vars.book_page_id
        book_page = db(db.book_page.id == book_page_id).select().first()
        # retrieve real file name
        filename, _ = db.book_page.image.retrieve(
            book_page.image,
            nameonly=True,
        )
        resizer = UploadImage(db.book_page.image, book_page.image)
        resizer.delete_all()
        book_page.delete_record()
        # Make sure page_no values are sequential
        reorder_query = (db.book_page.book_id == book_record.id)
        reorder(db.book_page.page_no, query=reorder_query)
        return dumps({"files": [{filename: 'true'}]})
    else:
        # GET
        return book_pages_as_json(db, book_record.id)


@auth.requires_login()
def book_pages_reorder():
    """Callback function for reordering book pages.

    request.args(0): integer, id of book.
    request.vars.book_page_id: integer, id of book_page
    request.vars.dir: string, direction to move page, 'up'(default) or 'down'
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

    page_record = None
    if request.vars.book_page_id:
        query = (db.book_page.id == request.vars.book_page_id)
        page_record = db(query).select(db.book_page.ALL).first()
    if not page_record:
        return do_error('Reorder service unavailable.')

    direction = request.vars.dir or 'up'
    if direction not in ['up', 'down']:
        direction = 'up'

    move_record(
        db.book_page.page_no,
        page_record.id,
        direction=direction,
        query=(db.book_page.book_id == book_record.id),
    )
    return dumps({'success': True})


@auth.requires_login()
def book_release():
    """Release a book controller.

    request.args(0): integer, id of book.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('books'))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if not book_record or book_record.creator_id != creator_record.id:
        redirect(URL('books'))

    page_count = db(db.book_page.book_id == book_record.id).count()

    form = SQLFORM.factory(
        Field('dummy'),
        _action=URL('book_release', args=request.args),
    )

    success_msg = '{name} released.'.format(name=book_record.name)

    if form.process(
        keepvalues=True,
        formname='book_release',
        message_onsuccess=success_msg
    ).accepted:
        book_record.update_record(
            release_date=datetime.datetime.today()
        )
        db.commit()
        # FIXME create torrent
        # FIXME add book to creator torrent
        # FIXME add book to ALL torrent
        redirect(URL('books'))
    elif form.errors:
        response.flash = 'Form could not be submitted.' + \
            ' Please make corrections.'

    return dict(
        book=book_record,
        form=form,
        page_count=page_count,
    )


@auth.requires_login()
def books():
    """Books controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    response.files.append(
        URL('static', 'bgrins-spectrum-28ab793/spectrum.css')
    )

    response.files.append(
        URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
    )

    creator_query = (db.book.creator_id == creator_record.id)
    released_query = creator_query & (db.book.release_date != None)
    released = db(released_query).select(db.book.ALL, orderby=db.book.name)
    ongoing_query = creator_query & (db.book.release_date == None)
    ongoing = db(ongoing_query).select(db.book.ALL, orderby=db.book.name)

    return dict(
        ongoing=ongoing,
        released=released,
    )


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

    return dict(creator=creator_record)


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

        try:
            stored_filename = db.creator.image.store(file, file.filename)
        except:
            stored_filename = None

        if not stored_filename:
            return do_error('')

        if creator_record.image and creator_record.image != stored_filename:
            filename, _ = db.creator.image.retrieve(
                creator_record.image,
                nameonly=True,
            )
            db(db.creator.id == creator_record.id).update(image=None)
            db.commit()
            resizer = UploadImage(db.creator.image, creator_record.image)
            resizer.delete_all()

        db(db.creator.id == creator_record.id).update(
            image=stored_filename,
        )
        db.commit()
        resizer = UploadImage(db.creator.image, stored_filename)
        resizer.resize_all()

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
        resizer = UploadImage(db.creator.image, creator_record.image)
        resizer.delete_all()
        return dumps({"files": [{filename: 'true'}]})

    # GET
    return image_as_json(db, creator_record.id)


@auth.requires_login()
def creator_crud():
    """Handler for ajax creator CRUD calls.

    request.vars.field: string, creator table field name
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

    if request.vars.field is not None and request.vars.field not in db.creator.fields:
        return do_error('Invalid data provided.')

    data = {}
    if request.vars.field is not None and request.vars.value is not None:
        data = {request.vars.field: request.vars.value}
    if not data:
        return do_error('Invalid data provided.')

    query = (db.creator.id == creator_record.id)
    ret = db(query).validate_and_update(**data)

    return {
        'errors': ret.errors,
    }


@auth.requires_login()
def index():
    """Creator profile controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL(c='default', f='index'))

    return dict(creator=creator_record)


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
        errors = {'url': msg or 'Server request failed.'}
        return {'errors': errors}

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return do_error('Permission denied')

    record_id = 0
    rows = []
    errors = []

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
                record_id = link_id
                errors = ret.errors
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
        errors = ret.errors
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
def order_no_handler():
    """Handler for order_no sorting.

    request.args(0): string, link table name, eg creator_to_link
    request.args(1): integer, id of record in table.
    request.args(2): string, direction, 'up' or 'down'
    """
    next_url = request.vars.next or URL(c='default', f='index')

    if not request.args(0):
        redirect(next_url, client_side=False)
    table = db[request.args(0)]

    if not request.args(1):
        redirect(next_url, client_side=False)
    record = db(table.id == request.args(1)).select(table.ALL).first()
    if not record:
        redirect(next_url, client_side=False)
    if not record.order_no:
        redirect(next_url, client_side=False)

    custom_links_table = db.book if request.args(0) == 'book_to_link' \
        else db.creator
    filter_field = 'book_id' if request.args(0) == 'book_to_link' \
        else 'creator_id'
    custom_links_id = record[filter_field]
    links = CustomLinks(custom_links_table, custom_links_id)
    links.move_link(request.args(1), request.args(2))

    redirect(next_url, client_side=False)
