#!/usr/bin/env python

"""
tests/runner.py

Classes for local python test_suite scripts.
"""
import inspect
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.parse
from io import StringIO
from bs4 import BeautifulSoup

from gluon.contrib.webclient import (
    WebClient,
    DEFAULT_HEADERS as webclient_default_headers,
)
from gluon.globals import current
from gluon.http import HTTP
import gluon.shell
from gluon.storage import (
    List,
    Storage,
)

FILTER_TABLES = []          # Cache for values in comment.filter_table fields
# Cache for app environments. Reuse of db prevents
# 'too many connections' errors.
APP_ENV = {}


class LocalTestCase(unittest.TestCase):
    """unittest.TestCase subclass with customizations.

    Customization:
        * The _opts class property provides options to all tests.
        * Each test is timed.

    """
    # R0904: *Too many public methods (%%s/%%s)*
    # pylint: disable=R0904
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    _opts = Storage({
        'force': False,
        'quick': False,
    })

    _objects = []           # Deprecated: Use _objs.case

    _objs = Storage({
        'case': [],         # Test objects at case level (eg in setUp)
        'runner': [],       # Test objects at runner level (eg in setUpClass)
    })

    _trackers = None
    _runner_trackers = []


    def __init__(self, methodName='runTest'):
        """Constructor."""
        unittest.TestCase.__init__(self, methodName=methodName)
        self._start_time = None

    @classmethod
    def _add_case_obj(cls, obj):
        """Add an object to the case objects list.

        Args:
            obj: DbObject
        """
        if obj not in cls._objs.case:
            cls._objs.case.append(obj)

    @classmethod
    def _add_runner_obj(cls, obj):
        """Add an object to the runner objects list.

        Args:
            obj: DbObject
        """
        if obj not in cls._objs.runner:
            cls._objs.runner.append(obj)

    def _cleanup(self):
        """Cleanup executed after every test fixture."""
        for obj in self._objects:
            if hasattr(obj, 'remove'):
                self._remove_comments_for(obj)
                obj.remove()
            elif hasattr(obj, 'delete') and hasattr(obj, 'id'):
                obj.delete()
            elif hasattr(obj, 'delete_record'):
                db = current.app.db
                obj.delete_record()
                db.commit()
        LocalTestCase._objects = []

    def _remove_comments_for(self, obj):
        """Remove all comments associated with an object.

        Args:
            obj: DbObject instance
        """
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # W0603: *Using the global statement*
        # pylint: disable=W0603
        # R0201: *Method could be a function*
        # pylint: disable=R0201

        # Remove comments.
        global FILTER_TABLES
        db = current.app.db
        if 'comment' in db.tables:
            if not FILTER_TABLES:
                FILTER_TABLES = [
                    x.filter_table for x in db(db.comment.id > 0).select(
                        db.comment.filter_table, distinct=True
                    )
                ]
            if obj.tbl._tablename in FILTER_TABLES:
                query = (db.comment.filter_table == obj.tbl._tablename) & \
                        (db.comment.filter_id == obj.id)
                db(query).delete()
                db.commit()

    @classmethod
    def add(cls, obj, data):
        """Helper function to add a test record and store it for removal.

        Args:
            obj: A Record subclass instance or a gluon.dal.Table
                instance.

            data: dict of data, {field: value, ...}

        """
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        db = current.app.db
        if hasattr(obj, 'insert'):
            record_id = obj.insert(**data)
            db.commit()
            record = db(obj.id == record_id).select(limitby=(0, 1)).first()
        elif hasattr(obj, 'from_add'):
            record = obj.from_add(data, validate=False)
        cls._objects.append(record)
        return record

    def _assertRaisesHTTPError(
            self,
            exception,
            expected_code,
            callable_obj,
            *args,
            **kwargs):
        """Helper function for asserts for HTTP errors.

        Args:
            exception: Exception instance
            expected_code: integer, eg 404
            callable_obj: Function to be called. (see assertRaises)
            args: Extra args. (see assertRaises)
            kwargs: Extra kwargs. (see assertRaises)
        """
        safe_repr = unittest.util.safe_repr
        try:
            callable_obj(*args, **kwargs)
        except exception as err:
            code = 'n/a'
            if hasattr(err, 'code'):
                code = err.code
            elif hasattr(err, 'status'):
                code = err.status
            if code != expected_code:
                msg = "HTTPError code %s is not %s" % (
                    safe_repr(code), safe_repr(expected_code))
                raise self.failureException(msg)
        else:
            msg = "HTTPError not raised"
            raise self.failureException(msg)

    def assertRaisesHTTP(self, expected_code, callable_obj, *args, **kwargs):
        """Fail unless an HTTP (gluon.http.py) is raised with the expected
        code.

        Args:
            See _assertRaisesHTTPError
        """
        self._assertRaisesHTTPError(
            HTTP, expected_code, callable_obj, *args, **kwargs)

    def assertRaisesHTTPError(
            self,
            expected_code,
            callable_obj,
            *args,
            **kwargs):
        """Fail unless an HTTPError is raised with the expected code.

        Args:
            See _assertRaisesHTTPError
        """
        self._assertRaisesHTTPError(
            urllib.error.HTTPError, expected_code, callable_obj, *args, **kwargs)

    def assertWebTest(
            self,
            url_path,
            app=None,
            match_page_key=None,
            match_strings=None,
            match_type='all',
            tolerate_whitespace=False,
            post_data=None,
            login_required=True,
            charset='utf-8'):
        """Fail if the content of the page returned by url does not match page
        key and optional strings.

        Args:
            url_path: string, the path of the url.
            app: string, application name, if None, get_app() is called.
            match_page_key: string, key to WebTestCase.page_identifiers
                if None, url_path is used.
                if '', no page_identifier is matched.
            match_strings: list of strings
            match_type: see LocalWebClient.match_type
            tolerate_whitespace: see LocalWebClient.tolerate_whitespace
            post_data: see LocalWebClient.post_data
            login_required: see LocalWebClient.login_required
        """
        if match_page_key is None:
            match_page_key = url_path
        if app is None:
            app = self.get_app()
        url = '/' + '/'.join([app, url_path])
        matches = []
        if match_page_key:
            page_identifiers = self.page_identifiers[match_page_key]
            if not isinstance(page_identifiers, list):
                page_identifiers = [page_identifiers]
            matches.extend(page_identifiers)
        if match_strings:
            matches.extend(match_strings)
        current.app.web.sessions = {}   # Avoid: 'Changed session ID' warnings
        current.app.web.login_required = login_required
        if not current.app.web.test(
                url,
                matches,
                match_type=match_type,
                tolerate_whitespace=tolerate_whitespace,
                post_data=post_data,
                charset=charset):
            first = current.app.web.errors
            second = []

            err_msg = ''
            try:
                self.assertEqual(first, second)
            except self.failureException as err:
                err_msg = str(err)

            # assertion_func = self._getAssertEqualityFunc(first, second)
            # assertion_func(first, second, msg='Page identifiers not found')
            msg = 'Unmatched page identifier list not empty. ' + err_msg
            raise self.failureException(msg)

    @classmethod
    def get_app(cls):
        """Get the web2py app.

        Returns:
            str: web2py application
        """
        filename = inspect.getouterframes(inspect.currentframe())[1][1]
        subdirs = filename.split(os.sep)
        # The app is the subdirectory just after 'applications'
        dirs = [i for i, x in enumerate(subdirs) if x == 'applications']
        try:
            app = subdirs[dirs[0] + 1]
        except IndexError:
            app = 'zcomx'
        return app

    def run(self, result=None):
        """Run test fixture."""
        self.addCleanup(self._cleanup)
        self._start_time = time.time()
        unittest.TestCase.run(self, result)

    @classmethod
    def set_env(cls, env):
        """Set the environment.

        Args:
            env: environment (eg globals())

        Returns:
            current: threading.local()
        """
        app = cls.get_app()
        if app not in APP_ENV:
            APP_ENV[app] = gluon.shell.env(app, import_models=True)
        if 'current' not in APP_ENV[app]:
            current.request = APP_ENV[app]['request']
            current.response = APP_ENV[app]['response']
            current.session = APP_ENV[app]['session']
            current.app = Storage()
            current.app.auth = APP_ENV[app]['auth']
            current.app.crud = APP_ENV[app]['crud']
            current.app.db = APP_ENV[app]['db']
            if 'local_settings' in APP_ENV[app]:
                current.app.local_settings = APP_ENV[app]['local_settings']
            APP_ENV[app]['current'] = current
        env['current'] = APP_ENV[app]['current']
        env['request'] = APP_ENV[app]['current'].request
        env['request'].args = List()
        env['request'].vars = Storage()
        env['response'] = APP_ENV[app]['current'].response
        env['session'] = APP_ENV[app]['current'].session
        env['auth'] = APP_ENV[app]['current'].app.auth
        env['crud'] = APP_ENV[app]['current'].app.crud
        env['db'] = APP_ENV[app]['current'].app.db
        login_user = None
        login_password = None
        login_employee_id = 0
        if 'local_settings' in APP_ENV[app]['current'].app:
            env['local_settings'] = APP_ENV[app]['current'].app.local_settings
            login_user = env['local_settings'].login_user
            login_password = env['local_settings'].login_password
            login_employee_id = env['local_settings'].login_employee_id

        login_required = True if 'auth_user' in env['db'].tables else False
        web_client_url = current.app.local_settings.web_site_url \
            if current.app.local_settings.web_site_url else ''
        web = LocalWebClient(
            app,
            login_user,
            login_password,
            db=env['db'],
            login_employee_id=login_employee_id,
            url=web_client_url,
            dump=LocalTestCase._opts.dump,
            login_required=login_required,
        )
        current.app.web = web
        env['web'] = APP_ENV[app]['current'].app.web
        return APP_ENV[app]['current']

    @classmethod
    def set_post_env(cls, env, post_vars=None):
        """Set the env for a post test.

        Args:
            env: dict of envirnoment, eg env = globals()
            post_vars: dict of data to post. If None the request environment
                is reset.
        """
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        env['request']._body = None             # Force reload
        env['request']._vars = None             # Force reload
        env['request']._post_vars = None        # Force reload
        env['request']._get_vars = None         # Force reload
        env['request'].vars = Storage()
        if post_vars is not None:
            wsgi_input = urllib.parse.urlencode(post_vars)
            env['request'].env['CONTENT_LENGTH'] = str(len(wsgi_input))
            env['request'].env['wsgi.input'] = StringIO(wsgi_input)
            env['request'].env['REQUEST_METHOD'] = 'POST'  # for cgi.py
            env['request'].env['request_method'] = 'POST'  # parse_post_vars


