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
                true,
                {},
                $.fn.image_upload.defaults,
                options
            );
            this.load(element);
        },

        abort_send: function() {
            $('button.btn.cancel').each(function(indx) {
                $(this).click();
            });
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
            var return_msg = raw_msg;

            $.each(translation, function(old_msg, new_msg) {
                var cmp_msg = raw_msg.substring(0, old_msg.length);
                if (cmp_msg === old_msg) {
                    return_msg = new_msg;
                    return false;
                }
            });
            return return_msg;
        },

        failed_callback: function(e, data) {
            return;
        },

        finished_callback: function(e, data) {
            return;
        },

        img_count: function() {
            return this.$element.find('.template-download').length;
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
            var fileupload_opts = $.extend(
                {},
                {
                    url: that.$url,
                    change: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('change triggered, data: %o', data);
                        that.change_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.change)) {
                            that.options.post_callbacks.change(e, data);
                        }
                    },
                    completed: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('completed triggered, data: %o', data);
                        that.completed_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.completed)) {
                            that.options.post_callbacks.completed(e, data);
                        }
                    },
                    destroyed: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('destroyed triggered, data: %o', data);
                        that.deleted_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.destroyed)) {
                            that.options.post_callbacks.destroyed(e, data);
                        }
                    },
                    failed: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('failed triggered, data: %o', data);
                        that.failed_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.failed)) {
                            that.options.post_callbacks.failed(e, data);
                        }
                    },
                    finished: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('finished triggered, data: %o', data);
                        if (that.options.message_elem) {
                            that.options.message_elem.hide();
                        }
                        if (that.options.loading_gif_elem) {
                            that.options.loading_gif_elem.hide();
                        }
                        that.finished_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.finished)) {
                            that.options.post_callbacks.finished(e, data);
                        }
                    },
                    processstart: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('processstart triggered, data: %o', data);
                        if (that.options.message_elem) {
                            that.options.message_elem.show();
                        }
                        if (that.options.loading_gif_elem) {
                            that.options.loading_gif_elem.show();
                        }
                        that.processstart_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.processstart)) {
                            that.options.post_callbacks.processstart(e, data);
                        }
                    },
                    processdone: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('processdone triggered, data: %o', data);
                        that.processdone_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.processdone)) {
                            that.options.post_callbacks.processdone(e, data);
                        }
                    },
                    stopped: function(e, data) {
                        that.options.debug_fileupload_listeners && console.log('stopped triggered, data: %o', data);
                        that.stopped_callback(e, data);
                        if ($.isFunction(that.options.post_callbacks.stopped)) {
                            that.options.post_callbacks.stopped(e, data);
                        }
                    },
                    _error_scrub: function(raw_msg) {
                        return that.error_scrub(raw_msg);
                    }
                },
                that.options.fileupload_options
            );

            $(elem).fileupload(fileupload_opts);

            if (that.options.debug_fileupload_listeners) {
                $(elem).on('fileuploaddestroy', function (e, data) {
                    console.log('destroy triggered, data: %o', data);
                });
                $(elem).on('fileuploadsubmit', function(e, data) {
                    console.log('submit triggered, data: %o', data);
                });
                $(elem).on('fileuploaddone', function(e, data) {
                    console.log('done triggered');
                });
                $(elem).on('fileuploadfail', function(e, data) {
                    console.log('fail triggered, data: %o', data);
                });
                $(elem).on('fileuploadalways', function(e, data) {
                    console.log('always triggered, data: %o', data);
                });
                $(elem).on('fileuploadprogress', function(e, data) {
                    console.log('progress triggered, data: %o', data);
                });
                $(elem).on('fileuploadprogressall', function(e, data) {
                    console.log('progressall triggered, data: %o', data);
                });
                $(elem).on('fileuploadstart', function(e, data) {
                    console.log('start triggered');
                });
                $(elem).on('fileuploadstop', function(e, data) {
                    console.log('stop triggered');
                });
                $(elem).on('fileuploadpaste', function(e, data) {
                    console.log('paste triggered, data: %o', data);
                });
                $(elem).on('fileuploaddrop', function(e, data) {
                    console.log('drop triggered, data: %o', data);
                });
                $(elem).on('fileuploaddragover', function(e) {
                    console.log('dragover triggered');
                });
                $(elem).on('fileuploadchunkbeforesend', function(e, data) {
                    console.log('chunkbeforesend triggered, data: %o', data);
                });
                $(elem).on('fileuploadchunksend', function(e, data) {
                    console.log('chunksend triggered, data: %o', data);
                });
                $(elem).on('fileuploadchunkdone', function(e, data) {
                    console.log('chunkdone triggered, data: %o', data);
                });
                $(elem).on('fileuploadchunkfail', function(e, data) {
                    console.log('chunkfail triggered, data: %o', data);
                });
                $(elem).on('fileuploadchunkalways', function(e, data) {
                    console.log('chunkalways triggered, data: %o', data);
                });
                $(elem).on('fileuploadprocessstart', function(e, data) {
                    console.log('processstart triggered');
                });
                $(elem).on('fileuploadprocess', function(e, data) {
                    console.log('process triggered, data: %o', data);
                });
                $(elem).on('fileuploadprocessfail', function(e, data) {
                    console.log('processfail triggered, data: %o', data);
                });
                $(elem).on('fileuploadprocessalways', function(e, data) {
                    console.log('processalways triggered, data: %o', data);
                });
                $(elem).on('fileuploadprocessstop', function(e, data) {
                    console.log('processstop triggered');
                });
                $(elem).on('fileuploaddestroyfailed', function(e, data) {
                    console.log('destroyfailed triggered, data: %o', data);
                });
                $(elem).on('fileuploadadded', function(e, data) {
                    console.log('added triggered, data: %o', data);
                });
                $(elem).on('fileuploadsend', function(e, data) {
                    console.log('send triggered, data: %o', data);
                });
                $(elem).on('fileuploadsent', function(e, data) {
                    console.log('sent triggered, data: %o', data);
                });
                $(elem).on('fileuploadstarted', function(e) {
                    console.log('started triggered');
                });
            }

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

        processdone_callback: function(e, data) {
            return;
        },

        processstart_callback: function(e, data) {
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
            that.set_sort_link();
            that.set_close_button();
            this.set_tooltip_text();
        },

        deleted_callback: function(e, data) {
            ImageUpload.prototype.deleted_callback.apply(this);
            this.set_arrows();
            this.set_sort_link();
            this.set_close_button();
            this.set_tooltip_text();
        },

        failed_callback: function(e, data) {
            $('.fileupload-process').hide();
        },

        loaded_callback: function(e) {
            $('span.preview').removeClass('hidden');
            this.set_tooltip_text();
        },

        set_arrows: function() {
            $('.reorder-arrow').removeClass('arrow-muted');
            $('.reorder-arrow-up').first().addClass('arrow-muted');
            $('.reorder-arrow-down').last().addClass('arrow-muted');
        },

        set_close_button: function() {
            var button_text = this.img_count() > 0 ? 'Post On Web' : 'Close';
            $('.btn_upload_close').first().text(button_text);
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

        set_sort_link: function() {
            var that = this;
            var link_container = $('#sort_link_container');
            var sort_link = $('#sort_by_filename_link');
            if (this.img_count() > 0) {
                link_container.show();
                sort_link.on('click', function() {
                    that.sort_by_filename();
                });
                if(sort_link.next('span.info_icon_container').length === 0) {
                    var tooltip_text = $('#sort_link_tooltip').html();
                    var icon = $.fn.zco_utils.tooltip(
                        'sort_by_filename_link',
                        tooltip_text
                    );
                    sort_link.after(icon);
                }
            } else {
                link_container.hide();
            }
        },

        set_tooltip_text: function(elem) {
            var icon_container = $('.fileupload-buttonbar').find('.info_icon_container').first();
            if (this.img_count() > 0) {
                $('#tooltip_text').hide();
                icon_container.show();
            } else {
                $('#tooltip_text').show();
                icon_container.hide();
            }
        },

        sort_by_filename: function() {
            var filename_to_tr = {}
            $('form#fileupload p.name').each(function(idx, e) {
                var link = $(e).find('a');
                filename_to_tr[link.text()] = this.closest('tr');
            })

            var sorted_filenames = Object.keys(filename_to_tr).sort();
            $.each(sorted_filenames, function(idx, filename) {
                var tr = filename_to_tr[filename];
                $('form#fileupload p.name').eq(idx).closest('tr').before(tr);
            })
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
            $('#creator_img').data().profile_creator_image.clear_message();
        },

        completed_callback: function(e, data) {
            this.show_buttons();
        },

        deleted_callback: function(e, data) {
            this.show_buttons();
        },

        failed_callback: function(e, data) {
            $('.fileupload-process').hide();
            this.show_buttons();
        },

        loaded_callback: function(e) {
            var that = this;
            $(document).on('click', '#remove_button', function(e) {
                that.clear_error();
            });
            this.show_buttons();
        },

        processstart_callback: function(e, data) {
            $('.btn_submit').prop('disabled', true);
            $('.fileinput-button').hide();
        },

        show_buttons: function() {
            if ($('#remove_button').length > 0) {
                $('#remove_button').hide();
                $('#upload_button').text('Change Image');
            } else {
                $('#upload_button').text('Upload');
                $('.no_photo_section').show().css(
                    {display: 'inline-block'}
                );
            }
            $('.btn_submit').prop('disabled', false);
            $('.fileinput-button').show();
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
            if (data.result.files.length && data.result.files[0].error === undefined) {
                // Remove all but last template-download div in filesContainer
                var filesList = this.$element.fileupload('option', 'filesContainer');
                var files = filesList.find('.template-download');
                for (var i=0; i < (files.length - 1); i++) {
                    files[i].remove();
                }
                this.reload_previews();
            }
        },

        deleted_callback: function(e, data) {
            this.show_buttons();
            this.reload_previews()
        },

        reload_previews: function() {
            if ($('.previews_section').data) {
                $('.previews_section').data('indicia_preview').load();
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
        debug_fileupload_listeners: false,
        fileupload_options: {
            autoUpload: true,
            limitConcurrentUploads: 3,
            previewMaxWidth:  170,
            previewMaxHeight: 170,
        },
        loading_gif_elem: null,
        message_elem: null,
        post_callbacks: {
            change: null,
            completed: null,
            destroyed: null,
            failed: null,
            finished: null,
            processdone: null,
            processstart: null,
            stopped: null,
        },
    };

}(window.jQuery));
