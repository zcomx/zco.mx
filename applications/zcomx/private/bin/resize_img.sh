#!/bin/bash

d1='cbz 1600 2560 625 1600
    web  750 1200 625 1600'
#    tbn  140  168 882 1133'

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2

_u() { script=${0##*/}; cat << EOF
usage: $script [file1, file2... fileN]

This script resizes GIF, JPG and PNG files.  If the input image is large
enough, the script outputs images suitable for cbz files, for use on the
web as well as thumbnails.

EOF
}

_check_files() {
    r1='GIF|JPEG|PNG'
    identify "$i" &>/dev/null || _me "$i is not an image or image is corrupt"
    identify -regard-warnings -format "%g" "$i" &>/dev/null || _me "$i is corrupt"
    ext=$(identify -format '%m' "$i"[0] 2>/dev/null)
    [[ $ext =~ $r1 ]] || _me "$i is not a GIF, PNG or JPEG image"
}

_colourmap() {
    [[ -f colourmap.png ]] && { nf=${nf%.*}.png; return; }      ## skip colourmap if it exists
    unset cm
    if [[ ${f##*.} == jpg || ${f##*.} == gif ]]; then
        nc=$(identify -format '%k' "$f"[0])
        (( $nc > 256 )) && return
        cj="+dither -colors $nc"
        nf=${nf/.jpg/.png}
        nf=${nf/.gif/.png}
    else
        return
    fi

    colours=$(convert "$f" $cj -unique-colors txt: | awk -v _=\" 'NR>1 {print "xc:"_$4_}')
    eval convert -size 1x1 $colours +append colourmap.png
    cm="-remap colourmap.png"
}

_resize() {
    _colourmap      ## if jpg and < 256, use a colourmap
    while read -r fmt t1 t2 arl arh; do
        IFS=x read -r w h < <(identify -format '%P' "$f"[0])
        (( $w == $h && $w < $t1 )) && continue      ## if square image is too small, then continue
        (( $w < $h && $w < $t1 ))  && continue      ## if portrait image is too small, then continue
        (( $w > $h && $w < $t2 ))  && continue      ## if landscape image is too small, then continue

        cs=RGB
        nf=$fmt-${f##*/}

        meta=$(identify -format '%[colorspace] %m' "$f"[0])
        [[ $meta == sRGB* || $meta == Gray* ]]  || _mw "$f colorspace is not sRGB: $meta"
        [[ $meta == CMYK* ]] && cs=CMYK             ## convert CMYK to RBG
        [[ $meta == *GIF  ]] && nf=${nf%.*}.png     ## convert gif to png
        [[ $meta == *PNG  ]] && nf=${nf%.*}.png     ## set ext to png
        [[ $meta == *JPEG ]] && nf=${nf%.*}.jpg     ## set ext to jpg

        ap=$(( $w*1000/$h ))
        if (( $ap > 940 && $ap < 1050 )); then              ## square: resize to large threshold (small for tbn)
            [[ $fmt == cbz ]] && res=2080x                  ## (2560+1600)/2
            [[ $fmt == web ]] && res=975x                   ## (1200+ 750)/2
#            [[ $fmt == tbn ]] && res=140x
        elif [[ $fmt == web ]]; then
            (( $w < $h )) && res=${t1}x || res=${t2}x       ## if portrait, else landscape
        else
            if (( $ap > $arl && $ap < $arh )); then         ## if aspect ratio is between the limits
                (( $w < $h )) && res=${t1}x || res=x$t1     ##  resize small threshold (t1)
            else                                            ## else
                (( $w < $h )) && res=x$t2 || res=${t2}x     ##  resize large threshold (t2)
            fi
        fi

        filter=RobidouxSharp
        convert \( "$f[0]" -quiet -define jpeg:preserve-settings -colorspace $cs \) \
            \( -clone 0 -gamma 1.666666666666666 -filter $filter -distort Resize $res -gamma 0.6 \) \
            \( -clone 0 -filter $filter -distort Resize $res \) -delete 0 \
            \( -clone 1 -colorspace gray -auto-level \) -compose over -composite \
            -set colorspace $cs -colorspace sRGB -depth 8 $cm \
            +set date:modify +set date:create +set Software  +repage "$nf"

#        IFS=x read -r nw nh < <(identify -format '%P' "$nf")
#        printf "%s %04s %04s %s\n" $fmt $nw $nh $nf
    done <<< "$d1"
    rm colourmap.png &>/dev/null
    return 0
}

_rename() {
    ext=$(identify -format '%m' "$j"[0] 2>/dev/null)
    [[ $ext == JPEG ]] && ext=jpg
    ## there is no reason to store a gif; conver to png
    [[ $ext == GIF ]] && { ext=png; convert "$j[0]" "${j%.*}.$ext"; rm "$j"; j=${j%.*}.$ext; }
    ori=${j##*/}; ori=ori-${ori%.*}.${ext,,}    ## strip off path and ensure ext is correct
    mv "$j" "$ori"  ## add 'ori-' to filename and mv file to current dir
    return 0
}


grep -q ^processor /proc/cpuinfo || _me "Could not determind number of CPUs"
cpu=$(grep -c ^processor /proc/cpuinfo)
export MAGICK_THREAD_LIMIT=$cpu

for i in convert identify; do command -v "$i" &>/dev/null || _me "$i not installed"; done
(( $# == 0 )) && { _u; exit 1; }
for i in "$@"; do _check_files; done
for f in "$@"; do _resize; done
for j in "$@"; do _rename; done


#####################################
# NARROW
# 11x16 1600x t:0.625  0.625 > && < 1.6 && resize width_x || resize height_x
# 16x11 x1600 t:1.6    0.625 > && < 1.6 && resize x_width || resize x_height
#
# SHORT
# 10x17 x2560
# 17x10 2560x
