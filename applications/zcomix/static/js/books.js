(function () {
    "use strict";

    function book_id_from_link(link, link_func) {
        var book_id = 0;
        var href_parts = link.attr('href').split('/');
        if (href_parts[2] === link_func) {
            book_id = href_parts[3];
        }
        return book_id;
    }

    function close_button(label) {
        label = typeof label !== 'undefined' ? label : 'Close';
        return {
            id: 'close_button',
            label: label,
            action : function(dialog){
                dialog.close();
            }
        };
    }

    function display_message(title, msg, panel_class) {
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
    }

    function get_message_by_url(url) {
        return $('<div></div>').load(url);
    }

    function get_message(elem) {
        var url = elem.attr('href');
        return get_message_by_url(url);
    }

    function get_title(elem, action) {
        var title = '';
        if (action) {
            title += action + ': ';
        }
        var tr = elem.closest('tr');
        var td = tr.find('td').first();
        title += td.text();
        return title;
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

        var url = '/zcomix/profile/book_pages_reorder'
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

    function open_edit_modal(link, url, title, book_id) {
        var action = 'Edit';
        title = title || get_title(link, action),
        new BootstrapDialog({
            title: title,
            message: url ? get_message_by_url(url) : get_message(link),
            onhidden: function(dialog) {
                display_book_lists();
            },
            onshow: onshow_callback,
            buttons: [
                {
                    label: 'Upload',
                    action : function(dialog){
                        dialog.close();
                        var url = '/profile/book_pages/' + dialog.getData('book_id');
                        var new_title = title.replace('Edit: ', 'Upload: ');
                        open_upload_modal(null, url, new_title);
                    }
                },
                close_button(),
            ],
            data: {
                'book_id': book_id || book_id_from_link(link, 'book_edit'),
            },
        }).open();
    }

    function open_upload_modal(link, url, title) {
        var action = 'Upload';
        new BootstrapDialog({
            title: title || get_title(link, action),
            message: url ? get_message_by_url(url) : get_message(link),
            onshow: onshow_callback,
            onhidden: reorder_pages,
            buttons: [
                close_button(),
            ],
        }).open();
    }

    function onshow_callback(dialog) {
        dialog.getModalDialog().addClass('modal-lg');
    }

    function submit_form(elem) {
        var form = elem.find('form').first();
        form.submit();
    }

    function update_book(action, dialog) {
        var that = $(this);
        var url = '/zcomix/profile/book_crud.json';

        var book_id = dialog.getData('book_id');
        if (!book_id) {
            return;
        }

        $('#message_panel').hide();

        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
            data: {
                '_action': action,
                'pk': book_id,
            },
            success: function (data, textStatus, jqXHR) {
                if (data.status === 'error') {
                    var msg = 'ERROR: ' + data.msg || 'Server request failed';
                    display_message('', msg, 'panel-danger');
                }
                else {
                    dialog.close();
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                var msg = 'ERROR: Unable to ' + action + ' record. Server request failed.';
                display_message('', msg, 'panel-danger');
            }
        });
    }


    $.fn.set_modal_events = function() {
        $('.modal-add-btn').each( function(indx, elem) {
            var that = $(this);
            if (!that.data('has_modal_add_btn')) {
                that.on('click', function(event) {
                    var action = 'Add book';
                    var link = that;
                    var add_dialog = new BootstrapDialog({
                        title: action,
                        message: get_message(link),
                        onhidden: function(dialog) {
                            var book_id = dialog.getData('book_id');
                            if (book_id) {
                                var url = '/profile/book_edit/' + book_id;
                                var title = 'Edit: ' + dialog.getData('title');
                                open_edit_modal(null, url, title, book_id);
                            } else {
                                display_book_lists();
                            }
                        },
                        onshow: onshow_callback,
                        buttons: [
                            close_button(),
                        ],
                    }).open();
                    that.data({'dialog': add_dialog});
                    event.preventDefault();
                });
                that.data('has_modal_add_btn', true);
            }
        });

        $('.modal-delete-btn').each( function(indx, elem) {
            var that = $(this);
            if (!that.data('has_modal_delete_btn')) {
                that.on('click', function(event) {
                    var action = 'Delete';
                    var link = that;
                    new BootstrapDialog({
                        title: get_title(link, action),
                        message: get_message(link),
                        onhidden: function(dialog) {
                            display_book_lists();
                        },
                        onshow: onshow_callback,
                        buttons: [
                            {
                                label: 'Delete',
                                action : function(dialog){
                                    update_book('delete', dialog);
                                }
                            },
                            close_button('Cancel'),
                        ],
                        data: {
                            'book_id': book_id_from_link(link, 'book_delete')
                        },
                    }).open();
                    event.preventDefault();
                });
                that.data('has_modal_delete_btn', true);
            }
        });

        $('.modal-edit-btn').each( function(indx, elem) {
            var that = $(this);
            if (!that.data('has_modal_edit_btn')) {
                that.on('click', function(event) {
                    open_edit_modal(that);
                    event.preventDefault();
                });
                that.data('has_modal_edit_btn', true);
            }
        });

        $('.modal-release-btn').each( function(indx, elem) {
            var that = $(this);
            if (!that.data('has_modal_release_btn')) {
                that.on('click', function(event) {
                    var action = 'Release';
                    var link = that;
                    new BootstrapDialog({
                        title: get_title(link, action),
                        message: get_message(link),
                        onhidden: function(dialog) {
                            display_book_lists();
                        },
                        onshow: onshow_callback,
                        buttons: (function() {
                            if (link.hasClass('release_not_available')) {
                                return [
                                    close_button(),
                                ];
                            }
                            else {
                                return [
                                    {
                                        label: 'Release',
                                        action : function(dialog){
                                            update_book('release', dialog);
                                        }
                                    },
                                    close_button('Cancel'),
                                ];
                            }
                        })(),
                        data: {
                            'book_id': book_id_from_link(link, 'book_release')
                        },
                    }).open();
                    event.preventDefault();
                });
                that.data('has_modal_release_btn', true);
            }
        });

        $('.modal-upload-btn').each( function(indx, elem) {
            var that = $(this);
            if (!that.data('has_modal_upload_btn')) {
                that.on('click', function(event) {
                    open_upload_modal(that);
                    event.preventDefault();
                });
                that.data('has_modal_upload_btn', true);
            }
        });
    }
}());
