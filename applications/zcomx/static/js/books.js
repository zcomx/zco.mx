(function ($) {
    "use strict";

    //utils
    $.fn.modalize_utils = {
        /**
        * classic JS inheritance function
        */
        inherit: function (Child, Parent) {
            var F = function() { };
            F.prototype = Parent.prototype;
            Child.prototype = new F();
            Child.prototype.constructor = Child;
            Child.superclass = Parent.prototype;
        },

        toTitleCase: function (str) {
            return str.replace(/\b\w/g, function (txt) { return txt.toUpperCase(); });
        }
    };
}(window.jQuery));


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
                } else {
                    var link_func = 'book_' + this.$action;
                    var href_parts = this.$element.attr('href').split('/');
                    if (href_parts[2] === link_func) {
                        this.$book_id = href_parts[3];
                    }
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
                title += $.fn.modalize_utils.toTitleCase(this.$action) + ': ';
            }
            title += this.get_book_title();
            return title;
        },

        onhidden: function(dialog) {
            this.$dialog = null;
        },

        onshow: function(dialog) {
            dialog.getModalDialog().addClass('modal-lg');
        },

        update: function() {
            var that = this;
            var url = '/zcomx/profile/book_crud.json';

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
    $.fn.modalize_utils.inherit(AddModalize, Modalize);
    $.extend(AddModalize.prototype, {
        onhidden: function(dialog) {
            this.$book_id = dialog.getData('book_id');
            if (this.$book_id) {
                var url = '/profile/book_edit/' + this.$book_id;
                var modal = new EditModalize(null, 'edit', {
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
    $.fn.modalize_utils.inherit(DeleteModalize, Modalize);
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
    $.fn.modalize_utils.inherit(EditModalize, Modalize);
    $.extend(EditModalize.prototype, {
        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Upload Images',
                cssClass: 'btn-default pull-left btn_upload',
                action : function(dialog){
                    dialog.close();
                    var url = '/profile/book_pages/' + that.$book_id;
                    var modal = new UploadModalize(null, 'upload', {
                        'book_id': that.$book_id,
                        'book_title': that.$book_title,
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
    $.fn.modalize_utils.inherit(ReleaseModalize, Modalize);
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
    $.fn.modalize_utils.inherit(UploadModalize, Modalize);
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
        bootstrap_dialog_options: {},
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
            if ($('#' + target).length) {
                web2py_component(url, target);
            }
        });
    }

    function reorder_pages(dialog) {
        var page_ids = [];
        var book_id = 0;
        dialog.getModalBody().find('tr.template-download').each(function(index, elem) {
            if (!book_id) {
                book_id = $(elem).data('book_id');
            }
            page_ids.push($(elem).data('book_page_id'));
        });

        var url = '/zcomx/profile/book_pages_reorder'
        url = url + '/' + book_id;

        var that = $(this);

        $('#fileupload').addClass('fileupload-processing');

        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
            data: {book_page_ids: page_ids},
        }).always(function () {
            $('#fileupload').removeClass('fileupload-processing');
        // }).done(function (result) {
        // Reordering not critical, ignore results
        })
    }

    $.fn.set_modal_events = function() {
        $('.modal-add-btn').modalize('add', {
            'onhidden': display_book_lists,
            'title': 'Add book'
        });
        $('.modal-delete-btn').modalize('delete', {'onhidden': display_book_lists});
        $('.modal-edit-btn').modalize('edit', {'onhidden': display_book_lists});
        $('.modal-release-btn').modalize('release', {
            'onhidden': display_book_lists,
            'bootstrap_dialog_options':  {
                'onshown': function(dialog) {
                    $('.btn_release').prop('disabled', !release_enabled).toggleClass('disabled', !release_enabled);
                }
            }
        });
        $('.modal-upload-btn').modalize('upload', {
            'onhidden': reorder_pages,
            'bootstrap_dialog_options':  {'closable': false},
        });
    }

    $(document).ready(function(){
        display_book_lists();
    });
}());