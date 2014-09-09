(function () {
    "use strict";

    function set_viewport_size() {
        $('#viewport_px').text($(window).width().toString());
    }

    $(document).ready(function(){
        setTimeout(function() {
            $('.fixme').click(function(e) {
                alert('This feature is not working yet.');
                e.preventDefault();
            });
            $(window).resize( function() {
                set_viewport_size();
            });
        }.bind(this), 1000);

        set_viewport_size();
    });

}());
