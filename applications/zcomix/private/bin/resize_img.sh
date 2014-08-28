#!/bin/bash

r1='GIF|JPEG|PNG'

d1='cbz 1600 2560 625 1600
    web  750 1200 625 1600
    tbn  140  168 882 1133'

#d1='cbz 1600 2560 625 1600'
#d1='web  750 1200 625 1600'
#d1='tbn  140  168 882 1133'

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [file1, file2... fileN]

This script resizes and optimizes GIF, JPG and PNG files.  If the input
image is large enough, the script outputs images suitable for cbz files,
for use on the web as well as thumbnails.

EOF
}

_check_files() {
    identify "$i" &>/dev/null || _me "$i is not an image or image is corrupt"
    identify -verbose "$i" 2>&1 | grep -Pq '^identify: Corrupt' && _me "$i is corrupt"
    ext=$(identify -format '%m' "$i"[0] 2>/dev/null)
    [[ $ext =~ $r1 ]] || _me "$i is not a GIF, PNG or JPEG image"
}

_resize() {
    while read -r fmt t1 t2 arl arh; do
        IFS=x read -r w h < <(identify -format '%P' "$f"[0])
        (( $w < $t2 && $h < $t2 )) && continue      ## if image is too small, then continue

        cs=RGB
        nf=$fmt-${f##*/}

        meta=$(identify -format '%[colorspace] %m' "$f"[0])
        [[ $meta != sRGB* ]]  && _mw "$f colorspace is not sRGB: $meta"
        [[ $meta == CMYK* ]]  && cs=CMYK             ## convert CMYK to RBG
        [[ $meta == *GIF  ]]  && nf=${nf%.*}.png     ## convert gif to png
        [[ $meta == *PNG  ]]  && nf=${nf%.*}.png     ## set ext to png
        [[ $meta == *JPEG  ]] && nf=${nf%.*}.jpg     ## set ext to jpg

        ap=$(( $w*1000/$h ))
        ## square: resize to large threshold (small for tbn)
        if (( $ap > 940 && $ap < 1050 )); then
            res=$t2
            [[ $fmt == tbn ]] && res=$t1
        elif ! (( $ap > 940 && $ap < 1050 )); then
            ## if aspect ratio is between the limits && resize small threshold || resize large threshold
            (( $ap > $arl && $ap < $arh )) && res=$t1 || res=$t2
        else
            _me "wtf?: $f $fmt $s $l $filter $nf"
        fi

        [[ $res == $t1 ]] && { (( $w < $h )) && res=${res}x || res=x$res; }
        [[ $res == $t2 ]] && { (( $w < $h )) && res=x$res || res=${res}x; }
        filter="-gamma 1.333333333333333 -filter Catrom -resize $res -gamma .75 -colorspace sRGB +repage"
#        echo convert "$f[0]" -quiet -colorspace "$cs" $filter "$nf"
        convert "$f[0]" -quiet -colorspace "$cs" $filter "$nf"

#        IFS=x read -r nw nh < <(identify -format '%P' "$nf")
#        printf "%s %04s %04s %s\n" $fmt $nw $nh $nf
    done <<< "$d1"
}

_rename() {
    ext=$(identify -format '%m' "$i"[0] 2>/dev/null)
    [[ $ext == JPEG ]] && ext=jpg
    k=${j##*/}      ## strip off path
    mv "$j" "ori-${k%.*}.${ext,,}"      ## ensure ext is correct
}

command -v convert  &>/dev/null || { _me "convert not installed"; }
command -v identify &>/dev/null || { _me "identify not installed"; }
#command -v jpegtran &>/dev/null || { _me "jpegtran not installed"; }

(( $# == 0 )) && { _u; exit 1; }
for i in $@; do _check_files; done
for f in $@; do _resize; done
for j in $@; do _rename; done

## [ ] unit tests
## [ ] add image optimization and stripping -- vips?

#####################################

#NARROW
#11x16 1600x t:0.625  0.625 > && < 1.6 && resize width_x || resize height_x
#16x11 x1600 t:1.6    0.625 > && < 1.6 && resize x_width || resize x_height
#
#SHORT
#10x17 x2560
#17x10 2560x
