#!/bin/bash

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [-l] nnn /path/to/metadatafile /path/to/indicia-img

This script will generate an indicia file which is used in cbz files on
zco.mx.

    -l      Generate landscape indicia file
    nnn     Cartoonist ID

    -h      Print this help message.

EXAMPLE:
    $script 123 metadata.txt image.png
    $script -l 123 metadata.txt image.png
EOF
}

_check() {
    [[ $cid != *[!0-9]* ]] || _me "ID is not an integer"
    IFS=\/ read -r t _ < <(file -ib -- $metadata)
    [[ $t == text ]]  || _me "File $metadata is not a text file"
    metadata=$(< $metadata)

    IFS=\/  read -r t _ < <(file -ib -- $indiciaimg)
    [[ $t == image ]] || _me "File $indiciaimg is not an image file"
}

_indicia() {
#     w  h pos    colour  pt   x   y text
d=" 960 54 center #333333 46   0  80 IF  YOU  ENJOYED THIS WORK YOU CAN
    960 54 center #333333 46   0 145 HELP OUT BY  GIVING  SOME MONIES!!
    960 54 center #333333 46   0 210 OR BY TELLING OTHERS ON  TWITTER,
    960 54 center #333333 46   0 275 TUMBLR  AND  FACEBOOK.
    465 48 east   #333333 40   0 410 CONTRIBUTE MONIES:
    465 48 east   #333333 40   0 460 CONTACT INFO:
    600 48 west   #333333 40 480 410 https://$cid.zco.mx/monies
    600 48 west   #333333 40 480 460 https://$cid.zco.mx
     $w $h center #333333 26  $x  $y $metadata"

    while read -r w h pos colour pt x y text; do
        (( $pt == 46 )) && font=Brushy-Cre || font=SF-Cartoonist-Hand-Bold
        [[ $l ]] && (( $pt == 46 )) && pt=42

        convert -size ${w}x$h -gravity $pos -fill $colour \
            -font "$font" -background none -pointsize $pt \
            -page +${x}+$y  caption:"$text"  miff:-
    done <<< "$d" | convert -size 960x$b xc: - -flatten "$indiciatxt"

    [[ $l ]] && append='+append'
    convert -gravity center "$append" "$indiciaimg" "$indiciatxt" "$indicia"
    rm "$indiciatxt"
}

_textbox() {
    b=960
    font=SF-Cartoonist-Hand-Bold
    read -r w pos colour pt x y text <<< $"960 center #333333 26 0 560 $metadata"
    [[ $l ]] && w=800 x=80
    h=$(identify -format "%@" <(convert -size ${w}x -gravity $pos -font "$font" -pointsize $pt caption:"$text" miff:-))
    h=${h#*x} h=${h%%+*}
    h=$(($h+40))
    (($h < 400)) && y=$((960-$h))
    (($h > 400)) && y=560 && b=$(($h-400+$b))

#    convert -size ${w}x -gravity $pos -font "$font" -pointsize $pt caption:"$text" foo.png && exit
}

_options() {
    args=()
    unset l

    while [[ $1 ]]; do
        case "$1" in
            -l) l=1             ;;
            -h) _u; exit 0      ;;
            --) shift; [[ $* ]] && args+=( "$@" ); break ;;
            -*) _u; exit 0      ;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    (( ${#args[@]} != 3 )) && { _u; exit 1; }
    cid=${args[0]}
    metadata=${args[1]}
    indiciaimg=${args[2]}
}

_options "$@"

append='-append'
indiciatxt=tmp.indicia-text.png
indicia=$cid-indicia.png
_check
_textbox
_indicia
