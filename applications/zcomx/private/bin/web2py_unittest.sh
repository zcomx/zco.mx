#!/bin/bash

WEB2PY_ROOT=/srv/http/zco.mx
UTIL_APP=zcomx

script=${0##*/}
_u() { cat << EOF
usage: $script [options] [package name|path] [class] [method]

This script runs web2py unittests.
    --dump      Dump output into ~/tmp/dumps/
    --editor    Open test file and module/controller into editor.
    --quick     Do not run slow tests.
    --force     Run all tests including those requiring terminal.
    --max-diff  Set maxDiff=None so all error differences are displayed.
    -l          List test classes in package.
    -v          Verbose.
    -h          Print this help message.

EXAMPLE:
    $script                                     # Run all tests

    # Run tests for one application.
    $script applications.myapp
    $script applications/myapp

    # Run tests in specific script.
    $script applications.myapp.tests.test_mytest
    $script applications/myapp/tests/test_mytest.py

    # Run tests in specific class
    $script applications.myapp.tests.test_mytest.TestClass
    $script applications/myapp/tests/test_mytest.py TestClass

    # Run tests in specific method
    $script applications.myapp.tests.test_mytest.TestClass.test__mytest
    $script applications/myapp/tests/test_mytest.py TestClass test__mytest
EOF
}

rm_errors() {
    local app=$1
    find $WEB2PY_ROOT/applications/$app/errors -mindepth 1 -not -name '.gitignore' -exec rm '{}' \;
}

list_test_classes() {
    local package=$1
    # Convert applications.app.tests.test_file to applications/app/tests/test_file.py
    # Remove trailing '.py' if it exists
    # Replace '.' with '/', then append '.py'
    unset append
    if [[ $package =~ \.py$ ]]; then
        append=1
        package=${package%.py}
    fi
    package=${package//./\/}
    [[ $append ]] && package="$package.py"
    grep -r 'class Test' $package | sed 's/:class / /' | sed 's/^class //g' | sed 's/(unittest.TestCase)://g'
}

__mi() { __v && echo -e "===: $*" ;}
__me() { echo -e "===> ERROR: $*" >&2; }
__v()  { ${verbose-false} ;}

_options() {
    # set defaults
    args=()
    unset class
    unset list
    unset method
    unset package
    unset dump
    unset editor
    unset force
    unset max_diff
    unset quick
    unset verbose

    while [[ $1 ]]; do
        case "$1" in
            -l) list=1          ;;
        --dump) dump=1          ;;
      --editor) editor=1        ;;
       --force) force=1         ;;
       --quick) quick=1         ;;
    --max-diff) max_diff=1      ;;
            -v) verbose=true    ;;
            -h) _u; exit 0      ;;
            --) shift; [[ $* ]] && args+=( "$@" ); break;;
            -*) _u; exit 1      ;;
             *) args+=( "$1" )  ;;
        esac
        shift
    done

    ((${#args[@]} > 0)) && { package=${args[0]}; }
    ((${#args[@]} > 1)) && { class=${args[1]}; }
    ((${#args[@]} > 2)) && { method=${args[2]}; }
    [[ ! $list ]] && ((${#args[@]} > 3)) && { _u; exit 1; }
}

_options "$@"

flags=''
[[ $dump ]] && flags="$flags --dump"
[[ $force ]] && flags="$flags --force"
[[ $quick ]] && flags="$flags --quick"
[[ $max_diff ]] && flags="$flags --max-diff"
__v && flags="$flags -v"

export PYTHONPATH=$WEB2PY_ROOT:$WEB2PY_ROOT/gluon
cd $WEB2PY_ROOT

if [[ $list ]]; then
    list_test_classes $package
    exit 0
fi

py=$WEB2PY_ROOT/applications/$UTIL_APP/private/bin/python_web2py.sh

if [[ ! $MYSQL_TCP_PORT ]]; then
    export MYSQL_TCP_PORT=3307
fi

if [[ ! $package ]]; then
    # Test everything
    for x in $(ls -1 /srv/http/applications); do rm_errors "$x"; done
    $py applications/$UTIL_APP/private/bin/unittest.py discover $flags -p applications .
else
    # Strip trailing slash from package
    package=${package%/}
    if [[ ${package%/*} == 'applications' ]]; then
        # Run all tests for an application
        pattern=${package#*/}
        rm_errors "$pattern"
        tmp_app=${package#*/}
        app=${tmp_app%%/*}
        $py applications/$app/private/bin/unittest.py discover $flags -p $pattern .
    else
        tmp_app=${package#*/}
        app=${tmp_app%%/*}
        rm_errors "$app"

        [[ $editor ]] && flags="$flags --editor $package"
        # Convert applications/app/tests/test_file.py to applications.app.tests.test_file
        # Replace '/' with '.', remove trailing '.py'
        package=${package//\//.}
        package=${package%.py}
        [[ $class ]] && package="$package.$class"
        [[ $method ]] && package="$package.$method"
        $py applications/$app/private/bin/unittest.py $flags --app $app $package
    fi
fi
