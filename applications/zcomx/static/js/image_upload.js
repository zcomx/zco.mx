(function ($) {
    "use strict";

    var ImageUpload = function (element, type, url, options) {
        this.init(element, type, url, options);
    };

    ImageUpload.prototype = {
        constructor: ImageUpload,
        init: function (element, type, url, options) {
            this.$element = $(element);
            this.$type = type;
            this.$url = url;
            this.options = $.extend(
                {},
                $.fn.image_upload.defaults,
                options
            );
            this.load(element);
        },

        change_callback: function(e, data) {
            return;
        },

        completed_callback: function(e, data) {
            return;
        },

        deleted_callback: function(e, data) {
            return;
        },

        error_scrub: function(raw_msg) {
            var translation = {
                'Request Entity Too Large': 'The file is too large (max 500 MB).',
                'Unsupported file type.': 'Invalid file or unsupported file type.',
                'cannot identify image file': 'Invalid file or unsupported file type.',
            }
            if (translation.hasOwnProperty(raw_msg)) {
                return translation[raw_msg];
            }
            return raw_msg;
        },

        img_error: function(image) {
            var that = this;
            var tries = $(image).data('retries');
            if (isNaN(tries)) {
                tries = 0;
            }
            if (tries >= 5) {
                image.onerror = "";
            }
            $(image).data('retries', tries + 1);
            setTimeout( function() {
                that.reload_img(image);
            }, 2000);
            return true;
        },

        load: function (elem) {
            var that = this;
            $(elem).fileupload({
                url: that.$url,
                autoUpload: true,
                limitConcurrentUploads: 3,
                previewMaxWidth:  170,
                previewMaxHeight: 170,
                change: function(e, data) {
                    that.change_callback(e, data);
                },
                completed: function(e, data) {
                    that.completed_callback(e, data);
                },
                destroyed: function(e, data) {
                    that.deleted_callback(e, data);
                },
                stopped: function(e, data) {
                    that.stopped_callback(e, data);
                },
                _error_scrub: function(raw_msg) {
                    return that.error_scrub(raw_msg);
                }
            });


            /* that.display_download(); */
            $(elem).addClass('fileupload-processing');
            $.ajax({
                // Uncomment the following to send cross-domain cookies:
                //xhrFields: {withCredentials: true},
                url: $(elem).fileupload('option', 'url'),
                dataType: 'json',
                context: $(elem)[0]
            }).always(function () {
                $(elem).removeClass('fileupload-processing');
            }).done(function (result) {
                $(elem).fileupload('option', 'done')
                    .call(this, $.Event('done'), {result: result});
                that.loaded_callback(this);
            });
        },

        loaded_callback: function(e) {
            return;
        },

        reload_img: function(elem) {
            var src = $(elem).attr('src');
            if (src) {
                var dtr = src.indexOf('?') == -1 ? '?' : '&';
                $(elem).attr({'src': src + dtr + '_=' + (new Date()).getTime()});
            }
        },

        stopped_callback: function(e, data) {
            /* Some preview images don't load, reload */
            var that = this;
            $('span.preview a img').each(function(idx, e) {
                var image = this;
                $(this).attr(
                    {'onerror': function(image) {that.img_error(this)}}
                );
                that.reload_img(image);
            });
            $('span.preview').removeClass('hidden');
        }
    };

    var BookPageImageUpload = function (element, type, url, options) {
        this.init(element, type, url, options);
    }
    $.fn.zco_utils.inherit(BookPageImageUpload, ImageUpload);
    $.extend(BookPageImageUpload.prototype, {

        completed_callback: function(e, data) {
            var that = this;
            data.context.find('.reorder-arrow').each(function(index, elem) {
                that.set_reorder_links(elem);
            });
            that.set_arrows();
        },

        deleted_callback: function(e, data) {
            this.set_arrows();
        },

        loaded_callback: function(e) {
            $('span.preview').removeClass('hidden');
        },

        set_arrows: function() {
            $('.reorder-arrow').removeClass('arrow-muted');
            $('.reorder-arrow-up').first().addClass('arrow-muted');
            $('.reorder-arrow-down').last().addClass('arrow-muted');
        },

        set_reorder_links: function(elem) {
            var obj = this;
            $(elem).click(function(e) {
                e.preventDefault();
                obj.$element.addClass('fileupload-processing');
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
                        obj.set_arrows();
                    });
                });
                obj.$element.removeClass('fileupload-processing');
            });
        },

    });

    var CreatorImageUpload = function (element, type, url, options) {
        this.init(element, type, url, options);
    }
    $.fn.zco_utils.inherit(CreatorImageUpload, ImageUpload);
    $.extend(CreatorImageUpload.prototype, {

        clear_error: function() {
            $('.cancel_container').remove();
            $('.file_error_container').remove();
        },

        change_callback: function(e, data) {
            /* remove any existing */
            $('button.delete').trigger('click');
        },

        completed_callback: function(e, data) {
            this.show_buttons();
        },

        deleted_callback: function(e, data) {
            this.show_buttons();
        },

        loaded_callback: function(e) {
            var that = this;
            $(document).on('click', '#change_button', function(e) {
                that.clear_error();
                $('input[type=file]').trigger('click');
                e.preventDefault();
            });
            $(document).on('click', '#remove_button', function(e) {
                that.clear_error();
            });
            $(document).on('click', '.fileinput-button', function(e) {
                that.clear_error();
            });
            this.show_buttons();
        },

        show_buttons: function() {
            if ($('#change_button').length > 0) {
                $('.no_photo_section').hide();
            }
            else {
                $('.no_photo_section').show().css(
                    {display: 'inline-block'}
                );
            }
        },

    });

    var IndiciaImageUpload = function (element, type, url, options) {
        this.init(element, type, url, options);
    }
    $.fn.zco_utils.inherit(IndiciaImageUpload, CreatorImageUpload);
    $.extend(IndiciaImageUpload.prototype, {
        change_callback: function(e, data) {
            return;
            /* $('button.delete').trigger('click'); */
        },

        completed_callback: function(e, data) {
            CreatorImageUpload.prototype.completed_callback.apply(this)
            if (data.result.files[0].error === undefined) {
                // Remove all but last template-download div in filesContainer
                var filesList = this.$element.fileupload('option', 'filesContainer');
                var files = filesList.find('.template-download');
                for (var i=0; i < (files.length - 1); i++) {
                    files[i].remove();
                }
                this.reload_previews()
            }
        },

        deleted_callback: function(e, data) {
            CreatorImageUpload.prototype.deleted_callback.apply(this)
            this.reload_previews()
        },

        reload_previews: function() {
            var orientations = ['portrait', 'landscape'];
            for (var i = orientations.length - 1; i >= 0; i--) {
                var url = '/zcomx/login/indicia_preview.load/' + orientations[i];
                var target = orientations[i];
                web2py_component(url, target);
            }
        },

    });

    $.fn.image_upload = function (type, url, options) {
        var datakey = 'image_upload';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = null;
                switch(type) {
                    case 'book_page':
                        obj = new BookPageImageUpload(this, type, url, options);
                        break;
                    case 'creator':
                        obj = new CreatorImageUpload(this, type, url, options);
                        break;
                    case 'indicia':
                        obj = new IndiciaImageUpload(this, type, url, options);
                        break;
                    default:
                        obj = new ImageUpload(this, type, url, options);
                }
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.image_upload.defaults = {
        highlight: '#FFFF80'
    };

}(window.jQuery));
