#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Classes and functions related to facebook posts.
"""
import base64
import datetime
import urlparse
import requests
from BeautifulSoup import BeautifulSoup
from gluon import *
import applications.zcomx.modules.facepy as facepy

LOG = current.app.logger


class FacebookAPIError(Exception):
    """Exception class for facebook API errors."""
    pass


class FacebookAPIAuthenticator(object):
    """Class representing a Facebook API Authenticator"""

    page_titles = {
        # page key: list of possible titles of page <title></title>
        'login': [
            'Welcome to Facebook',
            'Log into Facebook | Facebook',
            'Log in to Facebook | Facebook',
        ],
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
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.session.headers.update({
            'Host': 'www.facebook.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        })

    def authenticate(self, client_class=None):
        """Authenticate."""
        if client_class is None:
            client_class = FacebookAPIClient

        if not self.login():
            raise FacebookAPIError('Login failed')
        LOG.debug('Login success')
        access_token = self.get_token()
        if not access_token:
            raise FacebookAPIError('Unable to acquire access token')

        graph = facepy.GraphAPI(access_token, version='2.10')
        client = client_class(graph)
        accounts = client.accounts()
        if not accounts:
            raise FacebookAPIError('Unable to access user accounts.')

        page_access_token = None
        user_id = None
        for account in accounts['data']:
            if account['name'] == self.page_name:
                user_id = account['id']
                page_access_token = account['access_token']

        if not user_id:
            raise FacebookAPIError('Unable to get page user-id.')

        if not page_access_token:
            raise FacebookAPIError('Unable to get page access_token.')

        # Reset the graph to use the page token.
        graph = facepy.GraphAPI(page_access_token, version='2.10')
        return client_class(graph, user_id)

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
        cookies = dict(wd='1920x1200')
        response = self.session.get(url, cookies=cookies)
        soup = BeautifulSoup(response.text)
        title = soup.html.head.title.string
        LOG.debug('Login title: "%s"', title)
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
            if 'type' not in form_input:
                continue
            if form_input['type'] != 'hidden':
                continue
            if 'value' in form_input:
                post_data[form_input['name']] = form_input['value']
            elif 'checked' in form_input:
                post_data[form_input['name']] = form_input['checked']
        post_data['email'] = self.email
        post_data['pass'] = self.password

        # These are set by facebook's js, so hard code
        viewport_dim = '{"w":1920,"h":1200,"aw":1920,"ah":1200,"c":24}'
        post_data['lgndim'] = base64.b64encode(viewport_dim)
        post_data['lgnjs'] = datetime.datetime.now().strftime("%s")
        post_data['timezone'] = '240'

        # Submit the login form
        self.session.headers.update({
            'Host': 'www.facebook.com',
            'Referer': url,
        })
        url = 'https://www.facebook.com/login.php?login_attempt=1&lwv=100'
        # Post two times. The first post sets cookie info.
        response = self.session.post(url, data=post_data)
        response = self.session.post(url, data=post_data)
        soup = BeautifulSoup(response.text)
        title = soup.html.head.title.string
        LOG.debug('Logged in title: "%s"', title)
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

    def delete_post(self, post_id):
        """Delete a post

        Args:
            post_id, id of post.
            See
            https://developers.facebook.com/docs/graph-api/reference/v2.4/post
            Deleting
        """
        return self.graph.delete(post_id)

    def page_feed_post(self, post_data):
        """Post to a page feed.

        Args:
            post_data, dict
            See:
            https://developers.facebook.com/docs/graph-api/reference/v2.4/page/feed
            Publishing
        """
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
            raise FacebookAPIError('Facebook post failed.')
        return result


class Authenticator(object):
    """Class representing a facebook authenticator"""

    def __init__(self, credentials):
        """Constructor

        Args:
            credentials: dict
        """
        self.credentials = credentials

    def authenticate(self):
        """Authenticate on facebook.

        Returns:
            authenticator, FacebookAPIAuthenticator instance
        """
        auth = FacebookAPIAuthenticator(
            self.credentials['email'],
            self.credentials['password'],
            self.credentials['client_id'],
            self.credentials['redirect_uri'],
            self.credentials['page_name'],
        )
        return auth.authenticate()


class PhotoDataPreparer(object):
    """Class representing a preparer of data for facebook photo posting."""

    def __init__(self, facebook_data):
        """Constructor

        Args:
            facebook_data: dict like
                {
                    'book': {...},      # book attributes
                    'creator': {...},   # creator attributes
                }
        """
        self.facebook_data = facebook_data

    def caption(self):
        """Return a caption."""
        # Eg 'by First Last'
        return 'by {c}'.format(c=self.facebook_data['creator']['name'])

    def data(self):
        """Return data for a facebook photo posting."""
        return {
            'caption': self.caption(),
            'description': self.facebook_data['book']['description'],
            'link': self.facebook_data['book']['url'],
            'name': self.facebook_data['book']['formatted_name'],
            'picture': self.facebook_data['book']['download_url'],
        }


class Poster(object):
    """Class representing a facebook poster"""

    def __init__(self, client):
        """Constructor

        Args:
            client,  FacebookAPIClient instance
        """
        self.client = client

    def delete_post(self, post_id):
        """Delete a post.

        Args:
            post_id, string, id of facebook post to delete
        """
        return self.client.delete_post(post_id)

    def post_photo(self, photo_data):
        """Post a photo.

        Args:
            photo_data: dict of data required for facebook photo post.
        """
        return self.client.page_feed_post(photo_data)

    def post_text(self, text_data):
        """Post text.

        Args:
            text_data: dict of data required for facebook text post.
        """
        return self.client.page_feed_post(text_data)


class TextDataPreparer(object):
    """Class representing a preparer of data for facebook text posting."""

    def __init__(self, facebook_data):
        """Constructor

        Args:
            facebook_data: dict like
                {
                    'tumblr_post_id': ...
                }

        Notes:
            Facebook uses the tumblr post for text posts. Facebook knows to
            format a posting with a tumblr link using data from that tumblr
            post.
        """
        self.facebook_data = facebook_data

    def data(self):
        """Return data for a facebook text posting."""
        return {
            'link': self.link(),
            'picture': 'https://zco.mx/zcomx/static/images/white_280x280.png'
        }

    def link(self):
        """Return the link."""
        return 'http://zcomx.tumblr.com/post/{i}'.format(
            i=self.facebook_data['tumblr_post_id'])
