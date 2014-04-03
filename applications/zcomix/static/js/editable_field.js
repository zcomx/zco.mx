(function( $ ) {
    $.fn.editable_field = function (options) {

        var settings = $.extend({}, $.fn.editable_field.defaults, options);

        var methods = {
            _editable_error_callback: function() {
                $(this).trigger(settings.editable_event);
            },

            _editable_callback: function(value) {
                settings.editable_callback.apply(this,
                    [value, methods._editable_error_callback]
                );
                return(value);
            },

            _set_editable: function(elem) {
                var opts = {};
                $.extend(opts, settings.jeditable_settings)
                $(elem).editable(methods._editable_callback, opts);
                $(elem).on('click', function(e) {
                    $(this).trigger(settings.editable_event);
                    $(this).parent().addClass('active');
                });
            },
        };

        return this.each( function(index, elem) {
            methods._set_editable.apply(this, [elem]);
        });
    };

    $.fn.editable_field.defaults = {
        editable_event: 'edit',
        editable_callback: $.noop,
        jeditable_settings: {
            cssclass: 'jeditable_form',
            event: 'edit',
            onblur: 'submit',
            placeholder: '<div class="jeditable_placeholder">Click to edit</div>',
            select: true,
            cols: 60,
            rows: 10,
        },
    };

}( jQuery ));
