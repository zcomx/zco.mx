(function ($) {
    "use strict";

    //utils
    $.fn.inplace_crud_utils = {
        /**
        * set an elem as editable
        */
        set_editable: function(elem, auto_open, extended_settings) {
            var args = Array.apply(null, arguments);
            args.shift();
            args.shift();
            var opts = {};
            for (var i=0; i < args.length; i++) {
                $.extend(true, opts, args[i]);
            }
            elem.editable(opts);

            /* auto proceed to next input */
            if (auto_open) {
                $(elem).on('save.' + $(elem).attr('id') || 'new_record', function(){
                       var that = this;
                       setTimeout(function() {
                           $(that).closest('.row_container').next().find('.editable').editable('show');
                       }, 200);
                });
            }
        },
    };

}(jQuery));

(function( $ ) {
    $.fn.inplace_link_crud = function (url, record_id, options) {
        var settings = $.extend(
            true,
            {},
            $.fn.inplace_link_crud.defaults,
            {url: url, record_id: record_id},
            options
        );

        var methods = {
            _add_input_onblur: function(elem) {
                /* don't submit if one of the inputs has focus */
                var with_focus = $('#' + settings.add_container_id + ' input:focus').length;
                if (with_focus === 0) {
                    var url = $('#' + settings.add_container_id).find('input.link_url').val();
                    var name = $('#' + settings.add_container_id).find('input.link_name').val();
                    if (url) {
                        $('.error_wrapper').hide();
                        $.ajax({
                            url: settings.url,
                            type: 'POST',
                            data: {
                                'action': 'create',
                                'link_id': 0,
                                'name': name,
                                'url': url,
                            },
                            error: methods._ajax_error,
                            success: function (data) {
                                methods._create_callback(data, elem);
                            }
                        });
                    }
                    else {
                        methods._clear_add_inputs();
                    }
                }
            },

            _ajax_error: function(data, textStatus) {
                var msgs = new Array();
                msgs.push(textStatus.toString());
                msgs.push(': ');
                msgs.push(data.status.toString());
                msgs.push(' - ');
                msgs.push(data.statusText.toString());
                $.web2py.flash(msgs.join(''), 'error');
            },

            _append_error: function(container, msg) {
                var error_wrapper = container.find('.error_wrapper');
                if (error_wrapper.length === 0) {
                    error_wrapper = $(
                            '<div class="error_wrapper">'
                          + '    <div class="help-block"></div>'
                          + '</div>'
                        );
                    container.append(error_wrapper);
                }
                $('#' + settings.add_container_id).addClass('has-error');
                error_wrapper.show();
                var error_div = error_wrapper.find('.help-block');
                error_div.text(msg);
            },

            _clear_add_inputs: function() {
                $('#' + settings.add_container_id).find('input.link_url').val('');
                $('#' + settings.add_container_id).find('input.link_name').val('');
                $('#' + settings.add_container_id).find('.error_wrapper').hide();
                $('#' + settings.add_container_id).removeClass('has-error');
            },

            _clear_row_messages: function() {
                $('.row_message').hide();
            },

            _create_add_inputs: function(elem) {
                if (! settings.add_container_id ){
                    return;
                }

                var add_container;
                if ( $('#' + settings.add_container_id).length === 0 ) {
                    $(elem).after('<div id="' + settings.add_container_id + '"></div>');
                }
                add_container = $('#' + settings.add_container_id).first();
                var inputs = $(
                            '<div class="arrow_container"></div>'
                          + '<div>'
                          + '    <input type="text" name="link_name" value="" class="link_name form-control" placeholder="Title-of-Book">'
                          + '</div>'
                          + '<div>'
                          + '    <input type="text" name="link_url" value="" class="link_url form-control" placeholder="http://etsy.com/title-of-book">'
                          + '</div>'
                        );
                inputs.appendTo(add_container);

                $('#' + settings.add_container_id + ' input').blur(function(e){
                    setTimeout(function() {
                        methods._add_input_onblur($(this));
                    }.bind(this), 100);
                }).keyup(function(event){
                    if (event.which == 13) {
                        var input = $(this).closest('div').next().find('input')
                        if (input.length > 0) {
                            input.focus();
                        }
                        else {
                            $(this).blur();
                        }
                        event.preventDefault();
                    }
                }).keydown(function( event ) {
                    if ( event.which == 13 ) {
                        event.preventDefault();
                    }
                });

                add_container.data('edit_container_id', $(elem).attr('id'));
            },

            _create: function(elem, row) {
                var link = $(
                            '<div class="row_container">'
                          + '    <div class="arrow_container">'
                          + '    <button type="button" class="btn btn-default btn-xs reorder-arrow edit_link_up" title="Move link up">'
                          + '          <i class="icon fi-arrow-up size-14"></i>'
                          + '    </button>'
                          + '    <button type="button" class="btn btn-default btn-xs reorder-arrow edit_link_down" title="Move link down">'
                          + '          <i class="icon fi-arrow-down size-14"></i>'
                          + '    </button>'
                          + '    </div>'
                          + '    <div class="field_container field_label">'
                          + '        <a href="#" class="link_name"></a>'
                          + '    </div>'
                          + '    <div class="field_container">'
                          + '        <a href="#" class="link_url"></a>'
                          + '    </div>'
                          + '    <button type="button" class="btn btn-default btn-xs edit_link_open" title="Open link in new window">'
                          + '          <i class="glyphicon glyphicon-new-window"></i>'
                          + '    </button>'
                          + '    <button type="button" class="btn btn-default btn-xs edit_link_delete" title="Delete link">'
                          + '          <i class="icon fi-trash size-18"></i>'
                          + '    </button>'
                          + '    <div class="row_message" style="display: none;"></div>'
                          + '</div>'
                        );
                link.appendTo(elem);
                var fields = ['name', 'url'];
                $.each(fields, function(i, field) {
                    var container = link.find('.field_container').eq(i);
                    var editable_elem = container.find('a').first();
                    editable_elem.text(row[field]);
                    var x_editable_settings = {
                        params: {
                            'action': 'update',
                            'link_id': row.id,
                            'field': field,
                        },
                    };

                    $.fn.inplace_crud_utils.set_editable(
                        editable_elem,
                        settings.auto_open,
                        {url: settings.url, pk: settings.record_id},
                        settings.x_editable_settings,
                        x_editable_settings
                    );
                });

                link.find('.edit_link_delete')
                    .click(methods._delete)
                    .data({'record_id': row.id});
                link.find('.edit_link_open')
                    .click(methods._open)
                    .data({'record_id': row.id});
                link.find('.edit_link_up')
                    .click(methods._move)
                    .data({'record_id': row.id, 'dir': 'up'});
                link.find('.edit_link_down')
                    .click(methods._move)
                    .data({'record_id': row.id, 'dir': 'down'});
            },

            _create_callback: function(data, input) {
                if (data.status === 'error') {
                    $.each(data.msg, function(k, v) {
                        var input = $('#' + settings.add_container_id + ' .link_' + k).first();
                        methods._append_error(input.closest('div'), v);
                    });
                }
                else {
                    edit_container_id = $('#' + settings.add_container_id).data('edit_container_id');
                    edit_container = $('#' + edit_container_id);
                    methods._load_links(edit_container, data.id);
                    methods._clear_add_inputs();
                }
            },

            _delete: function(e) {
                e.preventDefault();
                var that = $(this);
                $.ajax({
                    url: settings.url,
                    type: 'POST',
                    data: {
                        'action': 'delete',
                        'link_id': $(this).data('record_id'),
                    },
                    error: methods._ajax_error,
                    success: function (data) {
                        methods._delete_callback(data, that);
                    }
                });
            },

            _delete_callback: function(data, button) {
                methods._clear_row_messages();
                if (data.status === 'error') {
                    methods._display_row_message(
                        button,
                        data.msg || 'Server request failed',
                        'text-danger'
                    );
                }
                if (data.id) {
                    var row = $(button).closest('.row_container');
                    var edit_link_container = $(row).parent('div');
                    row.remove();
                    methods._set_arrows(edit_link_container);
                }
            },

            _display_row_message: function(elem, msg, text_class) {
                var row = $(elem).closest('.row_container');
                msg_div = row.find('.row_message');
                if (!msg_div) {
                    return;
                }

                var text_classes = [
                    'text-default',
                    'text-primary',
                    'text-success',
                    'text-info',
                    'text-warning',
                    'text-danger'
                ];

                msg_div.html(msg);

                var new_class = text_classes[0];
                if (text_classes.indexOf(text_class) >= 0) {
                    new_class = text_class;
                }
                for(var i = 0; i < text_classes.length; i++) {
                    msg_div.removeClass(text_classes[i])
                }
                msg_div.addClass(new_class).show();
            },

            _load: function(elem) {
                methods._load_links(elem);
                methods._create_add_inputs(elem);
            },

            _load_links: function(elem, link_id) {
                if (link_id === undefined) link_id = 0;
                $.ajax({
                    url: settings.url,
                    type: 'POST',
                    data: {
                        'action': 'get',
                        'link_id': link_id,
                    },
                    error: methods._ajax_error,
                    success: function (data) {
                        methods._load_links_callback(elem, data);
                    }
                });
            },

           _load_links_callback: function(elem, data) {
                if (data.errors && data.errors.length > 0) {
                    $.each(data.errors, function(k, v) {
                        console.log('k: ' + k.toString());
                        console.log('v: ' + v.toString());
                    });
                }
                else {
                    $.each(data.rows, function(k, v) {
                        methods._create(elem, v);
                    });
                    methods._set_arrows(elem);
                }
            },

           _move: function(e) {
               e.preventDefault();
               var that = $(this);
               $.ajax({
                   url: settings.url,
                   type: 'POST',
                   data: {
                       'action': 'move',
                       'link_id': $(this).data('record_id'),
                       'dir': $(this).data('dir'),
                   },
                   error: methods._ajax_error,
                   success: function (data) {
                       methods._move_callback(data, that);
                   }
               });
           },

           _move_callback: function(data, button) {
                methods._clear_row_messages();
                if (data.status === 'error') {
                    methods._display_row_message(
                        button,
                        data.msg || 'Server request failed',
                        'text-danger'
                    );
                }
                if (data.id) {
                    var row = $(button).closest('.row_container');
                    row.fadeOut(400, function() {
                        if (button.data('dir') === 'down') {
                            row.next('.row_container').after(row);
                        }
                        else {
                            row.prev('.row_container').before(row);
                        }
                        row.fadeIn(400, function() {
                            var edit_link_container = $(row).parent('div');
                            methods._set_arrows(edit_link_container);
                        });
                    });
                }
            },

            _open: function(e) {
                e.preventDefault();
                var row = $(this).closest('.row_container');
                var url = row.find('a.link_url').first().text();
                if (url) {
                    window.open(url, 'window_name');
                }
            },

           _set_arrows: function(elem) {
                $(elem).find('.reorder-arrow').removeClass('arrow-muted');
                $(elem).find('.edit_link_up').first().addClass('arrow-muted');
                $(elem).find('.edit_link_down').last().addClass('arrow-muted');
            },
        };

        return this.each( function(index, elem) {
            methods._load.apply(this, [elem]);
        });
    };

    $.fn.inplace_link_crud.defaults = {
        add_container_id: 'add_link_container',
        x_editable_settings: {
            emptytext: 'Click to edit',
            inputclass: 'inplace_crud',
            mode: 'inline',
            placement: 'right',
            showbuttons: false,
            onblur: 'submit',
            success: function(response, newValue) {
                if(response.status == 'error') {
                    return response.msg;
                }
            },
        },
        source_data: {},
    };

}( jQuery ));


