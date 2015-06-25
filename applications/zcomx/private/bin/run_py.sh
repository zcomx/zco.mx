#!/bin/bash
__loaded_logger 2>/dev/null || source ${BASH_SOURCE%/*}/lib/logger.sh

script=${BASH_SOURCE##*/}
_u() { cat << EOF
usage: $script [options] path/to/script.py

This script sets up the environment and runs a python script.
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

    (( ${#args[@]} == 0 )) && { _u; exit 1; }
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

# As a security precaution, validate that first argument is a script
# in the bin subdirectory.
script=${args[0]}
[[ ! -e "$script" ]] && {
    __me "Script not found: $script";
    exit 1;
}

[[ "$script" != applications/zcomx/private/bin/* ]] && {
    __me "Script not found in private/bin directory: $script";
    exit 1;
}

$py "${args[@]}"

__v && __md "Done ${0##*/}"
exit 0
