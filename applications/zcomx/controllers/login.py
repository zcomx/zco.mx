# -*- coding: utf-8 -*-
"""Creator login controller functions"""
import collections
import json
import os
import shutil
import urllib.parse
from PIL import Image
from applications.zcomx.modules.access import requires_agreed_to_terms
from applications.zcomx.modules.activity_logs import UploadActivityLogger
from applications.zcomx.modules.book.release_barriers import (
    complete_barriers,
    filesharing_barriers,
    has_complete_barriers,
    has_filesharing_barriers,
)
from applications.zcomx.modules.book_pages import (
    BookPageTmp,
    delete_pages_not_in_ids,
    reset_book_page_nos,
)
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.book_upload import BookPageUploader
from applications.zcomx.modules.books import (
    Book,
    name_fields,
    book_pages_as_json,
    book_pages_from_tmp,
    book_pages_to_tmp,
    calc_status,
    defaults as book_defaults,
    images,
    names,
    publication_months,
    publication_year_range,
    set_status,
)
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import (
    AuthUser,
    Creator,
    image_as_json,
    on_change_name,
    queue_update_indicia,
    short_url,
    url as creator_url,
)
from applications.zcomx.modules.image.validators import InvalidImageError
from applications.zcomx.modules.images import (
    CreatorImgTag,
    ResizeImgIndicia,
    on_delete_image,
    store,
)
from applications.zcomx.modules.images_optimize import AllSizesImages
from applications.zcomx.modules.indicias import (
    BookPublicationMetadata,
    Derivative,
    PublicationMetadata,
    create_creator_indicia,
)
from applications.zcomx.modules.job_queuers import (
    DeleteBookQueuer,
    FileshareBookQueuer,
    SetBookCompletedQueuer,
    ReverseFileshareBookQueuer,
    ReverseSetBookCompletedQueuer,
    queue_create_sitemap,
    queue_search_prefetch,
)
from applications.zcomx.modules.links import (
    Link,
    Links,
    LinksKey,
    LinkType,
)
from applications.zcomx.modules.search import (
    LoginCompletedGrid,
    LoginDisabledGrid,
    LoginDraftsGrid,
    LoginOngoingGrid,
)
from applications.zcomx.modules.shell_utils import TemporaryDirectory
from applications.zcomx.modules.stickon.validators import as_per_type
from applications.zcomx.modules.utils import (
    default_record,
    move_record,
    reorder,
)


