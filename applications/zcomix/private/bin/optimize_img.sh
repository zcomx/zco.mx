#!/bin/bash

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [file1, file2... fileN]

This script optimizes JPG and PNG files.

EOF
}

_optimize() {
    ext=$(identify -format '%m' "$i"[0] 2>/dev/null)
    [[ $ext == JPEG ]] && ext=jpg
    [[ ${ext,,} == ${i##*.} ]] || _me "File extension for $i should be $ext"

    tmp=tmp.$RANDOM
    [[ ${i##*.} == png ]] && pngcrush -q "$i" "$tmp.png" && mv "$tmp.png" "$i"
    [[ ${i##*.} == jpg ]] && jpegtran -copy none -optimize -progressive "$i" > "$tmp.jpg" && mv "$tmp.jpg" "$i"
}

(( $# == 0 )) && { _u; exit 1; }
for i in "$@"; do _optimize; done
