(function ($) {
    "use strict";

    function hide_book_container(book_container, iframe) {
        book_container.hide();
        iframe.attr('src', '');
    }

    $(document).ready(function(){
        $('.zco_book_reader').on('click', function(e) {
            e.preventDefault();
            var book_container;
            var iframe;

            if ($('#zco_book_container').length) {
                book_container = $('#zco_book_container');
                iframe = $('#zco_book_container_iframe');
            } else {
                book_container = $('<div id="zco_book_container"></div>');
                book_container.css({
                    "display": "none",
                    "height": "100%",
                    "width": "100%",
                    "position": "fixed",
                    "top": "0",
                    "left": "0",
                    "z-index": "99",
                    "background": "rgba(0, 0, 0, 0.5)",
                    "padding": "1em",
                    "box-sizing": "border-box",
                });

                var button = $('<button class="close">×</button>');
                button.css({
                    "-webkit-appearance": "none",
                    "background": "0 0",
                    "border": "0",
                    "color": "#000",
                    "cursor": "pointer",
                    "filter": "alpha(opacity=20)",
                    "float": "right",
                    "font-size": "21px",
                    "font-weight": "700",
                    "line-height": "1",
                    "margin-right": "-0.8em",
                    "margin-top": "-0.8em",
                    "opacity": ".2",
                    "padding": "0",
                    "text-shadow": "0 1px 0 #fff",
                });
                book_container.append(button);

                iframe = $('<iframe id="zco_book_container_iframe"></iframe>');
                iframe.css({
                    "height": "100%",
                    "width": "100%",
                    "box-shadow": "0 3px 9px rgba(0,0,0,.5)",
                });

                book_container.append(iframe);
                $('body').append(book_container);
                book_container.on('click', function(e) {
                    hide_book_container(book_container, iframe);
                }).on('keyup', function(e) {
                    if (e.which == 27) {
                        e.preventDefault();
                        // ESC
                        hide_book_container(book_container, iframe);
                    }
                });
            }

            iframe.attr('src', $(this).attr('href'));
            book_container.show();
        });
    });
}(window.jQuery));

