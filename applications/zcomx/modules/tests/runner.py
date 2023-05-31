#!/usr/bin/env python
"""
tests/runner.py

Classes for local python test_suite scripts.
"""
import inspect
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.parse
from io import StringIO
from bs4 import BeautifulSoup
from gluon import *
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
from applications.zcomx.modules.job_queue import (
    Job,
    JobHistory,
)
from applications.zcomx.modules.tests.trackers import TableTracker


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
        super().__init__(methodName=methodName)
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
        """Cleanup executed after every test fixture.

        Note: this is run once for each test__*, like setUp. Will be run
        multiple times for each test class.
        """
        remove_objects(LocalTestCase._objects)
        LocalTestCase._objects = []
        remove_objects(LocalTestCase._objs.case)
        LocalTestCase._objs.case = []
        if self._trackers:
            for obj in self._trackers.job.diff():
                obj.remove()
            for obj in self._trackers.job_history.diff():
                obj.remove()
        self._trackers = None

    def _create_job_trackers(self, runner_cleanup=False):
        """Create job trackers."""
        db = current.app.db
        max_history_id = db.job_history.id.max()
        rows = db(db.job_history.id != 0).select(max_history_id)
        max_id = rows[0][max_history_id] if rows else 0
        query = (db.job_history.id > max_id)
        job_tracker = TableTracker(Job)
        job_history_tracker = TableTracker(JobHistory, query=query)
        self._trackers = Storage({
            'job': job_tracker,
            'job_history': job_history_tracker,
        })
        if runner_cleanup:
            self._runner_trackers.append(job_tracker)
            self._runner_trackers.append(job_history_tracker)
        return self._trackers

    @classmethod
    def _reload(cls, obj):
        """Reload an object.

        Args:
            obj: DbObject
        """
        return obj.__class__.from_id(obj.id)

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
            urllib.error.HTTPError,
            expected_code,
            callable_obj,
            *args,
            **kwargs
        )

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
        # Clear memcache
        if current.app.local_settings \
                and current.app.local_settings.memcached_socket:
            current.cache.memcache.flush_all()
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
            current.cache = APP_ENV[app]['cache']
            current.app = Storage()
            current.app.auth = APP_ENV[app]['auth']
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
        env['db'] = APP_ENV[app]['current'].app.db
        env['cache'] = APP_ENV[app]['current'].cache
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
    # pylint: disable=protected-access
    # pylint: disable=super-init-not-called
    # pylint: disable=redefined-outer-name
    # pylint: disable=invalid-name
    # pylint: disable=line-too-long

    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, stream_err, descriptions, verbosity):
        """Constructor."""
        # pylint: disable=non-parent-init-called
        super().__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.stream_err = stream_err
        self.showAll = verbosity > 1
        self.showErr = verbosity == 1
        self.descriptions = descriptions
        self._runner_objects = []
        self._runner_trackers = []

    def startTest(self, test):
        """Adapted from unittest._TextTestResult. Method called just prior to
        test run
        """
        self.testsRun = self.testsRun + 1

    def stopTest(self, test):
        """Called when the given test has been run"""
        if hasattr(test, '_objs') and test._objs.runner:
            self._runner_objects.extend(test._objs.runner)
        if hasattr(test, '_runner_trackers') and test._runner_trackers:
            for x in test._runner_trackers:
                if x not in self._runner_trackers:
                    self._runner_trackers.append(x)

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
        re_fname = re.compile(r'.*/test_(.*).py$')
        for test, err in errors:
            # self.stream_err.writeln(self.separator1)
            # self.stream_err.writeln("%s: %s" % (flavour,
            #     self.getDescription(test)))
            # self.stream_err.writeln(self.separator2)
            # Print a command that will demonstrate the error.
            if hasattr(test, '_testMethodName'):
                fname = test.__module__.replace('.', '/') + '.py'
                if '/controllers/' in fname:
                    fname = fname.replace('/tests/', '/')
                else:
                    fname = fname.replace('/tests/', '/modules/')
                m = re_fname.match(fname)
                if m:
                    basename = m[1]
                    fname = fname.replace('test_' + basename, basename)

                self.stream_err.writeln(
                    '$ un {fname} {case} {method}'.format(
                        fname=fname,
                        case=test.__class__.__name__,
                        method=test._testMethodName,
                    )
                )
            elif hasattr(test, 'description'):
                parts = test.description.split()
                if str(parts[1]).startswith('(') and str(parts[1]).endswith(')'):
                    fname = str(parts[1])[1:-1].replace('.', '/') + '.py'
                    self.stream_err.writeln(
                        '$ un {fname}'.format(fname=fname)
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
    # pylint: disable=protected-access
    # pylint: disable=super-init-not-called
    # pylint: disable=redefined-outer-name
    # pylint: disable=invalid-name

    def __init__(
            self,
            stream=sys.stdout,
            stream_err=sys.stderr,
            descriptions=True,
            verbosity=1,
            failfast=False,
            buffer=False,
            resultclass=None,
            warnings=None,
            *,
            tb_locals=False):
        """Constructor."""
        self.stream = unittest.runner._WritelnDecorator(stream)
        self.stream_err = unittest.runner._WritelnDecorator(stream_err)
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        self.resultclass = resultclass
        self.warnings = warnings
        self.tb_locals = tb_locals

    def _makeResult(self):
        """Format test results"""
        return LocalTextTestResult(
            self.stream, self.stream_err, self.descriptions, self.verbosity)

    def run(self, test):
        """Run the given test case or test suite."""
        result = self._makeResult()
        result.failfast = self.failfast
        result.buffer = self.buffer
        startTime = time.time()
        test(result)
        if hasattr(result, '_runner_objects'):
            remove_objects(result._runner_objects)
            result._runner_objects = []
        if hasattr(result, '_runner_trackers'):
            for tracker in result._runner_trackers:
                for obj in tracker.diff():
                    obj.remove()
            result._runner_trackers = []
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
        super().__init__(
            self.url, postbacks=self.postbacks, default_headers=headers)
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
        self._soup = None
        self.post(
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

    def is_logged_in(self):
        """Determine if session is logged in.

        Returns:
            True if logged in.
        """
        return bool(self.session_id())

    def login(self, url='', email=None):
        """Login to web2py application

        Args:
            url: string, login url defaults to
                '<self.application>/default/user/login'
            email: email to login with. If None, defaults to self.username.

        Returns:
            True if ..., False otherwise
        """
        if not url:
            url = '/{app}/default/user/login'.format(app=self.application)

        # Step 1: Get the login page. This creates a session record in
        #         web2py_session_<app> table. (The employee_select page
        #         doesn't do this properly.)
        self.get(url)

        # Step 2: Login.
        if email is None:
            email = self.username
        data = dict(
            email=email,
            password=self.password,
            _formname='login',
        )
        self.post(url, data=data)

        self._logged_in_username = email

    def login_if_not(self):
        """Login if not already."""
        if not self.is_logged_in() or not self._logged_in_username:
            self.login()

    def logout(self, url=''):
        """Logout of web2py application

        Args:
            url: string, login url defaults to
                '<self.application>/default/user/logout'
        """
        if not url:
            url = '/{app}/default/user/logout'.format(app=self.application)
        self.get(url)
        self._logged_in_username = None

    def post(
            self,
            url,
            data=None,
            cookies=None,
            headers=None,
            auth=None,
            method='auto',
            charset='utf-8'):
        """Override base class method.

        Args:
            See WebClient.post()

        Differences from base class method.
        * Clears _soup property.
        """
        self._soup = None
        WebClient.post(
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

    def session_id(self):
        """Get the current session_id.

        Returns:
            str, session_id
        """
        if not self.sessions:
            return
        if self.application not in self.sessions:
            return
        return self.sessions[self.application]

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
                self.login_if_not()

        if post_data is None:
            self.get(url, charset=charset)
        else:
            if self.forms and list(self.forms.keys()):
                if '_formname' not in post_data:
                    post_data['_formname'] = list(self.forms.keys())[0]
                if '_formkey' not in post_data:
                    post_data['_formkey'] = self.forms[
                        list(self.forms.keys())[0]]
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
            with open(
                    os.path.join(dump_dir, filename + '.htm'),
                    'w',
                    encoding='utf-8') as f_dump:
                f_dump.write(
                    match_text.encode('ascii', 'replace').decode(charset)
                    + "\n"
                )

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
        do_run_command = '--no-count' not in sys.argv

        def run_command(args):
            """Run system command."""
            retries = [1, 10, 60]

            while True:
                try:
                    with subprocess.Popen(
                            args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE) as p:
                        p_stdout, p_stderr = p.communicate()
                except OSError:
                    if not retries:
                        break

                    sleep_sec = retries.pop(0)
                    time.sleep(sleep_sec)
                    continue

                if p_stdout:
                    fmt = 'sql_record_count.sh p_stdout: {o}'
                    print(fmt.format(o=p_stdout))
                if p_stderr:
                    fmt = 'sql_record_count.sh p_stderr: {p}'
                    print(fmt.format(p=p_stderr))
                break

        count_script = '/root/bin/sql_record_count.sh'
        if do_run_command:
            run_command([count_script, '-a', 'before'])

        try:
            func(*arg)
        except (SystemExit, KeyboardInterrupt):
            # This prevents a unittest.py exit from killing the wrapper
            pass

        if do_run_command:
            run_command([count_script, '-a', 'after'])
            run_command([count_script, '-a', 'diff'])
    return wrapper


def remove_comments_for(obj):
    """Remove all comments associated with an object.

    Args:
        obj: DbObject instance
    """
    # pylint: disable=protected-access
    # pylint: disable=global-statement
    # Remove comments.
    global FILTER_TABLES
    db = current.app.db
    if 'comment' in db.tables:
        if not FILTER_TABLES:
            FILTER_TABLES = [
                x.filter_table for x in
                db(db.comment.id > 0).select(
                    db.comment.filter_table, distinct=True)
            ]
        if obj.tbl._tablename in FILTER_TABLES:
            query = (db.comment.filter_table == obj.tbl._tablename) & \
                    (db.comment.filter_id == obj.id)
            db(query).delete()
            db.commit()


def remove_objects(source):
    """Remove objects created during test.

    Args:
        source: list, list of objects.
    """
    for obj in source:
        if hasattr(obj, 'remove'):
            remove_comments_for(obj)
            obj.remove()
        elif hasattr(obj, 'delete'):
            db = current.app.db
            obj.delete()
            db.commit()
