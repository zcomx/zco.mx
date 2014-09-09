(function () {
    "use strict";

    $(document).ready(function(){
        $('.desc_more_link').click( function(e) {
            var short_desc = $(this).parent('.short_description');
            short_desc.hide();
            short_desc.nextAll('.full_description').removeClass('hidden').show();
            e.preventDefault();
        });
    });

}());
