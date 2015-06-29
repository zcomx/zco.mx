#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Indicias classes and functions.
"""
import datetime
import glob
import logging
import os
import shutil
import subprocess
from gluon import *

from applications.zcomx.modules.books import \
    cc_licence_data, \
    get_page, \
    next_book_in_series, \
    orientation as page_orientation, \
    publication_year_range, \
    read_link
from applications.zcomx.modules.creators import \
    can_receive_contributions, \
    formatted_name as creator_formatted_name, \
    short_url as creator_short_url
from applications.zcomx.modules.images import \
    on_delete_image, \
    store
from applications.zcomx.modules.images_optimize import AllSizesImages
from applications.zcomx.modules.links import CustomLinks
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    os_nice
from applications.zcomx.modules.social_media import SOCIAL_MEDIA_CLASSES
from applications.zcomx.modules.utils import \
    default_record, \
    entity_to_row, \
    vars_to_records
from applications.zcomx.modules.zco import NICES

LOG = logging.getLogger('app')
DEFAULT_BOOK_TYPE = 'one-shot'


class IndiciaPage(object):
    """Class representing an indicia page.

    The indicia page is the web version of the indicia (as opposed to the
    indicia image)
    """
    call_to_action_data = {
        'space': ' ',
        'twitter': 'TWITTER',
        'tumblr': 'TUMBLR',
        'facebook': 'FACEBOOK',
    }
    call_to_action_fmt = (
        'IF YOU ENJOYED THIS WORK YOU CAN HELP OUT BY GIVING SOME MONIES!!'
        '{space} OR BY TELLING OTHERS ON {twitter}, {tumblr} AND {facebook}.'
    )
    default_indicia_paths = ['static', 'images', 'indicia_image.png']
    default_licence_code = 'All Rights Reserved'

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
        """
        self.entity = entity
        self.creator = None     # Row instance representing creator

    def call_to_action_text(self):
        """Return the call to action text."""
        return self.call_to_action_fmt.format(
            **self.call_to_action_data).strip()

    def default_licence(self):
        """Return the default licence record."""
        cc_licence_entity = cc_licence_by_code(
            self.default_licence_code, default=None)
        if cc_licence_entity is None:
            raise LookupError('CC licence not found: {code}'.format(
                code=self.default_licence_code))
        return cc_licence_entity

    def follow_icons(self):
        """Return follow icons.

        Returns:
            list of 'follow' social media icons.
                [A(), ...]
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return []

    def licence_text(self, template_field='template_web'):
        """Return the licence record used for the licence text on the indicia
        page.

        Args:
            template_field: string, name of cc_licence template field. One of
                'template_img', 'template_web'
        """
        return render_cc_licence(
            {},
            self.default_licence(),
            template_field=template_field,
        )


class IndiciaPagePng(TempDirectoryMixin):
    """Base class representing a indicia page in png format."""
    _indicia_filename = None
    metadata_filename = None

    def create_metatext_file(self):
        """Create a text file containing the book metadata."""
        self.metadata_filename = os.path.join(
            self.temp_directory(), 'meta.txt')
        with open(self.metadata_filename, 'w') as f:
            f.write(self.licence_text(template_field='template_img'))

    def get_indicia_filename(self):
        """Return the name of the indicia image file."""
        db = current.app.db
        if not self._indicia_filename:
            indicia_filename = None
            if self.creator.indicia_image:
                _, indicia_filename = db.creator.indicia_image.retrieve(
                    self.creator.indicia_image, nameonly=True)
            if not indicia_filename:
                # Use default
                indicia_filename = os.path.join(
                    current.request.folder,
                    *self.default_indicia_paths
                )
            self._indicia_filename = indicia_filename
        return self._indicia_filename


class BookIndiciaPage(IndiciaPage):
    """Class representing a book indicia page."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.table = db.book
        self.book = entity_to_row(db.book, self.entity)
        self.creator = entity_to_row(db.creator, self.book.creator_id)
        self._orientation = None

    def call_to_action_text(self):
        """Return the call to action text."""

        call_to_action_data = dict(IndiciaPage.call_to_action_data)
        call_to_action_data['space'] = '&nbsp;'
        for name, obj_class in SOCIAL_MEDIA_CLASSES.items():
            text = IndiciaPage.call_to_action_data[name]
            media = obj_class(self.book, creator_entity=self.creator)
            if not media:
                continue
            url = media.share_url()
            if not url:
                continue
            call_to_action_data[name] = A(text, _href=url, _target='_blank')

        return XML(
            self.call_to_action_fmt.format(**call_to_action_data).strip())

    def follow_icons(self):
        """Return follow icons.

        Returns:
            dict representing 'follow' social media icons.
                {'social media': A()}
        """
        icons = []
        icons.append(
            A(
                IMG(_src=URL(c='static', f='images/follow_logo.svg')),
                _href=URL(c='rss', f='modal', args=[self.creator.id]),
                _class='rss_button',
                _target='_blank',
            )
        )
        for obj_class in SOCIAL_MEDIA_CLASSES.values():
            media = obj_class(self.book, creator_entity=self.creator)
            if not media:
                continue
            icons.append(
                A(
                    IMG(_src=media.icon_url()),
                    _href=media.follow_url() or media.site,
                    _target='_blank',
                )
            )
        return icons

    def get_orientation(self):
        """Return the orientation of the book (based on its last page)."""
        if self._orientation is None:
            orientation = None
            try:
                orientation = page_orientation(
                    get_page(self.book, page_no='last'))
            except LookupError:
                orientation = 'portrait'
            if orientation != 'landscape':
                orientation = 'portrait'
            self._orientation = orientation
        return self._orientation

    def licence_text(self, template_field='template_web'):
        """Return the licence record used for the licence text on the indicia
        page.

        Args:
            template_field: string, name of cc_licence template field. One of
                'template_img', 'template_web'
        """
        db = current.app.db
        sections = []
        data = cc_licence_data(self.book)
        cc_licence_entity = None
        if self.book.cc_licence_id:
            query = (db.cc_licence.id == self.book.cc_licence_id)
            cc_licence_entity = db(query).select().first()
            if not cc_licence_entity:
                raise LookupError('CC licence not found: {code}'.format(
                    code=self.default_licence_code))

        if not cc_licence_entity:
            cc_licence_entity = self.default_licence()

        sections.append(render_cc_licence(
            data,
            cc_licence_entity,
            template_field=template_field,
        ))

        meta = PublicationMetadata(self.book, first_publication_text='')
        meta.load()
        sections.append(str(meta))

        return ' '.join([x for x in sections if x])

    def render(self, orientation=None):
        """Render the indicia page.

        Args:
            orientation: string, one of 'portrait' or 'landscape'
                If None, the orientation of the last page of the book is used.
        """
        if orientation is None:
            orientation = self.get_orientation()

        img_src = URL(
            c=self.default_indicia_paths[0],
            f=os.path.join(*self.default_indicia_paths[1:])
        )
        if self.creator and self.creator.indicia_image:
            img_src = URL(
                c='images',
                f='download',
                args=self.creator.indicia_image,
                vars={'size': 'web'}
            )

        text_divs = []

        text_divs.append(
            DIV(
                self.call_to_action_text(),
                _class='call_to_action',
            )
        )

        contribute_and_links_divs = []

        db = current.app.db
        if self.creator and can_receive_contributions(db, self.creator):
            # js is used to flesh out the contribute widget
            contribute_and_links_divs.append(
                DIV(
                    DIV(
                        'Contribute',
                        _class='label',
                    ),
                    DIV(**{
                        '_class': 'contribute_widget',
                        '_data-link_type': 'button',
                    }),
                    _class='contribute_widget_container col-xs-12',
                )
            )

        links = CustomLinks(db.book, self.book.id).represent(
            ul_class='custom_links'
        )
        if links:
            contribute_and_links_divs.append(
                DIV(
                    DIV(
                        'Buy this book',
                        _class='label',
                    ),
                    DIV(
                        DIV(
                            links,
                            _class='vertical_align_wrapper',
                        ),
                        _class='book_links_content',
                    ),
                    _class='book_links_container col-xs-12',
                )
            )

        col_sm = 6
        col_sm_offset = 0
        empty_class = 'empty'
        border_class = 'bordered'
        if contribute_and_links_divs:
            col_sm_offset = int(
                (12 - (len(contribute_and_links_divs) * col_sm)) / 2)
            if col_sm_offset < 0:
                col_sm_offset = 0
            empty_class = 'non_empty'
        if len(contribute_and_links_divs) <= 1:
            border_class = 'borderless'

        col_class = ' col-sm-{s} col-sm-offset-{o}'.format(
            s=col_sm, o=col_sm_offset)
        for div in contribute_and_links_divs:
            div['_class'] += col_class

        text_divs.append(
            DIV(
                contribute_and_links_divs,
                _class='row contribute_and_links_container {e} {b}'.format(
                    e=empty_class, b=border_class).strip(),
            )
        )

        if self.creator:
            creator_name = creator_formatted_name(self.creator)
            if creator_name:
                creator_href = creator_short_url(self.creator)
                follow_text = creator_name
                if creator_href:
                    follow_text = A(
                        creator_name,
                        _href=creator_href,
                    )
                text_divs.append(DIV(
                    follow_text,
                    _class='follow_creator',
                ))

        icon_divs = []
        for icon in self.follow_icons():
            icon_divs.append(DIV(
                icon,
                _class='follow_icon',
            ))

        if icon_divs:
            text_divs.append(DIV(
                icon_divs,
                _class='follow_icons',
            ))

        next_book = next_book_in_series(self.book)
        if next_book:
            components = [
                'Read Next',
                TAG.i(_class='glyphicon glyphicon-play'),
            ]

            read_next = read_link(db, next_book, components=components)
            text_divs.append(DIV(
                read_next,
                _class='read_next_link',
            ))

        text_divs.append(
            DIV(
                XML(self.licence_text()),
                _class='copyright_licence',
            )
        )

        return DIV(
            DIV(
                IMG(
                    _src=img_src,
                ),
                _class='indicia_image_container',
            ),
            DIV(
                text_divs,
                _class='indicia_text_container',
            ),
            _class='indicia_preview_section {o}'.format(o=orientation)
        )


