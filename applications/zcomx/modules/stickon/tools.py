#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
stickon/tools.py

Classes extending functionality of gluon/tools.py.

"""
import os
from gluon import *
from gluon.contrib.appconfig import AppConfig
from gluon.dal import Field
from gluon.storage import Settings
from gluon.tools import (
    Auth,
    Crud,
    Expose,
    Mail,
    Service,
)
from applications.zcomx.modules.ConfigParser_improved import  \
    ConfigParserImproved
from applications.zcomx.modules.environ import server_production_mode
from applications.zcomx.modules.memcache import MemcacheClient
from applications.zcomx.modules.mysql import LocalMySQL
from applications.zcomx.modules.python import from_dict_by_keys


class ConfigFileError(Exception):
    """Exception class for configuration file errors."""
    pass


class ExposeImproved(Expose):
    """Class representing Expose with bug fixes/improvements.
    Sub classes gluon/tools.py class Expose
    Modifications:
        * Fixes raw_args bug
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
            display_breadcrumbs=True):
        """Constructor.
        """
        # E0602 (undefined-variable): *Undefined variable %%r*  # current
        # pylint: disable=E0602
        if 'raw_args' not in current.request:
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
        div_text = H2(self.breadcrumbs(self.basename)) \
            if self.display_breadcrumbs \
            else ''
        return DIV(
            div_text,
            self.paragraph or '',
            self.table_folders(),
            self.table_files()
        ).xml()


