#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
create_table_definition_file.py

A script to create table definition files. An example table definition
file is:

    applications/<app>/databases/07e0a7454f3966e22c43693c8e02ebc2_mystuff.table

This script is meant to be a template. Copy and edit before using.
"""
# pylint: disable=import-error
import logging
from optparse import OptionParser
from gluon.dal import Field, Table, SQLCustomType
from pydal.base import BaseAdapter
from pydal._compat import hashlib_md5, pjoin, pickle
from pydal._load import portalocker
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
LOG = logging.getLogger('root')


class DubBaseAdapter(BaseAdapter):
    """Class representing a DubBaseAdapter"""
    # pylint: disable=missing-docstring

    @classmethod
    def ALLOW_NULL(cls):
        # pylint: disable=invalid-name
        return ''

    @classmethod
    def file_open(cls, filename, mode='rb', lock=True):
        # pylint: disable=bad-whitespace
        #to be used ONLY for files that on GAE may not be on filesystem
        if lock:
            fileobj = portalocker.LockedFile(filename,mode)
        else:
            fileobj = open(filename,mode)
        return fileobj

    @classmethod
    def file_close(cls, fileobj):
        #to be used ONLY for files that on GAE may not be on filesystem
        if fileobj:
            fileobj.close()


def get_ftype(table, field):
    """Get the ftype of a field."""
    # pylint: disable=bad-builtin
    # pylint: disable=protected-access
    # pylint: disable=unused-variable
    # pylint: disable=invalid-name
    # pylint: disable=line-too-long
    # pylint: disable=bad-whitespace
    field_name = field.name
    field_type = field.type
    self = DubBaseAdapter
    types = DubBaseAdapter.types
    tablename = table._tablename
    postcreation_fields = []
    TFK = {}

    if isinstance(field_type,SQLCustomType):
        ftype = field_type.native or field_type.type
    elif field_type.startswith(('reference', 'big-reference')):
        if field_type.startswith('reference'):
            referenced = field_type[10:].strip()
            type_name = 'reference'
        else:
            referenced = field_type[14:].strip()
            type_name = 'big-reference'

        if referenced == '.':
            referenced = tablename
        constraint_name = self.constraint_name(tablename, field_name)
        # if not '.' in referenced \
        #         and referenced != tablename \
        #         and hasattr(table,'_primarykey'):
        #     ftype = types['integer']
        #else:
        try:
            rtable = db[referenced]
            rfield = rtable._id
            rfieldname = rfield.name
            rtablename = referenced
        except (KeyError, ValueError, AttributeError) as e:
            self.db.logger.debug('Error: %s' % e)
            try:
                rtablename,rfieldname = referenced.split('.')
                rtable = db[rtablename]
                rfield = rtable[rfieldname]
            except Exception as e:
                self.db.logger.debug('Error: %s' %e)
                raise KeyError('Cannot resolve reference %s in %s definition' % (referenced, table._tablename))

        # must be PK reference or unique
        if getattr(rtable, '_primarykey', None) and rfieldname in rtable._primarykey or \
                rfield.unique:
            ftype = types[rfield.type[:9]] % \
                dict(length=rfield.length)
            # multicolumn primary key reference?
            if not rfield.unique and len(rtable._primarykey)>1:
                # then it has to be a table level FK
                if rtablename not in TFK:
                    TFK[rtablename] = {}
                TFK[rtablename][rfieldname] = field_name
            else:
                ftype = ftype + \
                    types['reference FK'] % dict(
                        constraint_name = constraint_name, # should be quoted
                        foreign_key = rtable.sqlsafe + ' (' + rfield.sqlsafe_name + ')',
                        table_name = table.sqlsafe,
                        field_name = field.sqlsafe_name,
                        on_delete_action=field.ondelete)
        else:
            # make a guess here for circular references
            if referenced in db:
                id_fieldname = db[referenced]._id.sqlsafe_name
            elif referenced == tablename:
                id_fieldname = table._id.sqlsafe_name
            else: #make a guess
                id_fieldname = self.QUOTE_TEMPLATE % 'id'
            #gotcha: the referenced table must be defined before
            #the referencing one to be able to create the table
            #Also if it's not recommended, we can still support
            #references to tablenames without rname to make
            #migrations and model relationship work also if tables
            #are not defined in order
            if referenced == tablename:
                real_referenced = db[referenced].sqlsafe
            else:
                real_referenced = (referenced in db
                                   and db[referenced].sqlsafe
                                   or referenced)
            rfield = db[referenced]._id
            ftype_info = dict(
                index_name = self.QUOTE_TEMPLATE % (field_name+'__idx'),
                field_name = field.sqlsafe_name,
                constraint_name = self.QUOTE_TEMPLATE % constraint_name,
                foreign_key = '%s (%s)' % (real_referenced, rfield.sqlsafe_name),
                on_delete_action=field.ondelete,
                )
            ftype_info['null'] = ' NOT NULL' if field.notnull else ''
            ftype_info['unique'] = ' UNIQUE' if field.unique else ''
            ftype = types[type_name] % ftype_info
    elif field_type.startswith('list:reference'):
        ftype = types[field_type[:14]]
    elif field_type.startswith('decimal'):
        precision, scale = map(int,field_type[8:-1].split(','))
        ftype = types[field_type[:7]] % \
            dict(precision=precision,scale=scale)
    elif field_type.startswith('geo'):
        if not hasattr(self,'srid'):
            raise RuntimeError('Adapter does not support geometry')
        srid = self.srid
        geotype, parms = field_type[:-1].split('(')
        if not geotype in types:
            raise SyntaxError(
                'Field: unknown field type: %s for %s' \
                % (field_type, field_name))
        ftype = types[geotype]
        if self.dbengine == 'postgres' and geotype == 'geometry':
            if self.ignore_field_case is True:
                field_name = field_name.lower()
            # parameters: schema, srid, dimension
            dimension = 2 # GIS.dimension ???
            parms = parms.split(',')
            if len(parms) == 3:
                schema, srid, dimension = parms
            elif len(parms) == 2:
                schema, srid = parms
            else:
                schema = parms[0]
            ftype = "SELECT AddGeometryColumn ('%%(schema)s', '%%(tablename)s', '%%(fieldname)s', %%(srid)s, '%s', %%(dimension)s);" % types[geotype]
            ftype = ftype % dict(schema=schema,
                                 tablename=tablename,
                                 fieldname=field_name, srid=srid,
                                 dimension=dimension)
            postcreation_fields.append(ftype)
    elif field_type not in types:
        raise SyntaxError('Field: unknown field type: %s for %s' % \
            (field_type, field_name))
    else:
        ftype = types[field_type] % {'length':field.length}

    if not field_type.startswith(('id','reference', 'big-reference')):
        if field.notnull:
            ftype += ' NOT NULL'
        else:
            ftype += self.ALLOW_NULL()
        if field.unique:
            ftype += ' UNIQUE'
        if field.custom_qualifier:
            ftype += ' %s' % field.custom_qualifier
    return ftype


def man_page():
    """Print manual page-like help"""
    print """
