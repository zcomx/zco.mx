(function ($) {
    "use strict";
    var iframe_wrapper_z_index = 19999;
    var iframe_z_index = iframe_wrapper_z_index + 1;
    var overlay_z_index = iframe_z_index + 1;
    var overlay_bg_colour = 'white';

    function create_iframe_wrapper() {
        var iframe_wrapper;

        if ($('#zco_book_container_wrapper').length) {
            iframe_wrapper = $('#zco_book_container_wrapper');
        } else {
            iframe_wrapper = $('<div id="zco_book_container_wrapper"></div>');
            iframe_wrapper.css({
                "overflow-y": "scroll",
                "-webkit-overflow-scrolling": "touch",
                "position": "fixed",
                "left": "0",
                "top": "0",
                "bottom": "0",
                "top": "0",
                "width": "100%",
                "z-index": iframe_wrapper_z_index,
            });
        }
        return iframe_wrapper;
    }

    function create_iframe() {
        var iframe;

        if ($('#zco_book_container_iframe').length) {
            iframe = $('#zco_book_container_iframe');
        } else {

            iframe = $('<iframe id="zco_book_container_iframe" allowfullscreen="true">Sorry, your browser does not support iframes.</iframe>');
            iframe.css({
                "border": "none",
                "box-shadow": "0 3px 9px rgba(0,0,0,.5)",
                "box-sizing": "border-box",
                "height": "100%",
                "margin": "0",
                "padding": "0",
                "width": "100%",
            });
        }
        return iframe;
    }

    function create_overlay() {
        var overlay = null;
        if ($('#zco_book_reader_overlay').length) {
            overlay = $('#zco_book_reader_overlay');
        } else {
            overlay = $('<div id="zco_book_reader_overlay"></div>');
            overlay.css({
                "background-color": overlay_bg_colour,
                "border": "none",
                "box-sizing": "border-box",
                "display": "none",
                "height": "100%",
                "left": "0",
                "opacity": 1,
                "position": "fixed",
                "top": "0",
                "width": "100%",
                "z-index": overlay_z_index,
            });
            var loading_gif = $('<div class="loading_gif"></div>');
            loading_gif.css({
                "background": 'url("https://zco.mx/zcomx/static/images/loading/66x66.gif") center no-repeat',
                "background-size": "contain",
                "display": "inline-block",
                "height": "66px",
                "width": "66px",
                "position": "fixed",
                "left": "50%",
                "top": "50%",
                "margin-left": "-33px",
            });
            overlay.append(loading_gif);
            $('body').append(overlay);
        }
        return overlay;
    }

    function embed_url(url) {
        // Prepend url with "/embed"
        var target_url = parseURL(url);
        var is_dev = target_url.host.match('^dev\.') ? true : false;

        var zbr_origin = 'zbr_origin=' + encodeURIComponent(target_url.protocol + '://' + target_url.host);
        var query_joiner = target_url.query ? '&' : '?';

        var zco_reader_url = {
            'protocol': 'https',
            'host': is_dev ? 'dev.zco.mx' : 'zco.mx',
            'path': '/embed' + target_url.path.replace(/^\/zcomx\//, '/' ),
            'query': target_url.query + query_joiner + zbr_origin,
            'hash': target_url.hash,
        }

        var src = zco_reader_url.protocol + '://'
            + zco_reader_url.host
            + zco_reader_url.path
            + zco_reader_url.query
            + (zco_reader_url.hash ? '#' + zco_reader_url.hash : '')
        return src;
    }

    function goFullscreen(e) {
        if(e.requestFullscreen) {
            e.requestFullscreen();
        } else if(e.mozRequestFullScreen) {
            e.mozRequestFullScreen();
        } else if(e.webkitRequestFullscreen) {
            e.webkitRequestFullscreen();
        } else if(e.msRequestFullscreen) {
            e.msRequestFullscreen();
        }
    }

    function parseURL(url) {
        // Source: https://j11y.io/javascript/parsing-urls-with-the-dom/
        var a =  document.createElement('a');
        a.href = url;
        return {
            source: url,
            protocol: a.protocol.replace(':',''),
            host: a.hostname,
            port: a.port,
            query: a.search,
            params: (function(){
                var ret = {},
                    seg = a.search.replace(/^\?/,'').split('&'),
                    len = seg.length, i = 0, s;
                for (;i<len;i++) {
                    if (!seg[i]) { continue; }
                    s = seg[i].split('=');
                    ret[s[0]] = s[1];
                }
                return ret;
            })(),
            file: (a.pathname.match(/\/?([^/\?#]+)$/i) || [,''])[1],
            hash: a.hash.replace('#',''),
            path: a.pathname.replace(/^([^/])/,'/$1'),
            relative: (a.href.match(/tps?:\/\/[^\/]+(.+)/) || [,''])[1],
            segments: a.pathname.replace(/^\//,'').split('/')
        };
    }

    function reader_click_callback(e) {
        e.preventDefault();
        var ua = $.fn.zco_utils.userAgent();
        var overlay = create_overlay();
        var iframe_wrapper = create_iframe_wrapper();
        var iframe = create_iframe();

        iframe_wrapper.append(iframe);
        $('body').append(iframe_wrapper);

        overlay.css({
            "background-color": overlay_bg_colour,
        });
        overlay.fadeIn();
        iframe.off('load').on('load', function(e) {
            overlay.fadeOut();
            if (! ua.is_mobile) {
                $($('[id="zco_book_container_iframe"]')[0].contentWindow.document).on('keyup', function (e) {
                    if (e.originalEvent.keyCode === 70) {
                        var el = iframe[0];
                        goFullscreen(el);
                    }
                });
            }
        });

        var src = embed_url($(e.currentTarget).attr('href'));

        iframe.show();
        iframe.attr('src', src);
        var timeout_delay = ua.is_apple_mobile ? 1000 : 0;
        setTimeout( function() {
            iframe_wrapper.show();
            iframe.focus();
        }, timeout_delay);
    }

    $(document).ready(function(){
        if ($('.zco_book_reader').length) {
            $('.zco_book_reader').on('click', reader_click_callback);
        } else {
            setTimeout( function() {
                $('.zco_book_reader').on('click', reader_click_callback);
            }, 1000);
        }

        $(window).on("message onmessage", function(e) {
            if (e.originalEvent.origin !== "https://zco.mx" && e.originalEvent.origin !== "https://dev.zco.mx") {
                console.log('Invalid event origin: %o', e.originalEvent.origin);
                return;
            }

            var data = e.originalEvent.data;
            var iframe = $('#zco_book_container_iframe');
            var iframe_wrapper = $('#zco_book_container_wrapper');

            if (data.action == 'close') {
                iframe_wrapper.hide();
                iframe.hide();
                iframe.attr('src', '');
                $('body').focus();
            } else if (data.action == 'switch') {
                var overlay = create_overlay();
                overlay.css({
                    "background-color": data.bg_colour,
                });
                overlay.fadeIn();
                iframe.off('load').on('load', function(e) {
                    overlay.fadeOut();
                });
                iframe.attr('src', data.src);
            }
        });
    });
}(window.jQuery));

