# -*- coding: utf-8 -*-
"""Torrent controller functions"""

import os
import shutil
from applications.zcomx.modules.downloaders import TorrentDownloader
from applications.zcomx.modules.images import ResizeImg


def download():
    """Download torrent

    request.args(0): one of 'all', 'book', 'creator',
    request.args(1): integer, id of record
        if request.args(0) is 'book' or 'creator'.
        Not used if request.args(0) is 'all'.
    """
    return TorrentDownloader().download(request, db)
