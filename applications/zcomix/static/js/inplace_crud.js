$.editable.addInputType('date', {
    element: $.editable.types.text.element,
    plugin: function(settings, original) {
        Calendar.setup({
            inputField: $(':input:first', this),
            ifFormat: '%Y-%m-%d',
            showsTime: false
        });
    }
});

$.editable.addInputType('colour_picker', {
    element: $.editable.types.text.element,
    plugin: function(settings, original) {
        var input = $(':input:first', this);
        input.spectrum({
            cancelText: "Cancel",
            chooseText: "OK",
            preferredFormat: 'name',
            showInitial: true,
            showInput: true,
            showPalette: true,
            palette: [
                ["#000","#444","#666","#999","#ccc","#eee","#f3f3f3","#fff"],
                ["#f00","#f90","#ff0","#0f0","#0ff","#00f","#90f","#f0f"],
                ["#f4cccc","#fce5cd","#fff2cc","#d9ead3","#d0e0e3","#cfe2f3","#d9d2e9","#ead1dc"],
                ["#ea9999","#f9cb9c","#ffe599","#b6d7a8","#a2c4c9","#9fc5e8","#b4a7d6","#d5a6bd"],
                ["#e06666","#f6b26b","#ffd966","#93c47d","#76a5af","#6fa8dc","#8e7cc3","#c27ba0"],
                ["#c00","#e69138","#f1c232","#6aa84f","#45818e","#3d85c6","#674ea7","#a64d79"],
                ["#900","#b45f06","#bf9000","#38761d","#134f5c","#0b5394","#351c75","#741b47"],
                ["#600","#783f04","#7f6000","#274e13","#0c343d","#073763","#20124d","#4c1130"]
            ],
            change : function(color) {
                input.trigger('blur');
            },
         })
         setTimeout( function() {
             input.spectrum('show');
         }, 100);
    }
});

$.editable.addInputType('select_with_style', {
    element: $.editable.types.select.element,
    content: $.editable.types.select.content,
    plugin: function(settings, original) {
        $(':input:first', this).addClass('form-control');
    }
});

