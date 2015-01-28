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

        tooltip_lookup: function() {
            var key = $(this).data('tooltip_key');
            var title = $('body').data('zco:tooltips')[$(this).data('tooltip_key')];
            if ($.isFunction(title)) {
                return title.call(this);
            }
            return title;
        },

        tooltip: function(key, title) {
            var body = $('body')
            var data = body.data('zco:tooltips');
            if (!data) {
                data = {}
            }
            data[key] = title;
            body.data('zco:tooltips', data);
            body.tooltip(
                $.fn.zco_utils.tooltip_options({
                title: $.fn.zco_utils.tooltip_lookup,
                selector: '.zco_tooltip',
                })
            );
            var span = $('<span></span>');
            var icon = $('<i></i>');
            span.addClass('btn info_icon_container zco_tooltip');
            span.data('tooltip_key', key);
            icon.addClass('icon zc-info');
            icon.appendTo(span);
            return span
        },

        tooltip_options: function(options) {
            return $.extend({
                'html': true,
                'title': '<div></div>',
                'template': '<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>',
                'delay': { "show": 100, "hide": 100 },
                },
                options
            );
        },

        toTitleCase: function (str) {
            return str.replace(/\b\w/g, function (txt) { return txt.toUpperCase(); });
        }
    };
}(window.jQuery));


