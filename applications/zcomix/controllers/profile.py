# -*- coding: utf-8 -*-
"""Creator profile controller functions"""

import datetime
from gluon.contrib.simplejson import dumps, loads
from applications.zcomix.modules.books import \
    book_pages_as_json, \
    book_page_for_json, \
    read_link
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
def book_edit():
    """Book edit controller.

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
    if (request.args(0) and not book_record) or \
            (book_record and book_record.creator_id != creator_record.id):
        redirect(URL('books'))

    response.files.append(
        URL('static', 'bgrins-spectrum-28ab793/spectrum.css')
    )
    response.files.append(
        URL('static', 'bgrins-spectrum-28ab793/spectrum.js')
    )
    response.files.append(
        URL('static', 'js/book_edit.js')
    )

    crud.settings.update_deletable = False
    crud.settings.formstyle = formstyle_bootstrap3_custom
    if request.args(0):
        # Reload page to prevent consecutive self-submit warnings
        crud.settings.update_next = URL('book_edit', args=request.args)
        form = crud.update(db.book, book_record.id)
    else:
        db.book.creator_id.default = creator_record.id
        crud.settings.create_next = URL('books')
        form = crud.create(db.book)

    return dict(form=form)


@auth.requires_login()
def book_link_edit():
    """Book edit controller.

    request.args(0): integer, id of book
    request.args(1): integer, id of link record. Optional if None or 0, form
        is in create mode.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('book_links'))

    book_record = None
    if request.args(0):
        book_record = db(db.book.id == request.args(0)).select(
            db.book.ALL
        ).first()
    if (request.args(0) and not book_record) or \
            (book_record and book_record.creator_id != creator_record.id):
        redirect(URL('book_links'))

    def oncreate(form):
        """Callback for oncreate."""
        # Create book_to_link record for the new link.
        order_no = db(db.book_to_link.book_id == book_record.id).count() + 1
        db.book_to_link.insert(
            book_id=book_record.id,
            link_id=form.vars.id,
            order_no=order_no,
        )
        db.commit()

    crud.settings.update_deletable = False
    crud.settings.formstyle = formstyle_bootstrap3_custom
    if request.args(1):
        crud.settings.update_next = URL('book_links', args=request.args(0))
        form = crud.update(db.link, request.args(1))
    else:
        crud.settings.create_next = URL('book_links', args=request.args(0))
        crud.settings.create_onaccept = [oncreate]
        form = crud.create(db.link)

    return dict(
        book=book_record,
        creator=creator_record,
        form=form,
    )


@auth.requires_login()
def book_links():
    """Book links controller.

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

    return dict(
        book=book_record,
        creator=creator_record,
    )


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
        do_error('Upload unavailable')
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

    request.args(0): integer, id of book. Optional, if provided, only
        links associated with that book are listed. Otherwise only books for
        the logged in creator are listed.
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
        Field(
            'cancel',
            default='Cancel',
            widget=InputWidget({
                '_type': 'button',
                '_onclick': 'history.go(-1); return false;'
            }).widget,
        ),
        submit_button='Release',
    )

    if form.accepts(
        request.vars,
        session,
        formname='book_release',
        keepvalues=True
    ):
        book_record.update_record(
            release_date=datetime.datetime.today()
        )
        db.commit()
        # FIXME create torrent
        # FIXME add book to creator torrent
        # FIXME add book to ALL torrent
        session.flash = '{name} released.'.format(
            name=book_record.name
        )
        redirect(URL('books'))
    elif form.errors:
        response.flash = 'Form could not be submitted.' + \
            ' Please make corrections.'

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
        creator=creator_record,
        form=form,
        page_count=page_count,
        read_button=read_button,
    )


@auth.requires_login()
def books():
    """Creator links controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    return dict(creator=creator_record)


