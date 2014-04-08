(function () {
    "use strict";

    function close_button(label) {
        label = typeof label !== 'undefined' ? label : 'Close';
        return {
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

    function onshow_callback(dialog) {
        dialog.getModalDialog().addClass('modal-lg');
    }

    function submit_form(elem) {
        var form = elem.find('form').first();
        form.submit();
    }

    $(document).ready(function(){
        $('.modal-add-btn').click(function(event){
            var action = 'Add';
            var link = $(this);
            new BootstrapDialog({
                title: get_title(link, action),
                message: get_message(link),
                onhide: function(dialog) {
                    window.location.reload();
                },
                onshow: onshow_callback,
                buttons: [
                    close_button(),
                ],
            }).open();
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
                    close_button(),
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

    });
}());
