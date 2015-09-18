# -*- coding: utf-8 -*-
"""Creator login controller functions"""
import collections
import logging
import os
import shutil
from PIL import Image
from gluon.contrib.simplejson import dumps, loads
from applications.zcomx.modules.access import requires_agreed_to_terms
from applications.zcomx.modules.book_lists import \
    class_from_code as book_list_class_from_code
from applications.zcomx.modules.book.complete_barriers import \
    complete_barriers, \
    has_complete_barriers
from applications.zcomx.modules.book_pages import \
    BookPage, \
    delete_pages_not_in_ids, \
    reset_book_page_nos
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.book_upload import BookPageUploader
from applications.zcomx.modules.books import \
    Book, \
    name_fields, \
    book_pages_as_json, \
    calc_status, \
    defaults as book_defaults, \
    images, \
    names, \
    publication_year_range, \
    read_link, \
    set_status
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import \
    Creator, \
    image_as_json, \
    queue_update_indicia, \
    short_url
from applications.zcomx.modules.images import \
    ResizeImgIndicia, \
    on_delete_image, \
    store
from applications.zcomx.modules.images_optimize import AllSizesImages
from applications.zcomx.modules.indicias import \
    BookPublicationMetadata, \
    Derivative, \
    PublicationMetadata, \
    create_creator_indicia
from applications.zcomx.modules.job_queue import \
    DeleteBookQueuer, \
    ReleaseBookQueuer, \
    ReverseReleaseBookQueuer, \
    queue_search_prefetch
from applications.zcomx.modules.links import \
    Link, \
    Links, \
    LinksKey, \
    LinkType
from applications.zcomx.modules.shell_utils import TemporaryDirectory
from applications.zcomx.modules.stickon.validators import as_per_type
from applications.zcomx.modules.utils import \
    default_record, \
    move_record, \
    reorder
from applications.zcomx.modules.zco import BOOK_STATUS_DRAFT

LOG = logging.getLogger('app')

MODAL_ERROR = lambda msg: redirect(
    URL(c='z', f='modal_error', vars={'message': msg}))


@auth.requires_login()
def account():
    """Account login controller."""
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        redirect(URL(c='default', f='index'))

    return dict(creator=creator)


@auth.requires_login()
def agree_to_terms():
    """Creator agree to terms modal view.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        redirect(URL(c='default', f='index'))

    fields = [
        Field(
            'agree_to_terms',
            'boolean',
            requires=IS_NOT_EMPTY(
                error_message='You must agree to the terms to continue'),

        ),
    ]

    form = SQLFORM.factory(
        *fields,
        formstyle='table2cols',
        submit_button='Continue'
    )

    if form.process(
            keepvalues=True,
            message_onsuccess='',
            message_onfailure='',
            hideerror=True).accepted:
        data = dict(agreed_to_terms=form.vars.agree_to_terms)
        agreed_creator = Creator.from_updated(creator, data)
        if agreed_creator.agreed_to_terms:
            redirect(URL('books'))
        else:
            redirect(URL(c='default', f='index'))
    return dict(creator=creator, form=form)


@auth.requires_login()
def book_crud():
    """Handler for ajax book CRUD calls.

    request.vars._action: string, 'create', 'update', etc

    complete:
    request.vars.pk: integer, id of book record

    create:
    request.vars.name: string, book table field name ('name')
    request.vars.value: string, value of book table field.

    delete:
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

    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Permission denied')

    # W0212 (protected-access): *Access to a protected member
    # pylint: disable=W0212
    actions = ['complete', 'create', 'delete', 'update']
    if not request.vars._action or request.vars._action not in actions:
        return do_error('Invalid data provided')
    action = request.vars._action

    book = None
    if action != 'create':
        try:
            book_id = int(request.vars.pk)
        except (TypeError, ValueError):
            return do_error('Invalid data provided')
        try:
            book = Book.from_id(book_id)
        except LookupError:
            return do_error('Invalid data provided')

        if not book or (
                book and book.creator_id != creator.id):
            return do_error('Invalid data provided')

    if action == 'complete':
        if has_complete_barriers(book):
            return do_error('This book cannot be released.')

        book = Book.from_updated(book, dict(releasing=True))
        db.commit()
        job = ReleaseBookQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        if not job:
            msg = (
                'Complete process failed. '
                'The book cannot be set as completed at this time.'
            )
            return do_error(msg)

        return {'status': 'ok'}

    if action == 'create':
        data = {}
        # Validate all fields.
        if request.vars.name is not None and request.vars.value is not None:
            book_name = request.vars.value.strip()
            data = book_defaults(book_name, creator)
            data[request.vars.name] = book_name

        try:
            book = Book.from_add(data)
        except SyntaxError as err:
            return {'status': 'error', 'msg': str(err)}

        if book and book.id:
            return {
                'id': book.id,
                'status': 'ok',
            }
        return do_error('Unable to create book')

    if action == 'delete':
        # The process of deleting book can be slow, so queue a job to
        # take care of it. Flag the book status=False so it is hidden.
        book = Book.from_updated(book, dict(status=False))
        err_msg = 'Delete failed. The book cannot be deleted at this time.'

        job = ReverseReleaseBookQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        if not job:
            return do_error(err_msg)

        job = DeleteBookQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        if not job:
            return do_error(err_msg)

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

        if request.vars.name in name_fields():
            data.update(names(
                dict(book.as_dict(), **as_per_type(db.book, data)),
                fields=db.book.fields
            ))

        try:
            book = Book.from_updated(book, data)
        except SyntaxError as err:
            return {'status': 'error', 'msg': str(err)}

        queue_search_prefetch()

        numbers = \
            BookType.classified_from_id(
                request.vars.value).number_field_statuses() \
            if request.vars.name == 'book_type_id' else None

        show_cc_licence_place = False
        cc0 = CCLicence.by_code('CC0')
        if request.vars.name == 'cc_licence_id' \
                and request.vars.value == str(cc0.id):
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
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        MODAL_ERROR('Permission denied')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            MODAL_ERROR('Invalid data provided')

    if not book or book.creator_id != creator.id:
        MODAL_ERROR('Invalid data provided')

    return dict(book=book)