class BookIndiciaPagePng(BookIndiciaPage, IndiciaPagePng):
    """Class representing a book indicia page in png format."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
        """
        BookIndiciaPage.__init__(self, entity)
        self.metadata_filename = None
        self._indicia_filename = None

    def call_to_action_text(self):
        """Return the call to action text."""
        return IndiciaPage.call_to_action_text(self)

    def create(self, orientation=None):
        """Create the indicia png file for the book.

        Args:
            orientation: string, one of 'portrait' or 'landscape'
                If None, the orientation of the last page of the book is used.
        """
        if orientation is None:
            orientation = self.get_orientation()
        self.create_metatext_file()
        indicia_sh = IndiciaSh(
            self.book.creator_id,
            self.metadata_filename,
            self.get_indicia_filename(),
            landscape=(orientation == 'landscape')
        )
        indicia_sh.run()
        # IndiciaSh creates file in a temp directory that is removed as soon
        # as the instance is destroyed.
        # Copy png file to this classes temp directory.
        filename = os.path.join(self.temp_directory(), 'indicia.png')
        shutil.copy(indicia_sh.png_filename, filename)
        return filename


class CreatorIndiciaPagePng(IndiciaPage, IndiciaPagePng):
    """Class representing a creator indicia page in png format."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.creator = entity_to_row(db.creator, self.entity)
        self.metadata_filename = None
        self._indicia_filename = None

    def create(self, orientation):
        """Create the indicia png file for the creator.

        Args:
            orientation: string, one of 'portrait' or 'landscape'
        """
        self.create_metatext_file()
        indicia_sh = IndiciaSh(
            self.creator.id,
            self.metadata_filename,
            self.get_indicia_filename(),
            landscape=(orientation == 'landscape')
        )
        indicia_sh.run()
        # IndiciaSh creates file in a temp directory that is removed as soon
        # as the instance is destroyed.
        # Copy png file to this classes temp directory.
        filename = os.path.join(self.temp_directory(), 'indicia.png')
        shutil.copy(indicia_sh.png_filename, filename)
        return filename

    def licence_text(self, template_field='template_web'):
        """Return the licence record used for the licence text on the indicia
        page.

        Args:
            template_field: string, name of cc_licence template field. One of
                'template_img', 'template_web'
        """
        data = dict(
            owner=creator_formatted_name(self.creator),
            owner_url=creator_short_url(self.creator)
        )
        return render_cc_licence(
            data,
            self.default_licence(),
            template_field=template_field,
        )


class IndiciaShError(Exception):
    """Exception class for IndiciaSh errors."""
    pass


class IndiciaSh(TempDirectoryMixin):
    """Class representing a handler for interaction with indicia.sh"""

    font_path = 'applications/zcomx/static/fonts'

    def __init__(
            self,
            creator_id,
            metadata_filename,
            indicia_filename,
            landscape=False,
            font=None,
            action_font=None):
        """Constructor

        Args:
            creator_id: integer, id of creator record (can be a string)
            metadata_filename: string, name of metadata text file
            indicia_filename: string, name of indicia image file
            landscape: If True, use indicia.sh -l
        """
        self.creator_id = creator_id
        self.metadata_filename = metadata_filename
        self.indicia_filename = indicia_filename
        self.landscape = landscape
        self.font = font if font is not None \
            else os.path.abspath(os.path.join(
                self.font_path,
                'sf_cartoonist/sfcartoonisthand-bold-webfont.ttf'
            ))
        self.action_font = action_font if action_font is not None \
            else os.path.abspath(os.path.join(
                self.font_path,
                'brushy_cre/Brushy-Cre.ttf'
            ))
        self.png_filename = None

    def run(self, nice=NICES['indicia']):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice.
                See shell_utils.os_nice for acceptable values.
        """
        script = os.path.abspath(
            os.path.join(
                current.request.folder, 'private', 'bin', 'indicia.sh')
        )

        real_metadata_filename = os.path.abspath(self.metadata_filename)
        real_indicia_filename = os.path.abspath(self.indicia_filename)

        args = []
        args.append(script)
        if self.landscape:
            args.append('-l')
        if self.font:
            args.append('-f')
            args.append(self.font)
        if self.action_font:
            args.append('-c')
            args.append(self.action_font)
        args.append(str(self.creator_id))
        args.append(real_metadata_filename)
        args.append(real_indicia_filename)

        # The image created by indicia.sh is placed in the current
        # directory. Use cwd= to change to the temp directory so it is
        # created there.
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.temp_directory(),
            preexec_fn=os_nice(nice),
        )
        p_stdout, p_stderr = p.communicate()
        # Generally there should be no output. Log to help troubleshoot.
        if p_stdout:
            LOG.warn('IndiciaSh run stdout: %s', p_stdout)
        if p_stderr:
            LOG.error('IndiciaSh run stderr: %s', p_stderr)

        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        if p.returncode:
            raise IndiciaShError('Indicia png creation failed: {err}'.format(
                err=p_stderr or p_stdout))

        # png file name has format <creator_id>-indicia.png
        png_filename = '{cid}-indicia.png'.format(cid=str(self.creator_id))
        path = os.path.join(
            self.temp_directory(),
            png_filename
        )
        matches = glob.glob(path)
        if matches:
            self.png_filename = matches[0]


