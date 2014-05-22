#!/bin/bash

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
usage: $script [options] in-file [out-file]

This script converts and optimizes an image.
    -r SIZE Resize image to SIZE. Cmp imagemagick convert --resize.
    -v      Verbose.
    -h      Print this help message.

EXAMPLE:
    $script in.jpg out.jpg       # Optimize in.jpg and save as out.jpg
    $script in.jpg               # Optimize in.jpg in-place
    $script -r 1600 in.jpg       # Optimize and resize file.
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


_options() {
    # set defaults
    args=()
    unset input
    unset ouput
    unset resize
    unset verbose

    while [[ $1 ]]; do
        case "$1" in
            -r) shift; resize=$1;;
            -v) verbose=true    ;;
            -h) _u; exit 0      ;;
            --) shift; [[ $* ]] && args+=( "$@" ); break;;
            -*) _u; exit 0      ;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    (( ${#args[@]} < 1 )) && { _u; exit 1; }
    (( ${#args[@]} > 2 )) && { _u; exit 1; }
    input="${args[0]}"
    output="$input"
    (( ${#args[@]} == 2 )) && { output="${args[1]}"; }
}

_options "$@"

__v && __mi "Starting:"


if type convert &>/dev/null; then
    __v && __mi "Converting $input to $output"
    [[ $resize ]] && __v && __mi "Resizing: $resize"
    # Imagemagick uses the /tmp directory by default, but there may not be
    # enough space available. Use the uploads/tmp directory relative to
    # where the script is located.
    tmp=$0
    while true; do
        tmp=$(dirname $tmp)
        [[ -d "$tmp/uploads" ]] && { tmp="$tmp/uploads/tmp"; break; }
        [[ "$tmp" == '/' ]] && { tmp=/tmp; break; }
    done
    mkdir -p "$tmp"
    MAGICK_TMPDIR="$tmp" \
        convert "$input" \
        -limit memory 200MB \
        -limit map 200MB \
        -quiet \
        -colorspace Lab \
        ${resize:+-resize "$resize"} \
        -interpolate catrom \
        -set colorspace Lab \
        -colorspace sRGB \
        "$output" || exit 1
else
    __v && __mw "'convert' not found"
    if [[ "$input" != "$output" ]]; then
        __v && __mi "Copying $input to $output"
        cp "$input" "$output" || exit 1
    fi
fi

# Remove jpg headers if applicable.
if [[ $(file -b --mime-type "$output") == 'image/jpeg' ]]; then
    if type jpegoptim &>/dev/null; then
        __v && __mi 'Optimizing with jpegoptim'
       jpegoptim -q --strip-all "$output" || exit 1
    else
        __v && __mw "Skipping JPEG optimization. 'jpegoptim' not found."
    fi
fi

__v && __mi "Done:"

exit 0
