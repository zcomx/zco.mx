#!/bin/bash
__loaded_logger 2>/dev/null || source ${BASH_SOURCE%/*}/../lib/logger.sh

APP=zcomx
PY_SCRIPT="applications/shared/private/bin/python_web2py.sh"
SETTINGS_CONF="applications/$APP/private/settings.conf"
VIEWS_SQL=views.sql

script=${BASH_SOURCE##*/}
_u() { cat << EOF
usage: $script [options]

This script should be run when updates are installed on the production server.
    -v      Verbose.
    -h      Print this help message.

EOF
}

_migrate() {
    echo 'MIGRATE = True' > applications/$APP/models/0_migrate.py
    # Run a random script so the db migration is triggered.
    $PY_SCRIPT applications/$APP/private/bin/tally_book_ratings.py -h > /dev/null
    exit_status="$?"
    rm applications/$APP/models/0_migrate.py
    [[ $exit_status != 0 ]] && __me 'migrate failed'
}

_update_static_version () {
    local file new_version today version version_date version_num
    file=$1

    # Sample line from settings.conf
    # response.static_version = 2013.11.283
    version=$(grep '^response.static_version =' $file | awk '{print $3}')
    [[ ! $version ]] && __me "response.static_version not found in $file"

    version_date=$(echo $version | cut -c 1-10)
    version_num=$(echo $version | cut -c 11-)
    today=$(date "+%Y.%m.%d")
    if [[ $version_date == $today ]]; then
        let version_num++
    else
        version_num=0
    fi
    new_version="${today}${version_num}"
    __v && __mi "New version: $new_version"
    sed -i "s/^response.static_version = $version$/response.static_version = $new_version/" $file
}

_views() {
    for f in $(find applications/$APP -path "*/private/sqlite/$VIEWS_SQL"); do
        __v && __mi "Applying $f"
        sqlite3 "applications/$APP/databases/storage.sqlite" < "$f"
    done
}

_options() {
    # set defaults
    args=()
    unset verbose

    while [[ $1 ]]; do
        case "$1" in
            -v) verbose=true    ;;
            -h) _u; exit 0      ;;
            --) shift; [[ $* ]] && args+=( "$@" ); break;;
            -*) _u; exit 0      ;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    (( ${#args[@]} > 0 )) && { _u; exit 1; }
}

_options "$@"

__v && __mi "Starting"

# Get the app root directory
canonical_script=$(readlink -f "$0")
web2py_root=${canonical_script%/applications/$APP*}
cd $web2py_root || exit 1

__v && __mi "Migrating database"
_migrate

__v && __mi "Creating views"
_views

__v && __mi "Clearing cache"
cache_dir="applications/$APP/cache"
[[ -d $cache_dir ]] && rm -r "$cache_dir"/*

__v && __mi "Removing *.pyc"
find . -path ./applications/$APP/sessions -prune -o -type f -name "*.pyc" -exec rm -f {} \;


__v && __mi "Updating response.static_version"
_update_static_version "$SETTINGS_CONF"

__v && __mi "Restarting uwsgi emperor"
systemctl restart emperor.uwsgi.service

__v && __mi "SQL integrity"
$PY_SCRIPT applications/$APP/private/bin/utils/sql_integrity.py

__v && __mi "Done"

exit 0
