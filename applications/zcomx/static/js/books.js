(function ($) {
    "use strict";

    var Modalize = function (element, action, options) {
        this.init(element, action, options);
    };

    Modalize.prototype = {
        constructor: Modalize,

        add_click_listener: function() {
            this.$element.data(this.$click_listener_key, true);
        },

        buttons: function() {
            return [this.close_button()];
        },

        close_button: function(label) {
            label = typeof label !== 'undefined' ? label : 'Close';
            return {
                id: 'close_button',
                label: label,
                cssClass: 'btn_close',
                action : function(dialog){
                    dialog.close();
                }
            };
        },

        close_confirm: function(ignore) {
            if (typeof(ignore) == 'undefined') {
                ignore = 'changes'
            }
            var prompts = [];
            if (ignore === 'changes to metadata') {
                prompts.push('The "done" button must be clicked to save changes to metadata.');
            }
            prompts.push('Click "OK" to continue, ignore ' + ignore + ' and close the dialog.');
            prompts.push('Click "Cancel" if you changed your mind.');

            var reply = confirm(prompts.join('\n'));
            if (!reply) {
                return false;
            }
            return true;
        },

        display_message: function(title, msg, panel_class) {
            var panel_classes = [
                'panel-default',
                'panel-primary',
                'panel-success',
                'panel-info',
                'panel-warning',
                'panel-danger'
            ];

            var message_panel = $(this.options.message_panel);
            if (!message_panel) {
                return;
            }
            message_panel.find('.panel-title').first().text(title);
            message_panel.find('div.panel-body').first().html(msg);

            var new_class = panel_classes[0];
            if (panel_classes.indexOf(panel_class) >= 0) {
                new_class = panel_class;
            }
            for(var i = 0; i < panel_classes.length; i++) {
                message_panel.removeClass(panel_classes[i])
            }
            message_panel.addClass(new_class).show();
        },

        get_book_id: function() {
            if (!this.$book_id) {
                if (this.options.book_id) {
                    this.$book_id = this.options.book_id;
                }
                else if(this.$element.data('book_id')) {
                    this.$book_id = this.$element.data('book_id');
                }
            }
            return this.$book_id;
        },

        get_book_title: function() {
            if (!this.$book_title) {
                if (this.options.book_title) {
                    this.$book_title = this.options.book_title;
                } else {
                    var tr = this.$element.closest('tr');
                    var td = tr.find('td').first();
                    this.$book_title = td.text();
                }
            }
            return this.$book_title;
        },

        get_dialog: function() {
            var that = this;
            if (!this.$dialog) {
                var params = $.extend(
                    true,
                    {},
                    {
                        title: this.options.title || this.modal_title(),
                        message: this.get_message(),
                        onhide: function(dialog) {
                            var ok = that.onhide(dialog);
                            if ($.isFunction(that.options.onhide)) {
                                ok && that.options.onhide.call(that, dialog);
                            }
                            return ok;
                        },
                        onhidden: function(dialog) {
                            that.onhidden(dialog);
                            if ($.isFunction(that.options.onhidden)) {
                                that.options.onhidden.call(that, dialog);
                            }
                        },
                        onshow: function(dialog) {
                            that.onshow(dialog);
                            if ($.isFunction(that.options.onshow)) {
                                that.options.onshow.call(that, dialog);
                            }
                        },
                        onshown: function(dialog) {
                            that.onshown(dialog);
                            if ($.isFunction(that.options.onshown)) {
                                that.options.onshown.call(that, dialog);
                            }
                        },
                        buttons: this.buttons(),
                    },
                    this.options.bootstrap_dialog_options
                );
                this.$dialog = new BootstrapDialog(params);
            }
            return this.$dialog;
        },

        get_message: function() {
            return this.get_message_by_url(this.get_url());
        },

        get_message_by_url: function(url) {
            return $('<div></div>').load(url);
        },

        get_url: function() {
            if (!this.$url) {
                this.$url = this.options.url || this.$element.attr('href');
            }
            return this.$url;
        },

        has_click_listener: function() {
            return this.$element.data(this.$click_listener_key) ? true : false;
        },

        init: function (element, action, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.modalize.defaults,
                options
            );
            this.$action = action;
            this.$dialog = null;
            this.$book_id = null;
            this.$book_title = null;
            this.$click_listener_key = 'has_modal_' + action + '_btn';
            this.$page_count = 0;
            this.$url = null;

            var that = this;
            this.$book_id = that.get_book_id();
            this.$book_title = that.get_book_title();
            if (!that.has_click_listener()) {
                that.$element.on('click', function(event) {
                    that.get_dialog().open();
                    that.$element.data({'dialog': that.$dialog});
                    event.preventDefault();
                });
                that.add_click_listener();
            }
        },

        modal_title: function() {
            var title = '';
            if (this.$action) {
                title += $.fn.zco_utils.toTitleCase(this.$action) + ': ';
            }
            title += this.get_book_title();
            return title;
        },

        onhide: function(dialog) {
            if (dialog.$modalBody.find('.has-error').length) {
                if (! this.close_confirm('errors')) {
                    return false;
                }
            } else {
                var meta_container = dialog.$modalBody.find('#metadata_fields_container').first();
                if (meta_container.length && ! meta_container.hasClass('hidden')) {
                    if (! this.close_confirm('changes to metadata')) {
                        return false;
                    }
                }
            }
        },

        onhidden: function(dialog) {
            this.$dialog = null;
        },

        onshow: function(dialog) {
            dialog.getModalDialog().addClass('modal-lg');
        },

        onshown: function(dialog) {
            return;  // implement in sub-class
        },

        update: function() {
            console.log('update called');
            var that = this;
            var url = '/zcomx/login/book_crud.json';

            if (!this.$book_id) {
                return;
            }

            var message_panel = $(this.options.message_panel);
            if (message_panel) {
                message_panel.hide();
            }

            $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: {
                    '_action': this.$action,
                    'pk': this.$book_id,
                },
                success: function (data, textStatus, jqXHR) {
                    if (data.status === 'error') {
                        var msg = 'ERROR: ' + data.msg || 'Server request failed';
                        that.display_message('', msg, 'panel-danger');
                    }
                    else {
                        that.$dialog.close();
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var msg = 'ERROR: Unable to ' + action + ' record. Server request failed.';
                    that.display_message('', msg, 'panel-danger');
                }
            });
        },
    };

    var AddModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(AddModalize, Modalize);
    $.extend(AddModalize.prototype, {
        onhidden: function(dialog) {
            this.$book_id = dialog.getData('book_id');
            if (this.$book_id) {
                var url = '/zcomx/login/book_edit/' + this.$book_id;
                var modal = new EditOngoingModalize(null, 'edit', {
                    'book_id': this.$book_id,
                    'book_title': dialog.getData('title'),
                    'onhidden': this.options.onhidden,
                    'url': url
                });
                modal.get_dialog().open();
            }
            AddModalize.superclass.onhidden.call(this, dialog);
        }
    });

    var DeleteModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(DeleteModalize, Modalize);
    $.extend(DeleteModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Delete',
                cssClass: 'btn_delete',
                action : function(dialog){
                    that.update();
                }
            });
            btns.push(this.close_button('Cancel'));
            return btns;
        }
    });

    var EditModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(EditModalize, Modalize);

    var EditOngoingModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(EditOngoingModalize, EditModalize);
    $.extend(EditOngoingModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Upload Images',
                cssClass: 'btn-default pull-left btn_upload',
                action : function(dialog){
                    dialog.close();
                    // check if close preempted. Use bootstraps modal isShown
                    var bs_modal = dialog.getModal().data('bs.modal');
                    if (bs_modal && bs_modal.isShown) {
                        return;
                    }
                    var url = '/zcomx/login/book_pages/' + that.$book_id;
                    var modal = new UploadModalize(null, 'upload', {
                        'book_id': that.$book_id,
                        'book_title': that.$book_title,
                        'onhidden': that.options.onhidden,
                        'url': url
                    });
                    modal.get_dialog().open();
                }
            });
            btns.push(this.close_button());
            return btns;
        }
    });

    var ReleaseModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(ReleaseModalize, Modalize);
    $.extend(ReleaseModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Release',
                cssClass: 'btn_release',
                action : function(dialog){
                    that.update();
                }
            });
            btns.push(this.close_button('Cancel'));
            return btns;
        }
    });

    var UploadModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(UploadModalize, Modalize);
    $.extend(UploadModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Close',
                cssClass: 'btn_upload_close',
                action : function(dialog){
                    var close = true;
                    var activeUploads = $('#fileupload').fileupload('active');
                    if (activeUploads > 0) {
                        if (!confirm('Active uploads will be aborted.')) {
                            return false;
                        }
                        dialog.getModalBody().find('.template-upload').each(function() {
                            var data = $(this).data('data') || {};
                            if (data.jqXHR) {
                                data.jqXHR.abort();
                            }
                        });
                    }
                    dialog.close();
                }
            });
            return btns;
        },

        get_page_ids: function(dialog) {
            var page_ids = [];
            dialog.getModalBody().find('tr.template-download').each(function(index, elem) {
                page_ids.push($(elem).data('book_page_id'));
            });
            return page_ids;
        },

        onhidden: function(dialog) {
            this.post_image_upload(dialog);
            UploadModalize.superclass.onhidden.call(this, dialog);
        },

        onshown: function(dialog) {
            var page_ids = this.get_page_ids(dialog);
            this.$page_count = page_ids.length;
        },

        post_image_upload: function(dialog) {

            var url = '/zcomx/login/book_post_upload_session'
            url = url + '/' + this.$book_id;

            $('#fileupload').addClass('fileupload-processing');

            $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: {
                    book_page_ids: this.get_page_ids(dialog),
                    original_page_count: this.$page_count,
                },
            }).always(function () {
                $('#fileupload').removeClass('fileupload-processing');
            // }).done(function (result) {
                // Reordering not critical, ignore results
            })
        }
    });

    $.fn.modalize = function (action, options) {
        var datakey = 'modalize';
        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = null;
                switch(action) {
                    case 'add':
                        obj = new AddModalize(this, action, options);
                        break;
                    case 'delete':
                        obj = new DeleteModalize(this, action, options);
                        break;
                    case 'edit':
                        obj = new EditModalize(this, action, options);
                        break;
                    case 'edit_ongoing':
                        obj = new EditOngoingModalize(this, 'edit', options);
                        break;
                    case 'release':
                        obj = new ReleaseModalize(this, action, options);
                        break;
                    case 'upload':
                        obj = new UploadModalize(this, action, options);
                        break;
                    default:
                        obj = new Modalize(this, action, options);
                }
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.modalize.defaults = {
        book_id: null,
        book_title: null,
        bootstrap_dialog_options: {
            'closable': false,
        },
        message_panel: '#message_panel',
        onhidden: null,
        onshow: null,
        title: null,
        url: null,
    };

}(window.jQuery));

