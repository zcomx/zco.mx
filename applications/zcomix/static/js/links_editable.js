(function( $ ) {
    var EDITABLE_EVENT = 'edit';

    var JEDITABLE_SETTINGS = {
        cssclass: 'jeditable_form',
        event: EDITABLE_EVENT,
        onblur: 'submit',
        placeholder: '<div class="jeditable_placeholder">Click to edit</div>',
        select: true,
        cols: 60,
        rows: 10,
    }

    function ajax_error(data, textStatus) {
        var msgs = new Array();
        msgs.push(textStatus.toString());
        msgs.push(': ');
        msgs.push(data.status.toString());
        msgs.push(' - ');
        msgs.push(data.statusText.toString());
        $.web2py.flash(msgs.join(''), 'error');
    }

    function append_error(container, msg) {
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
    }

    function clear_add_container() {
        $('input#link_url').val('');
        $('input#link_name').val('');
        $('.error_wrapper').hide();
    }

    function create_callback(data, input) {
        if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
            $.each(data.errors, function(k, v) {
                var input = $('#add_link_container #link_' + k);
                var input_container = input.closest('.input_container');
                append_error(input_container, v);
            });
        }
        else {
            load_links(data.id);
            clear_add_container();
        }
    }

    function delete_callback(data, button) {
        if (data.id) {
            var container = $(button).closest('.row_container');
            container.remove();
        }
    }

    function delete_link(e) {
        e.preventDefault();
        var that = $(this);
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'delete',
                'link_id': $(this).data('record_id'),
            },
            error: ajax_error,
            success: function (data) {
                delete_callback(data, that);
            }
        });
    }

    function editable_callback(value, settings) {
        var container = $(this).closest('.edit_field_container');
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
            error: ajax_error,
            success: function (data) {
                update_callback(data, that);
            }
        });
        return(value);
    }

    function input_onblur(elem) {
        /* don't submit if one of the inputs has focus */
        var with_focus = $('#add_link_container input:focus').length;
        if (with_focus === 0) {
            var url = $('input#link_url').val();
            var name = $('input#link_name').val();
            if (url) {
                $('.error_wrapper').hide();
                $.ajax({
                    url: '/zcomix/profile/link_crud.json',
                    type: 'POST',
                    data: {
                        'action': 'create',
                        'link_id': 0,
                        'name': name,
                        'url': url,
                    },
                    error: ajax_error,
                    success: function (data) {
                        create_callback(data, elem);
                    }
                });
            }
            else {
                clear_add_container();
            }
        }
    }

    function load_field(label, value, jeditable_settings, data) {
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
        set_editable(editable_div, jeditable_settings);
        return link;
    }

    function load_link(row) {
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
        link.appendTo('#edit_links_container')
        var fields = ['name', 'url']
        $.each(fields, function(i, field) {
            var data = {
                'record_id': row.id,
                'field': field,
                'url': '/zcomix/profile/link_crud.json',
            };
            var container = link.find('.edit_field_container').eq(i);
            container.data(data);
            var editable_div = container.find('div').eq(0);
            editable_div.text(row[field]);
            set_editable(editable_div);
        });

        link.find('.edit_link_delete')
            .click(delete_link)
            .data({'record_id': row.id});
        link.find('.edit_link_up')
            .click(move_link)
            .data({'record_id': row.id, 'dir': 'up'});
        link.find('.edit_link_down')
            .click(move_link)
            .data({'record_id': row.id, 'dir': 'down'});
    }

    function load_links(link_id) {
        if (link_id === undefined) link_id = 0;
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'get',
                'link_id': link_id,
            },
            error: ajax_error,
            success: function (data) {
                load_links_callback(data);
            }
        });
    }

    function load_links_callback(data) {
        console.debug("%o", data);
        if (data.errors && data.errors.length > 0) {
            $.each(data.errors, function(k, v) {
                console.log('k: ' + k.toString());
                console.log('v: ' + v.toString());
            });
        }
        else {
            $.each(data.rows, function(k, v) {
                load_link(v);
            });
            set_arrows();
        }
    }

    function move_callback(data, button) {
        if (data.id) {
            console.log('data: %o', data);
            console.log('button: %o', button);
            console.log('button.data(): %o', button.data());
            var row = $(button).closest('.row_container');
            row.fadeOut(400, function() {
                if (button.data('dir') === 'down') {
                    row.next('.row_container').after(row);
                }
                else {
                    row.prev('.row_container').before(row);
                }
                row.fadeIn(400, function() {
                    set_arrows();
                });
            });
        }
    }

    function move_link(e) {
        e.preventDefault();
        var that = $(this);
        var dir = $(this).data('dir');
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'move',
                'link_id': $(this).data('record_id'),
                'dir': dir,
            },
            error: ajax_error,
            success: function (data) {
                move_callback(data, that);
            }
        });
    }

    function set_editable(elem, options) {
        var settings = {};
        $.extend(settings, JEDITABLE_SETTINGS)
        $.extend(settings, options)
        elem.editable(editable_callback, settings);
        elem.click(function(e) {
            $(this).trigger(EDITABLE_EVENT);
            $(this).closest('.edit_field_container').addClass('active');
        });
        elem.keydown(function(event){
            if (event.which == 9) {
                elem.find('input, textarea').blur();
                var nextBox = '';
                var selector = '.edit_field_container > div';
                var this_idx = $(selector).index(this);
                if (this_idx == ($(selector).length-1))     {
                    nextBox=$(selector)[0];         //last box, go to first
                } else {
                    nextBox=$(selector)[this_idx+1];
                }
                $(nextBox).click();  //Go to assigned next box
                return false;           //Suppress normal tab
            }
        });
    }

    function set_arrows() {
        $('.reorder-arrow').removeClass('arrow-muted');
        $('.edit_link_up').first().addClass('arrow-muted');
        $('.edit_link_down').last().addClass('arrow-muted');
    }

    function update_callback(data, input) {
        var input_container = $(input).closest('.edit_field_container');
        var error_wrapper = input_container.find('.error_wrapper');
        if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
            $(input).trigger(EDITABLE_EVENT);
            $.each(data.errors, function(k, v) {
                append_error(input_container, v);
            });
        }
        else {
            if (error_wrapper.length > 0) {
                error_wrapper.hide();
            }
        }
    }

    $.fn.format_number = function (url, data, options) {
        var settings = $.extend( {
            'container': '#editable_fields_container',
        }, options);

        var methods = {
            format: function(num) {
                var regex = /(\d+)(\d{3})/;
                var result = '';
                var sign = '';
                var value = parseFloat(num);
                if (! isNaN(value)) {
                    result = ((Math.abs(value)).toFixed(settings.places))
                            .toString();
                    for (result = result.replace('.', settings.point);
                        regex.test(result) && settings.group;
                        result=result.replace(regex, '$1'+settings.group+'$2')
                        ) { var filler=1;  }
                    sign = value < 0 ? '-' : '';
                }
                else {
                    result = settings.nan === null ? num : settings.nan;
                }
                return [
                        sign,
                        settings.prefix,
                        result,
                        settings.suffix
                    ].join('');
            }
        };

        load_links();
        $('#add_link_container input').blur(function(e){
            setTimeout(function() {
                input_onblur($(this));
            }.bind(this), 100);
        }).keyup(function(event){
            if (event.which == 13) {
                var input = $(this).closest('.input_container').next().find('input')
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

        $.each(creator_data, function(k, v) {
            var data = {
                'field': k,
                'url': '/zcomix/profile/creator_crud.json',
            }
            var link = load_field(v.label, v.value, v.jeditable_settings, data);
            link.appendTo(v.append_to || '#editable_fields_container');
        });
        $('div#mug_shot').show();

        return this.each( function(index, elem) {
            $(elem).change( function (e) {
                this.value = methods.format.apply(this, [this.value]);
            });
        });
    };
}( jQuery ));


(function () {
    "use strict";

    var EDITABLE_EVENT = 'edit';

    var JEDITABLE_SETTINGS = {
        cssclass: 'jeditable_form',
        event: EDITABLE_EVENT,
        onblur: 'submit',
        placeholder: '<div class="jeditable_placeholder">Click to edit</div>',
        select: true,
        cols: 60,
        rows: 10,
    }

    function ajax_error(data, textStatus) {
        var msgs = new Array();
        msgs.push(textStatus.toString());
        msgs.push(': ');
        msgs.push(data.status.toString());
        msgs.push(' - ');
        msgs.push(data.statusText.toString());
        $.web2py.flash(msgs.join(''), 'error');
    }

    function append_error(container, msg) {
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
    }

    function clear_add_container() {
        $('input#link_url').val('');
        $('input#link_name').val('');
        $('.error_wrapper').hide();
    }

    function create_callback(data, input) {
        if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
            $.each(data.errors, function(k, v) {
                var input = $('#add_link_container #link_' + k);
                var input_container = input.closest('.input_container');
                append_error(input_container, v);
            });
        }
        else {
            load_links(data.id);
            clear_add_container();
        }
    }

    function delete_callback(data, button) {
        if (data.id) {
            var container = $(button).closest('.row_container');
            container.remove();
        }
    }

    function delete_link(e) {
        e.preventDefault();
        var that = $(this);
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'delete',
                'link_id': $(this).data('record_id'),
            },
            error: ajax_error,
            success: function (data) {
                delete_callback(data, that);
            }
        });
    }

    function editable_callback(value, settings) {
        var container = $(this).closest('.edit_field_container');
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
            error: ajax_error,
            success: function (data) {
                update_callback(data, that);
            }
        });
        return(value);
    }

    function input_onblur(elem) {
        /* don't submit if one of the inputs has focus */
        var with_focus = $('#add_link_container input:focus').length;
        if (with_focus === 0) {
            var url = $('input#link_url').val();
            var name = $('input#link_name').val();
            if (url) {
                $('.error_wrapper').hide();
                $.ajax({
                    url: '/zcomix/profile/link_crud.json',
                    type: 'POST',
                    data: {
                        'action': 'create',
                        'link_id': 0,
                        'name': name,
                        'url': url,
                    },
                    error: ajax_error,
                    success: function (data) {
                        create_callback(data, elem);
                    }
                });
            }
            else {
                clear_add_container();
            }
        }
    }

    function load_field(label, value, jeditable_settings, data) {
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
        set_editable(editable_div, jeditable_settings);
        return link;
    }

    function load_link(row) {
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
        link.appendTo('#edit_links_container')
        var fields = ['name', 'url']
        $.each(fields, function(i, field) {
            var data = {
                'record_id': row.id,
                'field': field,
                'url': '/zcomix/profile/link_crud.json',
            };
            var container = link.find('.edit_field_container').eq(i);
            container.data(data);
            var editable_div = container.find('div').eq(0);
            editable_div.text(row[field]);
            set_editable(editable_div);
        });

        link.find('.edit_link_delete')
            .click(delete_link)
            .data({'record_id': row.id});
        link.find('.edit_link_up')
            .click(move_link)
            .data({'record_id': row.id, 'dir': 'up'});
        link.find('.edit_link_down')
            .click(move_link)
            .data({'record_id': row.id, 'dir': 'down'});
    }

    function load_links(link_id) {
        if (link_id === undefined) link_id = 0;
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'get',
                'link_id': link_id,
            },
            error: ajax_error,
            success: function (data) {
                load_links_callback(data);
            }
        });
    }

    function load_links_callback(data) {
        console.debug("%o", data);
        if (data.errors && data.errors.length > 0) {
            $.each(data.errors, function(k, v) {
                console.log('k: ' + k.toString());
                console.log('v: ' + v.toString());
            });
        }
        else {
            $.each(data.rows, function(k, v) {
                load_link(v);
            });
            set_arrows();
        }
    }

    function move_callback(data, button) {
        if (data.id) {
            console.log('data: %o', data);
            console.log('button: %o', button);
            console.log('button.data(): %o', button.data());
            var row = $(button).closest('.row_container');
            row.fadeOut(400, function() {
                if (button.data('dir') === 'down') {
                    row.next('.row_container').after(row);
                }
                else {
                    row.prev('.row_container').before(row);
                }
                row.fadeIn(400, function() {
                    set_arrows();
                });
            });
        }
    }

    function move_link(e) {
        e.preventDefault();
        var that = $(this);
        var dir = $(this).data('dir');
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'move',
                'link_id': $(this).data('record_id'),
                'dir': dir,
            },
            error: ajax_error,
            success: function (data) {
                move_callback(data, that);
            }
        });
    }

    function set_editable(elem, options) {
        var settings = {};
        $.extend(settings, JEDITABLE_SETTINGS)
        $.extend(settings, options)
        elem.editable(editable_callback, settings);
        elem.click(function(e) {
            $(this).trigger(EDITABLE_EVENT);
            $(this).closest('.edit_field_container').addClass('active');
        });
        elem.keydown(function(event){
            if (event.which == 9) {
                elem.find('input, textarea').blur();
                var nextBox = '';
                var selector = '.edit_field_container > div';
                var this_idx = $(selector).index(this);
                if (this_idx == ($(selector).length-1))     {
                    nextBox=$(selector)[0];         //last box, go to first
                } else {
                    nextBox=$(selector)[this_idx+1];
                }
                $(nextBox).click();  //Go to assigned next box
                return false;           //Suppress normal tab
            }
        });
    }

    function set_arrows() {
        $('.reorder-arrow').removeClass('arrow-muted');
        $('.edit_link_up').first().addClass('arrow-muted');
        $('.edit_link_down').last().addClass('arrow-muted');
    }

    function update_callback(data, input) {
        var input_container = $(input).closest('.edit_field_container');
        var error_wrapper = input_container.find('.error_wrapper');
        if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
            $(input).trigger(EDITABLE_EVENT);
            $.each(data.errors, function(k, v) {
                append_error(input_container, v);
            });
        }
        else {
            if (error_wrapper.length > 0) {
                error_wrapper.hide();
            }
        }
    }

    $(document).ready(function(){
        load_links();
        $('#add_link_container input').blur(function(e){
            setTimeout(function() {
                input_onblur($(this));
            }.bind(this), 100);
        }).keyup(function(event){
            if (event.which == 13) {
                var input = $(this).closest('.input_container').next().find('input')
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

        $.each(creator_data, function(k, v) {
            var data = {
                'field': k,
                'url': '/zcomix/profile/creator_crud.json',
            }
            var link = load_field(v.label, v.value, v.jeditable_settings, data);
            link.appendTo(v.append_to || '#editable_fields_container');
        });
    });
}());
