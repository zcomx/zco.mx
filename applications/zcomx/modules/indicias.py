#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Indicias classes and functions.
"""
import datetime
from gluon import *

from applications.zcomx.modules.books import \
    cc_licence_data, \
    get_page, \
    orientation as page_orientation
from applications.zcomx.modules.creators import \
    formatted_name as creator_formatted_name
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

DEFAULT_BOOK_TYPE = 'one-shot'


class IndiciaPage(object):
    """Class representing an indicia page.

    The indicia page is the web version of the indicia (as opposed to the
    indicia image)
    """
    default_indicia_image = URL(c='static', f='images/indicia_image.png')
    default_licence_code = 'All Rights Reserved'

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
            user_id: integer, id of user triggering event.
        """
        self.entity = entity
        self.creator = None     # Row instance representing creator

    def default_licence(self):
        """Return the default licence record."""
        db = current.app.db
        query = (db.cc_licence.code == self.default_licence_code)
        cc_licence_entity = db(query).select().first()
        if not cc_licence_entity:
            raise NotFoundError('CC licence not found: {code}'.format(
                code=self.default_licence_code))
        return cc_licence_entity

    def licence_text(self):
        """Return the licence record used for the licence text on the indicia
        page.
        """
        return render_cc_licence(
            {},
            self.default_licence()
        )

    def render(self, orientation='portrait'):
        """Render the indicia page."""
        img_src = self.default_indicia_image
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
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.table = db.book
        self.book = entity_to_row(db.book, self.entity)
        self.creator = entity_to_row(db.creator, self.book.creator_id)

    def licence_text(self):
        """Return the licence record used for the licence text on the indicia
        page.
        """
        db = current.app.db
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

        return render_cc_licence(
            data,
            cc_licence_entity
        )

    def render(self, orientation=None):
        """Render the indicia page."""
        if orientation is None:
            orientation = page_orientation(
                get_page(self.book, page_no='last'))
            if orientation != 'landscape':
                orientation = 'portrait'
        return IndiciaPage.render(self, orientation=orientation)


class CreatorIndiciaPage(IndiciaPage):
    """Class representing a book indicia page."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.creator = entity_to_row(db.creator, self.entity)

    def licence_text(self):
        """Return the licence record used for the licence text on the indicia
        page.
        """
        data = dict(owner=creator_formatted_name(self.creator))
        return render_cc_licence(
            data,
            self.default_licence()
        )


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


def render_cc_licence(
        data, cc_licence_entity, template_field='template_web'):
    """Render the cc licence for the book.

    Args:
        data: dict of data for the template.
        cc_licence_entity: Row instance or integer (id) representing cc_licence
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