class PublicationMetadata(object):
    """Class representing publication metadata"""

    def __init__(
            self,
            book_entity,
            metadata=None,
            serials=None,
            derivative=None,
            first_publication_text=None):
        """Constructor.

        Args:
            book_entity: Row instance representing book or integer (id of book)
            metadata: dict representing publication_metadata record.
            serials: list of dicts representing publication_serial records.
            derivative: dict representing derivative record.
            first_publication_text: string, text to use if this is the first
                publication. If None, uses 'First publication: zco.mx 2014.'
        """
        db = current.app.db
        book_record = entity_to_row(db.book, book_entity)
        if not book_record:
            raise LookupError('Book not found, {e}'.format(e=book_entity))
        self.book = book_record
        self.metadata = metadata if metadata is not None else {}
        self.serials = serials if serials is not None else []
        self.derivative = derivative if derivative is not None else {}
        self.first_publication_text = first_publication_text
        if first_publication_text is None:
            fmt = 'First publication: zco.mx {y}.'
            self.first_publication_text = fmt.format(
                y=datetime.date.today().year)
        self._publication_year_range = (None, None)
        self.errors = {}

    def __str__(self):
        return ' '.join(self.texts())

    def derivative_text(self):
        """Return the sentence form of a derivative record.

        Returns: string
        """
        db = current.app.db
        if not self.derivative:
            return ''

        fmt = (
            '"{name}" is a derivative of "{title}" '
            'from {y} by {creator} used under {cc_code}.'
        )

        years = '-'.join(
            sorted(set(
                [
                    str(self.derivative['from_year']),
                    str(self.derivative['to_year'])
                ]
            ))
        )

        query = (db.cc_licence.id == self.derivative['cc_licence_id'])
        cc_licence = db(query).select().first()
        cc_code = cc_licence.code if cc_licence \
            else IndiciaPage.default_licence_code

        return fmt.format(
            name=self.book.name,
            title=self.derivative['title'],
            y=years,
            creator=self.derivative['creator'],
            cc_code=cc_code,
        )

    def load(self):
        """Load the metadata, serials and derivative data from db."""
        db = current.app.db
        ignore_fields = ['id', 'created_on', 'updated_on']
        scrub = lambda d: {i:d[i] for i in d if i not in ignore_fields}

        self.metadata = {}
        query = (db.publication_metadata.book_id == self.book.id)
        metadata = db(query).select()
        if metadata:
            self.metadata = scrub(metadata.first().as_dict())

        self.serials = []
        query = (db.publication_serial.book_id == self.book.id)
        serials = db(query).select(
            orderby=[
                db.publication_serial.sequence,
                db.publication_serial.id,
            ],
        ).as_list()
        self.serials = [scrub(x) for x in serials]

        self.derivative = {}
        query = (db.derivative.book_id == self.book.id)
        derivative = db(query).select()
        if derivative:
            self.derivative = scrub(derivative.first().as_dict())
        return self

    def load_from_vars(self, request_vars):
        """Set the metadata, serials and derivative properties from
        request.vars.

        Args:
            request_vars: dict(request.vars)

        Returns:
            self
        """
        # The request_vars may include the following
        #     publication_metadata (none or one record)
        #     publication_serial   (none, one or more records)
        #     deravitive           (none or one record)

        # Convert republished from string to boolean
        if 'publication_metadata_republished' in request_vars:
            if request_vars['publication_metadata_republished'] == 'first':
                request_vars['publication_metadata_republished'] = False
            elif request_vars['publication_metadata_republished'] == 'repub':
                request_vars['publication_metadata_republished'] = True
            else:
                # This should trigger a validation error.
                request_vars['publication_metadata_republished'] = None

        if 'publication_metadata_is_anthology' in request_vars:
            request_vars['publication_metadata_is_anthology'] = True \
                if request_vars['publication_metadata_is_anthology'] == 'yes' \
                else False

        metadatas = vars_to_records(
            request_vars, 'publication_metadata', multiple=False)
        if not metadatas:
            raise LookupError('Unable to convert vars to metadata.')
        self.metadata = metadatas[0]
        if self.metadata['republished'] \
                and self.metadata['published_type'] == 'serial':
            self.serials = vars_to_records(
                request_vars, 'publication_serial', multiple=True)
        if 'is_derivative' in request_vars \
                and request_vars['is_derivative'] == 'yes':
            derivatives = vars_to_records(
                request_vars, 'derivative', multiple=False)
            if not derivatives:
                raise LookupError('Unable to convert vars to derivative.')
            self.derivative = derivatives[0]
        else:
            self.derivative = {}
        return self

    def metadata_text(self):
        """Return the sentence form of a publication_metadata record.

        Returns: string
        """
        if not self.metadata:
            return ''

        if not self.metadata['republished']:
            return self.first_publication_text

        if self.metadata['published_type'] == 'serial' and self.serials:
            # Set def serial_text produce the text.
            return ''

        # From here on: self.metadata['republished'] == True

        fmt = (
            'This work was originally '
            '{pubr_type} {pubd_type} in {y}{old}{publr}.'
        )
        pubr_type = 'self-published' \
            if self.metadata['published_format'] == 'paper' \
            and self.metadata['publisher_type'] == 'self' \
            else 'published'
        by = 'by' if self.metadata['publisher_type'] == 'press' else 'at'
        pubd_type = 'digitally' \
            if self.metadata['published_format'] == 'digital' \
            else 'in print'
        years = '-'.join(
            sorted(
                set([
                    str(self.metadata['from_year']),
                    str(self.metadata['to_year'])
                ])
            )
        )

        publr = ''
        if self.metadata['publisher']:
            by = 'by' if self.metadata['publisher_type'] == 'press' else 'at'
            publr = ' {by} {name}'.format(
                by=by,
                name=self.metadata['publisher'],
            )

        old = ''
        if self.book.name != self.metadata['published_name']:
            old = ' as "{name}"'.format(name=self.metadata['published_name'])

        return fmt.format(
            pubr_type=pubr_type,
            pubd_type=pubd_type,
            y=years,
            old=old,
            publr=publr.rstrip('.'),
        )

    def publication_year(self):
        """Calculate the book publication year based on the metadata.

        Returns:
            integer, the publication year
        """
        if not self.metadata:
            fmt = 'No metadata, no publication year, book id: {i}'
            raise ValueError(fmt.format(i=self.book.id))

        if self.serials:
            max_to_year = 0
            for serial in self.serials:
                if serial['to_year'] > max_to_year:
                    max_to_year = serial['to_year']
            return max_to_year
        else:
            return self.metadata['to_year']

    def serial_text(self, serial, is_anthology=False):
        """Return the sentence form of a publication_serial record.

        Args:
            serial: dict representing publication_serial record.
            is_anthology: If True, serial is an anthology.

        Returns: string
        """
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201

        if not serial:
            return ''

        fmts = {
            True: {
                'digital': '"{story}" was originally published digitally in "{title}" in {y} at {publr}.',
                'paper': {
                    'press': '"{story}" was originally published in print in "{title}" in {y} by {publr}.',
                    'self':  '"{story}" was originally self-published in print in "{title}" in {y}.',
                },
            },
            False: {
                'digital': 'This work was originally published digitally in {y} as "{title}" at {publr}.',
                'paper': {
                    'press': 'This work was originally published in print in {y} as "{title}" by {publr}.',
                    'self':  'This work was originally self-published in print in {y} as "{title}".',
                },
            }
        }

        formatted_title = lambda name, num: '{name} #{num}'.format(name=name, num=num) if num else name

        fmt = fmts[is_anthology][serial['published_format']]
        if serial['published_format'] == 'paper':
            fmt = fmts[is_anthology][serial['published_format']][serial['publisher_type']]

        years = '-'.join(
            sorted(
                set([str(serial['from_year']), str(serial['to_year'])])
            )
        )

        return fmt.format(
            story=formatted_title(serial['published_name'], serial['story_number']),
            title=formatted_title(serial['serial_title'], serial['serial_number']),
            y=years,
            publr=serial['publisher'].rstrip('.'),
        )

    def serials_text(self):
        """Return a list of sentence forms of publication_serial records.

        Returns: list of strings
        """
        is_anthology = False
        if self.metadata and 'is_anthology' in self.metadata:
            is_anthology = self.metadata['is_anthology']
        return [self.serial_text(x, is_anthology=is_anthology)
                for x in self.serials]

    def texts(self):
        """Return a list of sentence forms of publication metadata:
        metadata, serials, and derivative.

        Returns: list of strings
        """
        data = []
        data.append(self.metadata_text())
        data.extend(self.serials_text())
        data.append(self.derivative_text())
        return [x for x in data if x]

    def to_year_requires(self, from_year):
        """Return requires for to_year.

        Args:
            from_year: value of the record from_year
        """
        min_year, max_year = self.year_range()

        try:
            min_to_year = int(from_year)
        except (ValueError, TypeError):
            min_to_year = min_year
        return IS_INT_IN_RANGE(
            min_to_year, max_year,
            error_message='Enter a year {y} or greater'.format(
                y=str(min_to_year))
        )

    def update(self):
        """Update db records."""
        db = current.app.db

        query = (db.publication_metadata.book_id == self.book.id)
        existing = db(query).select(orderby=[db.publication_metadata.id])

        # There should be exactly one publication_metadata record per book
        if len(existing) > 1:
            for record in existing[1:]:
                db(db.publication_metadata.id == record.id).delete()
                db.commit()

        if not existing:
            db.publication_metadata.insert(book_id=self.book.id)
            db.commit()

        publication_metadata = db(query).select(
            orderby=[db.publication_metadata.id],
        ).first()

        if not publication_metadata:
            raise LookupError('publication_metadata record not found')

        default = default_record(
            db.publication_metadata, ignore_fields='common')
        default.update({
            'book_id': self.book.id,
        })

        data = dict(default)
        data.update(self.metadata)
        publication_metadata.update_record(**data)
        db.commit()

        # Update publication_serial records
        query = (db.publication_serial.book_id == self.book.id)
        existing = db(query).select(
            orderby=[
                db.publication_serial.sequence,
                db.publication_serial.id,
            ],
        )

        if len(self.serials) < len(existing):
            for serial in existing[len(self.serials):]:
                db(db.publication_serial.id == serial.id).delete()
                db.commit()

        if len(self.serials) > len(existing):
            for serial in self.serials[len(existing):]:
                db.publication_serial.insert(book_id=self.book.id)
            db.commit()

        query = (db.publication_serial.book_id == self.book.id)
        existing = db(query).select(
            orderby=[
                db.publication_serial.sequence,
                db.publication_serial.id,
            ],
        )

        if len(self.serials) != len(existing):
            raise LookupError('publication_serial do not match')

        default = default_record(db.publication_serial, ignore_fields='common')
        default.update({
            'book_id': self.book.id,
        })

        for c, record in enumerate(self.serials):
            data = dict(default)
            data.update(record)
            data['sequence'] = c
            existing[c].update_record(**data)
        db.commit()

        # Update derivative record.
        query = (db.derivative.book_id == self.book.id)
        existing = db(query).select(orderby=[db.derivative.id])

        # There should at most one derivative record per book
        if self.derivative:
            if len(existing) > 1:
                for record in existing[1:]:
                    db(db.derivative.id == record.id).delete()
                    db.commit()

            if not existing:
                db.derivative.insert(book_id=self.book.id)
                db.commit()

            derivative = db(query).select(orderby=[db.derivative.id]).first()

            if not derivative:
                raise LookupError('derivative record not found')

            cc_licence_id = cc_licence_by_code(
                IndiciaPage.default_licence_code,
                want='id',
                default=0
            )

            default = default_record(db.derivative, ignore_fields='common')
            default.update({
                'book_id': self.book.id,
                'cc_licence_id':cc_licence_id,
            })

            data = dict(default)
            data.update(self.derivative)
            derivative.update_record(**data)
            db.commit()
        else:
            # Delete any existing records
            for record in existing:
                db(db.derivative.id == record.id).delete()
                db.commit()

    def validate(self):
        """Validate data.

        Returns:
            dict, if no errors {}, else {field1: message, field2: message, ...}
        """
        db = current.app.db
        db_meta = db.publication_metadata
        db_serial = db.publication_serial

        published_types = ['whole', 'serial']
        published_formats = ['digital', 'paper']
        publisher_types = ['press', 'self']
        min_year, max_year = self.year_range()

        self.errors = {}
        if self.metadata:
            if self.metadata['republished']:
                db_meta.published_type.requires = IS_IN_SET(
                    published_types,
                    error_message='Please select an option',
                )
                if self.metadata['published_type'] == 'whole':
                    db_meta.published_name.requires = IS_NOT_EMPTY()
                    db_meta.published_format.requires = IS_IN_SET(
                        published_formats)
                    db_meta.publisher_type.requires = IS_IN_SET(
                        publisher_types)
                    db_meta.publisher.requires = IS_NOT_EMPTY()
                    if self.metadata['published_format'] == 'paper' and \
                            self.metadata['publisher_type'] == 'self':
                        db_meta.publisher.requires = None
                    db_meta.from_year.requires = IS_INT_IN_RANGE(
                        min_year, max_year)
                    db_meta.to_year.requires = self.to_year_requires(
                        self.metadata['from_year'])
                    for f in db_serial.fields:
                        db_serial[f].requires = None
                elif self.metadata['published_type'] == 'serial':
                    for f in db_meta.fields:
                        if f not in ['republished', 'published_type']:
                            db_meta[f].requires = None
                    if 'is_anthology' in self.metadata \
                            and self.metadata['is_anthology']:
                        db_serial.published_name.requires = IS_NOT_EMPTY()
                    else:
                        db_serial.published_name.requires = None
                    db_serial.published_format.requires = IS_IN_SET(
                        published_formats)
                    db_serial.publisher_type.requires = IS_IN_SET(
                        publisher_types)
                    db_serial.from_year.requires = IS_INT_IN_RANGE(
                        min_year, max_year)

            for field, value in self.metadata.items():
                if field in db_meta.fields:
                    value, error = db_meta[field].validate(value)
                    if error:
                        key = '{t}_{f}'.format(
                            t=str(db_meta), f=field)
                        self.errors[key] = error
                    self.metadata[field] = value

        for index, serial in enumerate(self.serials):
            for field, value in serial.items():
                if field in db_serial.fields:
                    if field == 'publisher':
                        db_serial.publisher.requires = IS_NOT_EMPTY()
                        if serial['published_format'] == 'paper' and \
                                serial['publisher_type'] == 'self':
                            db_serial.publisher.requires = None
                    if field == 'to_year':
                        db_serial.to_year.requires = self.to_year_requires(
                            serial['from_year'])
                    value, error = db_serial[field].validate(value)
                    if error:
                        key = '{t}_{f}__{i}'.format(
                            t=str(db_serial), f=field, i=index)
                        self.errors[key] = error
                    serial[field] = value

        db.derivative.from_year.requires = IS_INT_IN_RANGE(min_year, max_year)
        for field, value in self.derivative.items():
            if field in db.derivative.fields:
                if field == 'to_year':
                    db.derivative.to_year.requires = self.to_year_requires(
                        self.derivative['from_year'])
                value, error = db.derivative[field].validate(value)
                if error:
                    key = '{t}_{f}'.format(
                        t=str(db.derivative), f=field)
                    self.errors[key] = error
                self.derivative[field] = value

    def year_range(self):
        """Return a tuple representing the start and end range of publication
        years.

        Returns:
            tuple: (integer, integer)
        """
        if self._publication_year_range == (None, None):
            self._publication_year_range = publication_year_range()
        return self._publication_year_range


