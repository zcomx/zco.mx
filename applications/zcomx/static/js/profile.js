(function( $ ) {
    "use strict";

    $.fn.profile_name_edit = function (options) {
        var settings = $.extend(
            true,
            {},
            $.fn.profile_name_edit.defaults,
            options
        );

        var methods = {
            _load: function(elem) {
                if(!$(elem).hasClass('disabled')) {
                    $(elem).click(function (e) {
                        var url = $(elem).attr('href');
                        var dialog = new BootstrapDialog({
                            title: 'profile: Edit name',
                            message: $('<div></div>').load(url),
                            buttons: methods._buttons(elem),
                            cssClass: settings.cssClass,
                            onshown: function(dialog) {
                                methods._clear_message();
                            },
                        });
                        dialog.open();
                        e.preventDefault();
                    })
                }
            },

            _buttons: function(elem) {
                var btns = [];
                btns.push({
                    label: 'Submit',
                    cssClass: 'btn_submit',
                    action : function(dialog){
                        methods._update(dialog, elem);
                    }
                });
                btns.push(methods._close_button('Cancel'));
                return btns;
            },

            _close_button: function(label) {
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

            _clear_message: function() {
                var message_panel = $('#name_edit_message_panel').first();
                if (!message_panel.length > 0) {
                    return;
                }
                message_panel.hide();
            },

            _display_message: function(msg, panel_class) {
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

            _update: function(dialog, elem) {
                var that = this;
                var url = '/zcomx/login/profile_name_edit_crud.json';
                var name = $('.name_edit_input').val();
                var data = {'name': name}
                methods._clear_message();
                $.ajax({
                    url: url,
                    type: 'POST',
                    dataType: 'json',
                    data: data,
                    success: function (data, textStatus, jqXHR) {
                        if (data.status === 'error') {
                            var msg = 'ERROR: ' + data.msg || 'Server request failed';
                            methods._display_message(msg, 'panel-danger');
                        }
                        else {
                            $(elem).text(name);
                            dialog.close();
                        }
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        var msg = 'ERROR: Unable to ' + action + ' record. Server request failed.';
                        methods._display_message(msg, 'panel-danger');
                    }
                });
            },
        };

        return this.each( function(index, elem) {
            var $this = $(this);
            methods._load.apply(this, [elem]);
        });
    };

    $.fn.profile_name_edit.defaults = {
        cssClass: 'profile_name_edit_modal',
    };
}(window.jQuery));