(function( $ ) {
    $.fn.inplace_crud = function (url, options) {
        var settings = $.extend(true, {}, $.fn.inplace_crud.defaults, {url: url}, options);

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
                        methods._clear_add_container();
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
                          + '    <div class="error"></div>'
                          + '</div>'
                        );
                    container.append(error_wrapper);
                }
                error_wrapper.show();
                var error_div = error_wrapper.find('.error');
                error_div.text(msg);
            },

            _clear_add_container: function() {
                $('#' + settings.add_container_id).find('input.link_url').val('');
                $('#' + settings.add_container_id).find('input.link_name').val('');
                $('#' + settings.add_container_id).find('.error_wrapper').hide();
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
                          + '    <input type="text" name="link_name" value="" class="link_name">'
                          + '</div>'
                          + '<div>'
                          + '    <input type="text" name="link_url" value="" class="link_url" placeholder="http://www.example.com">'
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

            _create_callback: function(data, input) {
                if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
                    $.each(data.errors, function(k, v) {
                        var input = $('#' + settings.add_container_id + ' .link_' + k).first();
                        methods._append_error(input.closest('div'), v);
                    });
                }
                else {
                    edit_container_id = $('#' + settings.add_container_id).data('edit_container_id');
                    edit_container = $('#' + edit_container_id);
                    methods._load_links(edit_container, data.id);
                    methods._clear_add_container();
                }
            },

            _create_link: function(elem, row) {
                var link = $(
                            '<div class="row_container">'
                          + '    <div class="arrow_container">'
                          + '    <button type="button" class="btn btn-default btn-xs reorder-arrow edit_link_up">'
                          + '          <i class="icon fi-arrow-up size-14"></i>'
                          + '    </button>'
                          + '    <button type="button" class="btn btn-default btn-xs reorder-arrow edit_link_down">'
                          + '          <i class="icon fi-arrow-down size-14"></i>'
                          + '    </button>'
                          + '    </div>'
                          + '    <div class="edit_field_container field_label">'
                          + '        <div></div>'
                          + '    </div>'
                          + '    <div class="edit_field_container">'
                          + '        <div></div>'
                          + '    </div>'
                          + '    <button type="button" class="btn btn-default btn-xs edit_link_delete">'
                          + '          <i class="icon fi-trash size-18"></i>'
                          + '    </button>'
                          + '</div>'
                        );
                link.appendTo(elem);
                var fields = ['name', 'url'];
                $.each(fields, function(i, field) {
                    var data = {
                        'record_id': row.id,
                        'field': field,
                        'url': settings.url,
                    };
                    var container = link.find('.edit_field_container').eq(i);
                    container.data(data);
                    var editable_div = container.find('div').first();
                    editable_div.text(row[field]);
                    methods._set_editable(editable_div);
                });

                link.find('.edit_link_delete')
                    .click(methods._delete_link)
                    .data({'record_id': row.id});
                link.find('.edit_link_up')
                    .click(methods._move_link)
                    .data({'record_id': row.id, 'dir': 'up'});
                link.find('.edit_link_down')
                    .click(methods._move_link)
                    .data({'record_id': row.id, 'dir': 'down'});
            },

            _delete_callback: function(data, button) {
                if (data.id) {
                    var row = $(button).closest('.row_container');
                    var edit_link_container = $(row).parent('div');
                    row.remove();
                    methods._set_arrows(edit_link_container);
                }
            },

            _delete_link: function(e) {
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

            _editable_callback: function(value) {
                var container = $(this).parent();
                container.removeClass('active');
                var that = $(this);
                $.ajax({
                    url: container.data('url'),
                    type: 'POST',
                    data: {
                        'action': 'update',
                        'field': container.data('field'),
                        'link_id': container.data('record_id'),
                        'value': value,
                    },
                    error: methods._ajax_error,
                    success: function (data) {
                        methods._update_callback(data, that);
                    }
                });
                return(value);
            },

            _load: function(elem) {
                if (settings.links) {
                    methods._load_links(elem);
                    methods._create_add_inputs(elem);
                }
                else {
                    methods._load_fields(elem);
                }
            },

            _load_field: function(label, value, jeditable_settings, data) {
                var link = $(
                            '<div class="row_container">'
                          + '    <div class="arrow_container"></div>'
                          + '    <div class="field_label">' + label + '</div>'
                          + '    <div class="edit_field_container">'
                          + '        <div>' + value + '</div>'
                          + '    </div>'
                          + '</div>'
                        );
                var container = link.find('.edit_field_container').eq(0);
                container.data(data);
                var editable_div = link.find('.edit_field_container > div').eq(0)
                methods._set_editable(editable_div, jeditable_settings);
                return link;
            },

            _load_fields: function(elem) {
                $.each(settings.source_data, function(k, v) {
                    if (! v.hasOwnProperty('readable') || v.readable) {
                        var data = {
                            'field': k,
                            'url': settings.url,
                        }
                        var link = methods._load_field(v.label, v.value, v.jeditable_settings, data);
                        link.appendTo(elem);
                    }
                });
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
                        methods._create_link(elem, v);
                    });
                    methods._set_arrows(elem);
                }
            },

           _move_callback: function(data, button) {
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

           _move_link: function(e) {
               e.preventDefault();
               var that = $(this);
               var dir = $(this).data('dir');
               $.ajax({
                   url: settings.url,
                   type: 'POST',
                   data: {
                       'action': 'move',
                       'link_id': $(this).data('record_id'),
                       'dir': dir,
                   },
                   error: methods._ajax_error,
                   success: function (data) {
                       methods._move_callback(data, that);
                   }
               });
           },

           _set_arrows: function(elem) {
                $(elem).find('.reorder-arrow').removeClass('arrow-muted');
                $(elem).find('.edit_link_up').first().addClass('arrow-muted');
                $(elem).find('.edit_link_down').last().addClass('arrow-muted');
            },

            _set_editable: function(elem, extended_settings) {
                if (! extended_settings) {
                    extended_settings = {};
                }
                var opts = {};
                $.extend(opts, settings.jeditable_settings, extended_settings);
                elem.editable(methods._editable_callback, opts);
                elem.on('click', function(e) {
                    $(this).trigger(settings.jeditable_settings.event);
                    $(this).parent().addClass('active');
                });
                elem.on('keydown', function(e){
                    if (e.which == 9) {
                        $(elem).find('input, textarea').blur();
                        var nextBox = '';
                        var action = 'click';
                        var selector = ".edit_field_container > div:not('.error_wrapper')";
                        var this_idx = $(selector).index(this);
                        if (e.shiftKey) {
                            if (this_idx <= 0)     {
                                nextBox=$(selector)[$(selector).length];         //first box, go to last
                            } else {
                                nextBox=$(selector)[this_idx-1];
                            }
                        }
                        else {
                            if (this_idx >= ($(selector).length-1))     {
                                nextBox=$('#' + settings.add_container_id).find('input')[0];    //last box, go to next input
                                action = 'focus';
                            } else {
                                nextBox=$(selector)[this_idx+1];
                            }
                        }
                        if (action === 'focus') {
                            $(nextBox).focus();  //focus on next box
                        }
                        else {
                            $(nextBox).click();  //Go to assigned next box
                        }
                        return false;           //Suppress normal tab
                    }
                });
            },

            _update_callback: function(data, input) {
                var input_container = $(input).parent();
                var error_wrapper = input_container.find('.error_wrapper');
                if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
                    $(input).trigger(settings.jeditable_settings.event);
                    $.each(data.errors, function(k, v) {
                        methods._append_error(input_container, v);
                    });
                }
                else {
                    if (error_wrapper.length > 0) {
                        error_wrapper.hide();
                    }
                }
            },
        };

        return this.each( function(index, elem) {
            methods._load.apply(this, [elem]);
        });
    };

    $.fn.inplace_crud.defaults = {
        add_container_id: 'add_link_container',
        create: $.noop,
        jeditable_settings: {
            cssclass: 'jeditable_form',
            onblur: 'submit',
            event: 'edit',
            placeholder: '<div class="jeditable_placeholder">Click to edit</div>',
            select: true,
            cols: 60,
            rows: 10,
        },
        links: false,
        source_data: {},
    };

}( jQuery ));
