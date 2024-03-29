#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes for handling mysql.
"""
import os


class LocalMySQL():
    """Class representing the local MySQL connection parameters."""

    def __init__(
            self,
            request=None,
            database=None,
            user=None,
            password=None,
            hostname='127.0.0.1',
            port=None,
            charset='utf8',
            sqldb=None):
        """Constructor."""
        self.request = request
        self.database = database
        self.user = user
        self.password = password
        self.hostname = hostname
        self.port = port
        self.charset = charset
        self.sqldb = sqldb

        if not self.port:
            self.set_port()
        if not self.sqldb:
            self.set_sqldb()

    def set_port(self):
        """Set the MySQL port
        The port is set to the first value found in:
        1. request.env.mysql_tcp_port (set in httpd.conf)
        2. MYSQL_TCP_PORT env variable
        """

        port = None
        if self.request:
            port = self.request.env.mysql_tcp_port
        if not port:
            port = os.environ.get('MYSQL_TCP_PORT', None)
        self.port = port

    def set_sqldb(self):
        """Set the sqldb property."""

        self.sqldb = '%s://%s:%s@%s:%s/%s?set_encoding=%s' % (
            'mysql',
            self.user,
            self.password,
            self.hostname,
            self.port,
            self.database,
            self.charset,
        )

    def __repr__(self):
        fmt = ', '.join([
            'LocalMySQL(user={user!r}',
            'password={password!r}',
            'hostname={hostname!r}',
            'port={port!r}',
            'database={database!r}',
            'charset={charset!r})',
        ])
        return fmt.format(
                user=self.user,
                password=self.password,
                hostname=self.hostname,
                port=self.port,
                database=self.database,
                charset=self.charset)


def soundex(value):
    """Return the soundex string of a value.

    Args:
        value: string, soundex string

    Returns:
        string, the soundex of value.
    """
    if not value:
        return ''

    db = current.app.db
    soundex_sql = """SELECT SOUNDEX(%(value)s) as sndex;"""
    results = db.executesql(
        soundex_sql,
        placeholders=dict(value=value),
        as_dict=True
    )
    if not results or not results[0]:
        return
    return results[0]['sndex']
