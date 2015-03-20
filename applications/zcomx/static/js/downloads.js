(function( $ ) {
    "use strict";

    $.fn.download_button = function (options) {
        var settings = $.extend(
            true,
            {},
            $.fn.download_button.defaults,
            options
        );

        var methods = {
            _load: function(elem) {
                $(elem).click(function (e) {
                    var url = $(elem).attr('href');
                    var dialog = new BootstrapDialog({
                        title: ' ',
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

    $.fn.download_button.defaults = {
        cssClass: 'download_modal',
    };
}(window.jQuery));

(function( $ ) {
    "use strict";

    $.fn.log_download_link = function () {

        var methods = {
            _load: function(elem) {
                var self = this;
                $(elem).click(function (e) {
                    console.log('click registed');
                    $.ajax({
                        url: '/downloads/download_click_handler',
                        type: 'POST',
                        dataType: 'json',
                        data: $.param( $(elem).data() ),
                        success: function (data, textStatus, jqXHR) {
                            // this isn't critical
                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            // this isn't critical
                        }
                    });
                })
            },
        };

        return this.each( function(index, elem) {
            var $this = $(this);
            methods._load.apply(this, [elem]);
        });
    };
}(window.jQuery));