(function () {
    "use strict";

    function display_book_lists() {
        $.each(book_list_urls, function(key, url) {
            var target =  key + '_book_list';
            var target_elem =  $('#' + target);
            if (target_elem.length) {
                web2py_component(url, target);
                var container = target_elem.closest('.books_list_container');
                if (container.length) {
                    container.removeClass('hidden');
                }
            }
        });
    }

    $.fn.set_modal_events = function() {
        $('.modal-add-btn').modalize('add', {
            'onhidden': display_book_lists,
            'title': 'Add book'
        });
        $('.modal-delete-btn').modalize('delete', {'onhidden': display_book_lists});
        $('.modal-edit-btn').modalize('edit', {
            'onhidden': display_book_lists,
            'bootstrap_dialog_options':  {
                'closable': true,
                'closeByBackdrop': false,
                'closeByKeyboard': false,
            }
        });
        $('.modal-edit-ongoing-btn').modalize('edit_ongoing', {
            'onhidden': display_book_lists,
            'bootstrap_dialog_options':  {
                'closable': true,
                'closeByBackdrop': false,
                'closeByKeyboard': false,
            }
        });
        $('.modal-release-btn').modalize('release', {
            'onhidden': display_book_lists,
            'bootstrap_dialog_options':  {
                'onshown': function(dialog) {
                    $('.btn_release').prop('disabled', !release_enabled).toggleClass('disabled', !release_enabled);
                }
            }
        });
        $('.modal-upload-btn').modalize('upload', {
            'onhidden': display_book_lists,
        });
    }

    $(document).ready(function(){
        display_book_lists();
    });
}());
