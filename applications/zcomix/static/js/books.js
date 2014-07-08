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

    $(document).ready(function(){
        $('.modal-add-btn').click(function(event){
            var link = $(this);
            var add_dialog = new BootstrapDialog({
                title: 'Add book',
                message: get_message(link),
                onhide: function(dialog) {
                    setTimeout(function() {
                        window.location.reload();
                    }.bind(this), 100);
                },
                onshow: onshow_callback,
                buttons: [
                    close_button('Cancel'),
                ],
            }).open();
            $(this).data({'dialog': add_dialog});
            event.preventDefault();
        });

        $('.modal-delete-btn').click(function(event){
            var action = 'Delete';
            var link = $(this);
            new BootstrapDialog({
                title: get_title(link, action),
                message: get_message(link),
                onshow: onshow_callback,
                buttons: [
                    {
                        label: 'Delete',
                        action : function(dialog){
                            var modal_body = dialog.getModalBody();
                            var form = $(modal_body).find('form').first();
                            form.submit();
                        }
                    },
                    close_button('Cancel'),
                ],
            }).open();
            event.preventDefault();
        });

        $('.modal-edit-btn').click(function(event){
            var action = 'Edit';
            var link = $(this);
            new BootstrapDialog({
                title: get_title(link, action),
                message: get_message(link),
                onhide: function(dialog) {
                    setTimeout(function() {
                        window.location.reload();
                    }.bind(this), 100);
                },
                onshow: onshow_callback,
                buttons: [
                    close_button(),
                ],
            }).open();
            event.preventDefault();
        });

        $('.modal-release-btn').click(function(event){
            var action = 'Release';
            var link = $(this);
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

        $('.modal-upload-btn').click(function(event){
            var action = 'Upload';
            var link = $(this);
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
    });
}());
