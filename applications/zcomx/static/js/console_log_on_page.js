(function ($) {
    "use strict";

    var console_log_on_page = document.getElementById('console_log_on_page');
    if (typeof(console_log_on_page) == 'undefined' || console_log_on_page == null) {
        var d = document.createElement('div')
        d.setAttribute('id', 'console_log_on_page');
        d.setAttribute('style', 'z-index: 9999909; border: 1px solid black; position: absolute; top: 400px; left: 0; width: 50%; height: 8em; overflow: auto;');
        document.body.appendChild(d);
        console_log_on_page = document.getElementById('console_log_on_page');

    }
    console.origLog = console.log;
    console.log = function(arg1, arg2) {
        if (arguments.length == 2) {
            arg1 = arg1.replace('%o', JSON.stringify(arg2));
        }
        var p = document.createElement('div')
        p.innerHTML = arg1;
        console_log_on_page.appendChild(p);
        console_log_on_page.scrollTop = console_log_on_page.scrollHeight;
    }
    console.log('Console log overridden');
    window.onerror = function(msg, url, line)
    {
        console.log('msg: ' + msg);
        console.log('url: ' + url);
        console.log('line: ' + line);
    };
}(window.jQuery));