def modal_error(msg):
    """Redirect on modal error.

    Args:
        msg: str, error message
    """
    redirect(URL(c='z', f='modal_error', vars={'message': msg}))


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
def book_complete():
    """Book 'set as completed' controller for modal view.

    request.args(0): integer, id of book.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        modal_error('Permission denied')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            modal_error('Invalid data provided')
    if not book or book.creator_id != creator.id:
        modal_error('Invalid data provided')

    meta = BookPublicationMetadata.from_book(book)
    barriers = complete_barriers(book)

    return dict(
        book=book,
        barriers=barriers,
        metadata=str(meta) if meta else '',
    )


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
    # pylint: disable=too-many-return-statements
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

    actions = ['complete', 'create', 'delete', 'fileshare', 'update']
    # pylint: disable=protected-access
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
            return do_error('This book cannot be set as completed.')

        book = Book.from_updated(book, dict(complete_in_progress=True))
        db.commit()
        job = SetBookCompletedQueuer(
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

        job = ReverseFileshareBookQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        if not job:
            return do_error(err_msg)

        job = ReverseSetBookCompletedQueuer(
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

    if action == 'fileshare':
        if has_filesharing_barriers(book):
            return do_error('This book cannot be released for filesharing.')

        book = Book.from_updated(book, dict(fileshare_in_progress=True))
        db.commit()
        job = FileshareBookQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        if not job:
            msg = (
                'Fileshare process failed. '
                'The book cannot be released for filesharing at this time.'
            )
            return do_error(msg)

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
        queue_create_sitemap()

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
        modal_error('Permission denied')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            modal_error('Invalid data provided')

    if not book or book.creator_id != creator.id:
        modal_error('Invalid data provided')

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
        modal_error('Permission denied')

    book = None
    book_type = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            book = None
        if not book:
            modal_error('Invalid data provided')
        book_type = BookType.classified_from_id(book.book_type_id)

    if not book_type:
        book_type = BookType.by_name('one-shot')

    cc_licence = None
    show_cc_licence_place = False
    db.book.cc_licence_place.requires = None
    meta = None
    if book:
        try:
            cc_licence = book.as_one(CCLicence)
        except LookupError:
            cc_licence = None
        if cc_licence and cc_licence.code == 'CC0':
            show_cc_licence_place = True
            db.book.cc_licence_place.requires = IS_NOT_EMPTY(
                error_message='Select a territory')

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
        numbers=json.dumps(book_type.number_field_statuses()),
        show_cc_licence_place=json.dumps(show_cc_licence_place),
    )


@auth.requires_login()
def book_fileshare():
    """Book release for filesharing controller for modal view.

    request.args(0): integer, id of book.
    """
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        modal_error('Permission denied')

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            modal_error('Invalid data provided')
    if not book or book.creator_id != creator.id:
        modal_error('Invalid data provided')

    barriers = filesharing_barriers(book)

    return dict(
        book=book,
        barriers=barriers,
    )


@auth.requires_login()
def book_page_edit_handler():
    """Callback function for the x-editable plugin for renaming the
    image filename associated with the book page (book_page_tmp records).

    request.vars.pk: integer, id of book_page_tmp record
    request.vars.value: str, new name of image file.
    """
    # pylint: disable=too-many-return-statements
    def do_error(msg):
        """Error handler."""
        return json.dumps({'status': 'error', 'msg': msg})

    # Verify user is legit
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        return do_error('File rename service unavailable')

    book_page_tmp_id = request.vars.pk
    raw_filename = request.vars.value

    book_page_tmp = None
    try:
        book_page_tmp = BookPageTmp.from_id(book_page_tmp_id)
    except LookupError:
        pass
    if not book_page_tmp:
        return do_error('File rename service unavailable')

    # Double check that book belongs to creator
    book = None
    try:
        book = Book.from_id(book_page_tmp.book_id)
    except LookupError:
        return do_error('File rename service unavailable')
    if not book or book.creator_id != creator.id:
        return do_error('File rename service unavailable')

    new_filename = None
    if raw_filename:
        new_filename = raw_filename.strip()

    if not new_filename:
        return do_error('Invalid image filename')

    if book_page_tmp.image != new_filename:
        # pylint: disable=broad-except
        try:
            book_page_tmp = book_page_tmp.rename_image(new_filename)
        except Exception as err:
            LOG.error('Book page image rename error: %s', str(err))
            return do_error('Image file rename failed.')

    return json.dumps({'status': 'ok', 'msg': ''})


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
        modal_error('Permission denied')

    book = None
    if request.args(0):
        book = Book.from_id(request.args(0))
    if not book or book.creator_id != creator.id:
        modal_error('Invalid data provided')

    book_pages_to_tmp(book)

    return dict(
        book=book,
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
    # pylint: disable=too-many-return-statements
    def do_error(msg, files=None):
        """Error handler."""
        if files == None:
            files = ['']
        messages = [{'name': x, 'error': msg} for x in files]
        return json.dumps({'files': messages})

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
        # Create a book_page_tmp record for each upload.
        files = request.vars['up_files[]']
        if not isinstance(files, list):
            files = [files]
        # pylint: disable=broad-except
        try:
            result_json = BookPageUploader(book.id, files).upload()
        except InvalidImageError as err:
            return do_error(
                str(err),
                files=[x.filename for x in files]
            )
        except Exception as err:
            LOG.error('Upload failed, err: %s', str(err))
            return do_error(
                'The upload was not successful.',
                files=[x.filename for x in files]
            )

        return result_json

    if request.env.request_method == 'DELETE':
        try:
            book_page_tmp = BookPageTmp.from_id(request.vars.book_page_id)
        except LookupError:
            return do_error('Unable to delete page')

        # retrieve real file name
        filename, _ = db.book_page_tmp.image.retrieve(
            book_page_tmp.image,
            nameonly=True,
        )
        book_page_tmp.delete()
        return json.dumps({"files": [{filename: True}]})

    # GET
    return book_pages_as_json(book)


@auth.requires_login()
def book_post_upload_session():
    """Callback function for handling processing to run after images have been
        uploaded.

        * update book.page_added_on if applicable
        * check for errors
        * reorder book pages
        * set book status
        * trigger queue search prefetch
        * optimize book page images
        * trigger queue create sitemap

    request.args(0): integer, id of book.
    request.vars.book_page_ids[], list of book page ids.
    request.vars.original_page_count, integer, number of pages before upload
        session.
    """
    def do_error(msg=None):
        """Error handler."""
        return json.dumps(
            {'status': 'error', 'msg': msg or 'Server request failed'})

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
    pages_added = len([x for x in book_page_ids if x]) - original_page_count
    if pages_added > 0:
        book = Book.from_updated(book, dict(page_added_on=request.now))

    # Step 2: Check for errors.
    if '' in book_page_ids:
        return do_error((
            'One or more images could not be uploaded. '
            'Check error messages. '
            'Use Add files... to reload those images if desired. '
            'Click the Refresh button to clear error messages.'
        ))

    # Step 3: Reorder book pages
    page_ids = []
    for page_id in book_page_ids:
        try:
            page_ids.append(int(page_id))
        except (TypeError, ValueError):
            return do_error((
                'An error occurred. '
                'The pages of the book could not be updated. '
                'Retry if necessary. Refresh the page to start over.'
            ))

    delete_pages_not_in_ids(book.id, page_ids, book_page_tbl=db.book_page_tmp)
    reset_book_page_nos(page_ids, book_page_tbl=db.book_page_tmp)

    # Step 4:  Move book from tmp to live
    activity_logger = UploadActivityLogger(book)
    book_pages_from_tmp(book)
    activity_logger.log()

    # Step 5:  Set book status
    book = set_status(book, calc_status(book))

    # Step 6:  Trigger search prefetch
    # A book with no pages is not in search results. Adding pages makes it
    # searchable. A book is disabled while pages are are added. Disabled books
    # are taken out of search results. Ending the Upload session may make the
    # book active and thus searchable. A search prefetch will make the book
    # searchable if applicable.
    queue_search_prefetch()

    # Step 7:  Trigger optimization of book images
    AllSizesImages.from_names(images(book)).optimize()

    # Step 8: Trigger create sitemap
    queue_create_sitemap()

    return json.dumps({'status': 'ok'})


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

    queries = [(db.creator.id == creator.id)]
    completed_grid = LoginCompletedGrid(queries=queries, default_viewby='list')
    disabled_grid = LoginDisabledGrid(queries=queries, default_viewby='list')
    drafts_grid = LoginDraftsGrid(queries=queries, default_viewby='list')
    ongoing_grid = LoginOngoingGrid(queries=queries, default_viewby='list')

    return dict(
        completed_grid=completed_grid,
        disabled_grid=disabled_grid,
        drafts_grid=drafts_grid,
        grid=completed_grid,
        ongoing_grid=ongoing_grid,
        status_counts=status_counts,
    )


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
    request.args(0): string, name of creator field to update.
            Optional, if not set, update creator.image
            Eg 'indicia_image': update creator.indicia_image
    request.vars.up_files: list of files representing creator image.
    """
    # pylint: disable=too-many-return-statements
    def do_error(msg, files=None):
        """Error handler."""
        if files == None:
            files = ['']
        messages = [{'name': x, 'error': msg} for x in files]
        return json.dumps({'files': messages})

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
        'image': 336,
        'image_tmp': 336,
        'indicia_image': 1600,
    }

    if request.env.request_method == 'POST':
        files = request.vars.up_files
        if not isinstance(files, list):
            files = [files]
        up_file = files[0]

        with TemporaryDirectory() as tmp_dir:
            local_filename = os.path.join(tmp_dir, up_file.filename)
            with open(local_filename, 'w+b') as f:
                # This will convert cgi.FieldStorage to a regular file.
                shutil.copyfileobj(up_file.file, f)

            with open(local_filename, 'rb') as f:
                try:
                    im = Image.open(f)
                except IOError as err:
                    return do_error(str(err))

                if im.size[0] < minimum_widths[img_field]:
                    fmt = 'Image is too small. Minimum image width: {min}px'
                    return do_error(
                        fmt.format(min=minimum_widths[img_field]),
                        files=[up_file.filename]
                    )
            resizer = ResizeImgIndicia if img_field == 'indicia_image' \
                else None
            # pylint: disable=broad-except
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

    if request.env.request_method == 'DELETE':
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
        return json.dumps({"files": [{filename: 'true'}]})

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

    for orientation in list(urls.keys()):
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

    return json.dumps({
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
    # pylint: disable=too-many-return-statements
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
        rows = list(links.links)
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
    # pylint: disable=too-many-return-statements
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

    actions = ['get', 'update']
    # pylint: disable=protected-access
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

        month_ddm = {
            'type': 'select',
            'source': publication_months(),
        }

        year_ddm = {
            'type': 'select',
            'source': [
                {'value': x, 'text': x}
                for x in sorted(
                    list(range(*publication_year_range())), reverse=True)
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
        data['publication_metadata']['fields']['from_month'].update(month_ddm)
        data['publication_metadata']['fields']['to_year'].update(year_ddm)
        data['publication_metadata']['fields']['to_month'].update(month_ddm)

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
        data['publication_serial']['fields']['from_month'].update(month_ddm)
        data['publication_serial']['fields']['to_year'].update(year_ddm)
        data['publication_serial']['fields']['to_month'].update(month_ddm)

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

        for table in list(data.keys()):
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
    """Creator profile controller.

    request.vars.remove_image: if provided, remove the image on file.
    """
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

    if request.vars.remove_image:
        creator = Creator.from_updated(
            creator,
            {'image': None},
            validate=False,
        )
        redirect(URL('profile'))

    raw_name_url = '{s}{p}'.format(
        s=current.app.local_settings.web_site_url,
        p=creator_url(creator, extension=False)
    )
    name_url = urllib.parse.unquote_plus(raw_name_url)

    link_types = []
    for link_type_code in ['creator_article', 'creator_page']:
        link_types.append(LinkType.by_code(link_type_code))

    return dict(
        creator=creator,
        link_types=link_types,
        name_url=name_url,
        short_url=short_url(creator)
    )


@auth.requires_login()
def profile_creator_image_crud():
    """Handler for ajax profile creator image CRUD calls.

    request.args(0): str, action one of 'ok', 'cancel' or 'get'
    request.vars.percent: int, square_image offset eg 10
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

    action = request.args[0]

    html = None
    if action == 'ok':
        if creator.image_tmp:
            offset = None
            if request.vars.percent:
                offset = '{p}%'.format(p=request.vars.percent)
            creator.square_image_tmp(offset=offset)
            creator.copy_image_from_tmp()
    elif action == 'cancel':
        if creator.image_tmp:
            creator.clear_image_tmp()
    elif action == 'get':
        if creator.image:
            html = CreatorImgTag(
                creator.image,
                size='web',
                attributes={
                    '_alt': '',
                    '_class': 'img-responsive',
                    '_data-creator_id': creator.id
                }
            )()
        else:
            html = A(
                IMG(
                    _src=URL(
                        c='static',
                        f='images',
                        args=['placeholders', 'creator', 'upload.png']
                    ),
                    _class='img-responsive',
                ),
                _href='/login/profile_creator_image_modal',
                _class='profile_creator_image',
            )
    else:
        return do_error()

    return {'status': 'ok', 'html': html}


@auth.requires_login()
def profile_creator_image_modal():
    """Controller for profile creator image modal."""
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        modal_error('Permission denied')

    creator.clear_image_tmp()

    return dict(
        creator=creator,
    )


@auth.requires_login()
def profile_name_edit_crud():
    """Handler for ajax profile name edit CRUD calls.

    request.vars.name: string, name of creator
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

    name = request.vars.name
    if not name or len(name) < 3:
        return do_error('Name must be minimum 3 characters.')

    auth_user = AuthUser.from_id(auth.user_id)
    if auth_user:
        auth_user = AuthUser.from_updated(auth_user, dict(name=name.strip()))
        db.commit()

    if not auth_user:
        LOG.error('auth_user not found, id: %s', auth.user_id)
        return do_error('Unable to update record. Please try again.')

    on_change_name(creator)

    # Reload creator
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None

    name_url = None
    if creator:
        raw_name_url = '{s}{p}'.format(
            s=current.app.local_settings.web_site_url,
            p=creator_url(creator, extension=False)
        )
        name_url = urllib.parse.unquote_plus(raw_name_url)

    return {'status': 'ok', 'name_url': name_url}


@auth.requires_login()
def profile_name_edit_modal():
    """Controller for profile name edit modal."""
    try:
        creator = Creator.from_key(dict(auth_user_id=auth.user_id))
    except LookupError:
        creator = None
    if not creator:
        modal_error('Permission denied')

    fields = [
        Field(
            'name',
            type='string',
            default=creator.name,
        ),
    ]

    form = SQLFORM.factory(
        *fields,
        formstyle='table2cols',
        submit_button='Submit',
        hidden=dict(auth_user_id=auth.user_id),
    )

    form.element(_name='name')['_class'] += ' name_edit_input'

    return dict(
        form=form,
    )