def cc_licence_by_code(code, want=None, default=None):
    """Return the cc_licence record or field for a given code.

    Args:
        code: string, cc_licence.code
        want: string, cc_licence field name. If None return Row instance.
        default: value to return if cc_licence record not found.

    Return:
        mixed, field value or Row if want=None.
    """
    db = current.app.db
    query = (db.cc_licence.code == code)
    cc_licence = db(query).select().first()
    if not cc_licence:
        return default

    if want is not None:
        return cc_licence[want]
    return cc_licence


def cc_licence_places():
    """Return a XML instance representing book cc licence places suitable for
    an HTML radio button input.

    """
    countries = [
        '',
        'Afghanistan',
        'Aland Islands Aland Islands',
        'Albania',
        'Algeria',
        'American Samoa',
        'Andorra',
        'Angola',
        'Anguilla',
        'Antarctica',
        'Antigua and Barbuda',
        'Argentina',
        'Armenia',
        'Aruba',
        'Australia',
        'Austria',
        'Azerbaijan',
        'Bahamas',
        'Bahrain',
        'Bangladesh',
        'Barbados',
        'Belarus',
        'Belgium',
        'Belize',
        'Benin',
        'Bermuda',
        'Bhutan',
        'Bolivia',
        'Bosnia and Herzegovina',
        'Botswana',
        'Bouvet Island',
        'Brazil',
        'British Indian Ocean Territory',
        'Brunei Darussalam',
        'Bulgaria',
        'Burkina Faso',
        'Burundi',
        'Cambodia',
        'Cameroon',
        'Canada',
        'Cape Verde',
        'Cayman Islands',
        'Central African Republic',
        'Chad',
        'Chile',
        'China Mainland',
        'Christmas Island',
        'Cocos (Keeling) Islands',
        'Colombia',
        'Comoros',
        'Congo',
        'Congo, the Democratic Republic of the',
        'Cook Islands',
        'Costa Rica',
        'Cote d`Ivoire',
        'Croatia',
        'Cuba',
        'Cyprus',
        'Czech Republic',
        'Denmark',
        'Djibouti',
        'Dominica',
        'Dominican Republic',
        'Ecuador',
        'Egypt',
        'El Salvador',
        'Equatorial Guinea',
        'Eritrea',
        'Estonia',
        'Ethiopia',
        'Falkland Islands (Malvinas)',
        'Faroe Islands',
        'Fiji',
        'Finland',
        'France',
        'French Guiana',
        'French Polynesia',
        'French Southern Territories',
        'Gabon',
        'Gambia',
        'Georgia',
        'Germany',
        'Ghana',
        'Gibraltar',
        'Greece',
        'Greenland',
        'Grenada',
        'Guadeloupe',
        'Guam',
        'Guatemala',
        'Guernsey',
        'Guinea',
        'Guinea-Bissau',
        'Guyana',
        'Haiti',
        'Heard Island and McDonald Islands',
        'Holy See (Vatican City State)',
        'Honduras',
        'Hong Kong',
        'Hungary',
        'Iceland',
        'India',
        'Indonesia',
        'Iran, Islamic Republic of',
        'Iraq',
        'Ireland',
        'Isle of Man',
        'Israel',
        'Italy',
        'Jamaica',
        'Japan',
        'Jersey',
        'Jordan',
        'Kazakhstan',
        'Kenya',
        'Kiribati',
        'Korea, Democratic People`s Republic of',
        'Korea, Republic of',
        'Kuwait',
        'Kyrgyzstan',
        'Lao People`s Democratic Republic',
        'Latvia',
        'Lebanon',
        'Lesotho',
        'Liberia',
        'Libyan Arab Jamahiriya',
        'Liechtenstein',
        'Lithuania',
        'Luxembourg',
        'Macao',
        'Macedonia, the former Yugoslav Republic of',
        'Madagascar',
        'Malawi',
        'Malaysia',
        'Maldives',
        'Mali',
        'Malta',
        'Marshall Islands',
        'Martinique',
        'Mauritania',
        'Mauritius',
        'Mayotte',
        'Mexico',
        'Micronesia, Federated States of',
        'Moldova',
        'Monaco',
        'Mongolia',
        'Montenegro',
        'Montserrat',
        'Morocco',
        'Mozambique',
        'Myanmar',
        'Namibia',
        'Nauru',
        'Nepal',
        'Netherlands',
        'Netherlands Antilles',
        'New Caledonia',
        'New Zealand',
        'Nicaragua',
        'Niger',
        'Nigeria',
        'Niue',
        'Norfolk Island',
        'Northern Mariana Islands',
        'Norway',
        'Oman',
        'Pakistan',
        'Palau',
        'Palestinian Territory, Occupied',
        'Panama',
        'Papua New Guinea',
        'Paraguay',
        'Peru',
        'Philippines',
        'Pitcairn',
        'Poland',
        'Portugal',
        'Puerto Rico',
        'Qatar',
        'Reunion',
        'Romania',
        'Russian Federation',
        'Rwanda',
        'Saint Barthelemy',
        'Saint Helena',
        'Saint Kitts and Nevis',
        'Saint Lucia',
        'Saint Martin (French part)',
        'Saint Pierre and Miquelon',
        'Saint Vincent and the Grenadines',
        'Samoa',
        'San Marino',
        'Sao Tome and Principe',
        'Saudi Arabia',
        'Senegal',
        'Serbia',
        'Seychelles',
        'Sierra Leone',
        'Singapore',
        'Slovakia',
        'Slovenia',
        'Solomon Islands',
        'Somalia',
        'South Africa',
        'South Georgia and the South Sandwich Islands',
        'Spain',
        'Sri Lanka',
        'Sudan',
        'Suriname',
        'Svalbard and Jan Mayen',
        'Swaziland',
        'Sweden',
        'Switzerland',
        'Syrian Arab Republic',
        'Taiwan',
        'Tajikistan',
        'Tanzania, United Republic of',
        'Thailand',
        'Timor-Leste',
        'Togo',
        'Tokelau',
        'Tonga',
        'Trinidad and Tobago',
        'Tunisia',
        'Turkey',
        'Turkmenistan',
        'Turks and Caicos Islands',
        'Tuvalu',
        'Uganda',
        'Ukraine',
        'United Arab Emirates',
        'United Kingdom',
        'United States',
        'United States Minor Outlying Islands',
        'Uruguay',
        'Uzbekistan',
        'Vanuatu',
        'Venezuela',
        'Viet Nam',
        'Virgin Islands, British',
        'Virgin Islands, U.S.',
        'Wallis and Futuna',
        'Western Sahara',
        'Yemen',
        'Zambia',
        'Zimbabwe',
    ]

    return XML(
        ','.join(
            ['{{"value":"{x}", "text":"{x}"}}'.format(x=x) for x in countries]
        )
    )


