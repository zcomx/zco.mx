#!/bin/bash

_mi() { local e=$?; [[ -t 1 ]] && local g=$LIGHTGREEN coff=$COLOUROFF; printf "$g===: %s$coff\n" "$@"; return "$e"; }
_mw() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===: %s$coff\n" "$@"; return 1; } >&2
_me() { [[ -t 1 ]] && local r=$RED coff=$COLOUROFF; printf "$r===> ERROR: %s$coff\n" "$@"; exit 1; } >&2
_v()  { ${verbose-false}; }

_u() {
    script=${0##*/}; cat << EOF
usage: $script [-v] [-d] /path/to/file.cbz

    -d  Remove cbz from file-sharing networks
    -v  Verbose

    -h  This message

This script will add and remove a cbz file from zco.mx file-sharing
networks.  It will also update the torrent for the cartoonist as well as
the zco.mx torrent.  The script assumes the torrent file is in a
relative directory to the cbz file, eg:
  /srv/http/zco.mx/web2py/applications/zcomx/private/var/tor/zco.mx/J/JordanCrane/Uptight 001 (2006) (103.zco.mx).cbz.torrent
  /srv/http/zco.mx/web2py/applications/zcomx/private/var/cbz/zco.mx/J/JordanCrane/Uptight 001 (2006) (103.zco.mx).cbz

EOF
}

_check() {
    _v && _mi "cbz:    $cbz"
    _v && _mi "cbzdir: $cbzdir"
    _v && _mi "tor:    $tor"
    for i in lstor rtxmlrpc tmux tthsum; do command -v "$i" &>/dev/null || _me "$i not installed"; done
    if [[ ! $d ]]; then
        [[ -f $cbz ]] || _me 'cbz file not found'
        [[ -f $tor ]] || _me 'torrent file not found'
    fi
}

_del_tor() {
    hash=$(lstor -qo __hash__ "$tor.loaded")
    _v && _mi "hash:   $hash"
    rtxmlrpc -q d.close=$hash &>/dev/null && sleep 1
    rtxmlrpc -q d.erase=$hash &>/dev/null && sleep 1
    rtxmlrpc -q system.file_status_cache.prune && sleep 1
    [[ -f $tor.loaded ]] && rm "$tor.loaded"
}

_add_tor() {
    cp -alf "$tor" "${tor}.loaded" || _me "Error"   ## Create Hardlink of .torrent file
    _v && _mi "rtxmlrpc -q load.start '' ${tor}.loaded d.directory_base.set=\"$cbzdir\" d.priority.set=2"
    rtxmlrpc -q load.start '' "${tor}.loaded" "d.directory_base.set=\"$cbzdir\"" "d.priority.set=2" && sleep 1
}

_cbz() {
    _check
    _v && _mi "Update cbz torrent"
    _del_tor
    [[ ! $d ]] && _add_tor
    _v && echo
    return 0
}

_car() {
    _v && _mi "Update cartoonist torrent"
    #/srv/http/zco.mx/web2py/applications/zcomx/private/var/tor/zco.mx/J/JordanCrane/Uptight 001 (2006) (103.zco.mx).cbz.torrent
    #/srv/http/zco.mx/web2py/applications/zcomx/private/var/tor/zco.mx/J/JordanCrane (103.zco.mx).torrent
    tor="${tor%/*} (${tor##*\(}"; tor=${tor/.cbz./.}        ## Set cartoonist torrent filename
    _check
    _del_tor
    _add_tor
    _v && echo
}

_all() {
    _v && _mi "Update zco.mx torrent"
    cbzdir=/srv/http/zco.mx/web2py/applications/zcomx/private/var/cbz/zco.mx
    tor=/srv/http/zco.mx/web2py/applications/zcomx/private/var/tor/zco.mx/zco.mx.torrent
    _check
    _del_tor
    _add_tor
    _v && echo
}

_announce() {
    tmux send-keys -t ncdc M-r    ## refresh ncdc
    [[ $d ]] && return

    _v && _mi "Announce dc"
    #   cbz="/srv/http/zco.mx/web2py/applications/zcomx/private/var/cbz/zco.mx/J/JordanCrane/Uptight 001 (2006) (103.zco.mx).cbz"
    read -r tth _ < <(tthsum -- "$cbz")
    fs=$(stat -c '%s' "$cbz")           ## file size
    fn=${cbz##*/}                       ## filename, eg Uptight 001 (2006) (103.zco.mx).cbz

    msg1=${cbz##*zco.mx/[A-Z0-9]/}      ## output: JordanCrane/Uptight 001 (2006) (103.zco.mx).cbz
    msg1=${msg1%).*}                    ## output: JordanCrane/Uptight 001 (2006) (103.zco.mx
    msg1=$(sed -r 's/([a-z]+)([A-Z][a-z]+)/\1 \2/g' <<< "$msg1")    ## output: Jordan Crane/Uptight 001 (2006) (103.zco.mx
    msg1=${msg1/\// | }                 ## output: Jordan Crane | Uptight 001 (2006) (103.zco.mx
    end=${msg1##*(}
    msg1="${msg1%)*}) | http://$end"    ## output: Jordan Crane | Uptight 001 (2006) | http://103.zco.mx
    msg2="magnet:?xt=urn:tree:tiger:$tth&xl=$fs&dn=${fn// /+}"  ## magnet:?xt=urn:tree:tiger:IENTQM74OF2UH7DMMNHKLBU6HGW2ZO4DUGAQATY&xl=44519398&dn=Gutter+Magic+001+(2013)+(Digital)+(Darkness-Empire).cbr

    tmux send-keys -t ncdc M-2 Enter     && sleep 0.2
    tmux send-keys -t ncdc "$msg1" Enter && sleep 0.2
    tmux send-keys -t ncdc "$msg2" Enter && sleep 0.2

    #    announce twitter
    #    announce tumblr
    #       http://code.google.com/p/tumblr-cli/
}

_options() {
    args=()
    unset d

    while [[ $1 ]]; do
        case "$1" in
            -d) d=1             ;;
            -v) verbose=true    ;;
            -h) _u; exit 0      ;;
            --) shift; [[ $* ]] && args+=( "$@" ); break;;
            -*) _u; exit 0      ;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    (( ${#args[@]} != 1 )) && { _u; exit 1; }
    cbz=${args[0]}
    cbzdir=${cbz%/*}
    tor=${cbz/\/cbz\//\/tor\/}.torrent
}

_options "$@"

_cbz
_car
_all
_announce
