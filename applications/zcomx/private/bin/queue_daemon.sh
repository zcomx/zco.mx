#!/bin/bash
__loaded_logger 2>/dev/null || source ${BASH_SOURCE%/*}/lib/logger.sh

PID_PATH=/tmp/zco_queued
PID_FILE=$PID_PATH/pid

script=${BASH_SOURCE##*/}
_u() { cat << EOF
usage: $script [OPTIONS]

This script sets the environment and then sets up a loop that endlessly calls
the job queue handler script (queue_handler.py)

    -s SEC   Seconds to sleep between iterations. Default 60.
    -v       Verbose.
    -h       Print this help message.

SIGNALS:
   SIGUSR1: Wakes up daemon, repeatedly checks queue until at least one job
            is processed up to a maximum 10 times. Suitable when updates to
            job table may be delayed, eg from remote server.
   SIGUSR2: Wakes up daemon, checks queue once.
EOF
}

_options() {
    # set defaults
    args=()
    sleep_seconds=600
    unset verbose

    while [[ $1 ]]; do
        case "$1" in
            -s) shift; sleep_seconds=$1 ;;
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

__v && __md "Starting:"

__v && __md "Setting up environment"

py=applications/zcomx/private/bin/python_web2py.sh

mkdir -p "$PID_PATH"
echo "pid: $$" > $PID_FILE
echo "start: $(date '+%Y-%m-%d %H:%M:%S')" >> $PID_FILE
echo "last: " >> $PID_FILE

tries=0
trap 'let tries=10; __v && __mi "SIGUSR1 caught";' SIGUSR1
trap 'let tries+=1;  __v && __mi "SIGUSR2 caught";' SIGUSR2
trap '__v && __md "Shutting down."; exit 0;' SIGTERM SIGQUIT SIGKILL

v_flag=''
__v && v_flag='-v'
while :; do
    let tries-=1
    ((tries < 0)) && tries=0
    __v && __md "pid: $$, Checking job queue."
    result=$($py applications/zcomx/private/bin/queue_handler.py $v_flag -s)
    (( $? != 0 )) && __me "queue_handler.py exit status is error."
    checked=$(awk '/checked/ {print $2}' <<< "$result")
    __v && __md "pid: $$, Checking done, checked: $checked";
    sed -i "/^last:/d" $PID_FILE
    echo "last: $(date '+%Y-%m-%d %H:%M:%S')" >> $PID_FILE
    # Keep trying until the queue handler does something or we run out of tries
    exit_loop=false
    [[ ! $checked ]] && exit_loop=true                      # indeterminate response, exit
    [[ $checked && $checked != "0" ]] && exit_loop=true     # did something, exit
    (( $tries == 0 )) && exit_loop=true                     # run out of tries, exit
    if $exit_loop; then
        tries=0
        __v && __md "Sleeping $sleep_seconds"
        sleep $sleep_seconds &
        wait $!             # Wait for sleep to finish, quit wait on interrupt
    else
        sleep 1
    fi
done
exit 0
