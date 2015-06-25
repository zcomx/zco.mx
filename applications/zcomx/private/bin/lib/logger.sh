#!/bin/bash

#
# logger.sh
#
# Library of logging functions.
#

__log() {
    local level level_value level_values msg
    level=$1
    msg=$2

    declare -A level_values
    level_values=(
        [debug]=10
        [info]=20
        [warn]=30
        [error]=40
    )

    level_value=${level_values[$level]}

    # Typical message
    # Apr 17 17:27:34 input root [DEBUG queue_daemon.sh 157] File not found.
    # logger -p local7.$level -- "[${level^^} $script ${BASH_LINENO[0]}] $msg"
    logger -p local7.info -- "[${level^^} $script ${BASH_LINENO[0]}] $msg"
    __v || (( $level_value >= ${level_values[warn]} )) \
        && echo -e "===: ${level^^} $msg"
}

__me() { __log 'error' "$*" ;}
__mw() { __log 'warn'  "$*" ;}
__mi() { __log 'info'  "$*" ;}
__md() { __log 'debug' "$*" ;}
__v()  { ${verbose-false} ;}

# This function indicates this file has been sourced.
__loaded_logger() {
    return 0
}

# Export all functions to any script sourcing this library file.
while read -r function; do
    export -f "${function%%(*}"         # strip '()'
done < <(awk '/^__\w+\(\)/ {print $1}' "$BASH_SOURCE")
