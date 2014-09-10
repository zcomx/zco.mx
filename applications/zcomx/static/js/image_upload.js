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
                    $('span.preview').removeClass('hidden');
                });
            },

            _error_scrub: function(raw_msg) {
                translation = {
                    'Request Entity Too Large': 'The file is too large (max 500 MB).',
                    'Unsupported file type.': 'Invalid file or unsupported file type.',
                }
                if (translation.hasOwnProperty(raw_msg)) {
                    return translation[raw_msg];
                }
                return raw_msg;
            },

            _img_error: function(image) {
                var tries = $(image).data('retries');
                if (isNaN(tries)) {
                    tries = 0;
                }
                if (tries >= 5) {
                    image.onerror = "";
                }
                $(image).data('retries', tries + 1);
                setTimeout( function() {
                    methods._reload_img(image);
                }, 2000);
                return true;
            },

            _reload_img: function(elem) {
                console.log('_reload_img elem: %o', elem);
                var src = $(elem).attr('src');
                var dtr = src.indexOf('?') == -1 ? '?' : '&';
                $(elem).attr({'src': src + dtr + '_=' + (new Date()).getTime()});
            },

            _run: function(elem) {
                $(elem).fileupload({
                    url: settings.url,
                    autoUpload: true,
                    limitConcurrentUploads: 3,
                    previewMaxWidth:  170,
                    previewMaxHeight: 170,
                    completed: methods._completed_callback,
                    destroyed: methods._deleted_callback,
                    stopped: methods._stopped_callback,
                    _error_scrub: methods._error_scrub,
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

            _stopped_callback: function(e, data) {
                /* Some preview images don't load, reload */
                $('span.preview a img').each(function(idx, e) {
                    $(this).attr({'onerror': "methods._img_error(this)"});
                    methods._reload_img(this);
                });
                $('span.preview').removeClass('hidden');
            },

        };

        return this.each( function(index, elem) {
            methods._run.apply(this, [elem]);
        });
    };

    $.fn.image_upload.defaults = {
    };

}( jQuery ));
