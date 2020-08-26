#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
facebook_api.py

Script to test using facebook API (facepy)
https://pypi.python.org/pypi/facepy/1.0.6
"""

import base64
import datetime
import sys
import traceback
import urllib.parse
from optparse import OptionParser
import requests
import applications.zcomx.modules.facepy as facepy
from applications.zcomx.modules.facebook import FacebookAPIAuthenticator
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'

# line-too-long (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301


class APIClient(object):
    """Class representing a client for the facebook API"""

    def __init__(self, graph, user_id='me'):
        """Initializer

        Args:
            graph: facepy.GraphAPI instance
            user_id: string, facebook user id
        """
        self.graph = graph
        self.user_id = user_id
        self.access_token = graph.oauth_token

    def accounts(self):
        """Get accounts."""
        return self.graph.get('{i}/accounts'.format(i=self.user_id))

    def info(self, fields=None):
        """Get user info."""
        if fields is None:
            field_query = ''
        else:
            field_query = ','.join(fields)
        result = self.graph.get('{u}?fields={f}'.format(
            u=self.user_id,
            f=field_query,
        ))
        return result

    def permissions(self):
        """Get permission settings."""
        result = self.graph.get('{i}/permissions'.format(i=self.user_id))
        for item in result['data']:
            print(item['permission'], ': ', item['status'])
        return result

    def post_photo_link(self):
        """Post a link to a photo to facebook."""
        post_data = dict(
            link='https://zco.mx/DanielMcCloskey/TopOfTheLine-04of08',
            picture='https://zco.mx/images/download/book_page.image.8766f7e5f669ee91.73636f636f766572206973737565342e706e67.png?size=web',
            name='Top Of The Line',
            caption='Book completed by Daniel McCloskey.',
            description="""Crazy cyber-gods send bio-warplanes to test our young hero. Start at issue 1 or just start reading sweet dragons battles right here. Four thumbs up! {now}""".format(now=str(datetime.datetime.now())),
        )

        return self.post('{i}/feed'.format(i=self.user_id), post_data)

    def post_tumblr_link(self):
        """Post a tumblr link to a photo to facebook."""
        post_data = dict(
            # message='Test @[23497828950:National Geographic] page',
            link='http://zcomx.tumblr.com/post/123701349131/ongoing-books-update-2015-07-09',
            # link='http://zcomx.tumblr.com/post/121120663936/daniel-mccloskey-top-of-the-line-03-of-08',
            # link='http://zcomx.tumblr.com/post/122427615576/valentine-gallardo-its-not-about-cheese-adventures-in-ve',
            picture='https://zco.mx/zcomx/static/images/white_280x280.png',
        )

        return self.post('{i}/feed'.format(i=self.user_id), post_data)

    def post_photo(self):
        """Post a photo to facebook."""
        post_data = dict(
            url='https://zco.mx/images/download/book_page.image.8766f7e5f669ee91.73636f636f766572206973737565342e706e67.png?size=web',
        )

        return self.post('{i}/photos'.format(i=self.user_id), post_data)

    def post_text(self):
        """Post a text message to facebook."""
        now = str(datetime.datetime.now())
        post_data = dict(
            message='* This is a test 013.\r\n\r\n* This is the second line.\r\n\r\n* {d}'.format(d=now),
        )

        return self.post('{i}/feed'.format(i=self.user_id), post_data)

    def post(self, path, post_data=None):
        """Post on facebook."""
        if post_data is None:
            post_data = {}

        if 'access_token' not in post_data:
            post_data['access_token'] = self.access_token

        if 'debug' not in post_data:
            post_data['debug'] = 'all'

        try:
            result = self.graph.post(
                path=path,
                **post_data
            )
        except facepy.FacebookError as err:
            LOG.error('Post returned exception:')
            error_fields = [
                'message', 'code', 'error_subcode', 'error_user_msg',
                'is_transient', 'error_data', 'error_user_title']
            for field in error_fields:
                LOG.error('%s: %s', field, getattr(err, field))
            return
        return result


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    facebook_api.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """)


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
    )

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')

    settings = current.app.local_settings
    auth = FacebookAPIAuthenticator(
        settings.facebook_email,
        settings.facebook_password,
        settings.facebook_client_id,
        settings.facebook_redirect_uri,
        settings.facebook_page_name
    )

    client = auth.authenticate(client_class=APIClient)

    command = args[0] if args else 'info'

    if command == 'info':
        print(client.info(fields=['id', 'about', 'access_token']))
    elif command == 'accounts':
        print(client.accounts())
    elif command == 'permissions':
        print(client.permissions())
    elif command == 'post_text':
        print(client.post_text())
    elif command == 'post_photo_linke':
        print(client.post_photo_link())
    elif command == 'post_tumblr_link':
        print(client.post_tumblr_link())
    elif command == 'post_photo':
        print(client.post_photo())
    else:
        print('Invalid command: {c}'.format(c=command))

    LOG.info('Done.')

if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
