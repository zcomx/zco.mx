# -*- coding: utf-8 -*-

# default_application, default_controller, default_function
# are used when the respective element is missing from the
# (possibly rewritten) incoming URL
#
default_application = 'zcomx'    # ordinarily set in base routes.py
default_controller = 'default'  # ordinarily set in app-specific routes.py
default_function = 'index'      # ordinarily set in app-specific routes.py

# routes_app is a tuple of tuples.  The first item in each is a regexp that will
# be used to match the incoming request URL. The second item in the tuple is
# an applicationname.  This mechanism allows you to specify the use of an
# app-specific routes.py. This entry is meaningful only in the base routes.py.
#
# Example: support welcome, admin, app and myapp, with myapp the default:


routes_app = ()
# routes_app = ((r'/zcomx/(.*)', r'zcomx'),
#               (r'(.*)', r'zcomx'),
#               (r'/?(.*)', r'zcomx'))

# routes_in is a tuple of tuples.  The first item in each is a regexp that will
# be used to match the incoming request URL. The second item in the tuple is
# what it will be replaced with.  This mechanism allows you to redirect incoming
# routes to different web2py locations
#
# Example: If you wish for your entire website to use init's static directory:
#
#   routes_in=( (r'/static/(?P<file>[\w./-]+)', r'/init/static/\g<file>') )
#

BASE = ''  # optonal prefix for incoming URLs

CONTROLLERS = '|'.join([
    'admin',
    'books',
    'cbz',
    'contributions',
    'creators',
    'default',
    'downloads',
    'ebay',
    'errors',
    'images',
    'login',
    'rss',
    'search',
    'torrents',
    'z',
])

# Creator: Allow everything but slash and keywords 'zcomx' or 'embed'
creator_re = r'(?!zcomx|embed)(?P<creator>[^/]+)'
book_re = r'(?P<book>[^/]+)'            # Allow everything but slash
page_re = r'(?P<page>[\w]+)'            # No period to exclude extensions
image_re = r'(?P<page>[\w]+\.[\w]+)'      # Allow period for extension

routes_in = (
    # do not reroute static files
    ('/$app/static/$anything', '/$app/static/$anything'),
    ('/(zcomx)?', '/zcomx/search/index'),
    ('/(zcomx/)?login', '/zcomx/default/user/login'),
    ('/(zcomx/)?(?P<controller>{ctrs})'.format(ctrs=CONTROLLERS), r'/zcomx/\g<controller>/index'),
    ('/(zcomx/)?(?P<controller>{ctrs})/$anything'.format(ctrs=CONTROLLERS), r'/zcomx/\g<controller>/$anything'),

    #  reroute favicon and robots
    ('/favicon.ico', '/zcomx/static/images/favicon.ico'),
    ('/apple-touch-icon.png', '/zcomx/static/images/favicon.ico'),
    ('/apple-touch-icon-precomposed.png', '/zcomx/static/images/favicon.ico'),
    ('/robots.txt', '/zcomx/static/robots.txt'),
    ('/sitemap.xml', '/zcomx/static/sitemap.xml'),
    ('/google23f195580c35fe70.html', '/zcomx/static/google23f195580c35fe70.html'),
    ('/BingSiteAuth.xml', '/zcomx/static/BingSiteAuth.xml'),

    # reroute cbz files, look for .cbz extension
    (r'/(zcomx/)?{c}/(?P<cbz>.*\.cbz)'.format(c=creator_re), r'/zcomx/cbz/route?creator=\g<creator>&cbz=\g<cbz>'),
    (r'/(zcomx/)?(?P<cbz>.*\.cbz)', r'/zcomx/cbz/route?cbz=\g<cbz>'),

    # reroute rss feeds, look for .rss extension
    (r'/(zcomx/)?{c}/(?P<rss>.*\.rss)'.format(c=creator_re), r'/zcomx/rss/route?creator=\g<creator>&rss=\g<rss>'),
    (r'/(zcomx/)?(?P<rss>.*\.rss)', r'/zcomx/rss/route?rss=\g<rss>'),

    # reroute torrents, look for .torrent extension
    (r'/(zcomx/)?{c}/(?P<tor>.*\.torrent)'.format(c=creator_re), r'/zcomx/torrents/route?creator=\g<creator>&torrent=\g<tor>'),
    (r'/(zcomx/)?(?P<tor>.*\.torrent)', r'/zcomx/torrents/route?torrent=\g<tor>'),

    # Handle embeded books
    ('/(zcomx/)?embed/{c}/{b}/{p}/?'.format(c=creator_re, b=book_re, p=page_re),
        r'/zcomx/creators/index?creator=\g<creator>&book=\g<book>&page=\g<page>&embed=1'),
    ('/(zcomx/)?embed/{c}/{b}/?'.format(c=creator_re, b=book_re),
        r'/zcomx/creators/index?creator=\g<creator>&book=\g<book>&page=001&embed=1'),

    # Assume everything else doesn't match a controller and is a creator/book/page
    ('/(zcomx/)?{c}/{b}/{p}/?'.format(c=creator_re, b=book_re, p=image_re),
        r'/zcomx/creators/index?creator=\g<creator>&book=\g<book>&page=\g<page>'),
    ('/(zcomx/)?{c}/{b}/{p}/?'.format(c=creator_re, b=book_re, p=page_re),
        r'/zcomx/creators/index?creator=\g<creator>&book_reader_url=/\g<creator>/\g<book>/\g<page>'),
    ('/(zcomx/)?{c}/monies/?'.format(c=creator_re),
        r'/zcomx/creators/index?creator=\g<creator>&monies=1'),
    ('/(zcomx/)?{c}/{b}/?'.format(c=creator_re, b=book_re),
        r'/zcomx/creators/index?creator=\g<creator>&book=\g<book>'),
    ('/(zcomx/)?{c}/?'.format(c=creator_re),
        r'/zcomx/creators/index?creator=\g<creator>'),
)

