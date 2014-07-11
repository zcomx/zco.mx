(function () {
    "use strict";

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

    function delete_book(dialog) {
        var that = $(this);
        var url = '/zcomix/profile/book_crud.json';
        var book_id = delete_book_id || 0;

        $('#message_panel').hide();

        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
            data: {
                '_action': 'delete',
                'book_id': book_id,
            },
            success: function (data, textStatus, jqXHR) {
                console.log('data: %o', data);
                console.log('textStatus: %o', textStatus);
                if (data.status === 'error') {
                    var msg = 'ERROR: ' + data.msg || 'Server request failed';
                    display_message('', msg, 'panel-danger');
                }
                else {
                    dialog.close();
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                var msg = 'ERROR: Unable to delete record. Server request failed.';
                display_message('', msg, 'panel-danger');
            }
        });
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

    function get_message(elem) {
        var url = elem.attr('href');
        return $('<div></div>').load(url);
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

    function onshow_callback(dialog) {
        dialog.getModalDialog().addClass('modal-lg');
    }

    function submit_form(elem) {
        var form = elem.find('form').first();
        form.submit();
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
                        onhide: function(dialog) {
                            web2py_component('/profile/book_list.load/released', 'released_book_list');
                            web2py_component('/profile/book_list.load/ongoing', 'ongoing_book_list');
                        },
                        onshow: onshow_callback,
                        buttons: [
                            close_button('Cancel'),
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
                        onhide: function(dialog) {
                            delete_book_id = 0;
                            web2py_component('/profile/book_list.load/released', 'released_book_list');
                            web2py_component('/profile/book_list.load/ongoing', 'ongoing_book_list');
                        },
                        onshow: onshow_callback,
                        buttons: [
                            {
                                label: 'Delete',
                                action : function(dialog){
                                    delete_book(dialog);
                                }
                            },
                            close_button('Cancel'),
                        ],
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
                    var action = 'Edit';
                    var link = that;
                    new BootstrapDialog({
                        title: get_title(link, action),
                        message: get_message(link),
                        onhide: function(dialog) {
                            web2py_component('/profile/book_list.load/released', 'released_book_list');
                            web2py_component('/profile/book_list.load/ongoing', 'ongoing_book_list');
                        },
                        onshow: onshow_callback,
                        buttons: [
                            close_button(),
                        ],
                    }).open();
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
                                            var modal_body = dialog.getModalBody();
                                            var form = $(modal_body).find('form').first();
                                            form.submit();
                                        }
                                    },
                                    close_button('Cancel'),
                                ];
                            }
                        })(),
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
                    var action = 'Upload';
                    var link = that;
                    new BootstrapDialog({
                        title: get_title(link, action),
                        message: get_message(link),
                        onshow: onshow_callback,
                        onhide: reorder_pages,
                        buttons: [
                            close_button(),
                        ],
                    }).open();
                    event.preventDefault();
                });
                that.data('has_modal_upload_btn', true);
            }
        });
    }
}());
