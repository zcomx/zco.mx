#!/bin/bash
TMPDIR=/tmp/square_image

__me() { __log 'error' "$*" ;}
__mw() { __log 'warn'  "$*" ;}
__mi() { __log 'info'  "$*" ;}
__md() { __log 'debug' "$*" ;}
__v()  { ${verbose-false} ;}

_u() { script=${0##*/}; cat << EOF
usage: $script /path/to/file.jpg

This script will convert an image to a square image.

OPTIONS:
    -f OFFSET  Crop offset. Can be in pixels or percent. See NOTES.
    -o FILE    Output squared image to FILE instead of squaring in-place.

    -v      Verbose.
    -h      Print this help message.

NOTES:
    * The longer dimension of the image is cropped.
      If the image is landscape, the width is cropped.
      If the image is portrait, the height is cropped.

    * If the image is already square, no cropping is done. If the -f OFFSET
      option is provided, it is ignored.

    * By default, the image is cropped leaving the center square.
      If landscape, the left and right sides are cropped equally.
      If portrait, the top and bottom are cropped equally.

    * The -f OFFSET option can be provided in the following forms

        -f 10           # offset is in pixels
        -f 10%          # offset is a percentage

    * If the -f OFFSET option is a percent, the offset value is determined as a
      percent of the dimension that will be cropped.

        # landscape
        offset = (width x OFFSET) / 100

        # portrait
        offset = (height x OFFSET) / 100

EXAMPLES:
    # Convert file.jpg to a square image, cropping to the center.
    $script file.jpg

    # Convert file.jpg to a square image, cropping from offset at 10 pixel.
    $script -f 10 file.jpg

    # Convert file.jpg to a square image, cropping from offset at 10%.
    $script -f 10% file.jpg

    # Convert in.jpg to a square image named out.jpg. in.jpg is left unchanged.
    $script -o out.jpg in.jpg
EOF
}

_get_geometry() {
    local h=$1
    local w=$2
    local offset_px=$3
    local geometry

    local orientation=$(_orientation "$h" "$w")

    if [[ $orientation == 'landscape' ]]; then
        geometry="${h}x${h}+${offset_px}+0"
    else
        geometry="${w}x${w}+0+${offset_px}"
    fi
    echo "$geometry"
}

_get_offset_centered() {
    local h=$1
    local w=$2
    local offset

    local orientation=$(_orientation "$h" "$w")

    if [[ $orientation == 'landscape' ]]; then
        offset=$(echo "($w - $h) / 2" | bc)
    else
        offset=$(echo "($h - $w) / 2" | bc)
    fi

    echo $offset
}

_get_offset_percent() {
    local h=$1
    local w=$2
    local percent=$3
    local offset

    local orientation=$(_orientation "$h" "$w")

    if [[ $orientation == 'landscape' ]]; then
        offset=$(echo "($w * $percent) / 100" | bc)
    else
        offset=$(echo "($h * $percent) / 100" | bc)
    fi

    echo $offset
}

_get_offset_px() {
    local h=$1
    local w=$2
    local raw_offset=$3
    local offset

    if [[ ! $raw_offset ]]; then
        offset=$(_get_offset_centered "$h" "$w")
    else
        if [[ $raw_offset =~ .*% ]]; then
            offset=$(_get_offset_percent "$h" "$w" "${raw_offset%*%}")
        else
            offset=$raw_offset
        fi
    fi

    echo $offset
}

_orientation() {
    local h=$1
    local w=$2

    (( $h > $w )) && { echo 'portrait'; return; }
    (( $w > $h )) && { echo 'landscape'; return; }
    echo 'square';
}

_options() {
    args=()
    unset outfile
    unset verbose
    unset offset

    while [[ $1 ]]; do
        case "$1" in
            -f) shift; offset=$1;;
            -o) shift; outfile=$1;;
            -v) verbose=true    ;;
            -h) _u; exit 0      ;;
            --) shift; [[ $* ]] && args+=( "$@" ); break ;;
            -*) _u; exit 0      ;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    (( ${#args[@]} != 1 )) && { _u; exit 1; }
    infile=${args[0]}
}

_options "$@"

[[ ! -e $infile ]] && {
    __me "File not found: $infile"
    exit 1
}

__v && __md "infile: $infile"
__v && __md "offset: $offset"

mkdir -p $TMPDIR
chown -R http:http $TMPDIR
tmpfile=$(mktemp --tmpdir=$TMPDIR)

__v && __md "tmpfile: $tmpfile"

wxh=$(identify -format '%P' "$infile")
w=${wxh%x*}
h=${wxh#*x}

__v && __md "image h: $h"
__v && __md "image w: $w"

orientation=$(_orientation "$h" "$w")

__v && __md "orientation: $orientation"

if [[ $orientation == 'square' ]]; then
    cp "$infile" "$tmpfile"
else
    offset_px=$(_get_offset_px "$h" "$w" "$offset")
    geometry=$(_get_geometry "$h" "$w" "$offset_px")
    __v && __md "offset_px: $offset_px"
    __v && __md "geometry: $geometry"
    convert "$infile" -crop "$geometry" "$tmpfile"
fi

if [[ $outfile ]]; then
    mv "$tmpfile" "$outfile"
else
    mv "$tmpfile" "$infile"
fi
