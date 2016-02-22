#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

modules/stickon/restricted.py

Classes extending functionality of gluon/restricted.py particular to the zcomx
application.

"""
import os
from gluon import *
from gluon.restricted import TicketStorage

# E1101: *%s %r has no %r member*
# pylint: disable=E1101

LOG = current.app.logger


def log_ticket(ticket):
    """Log a ticket."""
    if not ticket:
        return

    # Ticket may have have the app prepended
    parts = ticket.split(os.sep)
    ticket_id = parts[-1]
    if not ticket_id:
        return

    request = current.request
    ticket_storage = TicketStorage()
    app = None   # 'app' is an errors sub directory, not used
    contents = ticket_storage.load(request, app, ticket_id)
    traceback = contents.get('traceback')
    for line in traceback.split("\n"):
        LOG.error(line)
