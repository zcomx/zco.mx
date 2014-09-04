#!/bin/bash
r1='JPEG|PNG'

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [file1, file2... fileN]

This script optimizes JPG and PNG files.

EOF
}

_check_files() {
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
        pngcrush -q "$i" "$tmp.png" || rm "$tmp.jpg" &>/dev/null
        mv "$tmp.png" "$i" &>/dev/null
    elif [[ ${i##*.} == jpg ]]; then
        jpegtran -copy none -optimize -progressive "$i" > "$tmp.jpg" || rm "$tmp.jpg" &>/dev/null
        mv "$tmp.jpg" "$i" &>/dev/null
    else
        _me "File $i was not optimized"
    fi
}

for i in identify jpegtran pngcrush; do command -v "$i" &>/dev/null || _me "$i not installed"; done
(( $# == 0 )) && { _u; exit 1; }
for i in "$@"; do _check_files; done
for i in "$@"; do _optimize; done
