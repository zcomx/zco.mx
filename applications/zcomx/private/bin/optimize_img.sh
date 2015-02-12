#!/bin/bash

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [file1, file2... fileN]

This script optimizes JPG and PNG files.

EOF
}

_check_files() {
    r1='JPEG|PNG'
    identify "$i" &>/dev/null || _me "$i is not an image or image is corrupt"
    identify -regard-warnings -format "%g" "$i" &>/dev/null || _me "$i is corrupt"
    ext=$(identify -format '%m' "$i"[0] 2>/dev/null)
    [[ $ext =~ $r1 ]] || _me "$i is not a PNG or JPEG image"
}

_optimize() {
    [[ $ext == JPEG ]] && ext=jpg
    [[ ${ext,,} == ${i##*.} ]] || _me "File extension for $i should be $ext"

    tmp=tmp.$RANDOM
    if [[ ${i##*.} == png ]]; then
        zopflipng "$i" "$tmp.png" >/dev/null || rm "$tmp.png" &>/dev/null
        defluff < "$tmp.png" > "$i" 2>/dev/null
        rm "$tmp.png" &>/dev/null
    elif [[ ${i##*.} == jpg ]]; then
        jpegoptim -q -s "$i" "$tmp.jpg" || rm "$tmp.jpg" &>/dev/null
        mv "$tmp.jpg" "$i" &>/dev/null
    else
        _me "File $i was not optimized"
    fi
    return 0
}

for i in defluff identify jpegoptim zopflipng; do command -v "$i" &>/dev/null || _me "$i not installed"; done
(( $# == 0 )) && { _u; exit 1; }
for i in "$@"; do _check_files; done
for i in "$@"; do _optimize; done
