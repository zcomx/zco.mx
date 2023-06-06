#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to HTML meta data.
"""
from applications.zcomx.modules.books import (
    html_metadata as book_metadata
)
from applications.zcomx.modules.creators import (
    html_metadata as creator_metadata
)
from applications.zcomx.modules.zco import (
    html_metadata as site_metadata
)


class BaseMetaPreparer():
    """Base class representing an HTML metadata preparer"""

    def __init__(self, metadata):
        """Constructor

        Args:
            metadata: dict of metadata.
                Example:
                {
                    'book': {k: v, ...},
                    'creator': {k, v, ...},
                    'site': {k: v, ...}
                }
        """
        self.metadata = metadata

    @staticmethod
    def as_property_content(metadata):
        """Convert a dict of property contents suitable for response.meta.

        Args:
            metadata: dict, {property1: content1, property2, content2, ...}

        Returns:
            dict, named dict
                {
                    property1: {property1: content1},
                    property2: {property2: content2},
                    ...
                }
        """
        meta = {}
        for k, v in list(metadata.items()):
            meta[k] = {'property': k, 'content': v}
        return meta

    @staticmethod
    def formatter():
        """Return the formatter used to prepare data.

        Returns:
            function used for formatting.
        """
        return lambda x: x          # Default no formatting.

    def prepared(self):
        """Return the metadata prepared for html.

        Returns:
            dict, format depends on formatter. Examples:
                1. default formatter (name value pairs):
                    {'name': 'val'}
                    <meta name="name" value="val">
                2. as_property_content (The name is insignificant)
                    {'name': {'prop1': val1, 'prop2': 'val2',...}}
                    <meta prop1="val1" prop2="val2">
        """
        func = self.formatter()
        return func(self.set_data())

    def set_data(self):
        """Convert the generic metadata to data need for this format.
        Subclasses decide what format this is.

        Returns:
            dict
        """
        raise NotImplementedError()


class OpenGraphMetaPreparer(BaseMetaPreparer):
    """Class representing a OpenGraph HTML metadata preparer
    Facebook sharer.php uses these.
    """

    @staticmethod
    def formatter():
        return BaseMetaPreparer.as_property_content

    def set_data(self):
        site = self.metadata['site']
        meta = {}
        meta['og:title'] = site['title']
        meta['og:type'] = site['type']
        meta['og:url'] = site['url']
        meta['og:image'] = site['icon']
        meta['og:site_name'] = site['name']
        meta['og:description'] = site['description']
        return meta


class OpenGraphBookMetaPreparer(OpenGraphMetaPreparer):
    """Class representing a OpenGraph HTML metadata preparer for a book"""

    def set_data(self):
        book = self.metadata['book']
        site = self.metadata['site']
        meta = {}
        meta['og:title'] = book['name']
        meta['og:type'] = book['type']
        meta['og:url'] = book['url']
        if book['image_url']:
            meta['og:image'] = book['image_url']
        meta['og:site_name'] = site['name']
        by_msg = 'By {c} available at {s}'.format(
            c=book['creator_name'],
            s=site['name']
        )
        site_msg = 'Available at {s}'.format(s=site['name'])
        meta['og:description'] = \
            book['description'] if book['description'] else \
            by_msg if book['creator_name'] else \
            site_msg
        return meta


class OpenGraphCreatorMetaPreparer(OpenGraphMetaPreparer):
    """Class representing a OpenGraph HTML metadata preparer for a creator"""

    def set_data(self):
        creator = self.metadata['creator']
        site = self.metadata['site']
        meta = {}
        meta['og:title'] = creator['name']
        meta['og:type'] = creator['type']
        meta['og:url'] = creator['url']
        if creator['image_url']:
            meta['og:image'] = creator['image_url']
        else:
            meta['og:image'] = ''
        meta['og:site_name'] = site['name']
        site_msg = 'Available at {s}'.format(s=site['name'])
        meta['og:description'] = \
            creator['description'] if creator['description'] else \
            site_msg
        return meta


class TwitterMetaPreparer(BaseMetaPreparer):
    """Class representing a twitter HTML metadata preparer"""

    twitter_card = 'summary_large_image'

    def set_data(self):
        site = self.metadata['site']
        meta = {}
        meta['twitter:card'] = self.twitter_card
        meta['twitter:site'] = site['twitter']
        meta['twitter:creator'] = site['twitter']
        meta['twitter:title'] = site['title']
        meta['twitter:description'] = site['description']
        meta['twitter:image'] = site['icon']
        return meta


class TwitterBookMetaPreparer(TwitterMetaPreparer):
    """Class representing a twitter HTML metadata preparer for a book"""

    def set_data(self):
        book = self.metadata['book']
        site = self.metadata['site']
        meta = {}
        meta['twitter:card'] = self.twitter_card
        meta['twitter:site'] = site['twitter']
        meta['twitter:creator'] = book['creator_twitter'] or site['twitter']
        meta['twitter:title'] = book['name']
        site_msg = 'Available at {s}'.format(s=site['name'])
        meta['twitter:description'] = \
            book['description'] if book['description'] else \
            site_msg
        meta['twitter:image'] = book['image_url'] or site['icon']
        return meta


class TwitterCreatorMetaPreparer(TwitterMetaPreparer):
    """Class representing a twitter HTML metadata preparer for a creator"""

    def set_data(self):
        creator = self.metadata['creator']
        site = self.metadata['site']
        meta = {}
        meta['twitter:card'] = self.twitter_card
        meta['twitter:site'] = site['twitter']
        meta['twitter:creator'] = creator['twitter'] or site['twitter']
        meta['twitter:title'] = creator['name']
        site_msg = 'Available at {s}'.format(s=site['name'])
        meta['twitter:description'] = \
            creator['description'] if creator['description'] else \
            site_msg
        meta['twitter:image'] = creator['image_url'] or site['icon']
        return meta


class MetadataFactory():
    """Class representing a factory for metadata."""

    class_lookup = {
        'opengraph': {
            'book': OpenGraphBookMetaPreparer,
            'creator': OpenGraphCreatorMetaPreparer,
            'site': OpenGraphMetaPreparer,
        },
        'twitter': {
            'book': TwitterBookMetaPreparer,
            'creator': TwitterCreatorMetaPreparer,
            'site': TwitterMetaPreparer,
        },
    }

    def __init__(self, preparer_codes, html_metadata, page_type='site'):
        """Constructor

        Args:
            preparer_codes: list of strings, codes of preparers.
            html_metadata: dict as returned by html_metadata_from_records
            page_type: str, one of 'book', 'creator', or 'site'
        """
        self.preparer_codes = preparer_codes
        self.html_metadata = html_metadata
        self.page_type = page_type

    def classes(self):
        """Return the preparer classes needed to prepare the records.

        Returns:
            list of BaseMetaPreparer subclass classes
        """
        classes = []
        for preparer_code in self.preparer_codes:
            classes.append(self.class_lookup[preparer_code][self.page_type])
        return classes

    def instantiated_preparers(self):
        """Return a list metadata preparers.

        Args:
            classes: list of BaseMetaPreparer subclass classes
            metadata: dict of data as per metadata_from_records
        """
        preparers = []
        for c in self.classes():
            preparers.append(c(self.html_metadata))
        return preparers

    def metadata(self):
        """Return prepared metadata."""
        meta = {}
        for p in self.instantiated_preparers():
            meta.update(p.prepared())
        return meta


def html_metadata_from_records(creator, book):
    """Get the prepared metadata from records.

    Args:
        creator: Creator instance
        book: book instance

    Returns:
        dict {'book': {}, 'creator': {}, 'site': {}}
    """
    metadata = {
        'book': {},
        'creator': {},
        'site': site_metadata(),
    }

    if book is not None:
        metadata['book'] = book_metadata(book)
    if creator is not None:
        metadata['creator'] = creator_metadata(creator)
    return metadata
