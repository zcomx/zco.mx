    #!/usr/bin/python
# -*- coding: utf-8 -*-

"""
stickon/tools.py

Classes extending functionality of gluon/tools.py.

"""
from applications.zcomx.modules.environ import server_production_mode
from gluon import *
from pydal import Field
from gluon.storage import Settings
from gluon.tools import \
    Auth, \
    Crud, \
    Expose, \
    Mail, \
    Service
import os
import ConfigParser
from applications.zcomx.modules.ConfigParser_improved import  \
    ConfigParserImproved

# C0103: *Invalid name "%s" (should match %s)*
# Some variable names are adapted from web2py.
# pylint: disable=C0103


class ConfigFileError(Exception):
    """Exception class for configuration file errors."""
    pass


class ExposeImproved(Expose):
    """Class representing Expose with bug fixes/improvements.
    Sub classes gluon/tools.py class Expose
    Modifications:
        * Fixes raw_args bug
          http://code.google.com/p/web2py/issues/detail?id=1947
        * breadcrumbs are optional
        * .svg are considered images.

    """
    image_extensions = ('.bmp', '.png', '.jpg', '.jpeg', '.gif', '.tiff',
                        '.svg')

    def __init__(
        self,
        base=None,
        basename=None,
        extensions=None,
        allow_download=True,
        display_breadcrumbs=True
    ):
        """Constructor.
        """
        # E0602 (undefined-variable): *Undefined variable %%r*  # current
        # pylint: disable=E0602
        if not 'raw_args' in current.request:
            current.request.raw_args = '/'.join(current.request.args)
        Expose.__init__(
            self,
            base=base,
            basename=basename,
            extensions=extensions,
            allow_download=allow_download
        )
        self.display_breadcrumbs = display_breadcrumbs

    @staticmethod
    def isimage(f):
        return os.path.splitext(f)[-1].lower() \
            in ExposeImproved.image_extensions

    def xml(self):
        return DIV(
            H2(self.breadcrumbs(self.basename))
                if self.display_breadcrumbs else '',
            self.paragraph or '',
            self.table_folders(),
            self.table_files()
        ).xml()


