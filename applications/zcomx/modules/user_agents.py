#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

User Agent classes and functions.
"""
from gluon import *
from gluon.storage import Storage

LOG = current.app.logger

USER_AGENTS = Storage({
    'bot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www. google.com/bot.html)',
    'non_bot': 'Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0',
})

def is_bot(indeterminate_is_bot=True):
    """Determine if the http request is a bot or not.

    Args:
        indeterminate_is_bot: If True, if the user agent is indeterminate,
            assume it is a bot.

    Returns:
        True if request is from a bot (ss per user_agent_parser)
    """
    try:
        user_agent = current.request.user_agent()
    except TypeError:
        # This indicates http_user_agent is None
        # Treat as if it is a bot.
        return indeterminate_is_bot

    if not user_agent:
        LOG.error(
            'Bot status unknown, user agent: %s',
            current.request.env.http_user_agent
        )
        return indeterminate_is_bot

    if user_agent.bot is None:
        return indeterminate_is_bot

    return user_agent.bot
