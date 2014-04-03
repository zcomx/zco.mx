(function () {
    "use strict";

    function get_message(elem) {
        var url = elem.attr('href');
        return $('<div>Loading...</div>').load(url);
    }

    function get_title(elem) {
        var tr = elem.closest('tr');
        var td = tr.find('td').first();
        return td.text();
    }

    function onshow_callback(dialog) {
        dialog.getModalDialog().addClass('modal-lg');
    }

    function submit_form(elem) {
        var form = elem.find('form').first();
        form.submit();
    }

    $(document).ready(function(){
        $('.modal-btn').click(function(event){
            var link = $(this);
            new BootstrapDialog({
                title: get_title(link),
                message: get_message(link),
                onshow: onshow_callback,
                buttons: [
                    {
                        label   :   'Close',
                        action :   function(dialog){
                            dialog.close();
                        }
                    },
                ],
            }).open();
            event.preventDefault();
        });
    });
}());
