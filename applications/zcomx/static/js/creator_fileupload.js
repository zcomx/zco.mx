(function () {
    "use strict";

    function display_download() {
        $('#fileupload').addClass('fileupload-processing');
        $.ajax({
            // Uncomment the following to send cross-domain cookies:
            //xhrFields: {withCredentials: true},
            url: $('#fileupload').fileupload('option', 'url'),
            dataType: 'json',
            context: $('#fileupload')[0]
        }).always(function () {
            $(this).removeClass('fileupload-processing');
        }).done(function (result) {
            $(this).fileupload('option', 'done')
                .call(this, $.Event('done'), {result: result});
            show_buttons();
        });
    }

    function show_buttons() {
        if ($('#change_button').length > 0) {
            $('.no_photo_section').hide();
        }
        else {
            $('.no_photo_section').show().css(
                {display: 'inline-block'}
            );
        }
    }

    $(document).ready(function(){
        $('#fileupload').fileupload({
            url: '/zcomx/profile/creator_img_handler',
            autoUpload: true,
            change: function(e, data) {
                /* remove any existing */
                $('button.delete').trigger('click');
                },
            destroyed: function(e, data) {
                show_buttons();
                },
            completed: function(e, data) {
                show_buttons();
                },
            });

        $(document).on('click', '#change_button', function(e) {
            $('input[type=file]').trigger('click');
            e.preventDefault();
        });
        display_download();
    });
}());