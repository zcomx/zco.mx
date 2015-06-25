(function ($) {
    "use strict";
    /* adapted from x-editable */

    var InputClearButton = function (element, options) {
        this.init(element, options);
    };

    InputClearButton.prototype = {
        constructor: InputClearButton,
        init: function (element, options) {
            this.$input = $(element);
            this.$clear = null;
            this.options = $.extend(
                {},
                $.fn.input_clear_button.defaults,
                options
            );
            this.load();
        },

        clear: function() {
           this.$clear.hide();
           this.$input.val('').focus();
        },

        load: function () {
            this.$clear = $('<span class="editable-clear-x"></span>');
            this.renderClear()
            this.$clear.hide();
        },

        renderClear: function() {
            var that = this;
            this.$input.after(this.$clear)
                .css('padding-right', 24)
                .keyup($.proxy(function(e) {
                    //arrows, enter, tab, etc
                    if(~$.inArray(e.keyCode, [40,38,9,13,27])) {
                        return;
                    }
                    clearTimeout(this.t);
                    var that = this;
                    this.t = setTimeout(function() {
                        that.toggleClear(e);
                    }, 100);
                }, this))
                .parent().css('position', 'relative');
            this.$clear.click($.proxy(this.clear, this));
        },

        toggleClear: function(e) {
            if(!this.$clear) {
                return;
            }
            var len = this.$input.val().length,
                visible = this.$clear.is(':visible');
            if(len && !visible) {
                this.$clear.show();
            }
            if(!len && visible) {
                this.$clear.hide();
            }
        },
    };

    $.fn.input_clear_button = function (options) {
        var datakey = 'input_clear_button';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new InputClearButton(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.input_clear_button.defaults = {
        clear_css_class: 'editable-clear-x',
        input_css_class: 'input_clear_button',
    };

}(window.jQuery));