class ModelDb(object):
    """Class representing the db.py model"""
    migrate = False

    def __init__(self, environment, config_file=None, init_all=True):
        """Constructor.

        Args:
            environment: dict, dictionary defining environment as returned by
                    gluon/shell.py def env
            config_file: string, name of file used for configuration settings
                If None, this is set as per application. See _settings_loader()
                method.
        """
        self.environment = environment
        self.config_file = config_file
        self._server_mode = None

        self.local_settings = Settings()
        self.settings_loader = self._settings_loader()

        if init_all:
            # The order of these is intentional. Some depend on each other.
            self.DAL = self.environment['DAL']
            self.db = self._db()
            self.mail = self._mail()
            self.auth = self._auth()
            self.crud = self._crud()
            self.service = self._service()

        if self.settings_loader and 'response' in self.environment:
            self.settings_loader.import_settings(
                group='response', storage=self.environment['response'])

    def _auth(self):
        """Create a auth instance. """

        auth = Auth(db=self.db, hmac_key=self.local_settings.hmac_key)
        # This may need to be set to True the first time an app is used.
        if not self.local_settings.disable_authentication:
            auth.settings.extra_fields['auth_user'] = [Field('name')]
            auth.define_tables(username=False, signature=False, migrate=True)
        if self.settings_loader:
            self.settings_loader.import_settings(
                group='auth', storage=auth.settings)
        auth.settings.mailer = self.mail
        auth.settings.verify_email_onaccept = self.verify_email_onaccept
        # Controller tests scripts require login's with same session.
        if self.get_server_mode() == 'test':
            # Resetting the session farks with controller test scripts
            auth.settings.renew_session_onlogin = False
            auth.settings.renew_session_onlogout = False
        else:
            auth.settings.renew_session_onlogin = True
            auth.settings.renew_session_onlogout = True

        host = ''
        request = self.environment['request']
        if 'wsgi' in request.keys():
            if hasattr(request['wsgi'], 'environ') and \
                    request['wsgi'].environ and \
                    'HTTP_HOST' in request['wsgi'].environ:
                host = request['wsgi'].environ['HTTP_HOST']
        elif 'env' in request.keys():
            host = request.env.http_post
        if host:
            auth.messages.verify_email = 'Click on the link http://' + host \
                + '/' + request.application \
                + '/default/user/verify_email/%(key)s to verify your email'
            auth.messages.reset_password = 'Click on the link http://' + host \
                + '/' + request.application \
                + '/default/user/reset_password/%(key)s to reset your password'

        # W0108: *Lambda may not be necessary*
        # pylint: disable=W0108
        auth.signature = self.db.Table(
            self.db,
            'auth_signature',
            Field(
                'created_on',
                'datetime',
                default=request.now,
                represent=lambda x: str(x),
                readable=False,
                writable=False,
            ),
            Field(
                'updated_on',
                'datetime',
                default=request.now,
                update=request.now,
                represent=lambda x: str(x),
                readable=False,
                writable=False,
            )
        )
        return auth

    def _crud(self):
        """Create a Crud instance
        """

        # for CRUD helpers using auth

        crud = Crud(self.environment, self.db)
        return crud

    def _db(self):
        """Create a database handle

        """
        request = self.environment['request']
        response = self.environment['response']
        session = self.environment['session']
        if request.env.web2py_runtime_gae:

            # if running on Google App Engine connect to Google BigTable and
            # store sessions and tickets there.

            db = self.DAL('gae')
            session.connect(request, response, db=db)
        else:
            driver_args={
                'timeout': 500          # milliseconds
            }

            # or use the following lines to store sessions in Memcache
            #   from gluon.contrib.memdb import MEMDB
            #   from google.appengine.api.memcache import Client
            #   session.connect(request, response, db=MEMDB(Client())
            db = self.DAL(
                'sqlite://storage.sqlite',
                migrate=self.migrate,
                debug=True,
                driver_args=driver_args,
            )
        return db

    def _mail(self):
        """Create a mailer object instance

        """

        mail = Mail()  # mailer
        if self.settings_loader:
            self.settings_loader.import_settings(
                group='mail', storage=mail.settings)
        return mail

    def _service(self):
        """Create a service object instance

        Service object is used for json, xml, jsonrpc, xmlrpc, amfrpc.
        """

        service = Service(self.environment)
        return service

    def _settings_loader(self):
        """Create a settings loader object instance

        """
        request = self.environment['request']
        etc_conf_file = self.config_file if self.config_file else \
            os.path.join(request.folder, 'private', 'settings.conf')
        if not os.path.exists(etc_conf_file):
            raise ConfigFileError(
                'Local configuration file not found: {file}'.format(
                    file=etc_conf_file)
            )
        settings_loader = SettingsLoader(
            config_file=etc_conf_file, application=request.application)
        settings_loader.import_settings(
            group='local', storage=self.local_settings)
        return settings_loader

    def get_server_mode(self):
        """Return the server mode setting.

        Returns:
            string: server mode, 'test' or 'live'
        """
        if self._server_mode is None:
            request = self.environment['request']
            self._server_mode = server_production_mode(request)
        return self._server_mode

    def verify_email_onaccept(self, user):
        """
        This is run after the registration email is verified. The
        auth.setting.verify_email_onaccept in model/db.py points here.
        """
        # Create an admin group if not already done.
        admin = 'admin'
        if not self.auth.id_group(admin):
            self.auth.add_group(admin,
                                description='Administration group')

        # Add user to admin group if email matches admin_email.
        if user.email == self.auth.settings.admin_email:
            if not self.auth.has_membership(
                    self.auth.id_group(admin), user.id):
                self.auth.add_membership(
                    self.auth.id_group(admin), user.id)


class MigratedModelDb(ModelDb):
    """Class representing the db.py model with migration enabled."""
    migrate = True


class SettingsLoader(object):

    """Class representing a settings loader.

    Object instances permit loading settings from a config file and importing
    them into web2py storage objects.
    """

    def __init__(self, config_file=None, application=''):
        """Constructor.

        Args:
            config_file: string, name of file containing configuration settings
            application: string, name of web2py application

        """

        self.config_file = config_file
        self.application = application

        # settings = {'grp1': {set1:val1, set2:val2}, 'grp2': {...}

        self.settings = {}
        self.get_settings()

    def __repr__(self):
        fmt = ', '.join([
            'SettingsLoader(config_file={config_file!r}',
            'application={application!r}',
        ])
        return fmt.format(
            config_file=self.config_file, application=self.application)

    def get_settings(self):
        """Read settings from config file."""

        if not self.config_file:
            return
        config = ConfigParserImproved()
        config.read(self.config_file)
        settings = {}

        # The 'web2py' section is required, if not found an exception is
        # raised.
        for (name, value) in config.items_scrubbed('web2py'):
            settings[name] = value

        # The application section is optional, if not found the web2py
        # values are used.
        if self.application:
            try:
                for (name, value) in config.items_scrubbed(self.application):
                    settings[name] = value
            except ConfigParser.NoSectionError:
                pass

        for key in settings.keys():
            # Set the group values
            parts = key.split('.', 1)
            if len(parts) == 1:
                parts.insert(0, 'local')
            (group, setting) = parts[0:2]
            if not group in self.settings:
                self.settings[group] = {}
            self.settings[group][setting] = settings[key]

    def import_settings(self, group, storage):
        """Import a group of settings into a storage.

        Args:
            group: string, The name of the group of settings to import,
                eg 'auth'
            storage: gluon.storage Storage object instance.

        """

        if group == 'auth':
            storage.lock_keys = False  # Required to permit custom settings
        if not group in self.settings:
            # nothing to import
            return
        for setting in self.settings[group].keys():
            storage[setting] = self.settings[group][setting]