@auth.requires_login()
def book_edit():
    """Book edit controller for modal view.

    request.args(0): integer, id of book
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        MODAL_ERROR('Permission denied')

    book = None
    book_type = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            book = None
        if not book:
            MODAL_ERROR('Invalid data provided')
        book_type = BookType.classified_from_id(book.book_type_id)

    if not book_type:
        book_type = BookType.by_name('one-shot')

    cc_licence = None
    show_cc_licence_place = False
    meta = None
    if book:
        try:
            cc_licence = book.as_one(CCLicence)
        except LookupError:
            cc_licence = None
        if cc_licence and cc_licence.code == 'CC0':
            show_cc_licence_place = True

        meta = BookPublicationMetadata.from_book(book)

    link_types = []
    for link_type_code in ['book_review', 'buy_book']:
        link_types.append(LinkType.by_code(link_type_code))

    return dict(
        book=book,
        book_type=book_type,
        cc_licence=cc_licence,
        link_types=link_types,
        metadata=str(meta) if meta else '',
        numbers=dumps(book_type.number_field_statuses()),
        show_cc_licence_place=dumps(show_cc_licence_place),
    )


@auth.requires_login()
def book_list():
    """Book list component controller.

    request.args(0): string, optional,
        one of 'completed', 'ongoing', 'disabled'
    """
    # Verify user is legit
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return dict()

    try:
        lister = book_list_class_from_code(request.args(0))(creator)
    except ValueError as err:
        LOG.error(err)
        return dict()

    return dict(lister=lister)


@auth.requires_login()
def book_pages():
    """Book pages (image upload) controller for modal view.

    request.args(0): integer, id of book.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        MODAL_ERROR('Permission denied')

    book = None
    if request.args(0):
        book = Book.from_id(request.args(0))
    if not book or book.creator_id != creator.id:
        MODAL_ERROR('Invalid data provided')

    # Temporarily set the book status to draft, so it does not appear
    # in search results while it is being edited.
    book = set_status(book, BOOK_STATUS_DRAFT)

    read_button = read_link(
        book,
        **dict(
            _class='btn btn-default btn-lg',
            _target='_blank',
        )
    )

    return dict(
        book=book,
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
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Upload service unavailable')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            return do_error('Upload service unavailable')
    if not book or book.creator_id != creator.id:
        return do_error('Upload service unavailable')

    if request.env.request_method == 'POST':
        # Create a book_page record for each upload.
        files = request.vars['up_files[]']
        if not isinstance(files, list):
            files = [files]
        # Catching too general exception (W0703)
        # pylint: disable=W0703
        try:
            result_json = BookPageUploader(book.id, files).upload()
        except Exception as err:
            LOG.error('Upload failed, err: %s', str(err))
            return do_error(
                'The upload was not successful.',
                files=[x.filename for x in files]
            )

        result = loads(result_json)
        if 'files' in result:
            for result_file in result['files']:
                if 'book_page_id' in result_file:
                    db.tentative_activity_log.insert(
                        book_id=book.id,
                        book_page_id=result_file['book_page_id'],
                        action='page added',
                        time_stamp=request.now,
                    )
                    db.commit()
        return result_json
    elif request.env.request_method == 'DELETE':
        book_page = BookPage.from_id(request.vars.book_page_id)
        if not book_page:
            return do_error('Unable to delete page')

        # retrieve real file name
        filename, _ = db.book_page.image.retrieve(
            book_page.image,
            nameonly=True,
        )
        on_delete_image(book_page.image)
        book_page.delete()
        return dumps({"files": [{filename: True}]})
    else:
        # GET
        return book_pages_as_json(book.id)


@auth.requires_login()
def book_post_upload_session():
    """Callback function for handling processing to run after images have been
        uploaded.

        * update book.page_added_on if applicable
        * reorder book pages
        * set book status
        * trigger queue search prefetch
        * optimize book page images

    request.args(0): integer, id of book.
    request.vars.book_page_ids[], list of book page ids.
    request.vars.original_page_count, integer, number of pages before upload
        session.
    """
    def do_error(msg):
        """Error handler."""
        return dumps({'success': False, 'error': msg})

    # Verify user is legit
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Reorder service unavailable')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            return do_error('Reorder service unavailable')
    if not book or book.creator_id != creator.id:
        return do_error('Reorder service unavailable')

    book_page_ids = []
    if 'book_page_ids[]' in request.vars:
        if not isinstance(request.vars['book_page_ids[]'], list):
            book_page_ids = [request.vars['book_page_ids[]']]
        else:
            book_page_ids = request.vars['book_page_ids[]']

    # Step 1: Update book page_added_on if applicable.
    try:
        original_page_count = int(request.vars.original_page_count)
    except (TypeError, ValueError):
        original_page_count = 0
    pages_added = len(book_page_ids) - original_page_count
    if pages_added > 0:
        book = Book.from_updated(book, dict(page_added_on=request.now))

    # Step 2: Reorder book pages
    page_ids = []
    for page_id in book_page_ids:
        try:
            page_ids.append(int(page_id))
        except (TypeError, ValueError):
            # reordering pages isn't critical, if page is not valid, just
            # move on
            continue

    delete_pages_not_in_ids(book.id, page_ids)
    reset_book_page_nos(page_ids)

    # Step 3:  Set book status
    book = set_status(book, calc_status(book))

    # Step 4:  Trigger search prefetch
    # A book with no pages is not in search results. Adding pages makes it
    # searchable. A book is disabled while pages are are added. Disabled books
    # are taken out of search results. Ending the Upload session may make the
    # book active and thus searchable. A search prefetch will make the book
    # searchable if applicable.
    queue_search_prefetch()

    # Step 5:  Trigger optimization of book images
    AllSizesImages.from_names(images(book)).optimize()

    return dumps({'success': True})


@auth.requires_login()
def book_release():
    """Book release controller for modal view.

    request.args(0): integer, id of book.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        MODAL_ERROR('Permission denied')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            MODAL_ERROR('Invalid data provided')
    if not book or book.creator_id != creator.id:
        MODAL_ERROR('Invalid data provided')

    return dict(
        book=book,
        barriers=complete_barriers(book),
    )


@auth.requires_login()
@requires_agreed_to_terms()
def books():
    """Books controller.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
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

    query = (db.book.creator_id == creator.id)
    status_count = db.book.status.count()
    rows = db(query).select(
        db.book.status,
        status_count,
        groupby=db.book.status,
    )

    status_counts = collections.defaultdict(
        lambda: 0,
        [(r.book.status, r[status_count]) for r in rows]
    )

    return dict(status_counts=status_counts)


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

    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
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

    try:
        creator = Creator.from_updated(creator, data)
    except SyntaxError as err:
        return {'status': 'error', 'msg': str(err)}

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
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Upload service unavailable')

    img_field = 'image'
    if request.args(0):
        if request.args(0) not in db.creator.fields:
            LOG.error('creator_img_handler invalid field: %s', request.args(0))
            return do_error('Upload service unavailable')
        img_field = request.args(0)

    minimum_widths = {
        # 'field': width in px
        'image': 263,
        'indicia_image': 1600,
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
                LOG.error('Creator image upload error: %s', str(err))
                stored_filename = None

        if not stored_filename:
            return do_error(
                'File upload failed',
                files=[up_file.filename]
            )

        img_changed = creator[img_field] != stored_filename
        if img_changed:
            if creator[img_field] is not None:
                # Delete an existing image before it is replaced
                on_delete_image(creator[img_field])
                data = {img_field: None}
                creator = Creator.from_updated(creator, data)
            if img_field == 'indicia_image':
                # Clear the indicia png fields. This will trigger a rebuild
                # in indicia_preview_urls
                on_delete_image(creator['indicia_portrait'])
                on_delete_image(creator['indicia_landscape'])
                data = {
                    'indicia_portrait': None,
                    'indicia_landscape': None,
                }
                creator = Creator.from_updated(creator, data)

        data = {img_field: stored_filename}
        creator = Creator.from_updated(creator, data)
        if img_changed:
            if img_field == 'indicia_image':
                # If indicias are blank, create them.
                if not creator.indicia_portrait \
                        or not creator.indicia_landscape:
                    # This runs in the forground so keep it fast.
                    create_creator_indicia(
                        creator, resize=False, optimize=False)
                queue_update_indicia(creator)
            AllSizesImages.from_names([creator[img_field]]).optimize()
        return image_as_json(creator, field=img_field)

    elif request.env.request_method == 'DELETE':
        # retrieve real file name
        if not creator[img_field]:
            return do_error('')

        filename, _ = db.creator[img_field].retrieve(
            creator[img_field],
            nameonly=True,
        )
        # Clear the images from the record
        data = {img_field: None}
        on_delete_image(creator[img_field])
        if img_field == 'indicia_image':
            on_delete_image(creator['indicia_portrait'])
            on_delete_image(creator['indicia_landscape'])
            data['indicia_portrait'] = None
            data['indicia_landscape'] = None
        creator = Creator.from_updated(creator, data)
        if img_field == 'indicia_image':
            queue_update_indicia(creator)
        return dumps({"files": [{filename: 'true'}]})

    # GET
    return image_as_json(creator, field=img_field)


@auth.requires_login()
def index():
    """Default login controller."""
    redirect(URL(c='login', f='books'))


@auth.requires_login()
def indicia():
    """Indicia controller.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
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

    return dict(creator=creator)


@auth.requires_login()
def indicia_preview_urls():
    """Handler for ajax link CRUD calls.
    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Permission denied')

    urls = {
        'portrait': None,
        'landscape': None,
    }

    for orientation in urls.keys():
        field = 'indicia_{o}'.format(o=orientation)
        if creator[field]:
            urls[orientation] = URL(
                c='images',
                f='download',
                args=creator[field],
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
    request.args(0): record_table, one of 'creator' or 'book'
    request.args(1): record_id, integer, id of record

    request.vars.action: string, one of
        'get', 'create', 'update', 'delete', 'move'
    request.vars.link_type_code: string, link_type.code value.

    # action = 'update', 'delete', 'move'
    request.vars.pk: integer, id of link record

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

    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Permission denied')

    record_table = request.args(0)
    if record_table not in ['book', 'creator']:
        return do_error('Invalid data provided')

    rows = []
    errors = {}     # Row() or dict
    new_value = None
    record = None

    if record_table == 'creator':
        try:
            request_args_1 = int(request.args(1))
        except (TypeError, ValueError):
            return do_error('Permission denied')
        if request_args_1 != creator.id:
            return do_error('Permission denied')
        record = creator

    if record_table == 'book':
        try:
            book = Book.from_id(request.args(1))
        except LookupError:
            return do_error('Invalid data provided')
        if not book:
            return do_error('Invalid data provided')
        if book.creator_id != creator.id:
            return do_error('Permission denied')
        record = book

    actions = ['get', 'update', 'create', 'delete', 'move']
    action = request.vars.action if request.vars.action in actions else 'get'

    link_id = None
    if request.vars.pk:
        try:
            link_id = int(request.vars.pk)
        except (TypeError, ValueError):
            link_id = None

    link_type = None
    if link_id:
        link = Link.from_id(link_id)
        if not link:
            return do_error('Invalid data provided')
        link_type = LinkType.from_id(link.link_type_id)

    if not request.vars.link_type_code:
        return do_error('Invalid data provided')

    if not link_type:
        try:
            link_type = LinkType.by_code(request.vars.link_type_code)
        except LookupError:
            link_type = None
        if not link_type:
            return do_error('Invalid data provided')

    links_key = LinksKey(link_type.id, record_table, record.id)

    do_reorder = False
    if action == 'get':
        links = None
        if link_id:
            links = Links([Link.from_id(link_id)])
        else:
            links = Links.from_links_key(links_key)
        rows = [x for x in links.links]
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
                try:
                    link = Link.from_id(link_id)
                except LookupError:
                    return do_error('Invalid data provided')
                try:
                    link = Link.from_updated(link, data)
                except SyntaxError as err:
                    return {'status': 'error', 'msg': str(err)}
                do_reorder = True
        else:
            return do_error('Invalid data provided')
    elif action == 'create':
        url = request.vars.url.rstrip('/')

        link_data = dict(
            link_type_id=link_type.id,
            record_table=record_table,
            record_id=record.id,
            order_no=99999,
            url=url,
            name=request.vars.name,
        )

        try:
            link = Link.from_add(link_data)
        except SyntaxError as err:
            return {'status': 'error', 'msg': str(err)}

        rows = [Link.from_id(link.id).as_dict()]
        if url != request.vars.url:
            new_value = url
        do_reorder = True
    elif action == 'delete':
        if link_id:
            Link.from_id(link_id).delete()
            do_reorder = True
        else:
            return do_error('Invalid data provided')
    elif action == 'move':
        dirs = ['down', 'up']
        direction = request.vars.dir if request.vars.dir in dirs else 'down'
        if link_id:
            move_record(
                db.link.order_no,
                link_id,
                direction=direction,
                query=links_key.filter_query(db.link)
            )
        else:
            return do_error('Invalid data provided')
    if do_reorder:
        reorder(
            db.link.order_no,
            query=links_key.filter_query(db.link)
        )
    result = {
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
            necessary.
    """
    # too-many-return-statements (R0911): *Too many return statements*
    # pylint: disable=R0911
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Permission denied')

    # W0212 (protected-access): *Access to a protected member
    # pylint: disable=W0212
    actions = ['get', 'update']
    if not request.vars._action or request.vars._action not in actions:
        return do_error('Invalid data provided')
    action = request.vars._action

    book = None
    try:
        book_id = int(request.args(0))
    except (TypeError, ValueError):
        return do_error('Invalid data provided')
    try:
        book = Book.from_id(book_id)
    except LookupError:
        return do_error('Invalid data provided')
    if not book or (
            book and book.creator_id != creator.id):
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

        data['derivative']['fields']['cc_licence_id'].update({
            'type': 'select',
            'source': [{'value': x.id, 'text': x.code} for x in licences]
        })

        for table in data.keys():
            data[table]['default'] = default_record(
                db[table], ignore_fields='common')

        data['publication_metadata']['default'].update({
            'published_name': book.name,
        })

        data['publication_serial']['default'].update({
            'published_name': book.name,
            'serial_title': book.name,
        })

        data['derivative']['default'].update({
            'is_derivative': 'no',
            'cc_licence_id': licences[0].id,
        })

        query = (db.publication_metadata.book_id == book.id)
        try:
            metadata_record = PublicationMetadata.from_query(query)
        except LookupError:
            data['publication_metadata']['record'] = \
                data['publication_metadata']['default']
        else:
            data['publication_metadata']['record'] = metadata_record.as_dict()

        query = (db.publication_serial.book_id == book.id)
        data['publication_serial']['records'] = db(query).select(
            orderby=[
                db.publication_serial.sequence,
                db.publication_serial.id,
            ],
        ).as_list()

        query = (db.derivative.book_id == book.id)
        try:
            derivative = Derivative.from_query(query)
        except LookupError:
            data['derivative']['record'] = data['derivative']['default']
        else:
            data['derivative']['record'] = derivative.as_dict()
            data['derivative']['record']['is_derivative'] = 'yes'
        return {'status': 'ok', 'data': data}

    if action == 'update':
        meta = BookPublicationMetadata.from_vars(book, dict(request.vars))
        meta.validate()
        if meta.errors:
            return {'status': 'error', 'fields': meta.errors}
        meta.update()
        book = Book.from_updated(
            book, dict(publication_year=meta.publication_year()))
        return {'status': 'ok'}
    return do_error('Invalid data provided')


@auth.requires_login()
def metadata_text():
    """Handler for ajax call to get metadata text.

    request.args(0): integer, book id.
    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('Permission denied')

    book = None
    try:
        book_id = int(request.args(0))
    except (TypeError, ValueError):
        return do_error('Invalid data provided')
    try:
        book = Book.from_id(book_id)
    except LookupError:
        return do_error('Invalid data provided')
    if not book or (
            book and book.creator_id != creator.id):
        return do_error('Invalid data provided')

    meta = BookPublicationMetadata.from_book(book)
    if not meta:
        return do_error('Invalid data provided')
    return {'status': 'ok', 'text': str(meta)}


@auth.requires_login()
def profile():
    """Creator profile controller."""
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
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

    link_types = []
    for link_type_code in ['creator_article', 'creator_page']:
        link_types.append(LinkType.by_code(link_type_code))

    return dict(
        creator=creator,
        link_types=link_types,
        short_url=short_url(creator)
    )
