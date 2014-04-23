(function( $ ) {

    $.fn.image_upload = function (url, options) {
        var settings = $.extend(true, {}, $.fn.image_upload.defaults, {url: url}, options);

        var methods = {
            _clear_download: function(context) {
                table = context.closest('table')
                table.find('tr.template-download').each(function(e) {
                    $(this).remove();
                });

            },

            _completed_callback: function(e, data) {
                data.context.find('.reorder-arrow').each(function(index, elem) {
                    methods._set_reorder_links(elem);
                });
                methods._set_arrows();
            },

            _deleted_callback: function(e, data) {
                methods._set_arrows();
            },

            _display_download: function() {
                $('#fileupload').addClass('fileupload-processing');
                $.ajax({
                    // Uncomment the following to send cross-domain cookies:
                    //xhrFields: {withCredentials: true},
                    url: $('#fileupload').fileupload('option', 'url'),
                    dataType: 'json',
                    context: $('#fileupload')[0]
                }).always(function () {
                    $(this).removeClass('fileupload-processing');
                }).done(function (result) {
                    $(this).fileupload('option', 'done')
                        .call(this, $.Event('done'), {result: result});
                });
            },

            _run: function(elem) {
                $(elem).fileupload({
                    url: settings.url,
                    completed: methods._completed_callback,
                    destroyed: methods._deleted_callback,
                    });

                methods._display_download();
            },

            _set_arrows: function() {
                $('.reorder-arrow').removeClass('arrow-muted');
                $('.reorder-arrow-up').first().addClass('arrow-muted');
                $('.reorder-arrow-down').last().addClass('arrow-muted');
            },

            _set_reorder_links: function(elem) {
                $(elem).click(function(e) {
                    e.preventDefault();
                    $('#fileupload').addClass('fileupload-processing');
                    var that = $(this);
                    var tr = that.closest('tr');
                    tr.fadeOut(400, function() {
                        if (that.data('dir') === 'down') {
                            tr.next().after(tr);
                        }
                        else {
                            tr.prev().before(tr);
                        }
                        tr.fadeIn(400, function() {
                            methods._set_arrows();
                        });
                    });
                    $('#fileupload').removeClass('fileupload-processing');
                });
            },
        };

        return this.each( function(index, elem) {
            methods._run.apply(this, [elem]);
        });
    };

    $.fn.image_upload.defaults = {
    };

}( jQuery ));
