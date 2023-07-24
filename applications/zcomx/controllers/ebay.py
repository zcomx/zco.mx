# -*- coding: utf-8 -*-
"""Ebay controller functions"""
import datetime
import socket
import urllib.parse
import requests
from ebaysdk.exception import ConnectionError as EbayConnectionError
from ebaysdk.finding import Connection


def accepted_callback():
    """Call back on ebay user request."""
    redirect('get_product_details')


def index():
    """Default controller."""
    redirect('get_product_details')


def get_product_details():
    """Get product details by UPC code. """
    fields = [
        Field(
            'upc',
            type='string',
            label='UPC',
        ),
    ]

    form = SQLFORM.factory(
        *fields,
        formstyle='table3cols',
        submit_button='Submit'
    )

    results = []

    app_id = current.app.local_settings.ebay_app_id

    domains = {
        'sandbox': 'svcs.sandbox.ebay.com',
        'prod': 'svcs.ebay.com',
    }

    if form.process(keepvalues=True, message_onsuccess='').accepted:
        session = requests.Session()
        # get ebay user consent
        env = 'sandbox' if socket.gethostname() == 'jimk' else 'prod'
        LOG.error('FIXME env: %s', env)

        request = {
            'keywords': form.vars.upc,
        }

        raw_results = {}
        # pylint: disable=broad-except
        try:
            api = Connection(
                domain=domains[env],
                appid=app_id,
                config_file=None,
                siteid="EBAY-US",
                https=True,
                debug=False
            )

            got = api.execute('findItemsAdvanced', request)
        except EbayConnectionError as err:
            LOG.error('Ebay API fail: %s', err)
            LOG.error('Ebay API fail: %s', err.got.dict())
        except Exception:
            LOG.error('Ebay API fail: Unexpected exception.')
        else:
            raw_results = got.dict()

        result_count = 0
        try:
            result_count = raw_results['searchResult']['_count']
        except KeyError:
            pass

        if result_count == 0:
            response.flash = 'No searchResult count found.'
        else:
            try:
                items = raw_results['searchResult']['item']
            except KeyError:
                response.flash = 'No Items found.'
                items = []

            for item in items:
                title = item['title']
                if title:
                    results.append(title)
    elif form.errors:
        response.flash = 'Form could not be submitted.' + \
            ' Please make corrections.'

    return dict(
        form=form,
        results=results,
    )