class LocalTextTestResult(unittest._TextTestResult):
    """A test result class that can print formatted text results to streams.
    Differs from unittest._TextTestResult
    * use distinct streams for errors and general output
    * Replace the "dots" mode with a showErr mode, prints only errors

    Used by TextTestRunner.
    """

    # Many varibles are copied as is from unittest code.
    # pylint: disable=C0103
    # pylint: disable=W0212
    # pylint: disable=W0231
    # pylint: disable=W0233

    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, stream_err, descriptions, verbosity):
        """Constructor."""
        unittest.TestResult.__init__(self)
        self.stream = stream
        self.stream_err = stream_err
        self.showAll = verbosity > 1
        self.showErr = verbosity == 1
        self.descriptions = descriptions

    def startTest(self, test):
        """Adapted from unittest._TextTestResult. Method called just prior to
        test run
        """
        self.testsRun = self.testsRun + 1

    def addSuccess(self, test):
        """Adapted from unittest._TextTestResult"""
        unittest.TestResult.addSuccess(self, test)
        self.printTestResult(test, 'ok')

    def addError(self, test, err):
        """Adapted from unittest._TextTestResult"""
        unittest.TestResult.addError(self, test, err)
        self.printTestResult(test, 'ERROR')

    def addFailure(self, test, err):
        """Adapted from unittest._TextTestResult"""
        unittest.TestResult.addFailure(self, test, err)
        self.printTestResult(test, 'FAIL')

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason)
        self.printTestResult(test, 'Skip')

    def printErrors(self):
        """Adapted from unittest._TextTestResult"""
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        """Adapted from unittest._TextTestResult"""
        for test, err in errors:
            # self.stream_err.writeln(self.separator1)
            # self.stream_err.writeln("%s: %s" % (flavour,
            #     self.getDescription(test)))
            # self.stream_err.writeln(self.separator2)
            # Print a command that will demonstrate the error.
            if hasattr(test, '_testMethodName'):
                self.stream_err.writeln(
                       '$ unit {fname} {case} {method}'.format(
                            fname=test.__module__.replace('.', '/') + '.py',
                            case=test.__class__.__name__,
                            method=test._testMethodName,
                            ))
            elif hasattr(test, 'description'):
                parts = test.description.split()
                if str(parts[1]).startswith('(') and str(parts[1]).endswith(')'):
                    fname = str(parts[1])[1:-1].replace('.', '/') + '.py'
                    self.stream_err.writeln(
                        '$ unit {fname}'.format(fname=fname)
                    )
                else:
                    self.stream_err.writeln('ERROR: ' + str(test))
            else:
                self.stream_err.writeln('ERROR: ' + str(test))
            self.stream_err.writeln("%s" % err)

    def printTestResult(self, test, msg):
        """Print a test result.

        Args:
            test: unittest.TestCase
            msg: string, message to append to output. Eg 'ok' if success.
        """
        stream = None
        if self.showErr:
            stream = self.stream_err
        elif self.showAll:
            stream = self.stream
        if not stream:
            return
        time_taken = 0
        if hasattr(test, '_start_time') and test._start_time:
            time_taken = time.time() - test._start_time
        # The format {t:3d} produces '0.1' and I want ' .1'
        # So create the string with no decimal, then insert the decimal.
        t = '{t:3d}'.format(t=int(time_taken * 10))
        stream.write(t[:-1] + '.' + t[-1:])
        stream.write(' ')
        stream.write(self.getDescription(test))
        stream.write(" ... ")
        stream.writeln(msg)
        stream.flush()


