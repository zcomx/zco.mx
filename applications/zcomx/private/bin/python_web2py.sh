#!/bin/bash
__loaded_logger 2>/dev/null || source ${BASH_SOURCE%/*}/lib/logger.sh

script=${BASH_SOURCE##*/}
_u() { cat << EOF
usage: $script [options] path/to/script [args]

This script runs a 'python web2py.py' command.

OPTIONS
    --app APP           Use this app. Default determined from script path.
                        applications/<app>/path/to/file.py
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

_options() {
    # set defaults
    args=()
    unset app
    unset script_to_run
    unset profile

    while [[ $1 ]]; do
        case "$1" in
         --app) shift; app=$1;;
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
if [[ $HOSTNAME == 'jimk' ]]; then
    export SERVER_PRODUCTION_MODE=test
else
    export SERVER_PRODUCTION_MODE=live
fi

# Validate script_to_run
if [[ ! -e "$script_to_run" ]]; then
    __me "Invalid script. File not found: $script_to_run"
    exit 1
fi

# Extract the app.
if [[ ! $app ]]; then
    tmp_script=${script_to_run#*/}        # Strip 'applications/'
    app=${tmp_script%%/*}                 # Strip 'private/bin/script_to_run.py'
fi

unset model_opt
if [[ $script_to_run != applications/* ]]; then
    model_opt='-M'
fi

unset profile_opts
if [[ $profile ]]; then
    profile_opts="-m cProfile -o $profile"
fi

python_bin=$(type -p python3)
[[ ! $python_bin ]] && {
    __me "Unable to run web2py script. python3 not found"
    exit 1
}

SERVER_PRODUCTION_MODE=$SERVER_PRODUCTION_MODE $python_bin $profile_opts  web2py.py --no_banner --no_gui --add_options -L config.py -S "$app" $model_opt -R "$script_to_run" -A "${args[@]}"
