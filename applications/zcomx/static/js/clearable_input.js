(function ($) {
    "use strict";

    var ClearableInput = function (element, options) {
        this.init(element, options);
    };

    ClearableInput.prototype = {
        constructor: ClearableInput,
        init: function (element, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.clearable_input.defaults,
                options
            );
            this.$input = null;
            this.$clear_x_span = null;
            this.load();
            this.init_listeners();
        },

        clear: function () {
            this.$clear_x_span.hide();
            this.$input.val('').focus();
        },

        init_listeners: function () {
            var that = this;
            this.$input.on('keyup', function(e) {
                //arrows, enter, tab, etc
                if(~$.inArray(e.keyCode, [40,38,9,13,27])) {
                  return;
                }

                clearTimeout(this.t);
                this.t = setTimeout(function() {
                    that.toggle_clear();
                }, 100);
            })

            this.$clear_x_span.on('click', function(e){
                that.clear();
                if (typeof that.options.on_clear_callback === 'function') {
                    return that.options.on_clear_callback.call(this);
                }
            });
        },

        load: function () {
            var input = this.$element.find('input.' + this.options.input_class);
            if (input.length > 0) {
                this.$input = input;
            } else {
                this.$input = $('<input class="'
                        + this.options.input_class
                        + '" type="text" value="">');
                this.$input.appendTo(this.$element);
            }

            var clear_x_span = this.$element.find('span.' + this.options.clear_x_span_class);
            if (clear_x_span.length > 0) {
                this.$clear_x_span = clear_x_span;
            } else {
                this.$clear_x_span = $('<span class="'
                        + this.options.clear_x_span_class
                        + '"></span>');
                this.$clear_x_span.appendTo(this.$element);
            }

            this.toggle_clear();
        },

        toggle_clear: function () {
            var len = this.$input.val().length,
                visible = this.$clear_x_span.is(':visible');

            if(len && !visible) {
                this.$clear_x_span.show();
            }

            if(!len && visible) {
                this.$clear_x_span.hide();
            }
        },
    };

    $.fn.clearable_input = function (options) {
        var datakey = 'clearable_input';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new ClearableInput(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.clearable_input.defaults = {
        input_class: 'clearable_input_input',
        clear_x_span_class: 'clearable_input_x',
        on_clear_callback: null,
    };

}(window.jQuery));
