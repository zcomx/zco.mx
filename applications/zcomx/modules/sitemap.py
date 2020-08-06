#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Classes and functions related to zco.mx sitemap.
"""
import datetime
from gluon import *
from applications.zcomx.modules.records import Record


class SiteMapUrl(object):
    """Class representing a sitemap url."""

    def __init__(
            self,
            loc,
            last_modified=None,
            changefreq='daily',
            priority=1.0):
        """Initializer

        Args:
            loc: str, url location
            last_modified: datetime.date, date page was last modified
            changefreq: str, how frequently page is likely to change
            priority: float, relative priority of page
        """
        self.loc = loc
        self.last_modified = last_modified
        if self.last_modified is None:
            self.last_modified = datetime.date.today()
        self.changefreq = changefreq
        self.priority = priority

    def xml_component(self):
         xml_comp = TAG.url()
         xml_comp.append(TAG.loc(self.loc))
         xml_comp.append(TAG.lastmod(str(self.last_modified)))
         xml_comp.append(TAG.changefreq(self.changefreq))
         xml_comp.append(TAG.priority(self.priority))
         return xml_comp