# routes_out, like routes_in translates URL paths created with the web2py URL()
# function in the same manner that route_in translates inbound URL paths.
#
# routes_out = [(x, y) for (y, x) in routes_in]

routes_out = (
    # do not reroute static files
    ('/zcomx/static/images/favicon.ico', '/favicon.ico'),
    ('/zcomx/static/robots.txt', '/robots.txt'),
    ('/$app/static/$anything', '/$app/static/$anything'),
    ('/zcomx/search/index', '/'),
    ('/zcomx/default/index', '/'),
    ('/zcomx/default/user/login', '/login'),
    ('/zcomx/creators/index/$anything', '/$anything'),
    ('/creators/index/$anything', '/$anything'),
    (r'/zcomx/(?P<cbz>.*\.cbz)/index', r'/\g<cbz>'),
    (r'/zcomx/$anything/(?P<cbz>.*\.cbz)', r'/$anything/\g<cbz>'),
    (r'/zcomx/(?P<rss>.*\.rss)/index', r'/\g<rss>'),
    (r'/zcomx/$anything/(?P<rss>.*\.rss)', r'/$anything/\g<rss>'),
    (r'/zcomx/(?P<tor>.*\.torrent)/index', r'/\g<tor>'),
    (r'/zcomx/$anything/(?P<tor>.*\.torrent)', r'/$anything/\g<tor>'),
    (r'/zcomx/(?P<controller>{ctrs})/index'.format(ctrs=CONTROLLERS), r'/\g<controller>'),
    (r'/zcomx/(?P<controller>{ctrs})/$anything'.format(ctrs=CONTROLLERS), r'/\g<controller>/$anything'),
)

# Specify log level for rewrite's debug logging
# Possible values: debug, info, warning, error, critical (loglevels),
#                  off, print (print uses print statement rather than logging)
# GAE users may want to use 'off' to suppress routine logging.
#
logging = 'debug'

# Error-handling redirects all HTTP errors (status codes >= 400) to a specified
# path.  If you wish to use error-handling redirects, uncomment the tuple
# below.  You can customize responses by adding a tuple entry with the first
# value in 'appName/HTTPstatusCode' format. ( Only HTTP codes >= 400 are
# routed. ) and the value as a path to redirect the user to.  You may also use
# '*' as a wildcard.
#
# The error handling page is also passed the error code and ticket as
# variables.  Traceback information will be stored in the ticket.
#
# routes_onerror = [
#     (r'init/400', r'/init/default/login')
#    ,(r'init/*', r'/init/static/fail.html')
#    ,(r'*/404', r'/init/static/cantfind.html')
#    ,(r'*/*', r'/init/error/index')
# ]

routes_onerror = [
    (r'*/404', r'/zcomx/errors/page_not_found'),
    (r'*/406', r'/zcomx/errors/index'),
    (r'*/*', r'/zcomx/errors/handler'),
]

# specify action in charge of error handling
#
# error_handler = dict(application='error',
#                      controller='default',
#                      function='index')

# In the event that the error-handling page itself returns an error, web2py will
# fall back to its old static responses.  You can customize them here.
# ErrorMessageTicket takes a string format dictionary containing (only) the
# "ticket" key.

