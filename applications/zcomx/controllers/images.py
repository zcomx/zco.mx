# -*- coding: utf-8 -*-
"""Image controller functions"""

from applications.zcomx.modules.images import Downloader


def download():
    """Download image function.

    Adapted from Response.download. Handles image files stored in multiple
    subdirectores.

    request.args(0)
    """
    return Downloader().download(request, db)
