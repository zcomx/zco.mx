#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
post_ongoing_update.py

Script to post an ongoing books update on tumblr.
"""
import datetime
import json
import logging
import random
from gluon import *
from optparse import OptionParser
from twitter import TwitterHTTPError
from applications.zcomx.modules.creators import \
    formatted_name as creator_formatted_name
from applications.zcomx.modules.stickon.dal import RecordGenerator
from applications.zcomx.modules.facebook import \
    Authenticator as FbAuthenticator, \
    FacebookAPIError, \
    Poster as FbPoster, \
    TextDataPreparer as FbTextDataPreparer
from applications.zcomx.modules.tumblr import \
    Authenticator, \
    Poster, \
    TextDataPreparer, \
    postable_activity_log_ids
from applications.zcomx.modules.tweeter import \
    Authenticator as TwAuthenticator, \
    Poster as TwPoster, \
    TextDataPreparer as TwTextDataPreparer, \
    creators_in_ongoing_post
from applications.zcomx.modules.utils import \
    entity_to_row
from applications.zcomx.modules.zco import \
    IN_PROGRESS, \
    SITE_NAME


VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def post_on_facebook(ongoing_post):
    """Post on facebook

    Args:
        ongoing_post: Row instance representing ongoing_post record.

    Returns:
        str, facebook post id
    """
    LOG.debug(
        'Creating facebook posting for date: %s', str(ongoing_post.post_date))

    settings = current.app.local_settings
    credentials = {
        'email': settings.facebook_email,
        'password': settings.facebook_password,
        'client_id': settings.facebook_client_id,
        'redirect_uri': settings.facebook_redirect_uri,
        'page_name': settings.facebook_page_name
    }
    client = FbAuthenticator(credentials).authenticate()
    poster = FbPoster(client)

    facebook_data = {'tumblr_post_id': ongoing_post.tumblr_post_id}
    text_data = FbTextDataPreparer(facebook_data).data()

    error = None
    try:
        result = poster.post_text(text_data)
    except FacebookAPIError as err:
        error = err
        result = {}

    if 'id' not in result:
        LOG.error(
            'Facebook post failed for ongoing_post: %s', ongoing_post.id
        )
        if error:
            LOG.error(err)
        return

    post_id = result['id']
    LOG.debug('post_id: %s', post_id)
    return post_id


def post_on_tumblr(ongoing_post):
    """Post on tumblr

    Args:
        ongoing_post: Row instance representing ongoing_post record.

    Returns:
        str, tumblr posting id
    """
    LOG.debug(
        'Creating tumblr posting for date: %s', str(ongoing_post.post_date))

    settings = current.app.local_settings
    credentials = {
        'consumer_key': settings.tumblr_consumer_key,
        'consumer_secret': settings.tumblr_consumer_secret,
        'oauth_token': settings.tumblr_oauth_token,
        'oauth_secret': settings.tumblr_oauth_secret,
    }
    client = Authenticator(credentials).authenticate()
    poster = Poster(client)
    query = (db.activity_log.ongoing_post_id == ongoing_post.id)
    generator = RecordGenerator(query)
    text_data = TextDataPreparer(ongoing_post.post_date, generator).data()
    if settings.tumblr_post_state:
        text_data['state'] = settings.tumblr_post_state
    result = poster.post_text(settings.tumblr_username, text_data)
    if 'id' not in result:
        LOG.error(
            'Tumblr ongoing post failed for date: %s',
            str(ongoing_post.post_date)
        )
        # Try to get an error message.
        if 'meta' in result:
            if 'status' in result['meta'] and 'msg' in result['meta']:
                LOG.error(
                    'Status: %s, msg: %s',
                    result['meta']['status'],
                    result['meta']['msg']
                )

        if 'response' in result and 'errors' in result['response']:
            for error in result['response']['errors']:
                LOG.error(error)
        return

    post_id = result['id']
    LOG.debug('post_id: %s', post_id)
    return post_id


def post_on_twitter(ongoing_post):
    """Post on twitter

    Args:
        ongoing_post: Row instance representing ongoing_post record.

    Returns:
        str, twitter posting id
    """
    LOG.debug(
        'Creating twitter posting for date: %s', str(ongoing_post.post_date))

    settings = current.app.local_settings
    credentials = {
        'consumer_key': settings.twitter_consumer_key,
        'consumer_secret': settings.twitter_consumer_secret,
        'oauth_token': settings.twitter_oauth_token,
        'oauth_secret': settings.twitter_oauth_secret,
    }
    client = TwAuthenticator(credentials).authenticate()
    poster = TwPoster(client)

    creators = []   # [{'name': 'Joe Smoe', 'twitter': '@joesmoe'},...]
    for creator_id in creators_in_ongoing_post(ongoing_post):
        creator = entity_to_row(db.creator, creator_id)
        if not creator:
            LOG.error('Creator not found, id: %s', creator_id)
            continue
        creators.append({
            'name': creator_formatted_name(creator),
            'twitter': creator.twitter,
        })

    # Shuffle creators so there is no alphabetical bias
    random.shuffle(creators)

    twitter_data = {
        'ongoing_post': {
            'creators': creators,
            'tumblr_post_id': ongoing_post.tumblr_post_id,
        },
        'site': {'name': SITE_NAME},
    }

    text_data = TwTextDataPreparer(twitter_data).data()

    error = None
    try:
        result = poster.post_text(text_data)
    except TwitterHTTPError as err:
        error = err
        result = {}

    if 'id' not in result:
        LOG.error(
            'Twitter post failed for ongoing_post: %s', ongoing_post.id
        )
        if error:
            response_data = json.loads(error.response_data)
            if 'errors' in response_data and response_data['errors']:
                code = response_data['errors'][0]['code']
                msg = response_data['errors'][0]['message']
                LOG.error('Code: %s, msg: %s', code, msg)
        return

    post_id = result['id']
    LOG.debug('post_id: %s', post_id)
    return post_id


def get_ongoing_post(date, create=True):
    """Get the ongoing_post record for the given date.

    Args:
        date: datetime.date instance
        create: If true, create an ongoing_post record if not found.

    Returns:
        Row instance representing the ongoing_post record.
    """
    query = (db.ongoing_post.post_date == date)
    ongoing_post = db(query).select().first()
    if not ongoing_post and create:
        ongoing_post_id = db.ongoing_post.insert(post_date=date)
        query = (db.ongoing_post.id == ongoing_post_id)
        ongoing_post = db(query).select().first()
        if not ongoing_post:
            raise LookupError(
                'Fail: get or create ongoing_post record for date {d}'.format(
                    d=str(date))
            )
    return ongoing_post


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    post_ongoing_update.py [OPTIONS] yyyy-mm-dd

OPTIONS
    -f, --force
        Post regardless if ongoing_post record indicates a post has already
        been made (ie ongoing_post.tumblr_post_id and
        ongoing_post.twitter_post_id are set)

    --facebook
        Post only on facebook.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -p --process-activity-logs
        By default posts are made for existing ongoing_post records only
        (matched on date) and no activity_log records are processed.
        With this option an ongoing_post is created for the date if necessary,
        and all activity_log records not yet associated with an ongoing_post
        are associated with the new ongoing_post.

    --tumblr
        Post only on tumblr.

    --twitter
        Post only on twitter.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] YYYY-MM-DD'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Post regardles if ongoing post_ids exist.',
    )
    parser.add_option(
        '--facebook',
        action='store_true', dest='facebook', default=False,
        help='Post only on facebook.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-p', '--process-activity-logs',
        action='store_true', dest='process_activity_logs', default=False,
        help='Process activity_log records.',
    )
    parser.add_option(
        '--tumblr',
        action='store_true', dest='tumblr', default=False,
        help='Post only on tumblr.',
    )
    parser.add_option(
        '--twitter',
        action='store_true', dest='twitter', default=False,
        help='Post only on twitter.',
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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')
    try:
        date = datetime.datetime.strptime(args[0], '%Y-%m-%d').date()
    except ValueError as err:
        LOG.error('Invalid date: %s, %s', args[0], err)
        exit(1)

    if options.process_activity_logs:
        activity_log_ids = postable_activity_log_ids()
        if not activity_log_ids:
            LOG.info('There are no postable activity_log records')
            LOG.info('Nothing to do. Aborting')
            exit(0)

        ongoing_post = get_ongoing_post(date)
        for activity_log_id in activity_log_ids:
            query = (db.activity_log.id == activity_log_id)
            db(query).update(ongoing_post_id=ongoing_post.id)
    else:
        ongoing_post = get_ongoing_post(date, create=False)

    if not ongoing_post:
        LOG.error('Ongoing post not found, date: %s', str(date))
        exit(1)

    services = []
    if options.facebook:
        services.append('facebook')
    if options.tumblr:
        services.append('tumblr')
    if options.twitter:
        services.append('twitter')
    if not options.facebook and not options.tumblr and not options.twitter:
        services = ['facebook', 'tumblr', 'twitter']

    if 'tumblr' in services:
        if ongoing_post.tumblr_post_id \
                and ongoing_post.tumblr_post_id != IN_PROGRESS \
                and not options.force:
            LOG.warn(
                'Ongoing_post has tumblr_post_id: %s',
                ongoing_post.tumblr_post_id
            )
            LOG.warn('Refusing to post to tumblr without --force')
        else:
            tumblr_post_id = post_on_tumblr(ongoing_post)
            if tumblr_post_id:
                ongoing_post.update_record(tumblr_post_id=tumblr_post_id)
                db.commit()

    if 'twitter' in services:
        if ongoing_post.twitter_post_id \
                and ongoing_post.twitter_post_id != IN_PROGRESS \
                and not options.force:
            LOG.warn(
                'Ongoing_post has twitter_post_id: %s',
                ongoing_post.twitter_post_id
            )
            LOG.warn('Refusing to post to twitter without --force')
        else:
            twitter_post_id = post_on_twitter(ongoing_post)
            if twitter_post_id:
                ongoing_post.update_record(twitter_post_id=twitter_post_id)
                db.commit()

    if 'facebook' in services:
        if not ongoing_post.tumblr_post_id \
                or ongoing_post.tumblr_post_id == IN_PROGRESS:
            LOG.error('Unable to post to facebook without a tumblr_post_id')
        elif ongoing_post.facebook_post_id \
                and ongoing_post.facebook_post_id != IN_PROGRESS \
                and not options.force:
            LOG.warn(
                'Ongoing_post has facebook_post_id: %s',
                ongoing_post.facebook_post_id
            )
            LOG.warn('Refusing to post to facebook without --force')
        else:
            facebook_post_id = post_on_facebook(ongoing_post)
            if facebook_post_id:
                ongoing_post.update_record(facebook_post_id=facebook_post_id)
                db.commit()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
