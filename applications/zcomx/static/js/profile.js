(function ($) {
    "use strict";

    var ProfileNameEdit = function (element, options) {
        this.init(element, options);
    };

    ProfileNameEdit.prototype = {
        constructor: ProfileNameEdit,
        init: function (element, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.profile_name_edit.defaults,
                options
            );
            this.image_squarer = null;
            this.load();
        },

        load: function () {
            var that = this;
            if(!this.$element.hasClass('disabled')) {
                this.$element.on('click', function (e) {
                    var url = that.$element.attr('href');
                    var dialog = new BootstrapDialog({
                        title: 'profile: Edit name',
                        message: $('<div></div>').load(url),
                        buttons: that.buttons(that.$element),
                        cssClass: that.options.cssClass,
                        onshown: function(dialog) {
                            that.clear_message();
                        },
                    });
                    dialog.open();
                    e.preventDefault();
                })
            }
        },

        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'Submit',
                cssClass: 'btn_submit',
                action : function(dialog){
                    that.update(dialog);
                }
            });
            btns.push({
                id: 'close_button',
                label: 'Cancel',
                cssClass: 'btn_close',
                action : function(dialog){
                    dialog.close();
                }
            });
            return btns;
        },

        clear_message: function() {
            var message_panel = $('#name_edit_message_panel').first();
            if (!message_panel.length > 0) {
                return;
            }
            message_panel.hide();
        },

        display_message: function(msg, panel_class) {
            var panel_classes = [
                'panel-default',
                'panel-primary',
                'panel-success',
                'panel-info',
                'panel-warning',
                'panel-danger'
            ];

            var message_panel = $('#name_edit_message_panel').first();
            if (!message_panel.length > 0) {
                return;
            }
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

        update: function(dialog) {
            var that = this;
            var url = '/zcomx/login/profile_name_edit_crud.json';
            var name = $('.name_edit_input').val();
            var data = {'name': name}
            that.clear_message();
            $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: data,
                success: function (data, textStatus, jqXHR) {
                    if (data.status === 'error') {
                        var msg = 'ERROR: ' + data.msg || 'Server request failed';
                        that.display_message(msg, 'panel-danger');
                    }
                    else {
                        that.$element.text(name);
                        if (data.name_url) {
                            $('a#name_url').each(function(indx) {
                                $(this).text(data.name_url);
                            });
                        }
                        dialog.close();
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var msg = 'ERROR: Unable to ' + action + ' record. Server request failed.';
                    that.display_message(msg, 'panel-danger');
                }
            });
        },
    };

    $.fn.profile_name_edit = function (options) {
        var datakey = 'profile_name_edit';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new ProfileNameEdit(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.profile_name_edit.defaults = {
        cssClass: 'profile_name_edit_modal',
    };

}(window.jQuery));

(function ($) {
    "use strict";

    var ProfileCreatorImage = function (element, options) {
        this.init(element, options);
    };

    ProfileCreatorImage.prototype = {
        constructor: ProfileCreatorImage,
        init: function (element, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.profile_creator_image.defaults,
                options
            );
            this.load();
        },

        load: function () {
            var that = this;
            this.get_image_html();
            if(!this.$element.hasClass('disabled')) {
                this.$element.on('click', function (e) {
                    var url = that.$element.children('a').first().attr('href');
                    var dialog = new BootstrapDialog({
                        title: 'profile: Upload image',
                        message: $('<div></div>').load(url),
                        buttons: that.buttons(),
                        cssClass: that.options.cssClass,
                        onshown: function(dialog) {
                            that.clear_message();
                        },
                    });
                    dialog.open();
                    e.preventDefault();
                })
            }
        },

        buttons: function() {
            var that = this;
            var btns = [];
            btns.push({
                label: 'OK',
                cssClass: 'btn_submit',
                action : function(dialog){
                    var params = {};
                    if (that.image_squarer) {
                        params = that.image_squarer.get_adjustment();
                    }
                    that.update('ok', params);
                    that.get_image_html();
                    dialog.close();
                }
            });
            btns.push({
                id: 'close_button',
                label: 'Cancel',
                cssClass: 'btn_close',
                action : function(dialog){
                    that.update('cancel');
                    dialog.close();
                }
            });
            return btns;
        },

        clear_message: function() {
            var message_panel = $('#creator_image_message_panel').first();
            if (!message_panel.length > 0) {
                return;
            }
            message_panel.hide();
        },

        display_message: function(msg, panel_class) {
            var panel_classes = [
                'panel-default',
                'panel-primary',
                'panel-success',
                'panel-info',
                'panel-warning',
                'panel-danger'
            ];

            var message_panel = $('#creator_image_message_panel').first();
            if (!message_panel.length > 0) {
                return;
            }
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

        get_image_html: function() {
            var that = this;
            that.update('get', {}, function(data) {
                that.$element.html(data.html);
                that.on_get_image_html();
            });
        },

        on_get_image_html: function() {
            var img = this.$element.find('img');
            var src = img.attr('src');
            var regex = new RegExp(this.options.placeholder_img_name);
            var remove_container = $('#' + this.options.remove_container_id);
            if (src.match(regex)) {
                remove_container.hide();
            } else {
                remove_container.show();
            }
        },

        set_image_squarer: function(image_squarer) {
            this.image_squarer = image_squarer;
        },

        update: function(action, data, success_callback) {
            var that = this;
            var url = '/zcomx/login/profile_creator_image_crud.json/' + action;
            that.clear_message();
            $.ajax({
                url: url,
                type: 'GET',
                data: data,
                dataType: 'json',
                success: function (data, textStatus, jqXHR) {
                    if (data.status === 'error') {
                        var msg = 'ERROR: ' + data.msg || 'Server request failed';
                        that.display_message(msg, 'panel-danger');
                    } else {
                        if ($.isFunction(success_callback)) {
                            success_callback(data);
                        }
                    }

                },
                error: function (jqXHR, textStatus, errorThrown) {
                    var msg = 'ERROR: Unable to ' + action + ' record. Server request failed.';
                    that.display_message(msg, 'panel-danger');
                }
            });
        },

    };

    $.fn.profile_creator_image = function (options) {
        var datakey = 'profile_creator_image';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new ProfileCreatorImage(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.profile_creator_image.defaults = {
        cssClass: 'profile_creator_image_modal',
        placeholder_img_name: 'upload.png',
        remove_container_id: 'creator_img_remove_container',
    };

}(window.jQuery));
