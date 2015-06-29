#!/bin/bash
# This script is cronned daily.
__loaded_logger 2>/dev/null || source ${BASH_SOURCE%/*}/lib/logger.sh

script=${BASH_SOURCE##*/}
_u() { cat << EOF
usage: $script [options]

This script sets up the environment and runs daily cron jobs for project.
Intended to be cronned.
    -v      Verbose.
    -h      Print this help message.
EOF
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
__v && __md "Starting ${0##*/}"

bin=$(cd -- "$(dirname "$0")" && pwd)
regex="/srv/http/(.*)/web2py/applications/zcomx/*"
[[ $bin =~ $regex ]]
server="${BASH_REMATCH[1]}"
web2py_root="/srv/http/$server/web2py"

export PYTHONPATH=${web2py_root}
cd $web2py_root

py=$web2py_root/applications/zcomx/private/bin/python_web2py.sh

__v && __md "Start: post_ongoing_update.py"
yesterday=$(date -d yesterday "+%Y-%m-%d")
$py applications/zcomx/private/bin/social_media/post_ongoing_update.py -p "$yesterday"

__v && __md "Start: tally_book_ratings.py"
$py applications/zcomx/private/bin/tally_book_ratings.py

__v && __md "Start: search_prefetch"
$py applications/zcomx/private/bin/queue_job.py --queuer SearchPrefetchQueuer

__v && __md "Start: purge_torrents"
$py applications/zcomx/private/bin/queue_job.py --queuer PurgeTorrentsQueuer

__v && __md "Start: integrity"
$py applications/zcomx/private/bin/integrity.py

__v && __md "Start: clean sessions"
touch applications/zcomx/sessions/.gitignore        # Prevents delete
$py applications/zcomx/../../scripts/sessions2trash.py --once

__v && __md "Done ${0##*/}"
exit 0
