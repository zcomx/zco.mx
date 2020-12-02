#!/bin/bash

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [file1, file2... fileN]

This script optimizes JPG and PNG files.
    -Q      If JPG Quality is greater than 92, then lower it

EOF
}

_check_files() {
    identify "$i" &>/dev/null || _me "$i is not an image or the image is corrupt"
    identify -regard-warnings -format "%g" "$i" &>/dev/null || _me "$i is corrupt"
    ff=$(identify -format '%m' "$i"[0] 2>/dev/null); [[ $ff == JPEG ]] && ff=JPG     ## determine file format
    r1='GIF|JPG|PNG'
    [[ $ff =~ $r1 ]] || _me "$i is not a GIF, JPEG or PNG image"
}

_jq() {
    jq=$(identify -format '%Q' "$i")
    (( $jq > 92 )) && pingo -jpgquality=92 -jpgsample=2 -quiet "$i"
}

_optimize() {
    t=tmp.$RANDOM

    ext=${i##*.}
    if [[ $ff != ${ext^^} ]]; then
        _mi "File extension of $i was changed to: ${ff,,}"
        mv "$i" "${i%.*}.${ff,,}"
        i=${i%.*}.${ff,,}
    fi

    if [[ $ff == GIF ]]; then
        convert "$i" "${i%.*}.png"
        rm "$i"
        ff=PNG
        i="${i%.*}.png"
    fi

    if [[ $ff == PNG ]]; then
        nice pingo -s9 -strip=3 "$i" >/dev/null || _me "pingo failed on file: $i"
        [[ $t ]] && { defluff < "$i" > "$t" 2>/dev/null && mv "$t" "$i"; }
    elif [[ $ff == JPG ]]; then
        [[ $(identify -format '%[colorspace]' "$i") == CMYK ]] && { convert "$i" -colorspace sRGB "$t" && mv "$t" "$i"; }
        [[ $Q ]] && _jq             ## If -Q, then check to see if jpg_quality should be lowered
        jpegoptim -q -s "$i" || _me "jpegoptim failed on file: $i"
    else
        _me "File $i was not optimized"
    fi

    rm "$t" &>/dev/null
    return 0
}

_options() {
    # set defaults
    args=()
    unset quick

    while [[ $1 ]]; do
        case "$1" in
            -Q) Q=1             ;;
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

for i in defluff convert identify jpegoptim pingo; do command -v "$i" &>/dev/null || _me "$i not installed"; done
for i in "${args[@]}"; do _check_files; done
for i in "${args[@]}"; do _optimize; done
#[[ -t 1 ]] && printf '\a'       ## when done, ring the bell
