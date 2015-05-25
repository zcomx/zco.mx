(function( $ ) {
    "use strict";

    $.fn.rss_button = function (options) {
        var settings = $.extend(
            true,
            {},
            $.fn.rss_button.defaults,
            options
        );

        var methods = {
            _load: function(elem) {
                $(elem).click(function (e) {
                    var url = $(elem).attr('href');
                    var dialog = new BootstrapDialog({
                        title: 'Reader Notifications',
                        message: $('<div></div>').load(url),
                        buttons: [],
                        cssClass: settings.cssClass,
                    });
                    dialog.open();
                    e.preventDefault();
                })
            },
        };

        return this.each( function(index, elem) {
            var $this = $(this);
            methods._load.apply(this, [elem]);
        });
    };

    $.fn.rss_button.defaults = {
        cssClass: 'rss_modal',
    };

}(window.jQuery));