(function( $ ) {
    $.fn.inplace_crud = function (url, record_id, options) {
        var settings = $.extend(
            true,
            {},
            $.fn.inplace_crud.defaults,
            {url: url, record_id: record_id},
            options
        );

        var methods = {
            _buttons: function(elem) {
                var button_div = $(
                    '<div>'
                  + '<button id="save-btn" class="btn btn-primary">Save</button>'
                  + '<button id="reset-btn" class="btn pull-right">Reset</button>'
                  + '</div>'
                );
                button_div.appendTo(elem);

                $('#save-btn').click(function() {
                    $('.editable').editable('submit', {
                        url: settings.url,
                        data: {'_action': 'create'},
                        ajaxOptions: {
                            dataType: 'json'     //assuming json response
                        },
                        success: function(data, config) {
                            if(data && data.id) { //record created, response like {"id": 2}
                                typeof settings.on_add === 'function' && settings.on_add(elem, data.id);
                            } else if(data && data.errors){
                                //server-side validation error, response like {"errors": {"username": "username already exist"} }
                                config.error.call(this, data.errors);
                            }
                        },
                        error: function(errors) {
                            var msg = '';
                            if(errors && errors.responseText) { //ajax error, errors = xhr object
                                msg = errors.responseText;
                            } else { //validation error (client-side or server-side)
                                $.each(errors, function(k, v) { msg += k+": "+v+"<br>"; });
                            }
                            methods.display_message('Errors', msg, 'panel-danger');
                        }
                    });
                });
            },

            _create_message_panel: function(elem) {
                var panel = $(
                    '<div id="message_panel" class="panel panel-default" style="display: none;">'
                  + '    <div class="panel-heading">'
                  + '        <h3 class="panel-title">Messages</h3>'
                  + '    </div>'
                  + '    <div class="panel-body"></div>'
                  + '</div>'
                  );
                if (settings.message_panel) {
                    settings.message_panel.html(panel);
                } else {
                    panel.prependTo(elem);
                }
            },

            _hide_message: function(title, msg) {
                $('#message_panel').hide();
            },

            _load: function(elem) {
                $.each(settings.source_data, function(k, v) {
                    if (! v.hasOwnProperty('readable') || v.readable) {
                        var opts = {'name': k, 'value': v.value};
                        $.extend(opts, v.x_editable_settings);
                        var link = methods._load_field(v.label, v.value, opts);
                        link.appendTo(elem);
                    }
                });
            },

            _load_field: function(label, value, x_editable_settings) {
                anchor = '<a href="#" id="' + x_editable_settings.name + '">' + value + '</a>';
                var link = $(
                            '<div class="row_container">'
                          + '    <div class="arrow_container"></div>'
                          + '    <div class="field_label">' + label + '</div>'
                          + '    <div class="field_container">'
                          + anchor
                          + '    </div>'
                          + '</div>'
                        );
                var container = link.find('.field_container').eq(0);
                var editable_elem = link.find('.field_container > a').eq(0);
                $.fn.inplace_crud_utils.set_editable(
                    editable_elem,
                    settings.auto_open,
                    {
                        url: settings.url,
                        pk: settings.record_id || null,
                        params: {
                            '_action': (! settings.record_id || settings.record_id === "0") ? 'create' : 'update',
                        },
                    },
                    settings.x_editable_settings,
                    x_editable_settings
                );
                return link;
            },

            /* Public methods */
            display_message: function(title, msg, panel_class) {
                var panel_classes = [
                    'panel-default',
                    'panel-primary',
                    'panel-success',
                    'panel-info',
                    'panel-warning',
                    'panel-danger'
                ];

                $('#message_panel').find('.panel-title').first().text(title);
                $('#message_panel div.panel-body').html(msg);

                var new_class = panel_classes[0];
                if (panel_classes.indexOf(panel_class) >= 0) {
                    new_class = panel_class;
                }
                for(var i = 0; i < panel_classes.length; i++) {
                    $('#message_panel').removeClass(panel_classes[i])
                }
                $('#message_panel').addClass(new_class).show();
            },
        };

        return this.each( function(index, elem) {
            var $this = $(this);
            methods._create_message_panel.apply(this, [elem]);
            methods._load.apply(this, [elem]);
            if (!settings.record_id) {
                methods._buttons.apply(this, [elem]);
            }
            /* expose display_message */
            $this.data({'display_message': methods.display_message });
        });
    };

    $.fn.inplace_crud.defaults = $.extend(
        true,
        {},
        $.fn.inplace_link_crud.defaults,
        {
            auto_open: false,
            message_panel: null,
            on_add: null,
        }
    );

}( jQuery ));