OVERVIEW
    This script can be used to create table definition files.
    !! This script is meant to be a template. Copy and edit before using. !!

    An example table definition file is:

    applications/<app>/databases/07e0a7454f3966e22c43693c8e02ebc2_mystuff.table

    This script will not work with py_web2py.sh

USAGE
    !!! This script has hard coded values. Not intended to be used directly !!!

    1. Copy script to temp script, and edit and use temp.script
    2. Update tablename
    2. Update table definition including all Field() definitions.
    3. Remove all Field attributes *except*
        name
        type (string, integer, etc)
        length
        unique
        notnull
        ondelete
        custom_qualifier

    Then:
    python web2py.py -S app -R applications/app/private/bin/tmp/tmp_create_table_definition_file.py

OPTIONS

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] table [table2 table3 ...]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
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

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    db = None

    app = 'app'                 # Replace with actual app name
    tablename = 'tablename'     # Replace with actual table name
    table = Table(
        db,
        tablename,
                                # Replace with actual Field() instances
                                # Remove unneeded attributes. See --man
        Field('name'),
        Field(
            'another_table_id',
            'integer',
        ),
        Field('time_stamp', 'datetime'),
    )

    sql_fields = {}

    for sortable, field in enumerate(table, start=1):
        field_name = field.name
        field_type = field.type
        ftype = get_ftype(table, field)
        sql_fields[field_name] = dict(
            length=field.length,
            unique=field.unique,
            notnull=field.notnull,
            sortable=sortable,
            type=str(field_type),
            sql=ftype)

    dbpath = 'applications/{a}/databases'.format(a=app)
    adapter_uri = 'sqlite://{a}.sqlite'.format(a=app)

    uri_hash = hashlib_md5(adapter_uri).hexdigest()
    print 'uri_hash: {var}'.format(var=uri_hash)

    # pylint: disable=protected-access
    table._dbt = pjoin(
        dbpath, '%s_%s.table' % (uri_hash, tablename))
    print 'table._dbt: {var}'.format(var=table._dbt)

    if table._dbt:
        tfile = DubBaseAdapter.file_open(table._dbt, 'wb')
        pickle.dump(sql_fields, tfile)
        DubBaseAdapter.file_close(tfile)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
