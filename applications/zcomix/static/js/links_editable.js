(function () {
    "use strict";

    var EDITABLE_EVENT = 'edit';

    function clear_add_container() {
        $('input#link_url').val('');
        $('input#link_name').val('');
        $('.error_wrapper').hide();
    }

    function create_callback(data) {
        if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
            $.each(data.errors, function(k, v) {
                var input = $('#add_link_container #link_' + k);
                var input_container = input.closest('.input_container');
                var error_wrapper = input_container.find('.error_wrapper');
                if (error_wrapper.length === 0) {
                    error_wrapper = $(
                            '<div class="error_wrapper">'
                          + '    <div class="error"></div>'
                          + '</div>'
                        );
                    input_container.append(error_wrapper);
                }
                error_wrapper.show();
                error_div = error_wrapper.find('.error');
                error_div.text(v);
                error_div.focus();
            });
        }
        else {
            load_links(data.id);
            clear_add_container();
        }
    }

    function delete_callback(data) {
        var record_id = data.id;
        $('#link_row_' + data.id).remove();
    }

    function delete_link(e) {
        e.preventDefault();
        var link_id = $(this).parent().attr('id').replace('link_row_', '');
        var creator_id = $('input#creator_id').val();
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'delete',
                'creator_id': creator_id,
                'link_id': link_id,
            },
            error: function (data, textStatus) {
                console.log('error data: ' + data.toString());
                console.log('textStatus: ' + textStatus.toString());
                //set_error({data: data, textStatus: textStatus});
                console.log('data.errors: ' + data.errors.toString());
                console.log('data.errors.url: ' + data.errors.url.toString());
            },
            success: function (data) {
                delete_callback(data);
            }
        });
    }

    function editable_callback(value, settings) {
        var field = $(this).attr('class').replace('edit_link_', '');
        var link_id = $(this).closest('.edit_link_container').attr('id').replace('link_row_', '');
        var creator_id = $('input#creator_id').val();
        var that = $(this);
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'update',
                'creator_id': creator_id,
                'link_id': link_id,
                'field': field,
                'value': value,
            },
            error: function (data, textStatus) {
                console.log('error data: ' + data.toString());
                console.log('textStatus: ' + textStatus.toString());
                //set_error({data: data, textStatus: textStatus});
                console.log('data.errors: ' + data.errors.toString());
                console.log('data.errors.url: ' + data.errors.url.toString());
            },
            success: function (data) {
                update_callback(data, that);
            }
        });
        return(value);
    }

    function editable_settings() {
        return {
            event: EDITABLE_EVENT,
            onblur: 'submit',
        }
    }

    function input_onblur(elem) {
        /* don't submit if one of the inputs has focus */
        var with_focus = $('#add_link_container input:focus').length;
        if (with_focus === 0) {
            var url = $('input#link_url').val();
            var name = $('input#link_name').val();
            var creator_id = $('input#creator_id').val();
            if (url) {
                $('.error_wrapper').hide();
                $.ajax({
                    url: '/zcomix/profile/link_crud.json',
                    type: 'POST',
                    data: {
                        'action': 'create',
                        'creator_id': creator_id,
                        'link_id': 0,
                        'name': name,
                        'url': url,
                    },
                    error: function (data, textStatus) {
                        console.log('error data: ' + data.toString());
                        console.log('textStatus: ' + textStatus.toString());
                        //set_error({data: data, textStatus: textStatus});
                        console.log('data.errors: ' + data.errors.toString());
                        console.log('data.errors.url: ' + data.errors.url.toString());
                    },
                    success: function (data) {
                        create_callback(data);
                    }
                });
            }
            else {
                clear_add_container();
            }
        }
    }

    function load_link(row) {
        var link = $(
                    '<div class="edit_link_container">'
                  + '    <div class="edit_field_container">'
                  + '        <div class="edit_link_name"></div>'
                  + '    </div>'
                  + '    <div class="edit_field_container">'
                  + '        <div class="edit_link_url"></div>'
                  + '    </div>'
                  + '    <button type="button" class="btn btn-default btn-xs edit_link_delete">'
                  + '          <i class="icon fi-trash size-18"></i>'
                  + '    </button>'
                  + '</div>'
                );
        link.appendTo('#edit_links_container')
        link.attr('id', 'link_row_' + row.id.toString());
        link.find('.edit_link_name').text(row.name);
        link.find('.edit_link_name').each(function(e) {
            set_editable($(this));
        });
        link.find('.edit_link_url').text(row.url);
        link.find('.edit_link_url').each(function(e) {
            set_editable($(this));
        });
        link.find('.edit_link_delete').click(delete_link);
    }

    function load_links(link_id) {
        if (link_id === undefined) link_id = 0;
        var creator_id = $('input#creator_id').val();
        $.ajax({
            url: '/zcomix/profile/link_crud.json',
            type: 'POST',
            data: {
                'action': 'get',
                'creator_id': creator_id,
                'link_id': link_id,
            },
            error: function (data, textStatus) {
                console.log('error data: ' + data.toString());
                console.log('textStatus: ' + textStatus.toString());
                //set_error({data: data, textStatus: textStatus});
                console.log('data.errors: ' + data.errors.toString());
                console.log('data.errors.url: ' + data.errors.url.toString());
            },
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
        }
    }

    function set_editable(elem) {
        elem.editable(editable_callback, editable_settings());
        elem.click(function(e) {
            $(this).trigger(EDITABLE_EVENT);
        });
    }

    function update_callback(data, input) {
        console.log('input: %o', input);
        if (data.errors && Object.getOwnPropertyNames(data.errors).length > 0) {
            console.log('has errors: %o', data.errors);
            $(input).trigger(EDITABLE_EVENT);
            $.each(data.errors, function(k, v) {
                var input_container = $(input).closest('.edit_field_container');
                var error_wrapper = input_container.find('.error_wrapper');
                if (error_wrapper.length === 0) {
                    error_wrapper = $(
                            '<div class="error_wrapper">'
                          + '    <div class="error"></div>'
                          + '</div>'
                        );
                    input_container.append(error_wrapper);
                }
                error_wrapper.show();
                error_div = error_wrapper.find('.error');
                error_div.text(v);
                error_div.focus();
            });
        }
        else {
            clear_add_container();
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
                input = $(this).closest('.input_container').next().find('input')
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
    });
}());
