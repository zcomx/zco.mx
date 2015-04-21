#!/bin/bash
PY_SCRIPT="applications/zcomx/private/bin/python_web2py.sh"
SETTINGS_CONF="applications/zcomx/private/settings.conf"


DEBUG=10
INFO=20
WARN=30
ERROR=40
LEVEL_NAMES=(
    [DEBUG]=debug
    [INFO]=info
    [WARN]=warn
    [ERROR]=error
)

script=${0##*/}
_u() { cat << EOF
usage: $script [options]

This script should be run when updates are installed on the production server.
    -v      Verbose.
    -h      Print this help message.

EOF
}

_log() {
    local level line_no msg
    level_value=$1
    msg=$2

    level=${LEVEL_NAMES[$level_value]}

    # Typical message
    # Apr 17 17:27:34 input root [DEBUG queue_daemon.sh 157] File not found.
    logger -p local7.$level -- "[${level^^} $script ${BASH_LINENO[0]}] $msg"
    [[ __v ]] || (($level >= $level_warn )) && echo -e "===: ${level^^} $msg"
}

__me() { _log "$ERROR" "$*" ;}
__mw() { _log "$WARN"  "$*" ;}
__mi() { _log "$INFO"  "$*" ;}
__md() { _log "$DEBUG" "$*" ;}
__v()  { ${verbose-false} ;}

_migrate() {
    echo 'MIGRATE = True' > applications/zcomx/models/0_migrate.py
    # Run a random script so the db migration is triggered.
    $PY_SCRIPT applications/zcomx/private/bin/tally_book_ratings.py -h > /dev/null
    exit_status="$?"
    rm applications/zcomx/models/0_migrate.py
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
web2py_root=${canonical_script%/applications/zcomx*}
cd $web2py_root || exit 1

__v && __mi "Migrating database"
_migrate

__v && __mi "Updating response.static_version"
_update_static_version "$SETTINGS_CONF"

__v && __mi "Restarting uwsgi emperor"
systemctl restart emperor.uwsgi.service

__v && __mi "SQL integrity"
$PY_SCRIPT applications/zcomx/private/bin/utils/sql_integrity.py


__v && __mi "Done"

exit 0
