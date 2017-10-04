#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

User Agent classes and functions.
"""
from gluon import *
from gluon.contrib.user_agent_parser import (
    Browser,
    DetectorBase,
    DetectorsHub,
)

LOG = current.app.logger


def is_bot():
    """Determine if the http request is a bot or not.

    Returns:
        True if request is from a bot (ss per user_agent_parser)

    """

    result = False
    user_agent = current.request.user_agent()
    if user_agent and user_agent.bot is not None:
        result = user_agent.bot
    else:
        LOG.error(
            'Bot status unknown, user agent: %s',
            current.request.env.http_user_agent
        )
    return result