class LocalTextTestRunner(unittest.TextTestRunner):
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    # Many varibles are copied as is from unittest code.
    # pylint: disable=C0103
    # pylint: disable=C0321
    # pylint: disable=R0903
    # pylint: disable=W0141
    # pylint: disable=W0212
    # pylint: disable=W0231

    def __init__(
            self, stream=sys.stdout, stream_err=sys.stderr, descriptions=1,
            verbosity=1
    ):
        """Constructor."""
        self.stream = unittest.runner._WritelnDecorator(stream)
        self.stream_err = unittest.runner._WritelnDecorator(stream_err)
        self.descriptions = descriptions
        self.verbosity = verbosity

    def _makeResult(self):
        """Format test results"""
        return LocalTextTestResult(
            self.stream,
            self.stream_err,
            self.descriptions,
            self.verbosity
        )

    def run(self, test):
        """Run the given test case or test suite."""
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        run = result.testsRun
        if self.verbosity > 1:
            self.stream.writeln(result.separator2)
            self.stream.writeln("Ran %d test%s in %.3fs" %
                                (run, run != 1 and "s" or "", timeTaken))
            if result.wasSuccessful():
                self.stream.writeln()

        if not result.wasSuccessful():
            self.stream.writeln()
            result.printErrors()
            self.stream_err.write("FAILED (")
            failed, errored = list(map(len, (result.failures, result.errors)))
            if failed:
                self.stream_err.write("failures=%d" % failed)
            if errored:
                if failed:
                    self.stream_err.write(", ")
                self.stream_err.write("errors=%d" % errored)
            self.stream_err.writeln(")")
        else:
            if self.verbosity > 1:
                self.stream.writeln("OK")
        return result


