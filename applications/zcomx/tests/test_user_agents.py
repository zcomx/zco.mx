#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/user_agents.py

"""
import unittest
from gluon import *
from gluon.globals import Request
from applications.zcomx.modules.user_agents import (
    USER_AGENTS,
    is_bot,
)
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    def test__is_bot(self):
        # pylint: disable=line-too-long
        tests = [
            # (user_agent, expect)
            (USER_AGENTS.non_bot, False),
            (USER_AGENTS.bot, True),
            ("Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0", False),
            ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www. google.com/bot.html)", True),
            ("Mozilla/5.0 (compatible; MJ12bot/v1.4.7; http://mj12bot.com/)", True),
            ("Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.  com/bingbot.htm)", True),
            # unregistered bots
            ("Mozilla/5.0 (compatible; AhrefsBot/5.2; +http://ahrefs.com/robot/)", True),
            ("Mozilla/5.0 (compatible; Dataprovider.com;)", True),
            ("", True),
            (None, True),
        ]
        for t in tests:
            # pylint: disable=protected-access
            current.session._user_agent = None      # Clear cache
            current.request.env.http_user_agent = t[0]
            self.assertEqual(is_bot(), t[1])


        # Test indeterminate_is_bot
        current.session._user_agent = None      # Clear cache
        current.request.env.http_user_agent = None
        self.assertEqual(is_bot(indeterminate_is_bot=True), True)
        self.assertEqual(is_bot(indeterminate_is_bot=False), False)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