# error_message = '<html><body><h1>%s</h1></body></html>'
# error_message_ticket = '<html><body><h1>Internal error</h1>Ticket issued: <a href="/admin/default/ticket/%(ticket)s" target="_blank">%(ticket)s</a></body></html>'

# specify a list of apps that bypass args-checking and use request.raw_args
#
#routes_apps_raw=['myapp']
#routes_apps_raw=['myapp', 'myotherapp']


def __routes_doctest():
    """
    Dummy function for doctesting routes.py.

    Use filter_url() to test incoming or outgoing routes;
    filter_err() for error redirection.

    filter_url() accepts overrides for method and remote host:
        filter_url(url, method='get', remote='0.0.0.0', out=False)

    filter_err() accepts overrides for application and ticket:
        filter_err(status, application='app', ticket='tkt')

    >>> import os
    >>> import gluon.main
    >>> from gluon.rewrite import regex_select, load, filter_url, regex_filter_out, filter_err, compile_regex
    >>> regex_select()
    >>> load(routes=os.path.basename(__file__))

    >>> os.path.relpath(filter_url('http://domain.com/favicon.ico'))
    'applications/examples/static/favicon.ico'
    >>> os.path.relpath(filter_url('http://domain.com/robots.txt'))
    'applications/examples/static/robots.txt'
    >>> filter_url('http://domain.com')
    '/init/default/index'
    >>> filter_url('http://domain.com/')
    '/init/default/index'
    >>> filter_url('http://domain.com/init/default/fcn')
    '/init/default/fcn'
    >>> filter_url('http://domain.com/init/default/fcn/')
    '/init/default/fcn'
    >>> filter_url('http://domain.com/app/ctr/fcn')
    '/app/ctr/fcn'
    >>> filter_url('http://domain.com/app/ctr/fcn/arg1')
    "/app/ctr/fcn ['arg1']"
    >>> filter_url('http://domain.com/app/ctr/fcn/arg1/')
    "/app/ctr/fcn ['arg1']"
    >>> filter_url('http://domain.com/app/ctr/fcn/arg1//')
    "/app/ctr/fcn ['arg1', '']"
    >>> filter_url('http://domain.com/app/ctr/fcn//arg1')
    "/app/ctr/fcn ['', 'arg1']"
    >>> filter_url('HTTP://DOMAIN.COM/app/ctr/fcn')
    '/app/ctr/fcn'
    >>> filter_url('http://domain.com/app/ctr/fcn?query')
    '/app/ctr/fcn ?query'
    >>> filter_url('http://otherdomain.com/fcn')
    '/app/ctr/fcn'
    >>> regex_filter_out('/app/ctr/fcn')
    '/ctr/fcn'
    >>> filter_url('https://otherdomain.com/app/ctr/fcn', out=True)
    '/ctr/fcn'
    >>> filter_url('https://otherdomain.com/app/ctr/fcn/arg1//', out=True)
    '/ctr/fcn/arg1//'
    >>> filter_url('http://otherdomain.com/app/ctr/fcn', out=True)
    '/fcn'
    >>> filter_url('http://otherdomain.com/app/ctr/fcn?query', out=True)
    '/fcn?query'
    >>> filter_url('http://otherdomain.com/app/ctr/fcn#anchor', out=True)
    '/fcn#anchor'
    >>> filter_err(200)
    200
    >>> filter_err(399)
    399
    >>> filter_err(400)
    400
    >>> filter_url('http://domain.com/welcome', app=True)
    'welcome'
    >>> filter_url('http://domain.com/', app=True)
    'myapp'
    >>> filter_url('http://domain.com', app=True)
    'myapp'
    >>> compile_regex('.*http://otherdomain.com.* (?P<any>.*)', r'/app/ctr\g<any>')[0].pattern
    '^.*http://otherdomain.com.* (?P<any>.*)$'
    >>> compile_regex('.*http://otherdomain.com.* (?P<any>.*)', r'/app/ctr\g<any>')[1]
    '/app/ctr\\\\g<any>'
    >>> compile_regex('/$c/$f', '/init/$c/$f')[0].pattern
    '^.*?:https?://[^:/]+:[a-z]+ /(?P<c>\\\\w+)/(?P<f>\\\\w+)$'
    >>> compile_regex('/$c/$f', '/init/$c/$f')[1]
    '/init/\\\\g<c>/\\\\g<f>'
    """
    pass

if __name__ == '__main__':
    import doctest
    doctest.testmod()
