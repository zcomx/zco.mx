#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

User Agent classes and functions.
"""
from gluon import *

LOG = current.app.logger

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0'

def is_bot():
    """Determine if the http request is a bot or not.

    Returns:
        True if request is from a bot (ss per user_agent_parser)

    """
    result = False
    user_agent = current.request.user_agent()
    if user_agent:
        if user_agent.bot is not None:
            result = user_agent.bot
        else:
            # Treat any unknown user agents as a bot.
            result = True
    else:
        LOG.error(
            'Bot status unknown, user agent: %s',
            current.request.env.http_user_agent
        )
    return result
