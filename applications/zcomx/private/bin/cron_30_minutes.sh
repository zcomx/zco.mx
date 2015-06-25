#!/bin/bash
# This script is cronned every 30 minutes.
__loaded_logger 2>/dev/null || source ${BASH_SOURCE%/*}/lib/logger.sh

script=${BASH_SOURCE##*/}
_u() { cat << EOF
usage: $script [options]

This script sets up the environment and runs cron jobs every 30 minutes for
project.
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

__v && __md "Start: queue_create_torrents"
$py applications/zcomx/private/bin/queue_create_torrents.py

__v && __md "Start: queue_check"
$py applications/zcomx/private/bin/queue_check.py --age 30

__v && __md "Start: process_activity_logs"
$py applications/zcomx/private/bin/process_activity_logs.py

__v && __md "Setting permissions"
chown -R http:http applications/zcomx/uploads
chown -R http:http applications/zcomx/private/var

__v && __md "Done ${0##*/}"
exit 0
