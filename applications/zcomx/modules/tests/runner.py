#!/usr/bin/python

"""
tests/runner.py

Classes for local python test_suite scripts.
"""
from BeautifulSoup import BeautifulSoup
import StringIO
import datetime
import inspect
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib
import urllib2
import urlparse

from gluon.contrib.webclient import \
    WebClient, \
    DEFAULT_HEADERS as webclient_default_headers
from gluon.globals import current
import gluon.shell
from gluon.storage import \
    List, \
    Storage

FILTER_TABLES = []          # Cache for values in comment.filter_table fields
APP_ENV = {}                # Cache for app environments. Reuse of db prevents
                            # 'too many connections' errors.


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
    _objects = []

    def __init__(self, methodName='runTest'):
        """Constructor."""
        unittest.TestCase.__init__(self, methodName=methodName)
        self._start_time = None

    def _cleanup(self):
        """Cleanup executed after every test fixture."""
        for obj in self._objects:
            if hasattr(obj, 'remove'):
                self._remove_comments_for(obj)
                obj.remove()
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
    def add(cls, table, data):
        """Helper function to add a test record and store it for removal."""
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        db = table._db
        record_id = table.insert(**data)
        db.commit()
        record = db(table.id == record_id).select().first()
        cls._objects.append(record)
        return record

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
        filename = inspect.getouterframes(inspect.currentframe())[1][1]
        subdirs = filename.split(os.sep)
        # The app is the subdirectory just after 'applications'
        dirs = [i for i, x in enumerate(subdirs) if x == 'applications']
        try:
            app = subdirs[dirs[0] + 1]
        except IndexError:
            app = 'zcomx'
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
        web = LocalWebClient(
            app,
            login_user,
            login_password,
            db=env['db'],
            login_employee_id=login_employee_id,
            dump=LocalTestCase._opts.dump,
            login_required=login_required,
        )
        env['web'] = web
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
            wsgi_input = urllib.urlencode(post_vars)
            env['request'].env['CONTENT_LENGTH'] = str(len(wsgi_input))
            env['request'].env['wsgi.input'] = StringIO.StringIO(wsgi_input)
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
            self.stream_err.writeln(
                '$ unit {fname} {case} {method}'.format(
                    fname=test.__module__.replace('.', '/') + '.py',
                    case=test.__class__.__name__,
                    method=test._testMethodName,
                )
            )
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
            failed, errored = map(len, (result.failures, result.errors))
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
        self.url = url if url else 'https://jimk.zsw.ca'
        self.postbacks = postbacks
        self.login_required = login_required
        self.db = db
        self.dump = dump
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
            self._soup = BeautifulSoup(self.text)
        return self._soup

    @property
    def flash(self):
        """Return the flash message in the response text."""
        try:
            return self.as_soup().find('div', {'class': 'flash'}).string
        except AttributeError:
            return

    def get(self, url, cookies=None, headers=None, auth=None):
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
        result = WebClient.get(
            self,
            url,
            cookies=None,
            headers=None,
            auth=None
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

    def post(
        self,
        url,
        data=None,
        cookies=None,
        headers=None,
        auth=None,
        method='auto'
    ):
        """Override base class method.

        Args:
            See WebClient.post()

        Differences from base class method.
        * Clears _soup property.
        """
        self._soup = None
        result = WebClient.post(
            self,
            url,
            data=data,
            cookies=None,
            headers=None,
            auth=None,
            method=method
        )
        if self.db:
            self.db.commit()
        return result

    def server_ip(self):
        """Return the server ip address."""
        self.get('/')
        url = self.response.geturl()
        return socket.gethostbyname(urlparse.urlparse(url).hostname)

    def test(
        self,
        url,
        expect,
        match_type='all',
        tolerate_whitespace=False,
        post_data=None
    ):
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
            self.get(url)
        else:
            if self.forms and self.forms.keys():
                if '_formname' not in post_data:
                    post_data['_formname'] = self.forms.keys()[0]
                if '_formkey' not in post_data:
                    post_data['_formkey'] = self.forms[self.forms.keys()[0]]
            self.post(url, post_data)

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
        if isinstance(expect, list):
            match_func = any if match_type == 'any' else all
            return match_func([x in match_text for x in expect])
        return expect in match_text


class TableTracker(object):
    """Class representing a TableTracker used to track records in a table
    during tests when records can be created in the background and not
    easily controlled.

    Usage:
        tracker = TableTracker(db.job)
        job = tested_function()
        self.assertFalse(tracker.had(job)
        self.assertTrue(tracker.has(job)
    """
    def __init__(self, table):
        """Constructor

        Args:
            table: gluon.dal.base.Table instance
        """
        self.table = table
        db = self.table._db
        self._ids = [x.id for x in db(self.table).select()]

    def had(self, row):
        """Return whether the record represented by row existed when the
        instance was initialized.

        Args:
            row: gluon.dal.objects.Row instance.
        """
        return True if row.id in self._ids else False

    def has(self, row):
        """Return whether the record represented by row exists.

        Args:
            row: gluon.dal.objects.Row instance.
        """
        db = self.table._db
        ids = [x.id for x in db(self.table).select()]
        return True if row.id in ids else False


def _mock_date(self, today_value=None):
    """Function used to override the datetime.date function in tests."""
    # pylint: disable=W0613
    class MockDate(datetime.date):
        """Class representing mock date"""
        @classmethod
        def today(cls):
            """Function to override datatime.date.today()"""
            return today_value
    return MockDate


def _mock_datetime(self, now_value=None):
    """Function used to override the datetime.datetime function in tests."""
    # pylint: disable=W0613
    class MockDatetime(datetime.datetime):
        """Class representing mock datetime"""
        @classmethod
        def now(cls):
            """Function to override datatime.datetime.now()"""
            return now_value
    return MockDatetime


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
        tmp_dir = '/tmp/test_suite/count_diff'
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        with open(os.path.join(tmp_dir, 'before.txt'), "w") as bef:
            subprocess.call(
                ["/root/bin/sql_record_count.sh -s applications/zcomx/databases/storage.sqlite"],
                stdout=bef,
                shell=True
            )
        try:
            func(*arg)
        except (SystemExit, KeyboardInterrupt):
            # This prevents a unittest.py exit from killing the wrapper
            pass
        with open(os.path.join(tmp_dir, 'after.txt'), "w") as aft:
            subprocess.call(
                ["/root/bin/sql_record_count.sh -s applications/zcomx/databases/storage.sqlite"],
                stdout=aft,
                shell=True
            )
        subprocess.call(
            [
                'diff',
                '{dir}/before.txt'.format(dir=tmp_dir),
                '{dir}/after.txt'.format(dir=tmp_dir),
            ]
        )
        return
    return wrapper
