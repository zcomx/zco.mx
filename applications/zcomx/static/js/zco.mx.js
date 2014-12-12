(function () {
    "use strict";

    function set_viewport_size() {
        $('#viewport_px').text($(window).width().toString());
    }

    $(document).ready(function(){
        setTimeout(function() {
            $('.contribute_button').contribute_button();
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

(function ($) {
    "use strict";

    //utils
    $.fn.zco_utils = {
        /**
        * classic JS inheritance function
        */
        inherit: function (Child, Parent) {
            var F = function() { };
            F.prototype = Parent.prototype;
            Child.prototype = new F();
            Child.prototype.constructor = Child;
            Child.superclass = Parent.prototype;
        },

        scroll_to_element: function(elem_id, buffer, duration){
            buffer = typeof buffer !== 'undefined' ? buffer : 10;
            duration = typeof duration !== 'undefined' ? duration : 400;
            var tag = $("#"+ elem_id);
            $('html,body').animate({scrollTop: tag.offset().top + buffer}, duration);
        },

        toTitleCase: function (str) {
            return str.replace(/\b\w/g, function (txt) { return txt.toUpperCase(); });
        }
    };
}(window.jQuery));