@auth.requires_login()
def creator():
    """Creator links controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    def custom_delete(oldname):
        resizer = UploadImage(db.creator.image, oldname)
        resizer.delete_all()

    def onupdate(form):
        """On update callback function"""
        if form.vars.image:
            resizer = UploadImage(db.creator.image, form.vars.image)
            resizer.resize_all()

    # custom_delete is not defined in the model to keep the model lean.
    db.creator.image.custom_delete = custom_delete

    crud.settings.update_onaccept = [onupdate]
    # Reload page to prevent consecutive self-submit warnings
    crud.settings.update_next = URL('creator')
    crud.settings.update_deletable = False
    crud.settings.formstyle = formstyle_bootstrap3_custom
    form = crud.update(db.creator, creator_record.id)

    return dict(form=form)


@auth.requires_login()
def creator_link_edit():
    """Creator link edit controller.

    request.args(0): integer, id of link record. Optional if None or 0, form
        is in create mode.
    """
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('creator_links'))

    def oncreate(form):
        """Callback for oncreate."""
        # Create creator_to_link record for the new link.
        order_no = db(db.creator_to_link.creator_id == creator_record.id).count() + 1
        db.creator_to_link.insert(
            creator_id=creator_record.id,
            link_id=form.vars.id,
            order_no=order_no,
        )
        db.commit()

    crud.settings.update_deletable = False
    crud.settings.formstyle = formstyle_bootstrap3_custom
    if request.args(0):
        crud.settings.update_next = URL('creator_links')
        form = crud.update(db.link, request.args(0))
    else:
        crud.settings.create_next = URL('creator_links')
        crud.settings.create_onaccept = [oncreate]
        form = crud.create(db.link)

    return dict(form=form)


@auth.requires_login()
def creator_links():
    """Creator links controller."""
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))
    return dict(creator=creator_record)


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
def links():
    """Controller for links grid component.

    request.vars.book_id: integer, id of book. Optional, if provided, only
        links associated with that book are listed. Otherwise only books for
        the logged in creator are listed.
    """
    # Verify user is legit
    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        redirect(URL('index'))

    book_record = None
    if request.vars.book_id:
        book_record = db(db.book.id == request.vars.book_id).select(
            db.book.ALL
        ).first()
        if not book_record or book_record.creator_id != creator_record.id:
            redirect(URL('books'))

    fields = [
        db.link.name,
        db.link.url,
        db.link.title,
    ]

    if book_record:
        link_table = db.book_to_link
        db.book_to_link.id.readable = False
        db.book_to_link.id.writable = False
        db.book_to_link.book_id.readable = False
        db.book_to_link.book_id.writable = False
        fields.append(db.book_to_link.id)
        fields.append(db.book_to_link.book_id)
        fields.append(db.book_to_link.order_no)
        query = (db.link.id > 0) & \
                (db.book_to_link.id != None) & \
                (db.book.id == book_record.id)
        left = [
            db.book_to_link.on(db.book_to_link.link_id == db.link.id),
            db.book.on(db.book_to_link.book_id == db.book.id),
        ]
        orderby = [db.book_to_link.order_no, db.book_to_link.id]
        next_url = URL(c='profile', f='book_links', args=request.vars.book_id, extension=False)
    else:
        link_table = db.creator_to_link
        db.creator_to_link.id.readable = False
        db.creator_to_link.id.writable = False
        db.creator_to_link.creator_id.readable = False
        db.creator_to_link.creator_id.writable = False
        fields.append(db.creator_to_link.id)
        fields.append(db.creator_to_link.creator_id)
        fields.append(db.creator_to_link.order_no)
        query = (db.link.id > 0) & \
                (db.creator_to_link.id != None) & \
                (db.creator.id == creator_record.id)
        left = [
            db.creator_to_link.on(
                (db.creator_to_link.link_id == db.link.id)
            ),
            db.creator.on(db.creator_to_link.creator_id == db.creator.id),
        ]
        orderby = [db.creator_to_link.order_no, db.creator_to_link.id]
        next_url = URL(c='profile', f='creator_links', extension=False)

    def oncreate(form):
        """Callback for oncreate."""
        if book_record:
            order_no = db(
                db.book_to_link.book_id == book_record.id
            ).count() + 1
            db.book_to_link.insert(
                book_id=book_record.id,
                link_id=form.vars.id,
                order_no=order_no,
            )
            db.commit()
        else:
            order_no = db(db.creator_to_link.creator_id == creator_record.id).count() + 1
            db.creator_to_link.insert(
                creator_id=creator_record.id,
                link_id=form.vars.id,
                order_no=order_no,
            )
            db.commit()

    def ondelete(table, record_id):
        """Callback for ondelete."""
        db(table.id == record_id).delete()
        db.commit()
        if book_record:
            to_link_table = db.book_to_link
            filter_field = 'book_id'
            record = book_record
            links = CustomLinks(db.book, book_record.id)
        else:
            filter_field = 'creator_id'
            to_link_table = db.creator_to_link
            record = creator_record
            links = CustomLinks(db.creator, creator_record.id)
        # Delete any _to_links associated with the record.
        db(to_link_table.link_id == record_id).delete()
        db.commit()
        links.reorder()

    def row_link_id(row):
        return row.link.id if 'link' in row else 0

    def edit_link(row):
        link_id = row_link_id(row)
        if not link_id:
            return ''
        main_name = 'book' if book_record else 'creator'
        args = []
        if book_record:
            args.append(book_record.id)
        args.append(link_id)

        return A(
            SPAN(_class="glyphicon glyphicon-pencil"),
            'Edit',
            _href=URL(
                c='profile',
                f='{m}_link_edit'.format(m=main_name),
                args=args,
                anchor='{m}_link_edit'.format(m=main_name),
                extension=False
            ),
            _class='btn btn-default',
            _type='button',
        )

    grid_links = [
        ReorderLink(link_table, direction='up', next_url=next_url).links_dict(),
        ReorderLink(link_table, direction='down', next_url=next_url).links_dict(),
        {'header': '', 'body': edit_link},
    ]

    grid = LocalSQLFORM.grid(
        query,
        fields=fields,
        field_id=db.link.id,
        orderby=orderby,
        left=left,
        paginate=10,
        maxtextlengths={
            'link.url': 100,
        },
        details=False,
        editable=False,
        deletable=True,
        create=False,
        csv=False,
        searchable=False,
        oncreate=oncreate,
        # onupdate=onupdate,
        ondelete=ondelete,
        editargs={'deletable': False},
        links=grid_links,
        client_side_delete=True,
    )

    # Remove 'None' record count if applicable.
    for count, div in enumerate(grid[0]):
        if str(div) == '<div class="web2py_counter">None</div>':
            del grid[0][count]

    return dict(grid=grid, book=book_record)


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

def link_crud():
    """Handler for ajax link CRUD calls."""
    response.generic_patterns = ['json']
    import sys; print >> sys.stderr, 'FIXME request.args: {var}'.format(var=request.args)
    import sys; print >> sys.stderr, 'FIXME request.vars: {var}'.format(var=request.vars)
    action = request.vars.action if request.vars.action else 'get'
    import sys; print >> sys.stderr, 'FIXME action: {var}'.format(var=action)

    link_id = None
    if request.vars.link_id:
        try:
            link_id = int(request.vars.link_id)
        except (TypeError, ValueError):
            link_id = None

    record_id = 0
    rows = []
    errors = []

    creator_record = db(db.creator.auth_user_id == auth.user_id).select(
        db.creator.ALL
    ).first()
    if not creator_record:
        return {}                           # FIXME doerror

    do_reorder = False
    if action == 'create':
        ret = db.link.validate_and_insert(
            url=request.vars.url,
            name=request.vars.name,
        )
        db.commit()
        if ret.id:
            db.creator_to_link.insert(
                link_id=ret.id,
                creator_id=creator_record.id,
                order_no=99999,
            )
            db.commit()
            do_reorder = True
        record_id = ret.id
        errors = ret.errors
    elif action == 'get':
        query = (db.creator_to_link.creator_id == creator_record.id)
        if link_id:
            query = query & (db.link.id == link_id)
        rows = db(query=query).select(
            db.link.ALL,
            left=[
                db.creator_to_link.on(
                    (db.creator_to_link.link_id == db.link.id)
                )
            ],
            orderby=[db.creator_to_link.order_no, db.creator_to_link.id],
        ).as_list()
        import sys; print >> sys.stderr, 'FIXME db._lastsql: {var}'.format(var=db._lastsql)
    elif action == 'update':
        if link_id:
            data = {}
            if request.vars.field is not None and request.vars.value is not None:
                data = {request.vars.field: request.vars.value}
            import sys; print >> sys.stderr, 'FIXME data: {var}'.format(var=data)
            if data:
                query = (db.link.id == link_id)
                ret = db(query).validate_and_update(**data)
                import sys; print >> sys.stderr, 'FIXME db._lastsql: {var}'.format(var=db._lastsql)
                import sys; print >> sys.stderr, 'FIXME ret: {var}'.format(var=ret)
                record_id = link_id
                errors = ret.errors
                do_reorder = True
        else:
            pass        # FIXME provide error?
    elif action == 'delete':
        if link_id:
            query = (db.creator_to_link.link_id == link_id)
            db(query).delete()
            query = (db.link.id == link_id)
            db(query).delete()
            db.commit()
            record_id = link_id
            do_reorder = True
            # FIXME errors = ret.errors
        else:
            pass        # FIXME provide error?
    if do_reorder:
        reorder_query = (db.creator_to_link.creator_id == creator_record.id)
        reorder(
            db.creator_to_link.order_no,
            query=reorder_query,
        )
    return {
        'id': record_id,
        'rows': rows,
        'errors': errors,
    }
