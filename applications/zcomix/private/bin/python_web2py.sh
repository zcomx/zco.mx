#!/bin/bash

RC_FILE=/srv/http/local/rc.sh

script=${0##*/}
_u() { cat << EOF
usage: $script [options] path/to/script [args]

This script runs a 'python web2py.py' command.

OPTIONS
    --app APP           Use this app. Default determined from script path.
                        applications/<app>/path/to/file.py
    --config FILE       Source this rc file.
                        Default: $RC_FILE
    --profile FILE      File to dump profile stats to.
    --                  Arguments following -- are not interpreted as options.

All other options and arguments are passed to the 'python web2py.py' command,
in other words as args to the -A, --args option.

NOTES:
    Use the -- option to prevent script options from being interpreted as
    options to python_web2py.sh.

EXAMPLES:
    $script applications/myapp/private/bin/script.py
    $script applications/myapp/private/bin/script.py -v
    $script --profile -- applications/myapp/private/bin/script.py -v
EOF
}

__mi() { __v && echo -e "===: $*" ;}
__me() { echo -e "===> ERROR: $*" >&2; exit 1 ;}
__v()  { ${verbose-false} ;}

_options() {
    # set defaults
    args=()
    rc_file=$RC_FILE
    unset app
    unset script_to_run
    unset profile

    while [[ $1 ]]; do
        case "$1" in
         --app) shift; app=$1;;
      --config) shift; rc_file=$1;;
     --profile) shift; profile=$1;;
            --) shift; [[ $* ]] && args+=( "$@" ); break;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    (( ${#args[@]} == 0 )) && { _u; exit 1; }
    script_to_run=${args[0]}
    unset args[0]
}

_options "$@"

__v && __mi "Starting:"

# Set environment
if [[ -e $rc_file ]]; then
    source "$rc_file"
else
    export SERVER_PRODUCTION_MODE=test
fi

# Validate script_to_run
[[ ! -e "$script_to_run" ]] && __me "Invalid script. File not found: $script_to_run"

# Extract the app.
if [[ ! $app ]]; then
    tmp_script=${script_to_run#*/}        # Strip 'applications/'
    app=${tmp_script%%/*}                 # Strip 'private/bin/script_to_run.py'
fi

unset profile_opts
if [[ $profile ]]; then
    profile_opts="-m cProfile -o $profile"
fi
python=python
type python2 &>/dev/null && python=python2

SERVER_PRODUCTION_MODE=$SERVER_PRODUCTION_MODE MYSQL_TCP_PORT=$MYSQL_TCP_PORT "$python" $profile_opts  web2py.py --no-banner -L config.py -S "$app" -R "$script_to_run" -A "${args[@]}"