class ModelDb(object):
    """Class representing the db.py model"""
    migrate = False
    db_driver_args = {'timeout': 500}          # milliseconds

    def __init__(self, environment, config_file=None):
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
        self.DAL = None
        self.db = None
        self.cache = None
        self.mail = None
        self.auth = None
        self.service = None
        self.local_settings = None
        self.settings_loader = None
        self._server_mode = None

    def _auth(self):
        """Create a auth instance. """

        auth = Auth(db=self.db, hmac_key=self.local_settings.hmac_key)
        self._auth_post_hook(auth)
        # This may need to be set to True the first time an app is used.
        if not self.local_settings.disable_authentication:
            # Create auth_* tables without signature
            auth.define_tables(username=False, signature=False, migrate=False)
        if self.settings_loader:
            self.settings_loader.import_settings(
                group=['auth', 'settings'],
                storage=auth.settings,
                unicode_to_str=True
            )
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
        if 'wsgi' in list(request.keys()):
            if hasattr(request['wsgi'], 'environ') and \
                    request['wsgi'].environ and \
                    'HTTP_HOST' in request['wsgi'].environ:
                host = request['wsgi'].environ['HTTP_HOST']
        elif 'env' in list(request.keys()):
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
                represent=lambda v, r=None: str(v),
                readable=False,
                writable=False,
            ),
            Field(
                'updated_on',
                'datetime',
                default=request.now,
                update=request.now,
                represent=lambda v, r=None: str(v),
                readable=False,
                writable=False,
            )
        )
        return auth

    def _auth_post_hook(self, auth):
        """Hook for post auth creation. Subclasses can add code here to be
        run directly following the creation of an Auth instance.

        Args:
            auth: Auth instance
        """
        pass

    def _cache(self):
        """Implement cache.

        """
        cache = self.environment['cache']

        if self.settings_loader and self.local_settings.memcached_socket:
            memcache_servers = [self.local_settings.memcached_socket]
            request = self.environment['request']
            cache.memcache = MemcacheClient(
                request,
                memcache_servers,
                default_time_expire=Auth.default_settings['expiration'],
            )
            cache.ram = cache.disk = cache.memcache

        return cache

    def _db(self):
        """Create a database handle

        """
        request = self.environment['request']
        response = self.environment['response']
        session = self.environment['session']
        if request.env.web2py_runtime_gae:
            # if running on Google App Engine connect to Google BigTable and
            # store sessions and tickets there.
            # or use the following lines to store sessions in Memcache
            #   from gluon.contrib.memdb import MEMDB
            #   from google.appengine.api.memcache import Client
            #   session.connect(request, response, db=MEMDB(Client())
            db = self.DAL(
                'gae',
                migrate=self.migrate
            )
            session.connect(request, response, db=db)
            return db

        if not self.settings_loader:
            # With not configuation, default to standard sqlite
            return self.DAL(
                'sqlite://storage.sqlite',
                migrate=self.migrate,
                driver_args=self.db_driver_args
            )

        if self.local_settings.db_adapter == 'sqlite':
            db_uri = self.local_settings.db_uri or 'sqlite://storage.sqlite'
            return self.DAL(
                db_uri,
                migrate=self.migrate,
                driver_args=self.db_driver_args
            )

        # MySQL
        # load using custom mysql class
        local_mysql = LocalMySQL(
            request=request,
                database=self.local_settings.database,
                user=self.local_settings.mysql_user,
            password=self.local_settings.mysql_password
        )
        check_reserved = None
        if self.local_settings.check_reserved and \
                self.local_settings.check_reserved != 'None':
            check_reserved = self.local_settings.check_reserved.split(',')
        db = self.DAL(
            local_mysql.sqldb,
            check_reserved=check_reserved,
            migrate=self.migrate
        )
        return db

    def _mail(self):
        """Create a mailer object instance

        """

        mail = Mail()  # mailer
        if self.settings_loader:
            self.settings_loader.import_settings(
                group=['mail', 'settings'],
                storage=mail.settings,
                unicode_to_str=True
            )
        return mail

    def _service(self):
        """Create a service object instance

        Service object is used for json, xml, jsonrpc, xmlrpc, amfrpc.
        """

        service = Service(self.environment)
        return service

    def _settings_config_file(self):
        """Return the file name where config settings are stored.

        Returns:
            str, full filename.
        """
        if self.config_file:
            return self.config_file

        env_config_file = os.environ.get('WEB2PY_SETTINGS_CONF_FILE', None)
        if env_config_file:
            return env_config_file

        request = self.environment['request']

        settings_json = os.path.join(
                request.folder, 'private', 'settings.json')
        return settings_json

    def _settings_loader(self):
        """Create a settings loader object instance

        """
        request = self.environment['request']
        etc_conf_file = self._settings_config_file()
        if not os.path.exists(etc_conf_file):
            raise ConfigFileError(
                    'Local configuration file not found: {file}'.format(
                    file=etc_conf_file
                )
            )

        settings_loader = SettingsLoader(
            config_file=etc_conf_file, application=request.application)
        settings_loader.get_settings()
        settings_loader.import_settings(
            group=['app'], storage=self.local_settings)
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

    def load(self, init_all=True):
        """Load components of model

        Args:
            init_all: If True, load all components.
        """
        self.local_settings = Settings()
        self.settings_loader = self._settings_loader()

        if init_all:
            # The order of these is intentional. Some depend on each other.
            self.DAL = self.environment['DAL']
            self.db = self._db()
            self.cache = self._cache()
            self.mail = self._mail()
            self.auth = self._auth()
            self.service = self._service()

        if self.settings_loader and 'response' in self.environment:
            self.settings_loader.import_settings(
                group=['response'],
                storage=self.environment['response'],
                unicode_to_str=True
            )

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

        if self.local_settings.admin_email:
            if user.email == self.local_settings.admin_email:
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

    def __init__(self, config_file=None, application='', unicode_to_str=False):
        """Constructor.

        Args:
            config_file: string, name of file containing configuration settings
            application: string, name of web2py application
            unicode_to_str: If True, unicode values are converted to str
        """

        self.config_file = config_file
        self.application = application
        self.unicode_to_str = unicode_to_str

        # settings = {'grp1': {set1:val1, set2:val2}, 'grp2': {...}
        self.settings = {}

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

        settings = {}

        json_settings = AppConfig(configfile=self.config_file, reload=True)

        if 'web2py' in json_settings:
            settings.update(json_settings['web2py'])

        if 'app' in json_settings:
            settings.update({'app': json_settings['app']})

        self.settings.update(settings)

    def import_settings(self, group, storage, unicode_to_str=False):
        """Import a group of settings into a storage.

        Args:
            group: list or str, The name of the group of settings to import,
                if list, represents the keys, eg ['auth', 'settings']
                if str, just a key: 'response'
            storage: gluon.storage Storage object instance.

        """
        if isinstance(group, str):
            groups = [group]
        else:
            groups = list(group)

        needs_unlock = False
        if groups[0] == 'auth' and storage.lock_keys:
            # auth requires lock_eyes = True permit custom settings
            needs_unlock = True

        if needs_unlock:
            storage.lock_keys = False

        try:
            sub_dict = from_dict_by_keys(self.settings, groups)
        except KeyError:
            # nothing to import
            return

        for setting in list(sub_dict.keys()):
            raw_value = sub_dict[setting]
            storage[setting] = self.scrub_unicode(raw_value) \
                if unicode_to_str else raw_value

        if needs_unlock:
            storage.lock_keys = True

    @classmethod
    def scrub_unicode(cls, setting_value):
        """Return the setting value scrubbed of unicide.

        Args:
            setting_value, mixed
            unicode_to_str: If True, unicode values are converted to str
        """
        if not isinstance(setting_value, str):
            return setting_value
        return str(setting_value)