class LocalWebClient(WebClient):
    """Class representing a LocalWebClient"""

    def __init__(
            self,
            application,
            username,
            password,
            login_employee_id=0,
            url='',
            postbacks=True,
            login_required=True,
            db=None,
            dump=False,
    ):
        """Constructor

        Args:
            application: string, name of web2py application
            username: string, application login username
            password: string, application login password
            employee_id: integer, id of employee record. If non-zero, the
                session employee is set using this employee.
            url: string, application url root
            postbacks: see WebClient
            login_required: If true, login to application before accessing
                    pages.
            db: gluon.dal.DAL instance
            dump: If true, dump page contents
        """
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103

        self.application = application
        self.username = username
        self.password = password
        self.login_employee_id = login_employee_id
        self.url = url
        self.postbacks = postbacks
        self.login_required = login_required
        self.db = db
        self.dump = dump
        self.errors = []
        headers = dict(webclient_default_headers)
        headers['user-agent'] = ' '.join((
            'Mozilla/5.0',
            '(X11; U; Linux i686; en-US; rv:1.9.2.10)',
            'Gecko/20100928', 'Firefox/3.5.7'
        ))
        WebClient.__init__(
            self,
            self.url,
            postbacks=self.postbacks,
            default_headers=headers
        )
        self._soup = None       # page as soup
        self._flash = None      # flash message

    def __repr__(self):
        fmt = ', '.join([
            'LocalWebClient(application={application!r}',
            'username={username!r}',
            'password={password!r}',
            'login_employee_id={login_employee_id!r}',
            'url={url!r}',
            'postbacks={postbacks!r}',
        ])
        return fmt.format(
            application=self.application,
            username=self.username,
            password=self.password,
            login_employee_id=self.login_employee_id,
            url=self.url,
            postbacks=self.postbacks
        )

    def as_soup(self):
        """Return the response text as a Beautiful soup instance"""
        if not self._soup:
            self._soup = BeautifulSoup(self.text, 'html.parser')
        return self._soup

    @property
    def flash(self):
        """Return the flash message in the response text."""
        flash_class = 'w2p_flash'
        soup = self.as_soup()
        divs = soup.findAll('div')
        flash_div = None
        for div in divs:
            if flash_class in div['class']:
                flash_div = div
                break
        if not flash_div:
            return
        return flash_div.string

    def get(self, url, cookies=None, headers=None, auth=None, charset='utf-8'):
        """Override base class method.

        Args:
            See WebClient.get()

        Differences from base class method.
        * Clears _soup property.
        * Issues a db.commit().
            Why this is needed is a bit foggy but, the module running tests and
            the script run by webclient urllib2 calls have two distinct
            database handles. Changes on one may not be available on the other
            until a commit() is called.
        """
        # return self.post(url, data=None, cookies=cookies, headers=headers, method='GET')
        self._soup = None
        result = self.post(
            url,
            data=None,
            cookies=None,
            headers=None,
            auth=None,
            method='GET',
            charset=charset,
        )
        if self.db:
            self.db.commit()
        return result

    def login(self, url='', employee_url=''):
        """Login to web2py application

        Args:
            url: string, login url defaults to
                    '<self.application>/default/user/login'
            employee_url: string, select employee url, defaults to
                    '<self.application>/employees/employee_select'

        Returns:
            True if ..., False otherwise
        """
        if not url:
            url = '/{app}/default/user/login'.format(app=self.application)

        if self.login_employee_id and not employee_url:
            employee_url = '/{app}/employees/employee_select'.format(
                app=self.application)

        # Step 1: Get the login page. This creates a session record in
        #         web2py_session_<app> table. (The employee_select page
        #         doesn't do this properly.)
        self.get(url)

        # Step 2: Set the session employee.
        if self.login_employee_id:
            data = dict(employee_id=self.login_employee_id)
            self.post(employee_url, data=data)

        # Step 3: Login. This permits access to admin-only pages.
        data = dict(
            email=self.username,
            password=self.password,
            _formname='login',
        )
        self.post(url, data=data)

    def logout(self):
        """Logout."""
        url = '/{app}/default/user/logout'.format(app=self.application)
        self.get(url)

    def post(
            self,
            url,
            data=None,
            cookies=None,
            headers=None,
            auth=None,
            method=None,
            charset='utf-8'):
        """Override base class method.

        Args:
            See WebClient.post()

        Differences from base class method.
        * Clears _soup property.
        """
        if method is None:
            method == 'auto'
        self._soup = None
        result = WebClient.post(
            self,
            url,
            data=data,
            cookies=None,
            headers=None,
            auth=None,
            method=method,
            charset=charset,
        )
        if self.db:
            self.db.commit()
        return result

    def server_ip(self):
        """Return the server ip address."""
        self.get('/')
        url = self.response.geturl()
        return socket.gethostbyname(urllib.parse.urlparse(url).hostname)

    def test(
            self,
            url,
            expect,
            match_type='all',
            tolerate_whitespace=False,
            post_data=None,
            charset='utf-8'):
        """Test accessing a page.

        Args:
            url: string, page url.
            expect: string or list of strings,
                if string: unique string expected to be found in page.
                if list: list of strings all expected to be found in page.
            match_type: 'all' or 'any', only applies if expect is a list.
                If all, all strings in expect list must be found.
                If any, a single string in expect list must be found.
            tolerate_whitespace: If True, when match on expected string,
                tolerate differences in whitespace.
                * All whitespace characters are replaced with space.
                * Multiple whitespace characters are replaced with single
                  space.
            post_data: dict, if None
                    * get() request is made instead of post().
                    * login is run if required, else sessions are cleared
        Return:
            True if expect found in page contents.
        """
        if post_data is None:
            if self.login_required:
                login_required = False
                if self.sessions:
                    if self.application in self.sessions:
                        session_id = None
                        if ':' in self.sessions[self.application]:
                            session_id, unused_unique_key = \
                                self.sessions[self.application].split(':', 2)
                        if session_id == 'None':
                            login_required = True
                else:
                    login_required = True
                if login_required:
                    self.login()
            else:
                # Without login, sessions take a value like this
                # {application: '"None:2284b815-f31d-408b-a6b2-82b1b1c17fd8"'}
                # The index 'None' remains constant, but the hash changes for
                # each page. WebClient thinks the session is broken and raises
                # an exception: RuntimeError: Broken sessions. Delete the
                # session to prevent this.
                self.sessions = {}
                if self.sessions and self.application in self.sessions:
                    if '"None:' in self.sessions[self.application]:
                        del self.sessions[self.application]

        if post_data is None:
            self.get(url, charset=charset)
        else:
            if self.forms and list(self.forms.keys()):
                if '_formname' not in post_data:
                    post_data['_formname'] = list(self.forms.keys())[0]
                if '_formkey' not in post_data:
                    post_data['_formkey'] = self.forms[list(self.forms.keys())[0]]
            self.post(url, post_data, charset=charset)

        match_text = ' '.join(self.text.split()) \
            if tolerate_whitespace else self.text
        if self.dump:
            dump_dir = '/root/tmp/dumps'
            if not os.path.exists(dump_dir):
                os.makedirs(dump_dir)

            # Explanation of next line:
            # * Strip leanding slash
            # * Remove query from url, eg ?id=2&client_id=2
            # * Get the url function and args
            # * Join with underscores.
            # Example:
            # url = /app/controller/function/123?record_id=123
            # filename = function_123
            try:
                filename = '_'.join(
                    url.lstrip('/').split('?')[0].split('/')[2:])
            except (AttributeError, KeyError):
                filename = 'dump'
            with open(os.path.join(dump_dir, filename + '.htm'), 'w') as f:
                f.write(match_text + "\n")

        expects = expect
        if not isinstance(expect, list):
            expects = [expect]

        self.errors = []
        for match_string in expects:
            if match_string not in match_text:
                self.errors.append(match_string)
                if match_type != 'all':
                    break
        return not self.errors


# Decorator
def count_diff(func):
    """Decorator used to display the effect of a function on sql record
    counts.

    """
    def wrapper(*arg):
        """Decorator wrapper function

        Args:
            arg: args passed to decorated function.
        """
        count_script = '/root/bin/sql_record_count.sh'
        args = [count_script, '-a', 'before']
        subprocess.call(args)

        try:
            func(*arg)
        except (SystemExit, KeyboardInterrupt):
            # This prevents a unittest.py exit from killing the wrapper
            pass

        args = [count_script, '-a', 'after']
        subprocess.call(args)
        args = [count_script, '-a', 'diff']
        subprocess.call(args)
    return wrapper