def cc_licences(book_entity):
    """Return a XML instance representing book cc licences suitable for
    an HTML radio button input.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    # {'value': record_id, 'text': description}, ...
    licences = db(db.cc_licence).select(
        db.cc_licence.ALL,
        orderby=db.cc_licence.number
    )

    data = cc_licence_data(book_record)

    scrub = lambda x: x.replace('"', '\\"')
    info = lambda x: scrub(render_cc_licence(data, cc_licence_entity=x))

    # line-too-long (C0301): *Line too long (%%s/%%s)*
    # pylint: disable=C0301
    return XML(
        ','.join(
            ['{{"value":"{x.id}", "text":"{x.code}", "info": "<div>{i}</div>"}}'.format(
                x=x, i=info(x)) for x in licences])
    )


def create_creator_indicia(creator, resize=False, optimize=False):
    """Create indicia for creator.

    Args:
        creator: Row instance representing creator.
        resize: If true, sizes of images are created
        optimize: If true, all images are optimized
    """
    db = current.app.db
    data = {}
    for orientation in ['portrait', 'landscape']:
        field = 'indicia_{o}'.format(o=orientation)
        # Delete existing
        if creator[field]:
            on_delete_image(creator[field])
            creator.update_record(**{field: None})
            db.commit()
        png_page = CreatorIndiciaPagePng(creator)
        png = png_page.create(orientation=orientation)
        stored_filename = store(
            db.creator[field],
            png,
            resize=resize,
        )
        if stored_filename:
            data[field] = stored_filename
            if optimize:
                AllSizesImages.from_names([data[field]]).optimize()

    creator.update_record(**data)
    db.commit()


def render_cc_licence(
        data, cc_licence_entity, template_field='template_web'):
    """Render the cc licence for the book.

    Args:
        data: dict of data for the template.
        cc_licence_entity: Row instance or integer (id) representing cc_licence
        template_field: string, name of cc_licence template field. One of
            'template_img', 'template_web'
    """
    db = current.app.db
    cc_licence_record = entity_to_row(db.cc_licence, cc_licence_entity)
    if not cc_licence_record:
        raise LookupError('CC licence not found, {e}'.format(
            e=cc_licence_entity))

    default_url = URL(c='search', f='index')

    if 'owner' not in data:
        data['owner'] = 'CREATOR NAME'

    if 'owner_url' not in data or data['owner_url'] is None:
        data['owner_url'] = default_url

    if 'title' not in data:
        data['title'] = 'NAME OF BOOK'

    if 'title_url' not in data or data['title_url'] is None:
        data['title_url'] = default_url

    if 'place' not in data or not data['place']:
        data['place'] = '&lt;YOUR COUNTRY&gt;'

    if 'year' not in data:
        data['year'] = datetime.date.today().year

    if 'url' not in data:
        data['url'] = cc_licence_record.url

    scrub = lambda x: x.upper().replace("'", '`') if x else 'n/a'

    for field in ['owner', 'place', 'title']:
        if field in data:
            data[field] = scrub(data[field])

    text = cc_licence_record[template_field].format(**data)
    return '{t}'.format(t=text)
