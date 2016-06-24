#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
facebook_poc.py

Script to POC test using facebook API (facepy)
https://pypi.python.org/pypi/facepy/1.0.6
"""
import datetime
import requests
import sys
import traceback
import urlparse
from BeautifulSoup import BeautifulSoup
from optparse import OptionParser
import applications.zcomx.modules.facepy as facepy
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'

# line-too-long (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301


class FacebookAPIAuthenticator(object):
    """Class representing a Facebook API Authenticator"""

    page_titles = {
        # page key: list of possible titles of page <title></title>
        'login': ['Welcome to Facebook', 'Log into Facebook | Facebook'],
        'logged_in': ['Facebook'],
    }

    def __init__(self, email, password, client_id, redirect_uri, page_name):
        """Initializer"""
        self.email = email
        self.password = password
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.page_name = page_name
        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/43.0.2357.121 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/35.0.0.48.273;]',
        })

    def authenticate(self):
        """Authenticate."""
        if not self.login():
            LOG.error('Login failed')
            exit(1)
        LOG.debug('Login success')
        access_token = self.get_token()
        if not access_token:
            LOG.error('Unable to acquire access token')
            exit(1)

        graph = facepy.GraphAPI(access_token, version='2.4')
        client = FacebookAPIClient(graph)
        accounts = client.accounts()
        if not accounts:
            LOG.error('Unable to access user accounts.')
            exit(1)

        page_access_token = None
        user_id = None
        for account in accounts['data']:
            if account['name'] == self.page_name:
                user_id = account['id']
                page_access_token = account['access_token']

        if not user_id:
            LOG.error('Unable to get page user-id.')
            exit(1)

        if not page_access_token:
            LOG.error('Unable to get page access_token.')
            exit(1)

        # Reset the graph to use the page token.
        graph = facepy.GraphAPI(page_access_token, version='2.4')
        return FacebookAPIClient(graph, user_id)

    def get_token(self):
        """Get the access token."""
        token = None
        data = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'token',
            'scope': 'publish_actions',
        }
        url = 'https://www.facebook.com/dialog/oauth'
        response = self.session.get(url, params=data)
        for h in response.history:
            if 'location' not in h.headers:
                continue
            result = urlparse.urlparse(h.headers['location'])
            query = urlparse.parse_qs(result.fragment)
            if 'access_token' in query:
                token = query['access_token'][0]
                break
        return token

    def login(self):
        """Log into facebook."""
        # Access the login page for the form inputs
        url = 'https://www.facebook.com/login.php'
        response = self.session.get(url)
        soup = BeautifulSoup(response.text)
        title = soup.html.head.title.string
        if not title or title not in self.page_titles['login']:
            LOG.error('Unable to access facebook login page')
            LOG.error(
                'Page title does not match, expected one of: %s, got: %s',
                str(self.page_titles['login']),
                title,
            )
            return False
        form = soup.find('form')
        inputs = form.findAll('input')
        post_data = {}
        for form_input in inputs:
            # pylint complains about has_key, but this is a custom
            # BeautifulSoup Tag method.
            if not form_input.has_key('type'):
                continue
            if form_input['type'] != 'hidden':
                continue
            if form_input.has_key('value'):
                post_data[form_input['name']] = form_input['value']
            elif form_input.has_key('checked'):
                post_data[form_input['name']] = form_input['checked']
        post_data['email'] = self.email
        post_data['pass'] = self.password

        # Submit the login form
        self.session.headers.update({'referer': 'url'})
        url = 'https://www.facebook.com/login.php?login_attempt=1'
        response = self.session.post(url, data=post_data)
        soup = BeautifulSoup(response.text)
        title = soup.html.head.title.string
        if not title or title not in self.page_titles['logged_in']:
            LOG.error('Unable to login into facebook page')
            LOG.error(
                'Page title does not match, expected one of: %s, got: %s',
                str(self.page_titles['logged_in']),
                title,
            )
            return False
        return True


class FacebookAPIClient(object):
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
            print item['permission'], ': ', item['status']
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
    print """
USAGE
    facebook_poc.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """


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

    (options, unused_args) = parser.parse_args()

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
    client = auth.authenticate()
    # print client.user_id()
    # print client.info(fields=['id', 'name'])
    print client.info(fields=['id', 'about', 'access_token'])
    # print client.accounts()
    # print client.permissions()
    # print client.post_text()
    # print client.post_photo_link()
    # print client.post_tumblr_link()
    # print client.post_photo()

    LOG.info('Done.')

if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
