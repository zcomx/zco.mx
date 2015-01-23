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
    orientation as page_orientation, \
    publication_year_range
from applications.zcomx.modules.creators import \
    formatted_name as creator_formatted_name
from applications.zcomx.modules.images import \
    UploadImage, \
    store
from applications.zcomx.modules.shell_utils import TempDirectoryMixin
from applications.zcomx.modules.utils import \
    NotFoundError, \
    default_record, \
    entity_to_row, \
    vars_to_records

LOG = logging.getLogger('app')
DEFAULT_BOOK_TYPE = 'one-shot'


class IndiciaPage(object):
    """Class representing an indicia page.

    The indicia page is the web version of the indicia (as opposed to the
    indicia image)
    """
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

    def default_licence(self):
        """Return the default licence record."""
        cc_licence_entity = cc_licence_by_code(
            self.default_licence_code, default=None)
        if cc_licence_entity is None:
            raise NotFoundError('CC licence not found: {code}'.format(
                code=self.default_licence_code))
        return cc_licence_entity

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

    def render(self, orientation='portrait'):
        """Render the indicia page.

        Args:
            orientation: string, one of 'portrait' or 'landscape'
        """
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

        intro = """
        IF  YOU  ENJOYED THIS WORK YOU CAN
        HELP OUT BY  GIVING  SOME MONIES!!
        OR BY TELLING OTHERS ON  TWITTER,
        TUMBLR  AND  FACEBOOK.
        """
        text_divs.append(
            DIV(
                intro.strip(),
                _class='call_to_action',
            )
        )

        if self.creator:
            text_divs.append(DIV(
                DIV('CONTRIBUTE MONIES: http://{i:03d}.zco.mx/monies'.format(
                    i=self.creator.id)),
                DIV('CONTACT INFO: http://{i:03d}.zco.mx'.format(
                    i=self.creator.id)),
                _class='contribute_contact_urls',
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

    def get_orientation(self):
        """Return the orientation of the book (based on its last page)."""
        if self._orientation is None:
            orientation = None
            try:
                orientation = page_orientation(
                    get_page(self.book, page_no='last'))
            except NotFoundError:
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
                raise NotFoundError('CC licence not found: {code}'.format(
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
        return IndiciaPage.render(self, orientation=orientation)


class BookIndiciaPagePng(BookIndiciaPage, TempDirectoryMixin):
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
        indicia_sh.run(nice=True)
        # IndiciaSh creates file in a temp directory that is removed as soon
        # as the instance is destroyed.
        # Copy png file to this classes temp directory.
        filename = os.path.join(self.temp_directory(), 'indicia.png')
        shutil.copy(indicia_sh.png_filename, filename)
        return filename

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


class CreatorIndiciaPage(IndiciaPage):
    """Class representing a creator indicia page.

    A creator indicia page is used to preview what a creator's book indicia
    page would look like.
    """

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.creator = entity_to_row(db.creator, self.entity)

    def licence_text(self, template_field='template_web'):
        """Return the licence record used for the licence text on the indicia
        page.

        Args:
            template_field: string, name of cc_licence template field. One of
                'template_img', 'template_web'
        """
        data = dict(owner=creator_formatted_name(self.creator))
        return render_cc_licence(
            data,
            self.default_licence(),
            template_field=template_field,
        )


class CreatorIndiciaPagePng(CreatorIndiciaPage, TempDirectoryMixin):
    """Class representing a creator indicia page in png format."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
        """
        CreatorIndiciaPage.__init__(self, entity)
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
        indicia_sh.run(nice=True)
        # IndiciaSh creates file in a temp directory that is removed as soon
        # as the instance is destroyed.
        # Copy png file to this classes temp directory.
        filename = os.path.join(self.temp_directory(), 'indicia.png')
        shutil.copy(indicia_sh.png_filename, filename)
        return filename

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
                'sf_cartoonist/SF-Cartoonist-Hand-Bold.ttf'
            ))
        self.action_font = action_font if action_font is not None \
            else os.path.abspath(os.path.join(
                self.font_path,
                'brushy_cre/Brushy-Cre.ttf'
            ))
        self.png_filename = None

    def run(self, nice=False):
        """Run the shell script and get the output.

        Args:
            nice: If True, run resize script with nice.
        """
        script = os.path.abspath(
            os.path.join(
                current.request.folder, 'private', 'bin', 'indicia.sh')
        )

        real_metadata_filename = os.path.abspath(self.metadata_filename)
        real_indicia_filename = os.path.abspath(self.indicia_filename)

        args = []
        if nice:
            args.append('nice')
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
            cwd=self.temp_directory()
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
            raise NotFoundError('Book not found, {e}'.format(e=book_entity))
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
            else CreatorIndiciaPage.default_licence_code

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
                db.publication_serial.story_number,
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

        metadatas = vars_to_records(
            request_vars, 'publication_metadata', multiple=False)
        if not metadatas:
            raise NotFoundError('Unable to convert vars to metadata.')
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
                raise NotFoundError('Unable to convert vars to derivative.')
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

    def serial_text(self, serial, single=True):
        """Return the sentence form of a publication_serial record.

        Args:
            serial: dict representing publication_serial record.
            single: if False, assume serial is one of several stories.

        Returns: string
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201

        if not serial:
            return ''

        fmt = (
            '"{story}" was originally '
            '{pubr_type} {pubd_type} in "{serial}" in {y}{publr}.'
        )
        num = ''
        if not single:
            num = ' #{num}'.format(num=serial['story_number'])
        story = '{name}{num}'.format(name=serial['published_name'], num=num)

        pubr_type = 'self-published' \
            if serial['published_format'] == 'paper' \
            and serial['publisher_type'] == 'self' \
            else 'published'
        by = 'by' if serial['publisher_type'] == 'press' else 'at'
        pubd_type = 'digitally' \
            if serial['published_format'] == 'digital' \
            else 'in print'

        serial_num = ''
        if serial['serial_number'] and serial['serial_number'] > 1:
            serial_num = ' #{num}'.format(num=serial['serial_number'])
        serial_name = '{name}{num}'.format(
            name=serial['serial_title'], num=serial_num)

        years = '-'.join(
            sorted(
                set([str(serial['from_year']), str(serial['to_year'])])
            )
        )

        publr = ''
        if serial['publisher']:
            by = 'by' if serial['publisher_type'] == 'press' else 'at'
            publr = ' {by} {name}'.format(
                by=by,
                name=serial['publisher'],
            )

        return fmt.format(
            story=story,
            num=num,
            pubr_type=pubr_type,
            pubd_type=pubd_type,
            serial=serial_name,
            y=years,
            publr=publr.rstrip('.'),
        )

    def serials_text(self):
        """Return a list of sentence forms of publication_serial records.

        Returns: list of strings
        """
        single = len(self.serials) <= 1
        return [self.serial_text(x, single=single) for x in self.serials]

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

        publication_metadata = db(query).select(
            orderby=[db.publication_metadata.id],
        ).first()

        if not publication_metadata:
            raise NotFoundError('publication_metadata record not found')

        default = default_record(
            db.publication_metadata, ignore_fields='common')
        default.update({
            'book_id': self.book.id,
        })

        data = dict(default)
        data.update(self.metadata)
        publication_metadata.update_record(**data)

        # Update publication_serial records
        query = (db.publication_serial.book_id == self.book.id)
        existing = db(query).select(
            orderby=[
                db.publication_serial.story_number,
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

        query = (db.publication_serial.book_id == self.book.id)
        existing = db(query).select(
            orderby=[
                db.publication_serial.story_number,
                db.publication_serial.id,
            ],
        )

        if len(self.serials) != len(existing):
            raise NotFoundError('publication_serial do not match')

        default = default_record(db.publication_serial, ignore_fields='common')
        default.update({
            'book_id': self.book.id,
        })

        for c, record in enumerate(self.serials):
            data = dict(default)
            data.update(record)
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

            derivative = db(query).select(orderby=[db.derivative.id]).first()

            if not derivative:
                raise NotFoundError('derivative record not found')

            cc_licence_id = cc_licence_by_code(
                CreatorIndiciaPage.default_licence_code,
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
                    db_serial.published_name.requires = IS_NOT_EMPTY()
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
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

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


def clear_creator_indicia(creator, field=None):
    """Clear indicia for creator.

    Args:
        creator: creator Row instance
    Returns:
        creator
    """
    db = current.app.db
    if field is not None:
        fields = [field]
    else:
        fields = ['indicia_image', 'indicia_portrait', 'indicia_landscape']

    data = {}
    for field in fields:
        if creator[field]:
            up_image = UploadImage(db.creator[field], creator[field])
            up_image.delete_all()
            data[field] = None
    creator.update_record(**data)
    db.commit()


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
        clear_creator_indicia(creator, field=field)
        png_page = CreatorIndiciaPagePng(creator)
        png = png_page.create(orientation=orientation)
        stored_filename = store(
            db.creator[field],
            png,
            resize=resize,
            run_optimize=optimize,
        )
        if stored_filename:
            data[field] = stored_filename

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
        raise NotFoundError('CC licence not found, {e}'.format(
            e=cc_licence_entity))

    if 'owner' not in data:
        data['owner'] = 'CREATOR NAME'

    if 'title' not in data:
        data['title'] = 'NAME OF BOOK'

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


class IndiciaUpdateInProgress(Exception):
    """Exception class for indicia update-in-progress errors."""
    pass


def update_creator_indicia(
        creator,
        background=False,
        nice=False,
        resize=True,
        optimize=True):
    """Update a creator's indicia images.

    Args:
        creator: Row instance representing a creator record.
        background: if True, the update process is backgrounded
        nice: if True, nice update process
        resize: if True, create various sizes of indicia images
        optimize: if True, optimize images

    Returns:
        creator_record if background is False
    """
    if not creator:
        return

    if not background:
        create_creator_indicia(
            creator,
            resize=resize,
            optimize=optimize,
        )
        return

    # Run background command
    run_py = os.path.abspath(os.path.join(
        current.request.folder,
        'private',
        'bin',
        'run_py.sh'
    ))

    script = os.path.join(
        'applications',
        current.request.application,
        'private',
        'bin',
        'update_creator_indicia.py'
    )

    args = []
    if nice:
        args.append('nice')
    args.append(run_py)
    args.append(script)
    if resize:
        args.append('-r')
    if optimize:
        args.append('-o')
    args.append(str(creator.id))
    if background:
        args.append('&')

    subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
