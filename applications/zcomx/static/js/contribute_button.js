(function( $ ) {
    $.fn.contribute_button = function (options) {
        var settings = $.extend(
            true,
            {},
            $.fn.contribute_button.defaults,
            options
        );

        var methods = {
            _load: function(elem) {
                $(elem).click(function (e) {
                    var url = $(elem).attr('href');
                    var dialog = new BootstrapDialog({
                        title: '<img src="/zcomx/static/images/zco.mx-logo-small.png">',
                        message: $('<div></div>').load(url),
                        buttons: [{
                            id: 'close_button',
                            label: 'Close',
                            cssClass: 'btn_close',
                            action : function(dialog){
                                dialog.close();
                            }
                        }],
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

    $.fn.contribute_button.defaults = {
        cssClass: 'contribute_modal',
    };

}( jQuery ));
