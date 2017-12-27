(function ($) {
    "use strict";

    function reader_click_callback(e) {
        e.preventDefault();
        var iframe;

        if ($('#zco_book_container_iframe').length) {
            iframe = $('#zco_book_container_iframe');
        } else {
            iframe = $('<iframe id="zco_book_container_iframe"></iframe>');
            iframe.css({
                "border": "none",
                "box-shadow": "0 3px 9px rgba(0,0,0,.5)",
                "box-sizing": "border-box",
                "height": "100%",
                "left": "0",
                "position": "fixed",
                "top": "0",
                "width": "100%",
                "z-index": "99",
            });

            $('body').append(iframe);
        }

        var src = '/embed' + $(this).attr('href');
        iframe.attr('src', src);
        iframe.show();
        iframe.focus();
    }

    $(document).ready(function(){
        $('.zco_book_reader').on('click', reader_click_callback);
        setTimeout( function() {
            $('.zco_book_reader').off('click').on('click', reader_click_callback);
        }, 1000);

        $(window).on("message onmessage", function(e) {
            if (e.originalEvent.origin !== "https://zco.mx" && e.originalEvent.origin !== "https://dev.zco.mx") {
                console.log('Invalid event origin: %o', e.originalEvent.origin);
                return;
            }

            if (e.originalEvent.data == 'close') {
                var iframe = $('#zco_book_container_iframe');
                iframe.hide();
                iframe.attr('src', '');
            }
        });
    });
}(window.jQuery));

