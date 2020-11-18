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

        format: function(template, vars) {
            // Source: http://stackoverflow.com/users/98517/ianj
            vars = typeof vars === 'object' ? vars : Array.prototype.slice.call(arguments, 1);

            return template.replace(/\{\{|\}\}|\{(\w+)\}/g, function (m, n) {
                if (m == "{{") { return "{"; }
                if (m == "}}") { return "}"; }
                return vars[n];
            });
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
                    var $td = this.$element.closest('tr').find('td').first();
                    var $anchor = $td.find('a').first();
                    if ($anchor.length) {
                        this.$book_title = $.trim($anchor.text());
                    } else {
                        this.$book_title = $.trim($td.text());
                    }
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
                        cssClass: 'modal_dialog_' + this.$action,
                        title: this.modal_title(),
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
            var data = {
                book_title: this.get_book_title(),
                action: $.fn.zco_utils.toTitleCase(this.$action),
            }
            return this.format(this.options.title_template, data);
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
            return;  // implement in sub-class
        },

        onshown: function(dialog) {
            return;  // implement in sub-class
        },

        reload_button: function(label, css_class) {
            var that = this;
            label = typeof label !== 'undefined' ? label : 'Reload';
            css_class = typeof css_class !== 'undefined' ? css_class : 'reload_button';
            var options = $.extend(
                {},
                that.options,
                {
                    'book_id': that.$book_id,
                    'book_title': that.$book_title,
                    'url': that.get_url(),
                }
            );
            return {
                label: label,
                cssClass: css_class,
                action: function(dialog){
                    dialog.close();
                    var modal = new that.constructor(null, that.$action, options)
                    modal.get_dialog().open();
                }
            };
        },

        update: function() {
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

    var CompleteModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(CompleteModalize, Modalize);
    $.extend(CompleteModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Complete',
                cssClass: 'btn_complete',
                action : function(dialog){
                    that.update();
                }
            });
            btns.push(this.close_button('Cancel'));
            return btns;
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

    var FileshareModalize = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(FileshareModalize, Modalize);
    $.extend(FileshareModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Release',
                cssClass: 'btn_fileshare',
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
        abort: function(dialog) {
            dialog.getModalBody().find('.template-upload').each(function() {
                var data = $(this).data('data') || {};
                if (data.jqXHR) {
                    data.jqXHR.abort();
                }
            });
        },

        buttons: function() {
            var that = this;
            var btns = [];
            btns.push(that.reload_button('Refresh', 'reload_button hidden'));
            btns.push({
                label: 'Cancel',
                cssClass: 'btn_upload_cancel',
                action : function(dialog){
                    that.abort(dialog);
                    dialog.close();
                }
            });
            btns.push({
                label: 'Close',
                cssClass: 'btn_upload_close',
                action : function(dialog){
                    that.post_on_web(dialog);
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

        onhide: function(dialog) {
            this.abort(dialog);
            UploadModalize.superclass.onhide.call(this, dialog);
        },

        onshow: function(dialog) {
            /* Disable buttons while loading */
            dialog.enableButtons(false);
            UploadModalize.superclass.onshow.call(this, dialog);
        },

        onshown: function(dialog) {
            var that = this;
            /* Delay or quick close gets invalid page_count */
            setTimeout( function() {
                var page_ids = that.get_page_ids(dialog);
                that.$page_count = page_ids.length;
                dialog.enableButtons(true);
            }, 1000);
        },

        post_on_web: function(dialog) {
            var that = this;

            $('#fileupload').addClass('fileupload-processing');
            $('.btn_upload_close').addClass('disabled');

            var message_panel = $(this.options.message_panel);
            if (message_panel) {
                message_panel.hide();
            }

            var activeUploads = $('#fileupload').fileupload('active');
            if (activeUploads > 0) {
                if (!confirm('Active uploads will be aborted.')) {
                    $('#fileupload').removeClass('fileupload-processing');
                    $('.btn_upload_close').removeClass('disabled');
                    return false;
                }
                that.abort(dialog);
            }

            var url = '/zcomx/login/book_post_upload_session'
            url = url + '/' + this.$book_id;

            var error_msg = null;

            $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: {
                    book_page_ids: this.get_page_ids(dialog),
                    original_page_count: this.$page_count,
                },
                success: function (data, textStatus, jqXHR) {
                    if (data.status === 'error') {
                        error_msg = 'ERROR: ' + data.msg || 'Server request failed';
                    }
                    else {
                        that.$dialog.close();
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    error_msg = 'ERROR: Unable to ' + action + ' record. Server request failed.';
                }
            }).always(function () {
                $('.btn_upload_close').removeClass('disabled');
                $('#fileupload').removeClass('fileupload-processing');
                if (error_msg) {
                    that.display_message('', error_msg, 'panel-danger');
                    $('.btn_upload_close').addClass('hidden');
                    $('.reload_button').removeClass('hidden');
                }
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
                    case 'complete':
                        obj = new CompleteModalize(this, action, options);
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
                    case 'fileshare':
                        obj = new FileshareModalize(this, action, options);
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
        title_template: '<span class="modal_title_action">{action}:</span> <span class="modal_title_book_title">{book_title}</span>',
        url: null,
    };

}(window.jQuery));

(function () {
    "use strict";

    function display_book_lists() {
        $.each(book_list_urls, function(key, url) {
            var target = key + '_book_list';
            var target_elem = $('#' + target);
            if (target_elem.length) {
                web2py_component(url, target);
                var container = target_elem.closest('.books_list_container');
                if (container.length) {
                    container.removeClass('hidden');
                }
            }
        });
    }

    $.fn.set_modal_events = function(options) {
        $('.modal-add-btn').modalize('add',
            $.extend({}, options, {
                'onhidden': display_book_lists,
                'title_template': 'Add Book'
            })
        );
        $('.modal-delete-btn').modalize('delete',
            $.extend({}, options, {'onhidden': display_book_lists})
        );
        $('.modal-edit-btn').modalize('edit',
            $.extend({}, options, {
                'onhidden': display_book_lists,
                'bootstrap_dialog_options':  {
                    'closable': true,
                    'closeByBackdrop': false,
                    'closeByKeyboard': false,
                },
            })
        );
        $('.modal-edit-ongoing-btn').modalize('edit_ongoing',
            $.extend({}, options, {
                'onhidden': display_book_lists,
                'bootstrap_dialog_options':  {
                    'closable': true,
                    'closeByBackdrop': false,
                    'closeByKeyboard': false,
                },
            })
        );
        $('.modal-complete-btn').modalize('complete',
            $.extend({}, options, {
                'onhidden': display_book_lists,
                'bootstrap_dialog_options':  {
                    'onshown': function(dialog) {
                        $('.btn_complete').prop('disabled', !complete_enabled).toggleClass('disabled', !complete_enabled);
                        $('.close_current_dialog').on('click', function(e) {
                            dialog.close();
                        });
                    }
                },
                'title_template': 'STEP 1: Set a Book as Completed \n {book_title}',
            })
        );
        $('.modal-fileshare-btn').modalize('fileshare',
            $.extend({}, options, {
                'onhidden': display_book_lists,
                'bootstrap_dialog_options':  {
                    'onshown': function(dialog) {
                        $('.btn_fileshare').prop('disabled', !fileshare_enabled).toggleClass('disabled', !fileshare_enabled);
                        $('.close_current_dialog').on('click', function(e) {
                            dialog.close();
                        });
                    }
                },
                'title_template': 'STEP 2: Release Book on Filesharing Networks \n {book_title}',
            })
        );
        $('.modal-upload-btn').modalize('upload',
            $.extend({}, options, {
                'onhidden': display_book_lists,
                'bootstrap_dialog_options': {
                    'closable': true,
                },
            })
        );
    }

    $(document).ready(function(){
        display_book_lists();
    });
}());
