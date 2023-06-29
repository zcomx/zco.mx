#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
twitter_api.py

Script to test using tweepy twitter api.
https://www.tweepy.org/
https://docs.tweepy.org/en/latest/index.html
"""
import argparse
import os
import pprint
import sys
import traceback
import tweepy
from twitter.oauth import OAuth
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def account_settings(client):
    """Print account settings."""
    pprint.pprint(client.account.settings())


def delete_post(client):
    """Delete a post."""
    # x = client.statuses.destroy(id='586561746363621377')
    # x = client.statuses.destroy(id='588821301546090498')
    # x = client.statuses.destroy(id='589138730570665984')
    x = client.statuses.destroy(id='589139718580871169')
    pprint.pprint(x)


def post_image(client):
    """Post tweet with image."""
    status = "This is a test 010."
    # pylint: disable=line-too-long
    img = '/srv/http/dev.zco.mx/web2py/applications/zcomx/uploads/web/book_page.image/88/book_page.image.883f5a1fce8dced9.30315f31337468666c6f6f725f636f7665722e706e67.png'
    if not os.path.exists(img):
        print('FIXME img not found: {var}'.format(var=img))
        sys.exit(1)

    with open(img, "rb") as imagefile:
        params = {"media[]": imagefile.read(), "status": status}
        x = client.statuses.update_with_media(**params)
        pprint.pprint(x)


def post_tweet(client):
    """Post tweet."""
    # status = "This is a test 001."
    # pylint: disable=line-too-long
    status = 'New pages added by @SGMosdal and Tony Zuvela on zco.mx | http://zcomx.tumblr.com/post/120738947276 | #zcomx'
    x = client.statuses.update(status=status)
    pprint.pprint(x)


def search(client):
    """Print search results."""
    x = client.search.tweets(q="sittler", count=2)
    pprint.pprint(x)


def statuses(client):
    """Print statuses."""
    pprint.pprint(client.statuses.home_timeline())


def user_timeline(client):
    """Print a user timeline."""
    x = client.statuses.user_timeline(screen_name="CharlesForsman", count=1)
    pprint.pprint(x)


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    twitter_api.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='twitter_api.py')

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    LOG.info('Started.')

    settings = current.app.local_settings

    bearer_token = 'AAAAAAAAAAAAAAAAAAAAAI0HogEAAAAAnyIndLxTqPv0GQY333aj0TD3pLI%3Dk6UWQklf9m2nSy2owmNukFcMCIE2rAWvLajYc8a13uqDaOgHmG'
    consumer_key = 'REdtWTJwMC11dldDVUUxS3FWLXM6MTpjaQ'
    consumer_secret = 'R5ELNBTyfeYjBf9EInaZPRfmZ0emvkhGuPEjtSslQDsPPoKIJT'
    access_token = '50643854-j4NqfjeSZknpwGCDLuJQiik0OKbb03IKEOafIkzCJ'
    access_token_secret = 'HbZSCgg6upBCeMa0yjvdE8bEH3ia8BA5e3Ee6CgTWxGdB'

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    api = tweepy.API(auth)
    public_tweets = api.home_timeline()
    for tweet in public_tweets:
        print(tweet.text)
    return


    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    client.create_tweet(text='This is a test tweet. Hello!')
    return
    got = client.get_bookmarks()
    print('FIXME got: {var}'.format(var=got))
    return
    query = '-is:retweet'
    tweets = client.search_recent_tweets(query=query)
    return
    for tweet in tweets.data:
        print('FIXME tweet.text: {var}'.format(var=tweet.text))

    return
    # account_settings(client)
    # delete_post(client)

    # post_image(client)
    # post_tweet(client)

    # search(client)
    statuses(client)
    # user_timeline(client)

    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
