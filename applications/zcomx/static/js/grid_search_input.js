(function ($) {
    "use strict";

    var GridSearchInput = function (element, options) {
        this.init(element, options);
    };

    GridSearchInput.prototype = {
        constructor: GridSearchInput,
        init: function (element, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.grid_search_input.defaults,
                options
            );
            this.$search_input = null;
            this.$clear_search_link = null;
            this.load();
            this.init_listeners();
        },

        clear_uri: function () {
            var uri = window.location+''; /* convert to string */
            return uri
                .replace(new RegExp('[?&]' + this.options.kw_param_name + '=[^&#]*(#.*)?$'), '$1')
                .replace(new RegExp('([?&])' + this.options.kw_param_name + '=[^&]*&'), '$1');
        },

        create_clear_link: function () {
            var div = $('<div class="' + this.options.clear_search_link_container_class + '"></div>');
            var uri = this.clear_uri();
            this.$clear_search_link = $(
                '<a class="'
                + this.options.clear_search_link_class
                + '" href="' + uri + '">'
                + this.options.clear_search_link_text
                + '</a>'
            );
            this.$clear_search_link.appendTo(div);
            div.appendTo(this.$element);
        },

        create_clearable: function (form) {
            var that = this;
            var div = $('<div class="' + this.options.clearable_input_container_class + '"></div>');
            this.$search_input.wrap(div);
            this.$search_input.addClass('clearable_input_input');
            var span = $('<span class="' + this.options.clearable_input_x_class + '"></span>');
            this.$search_input.parent().append(span)
            $('.' + this.options.clearable_input_container_class).clearable_input({
                on_clear_callback: function(el) { that.set_search_input_font();}
            });
            return div;
        },

        create_form: function (input_value) {
            var form = $('<form class="' + this.options.form_class + '"></form>');
            this.$search_input = $('<input type="text" value="' + input_value
                + '" class="' + this.options.input_class
                + '" placeholder="' + this.options.input_placeholder
                + '"/>'
            );
            this.$search_input.appendTo(form);
            var button = $('<input class="' + this.options.search_button_class + '" src="/shared/static/images/search_button.png" type="image">');
            button.appendTo(form);
            return form;
        },

        init_listeners: function () {
            var that = this;
            this.$element.on('submit', 'form', function(e) {
                e.preventDefault();
                var kw = that.$search_input.val();
                if (kw) {
                    var target_id = $(this).data('w2p_target');
                    if (typeof target_id != 'undefined') {
                        var component_url = $('#' + target_id).data('w2p_remote');
                        component_url = component_url + '?' + that.options.kw_param_name + '=' + kw;
                        $.web2py.component(component_url, target_id);
                        return false;
                    } else {
                        window.location = window.location.origin
                            + window.location.pathname
                            + '?' + that.options.kw_param_name + '=' + kw;
                    }
                }
            });

            this.$search_input.on('keyup', function (e) {
                that.set_search_input_font();
            })

            if (this.$clear_search_link) {
                this.$clear_search_link.on('click', function(e) {
                    var target_id = $('.' + that.options.form_class).data('w2p_target');
                    if (typeof target_id != 'undefined') {
                        e.preventDefault();
                        var component_url = $('#' + target_id).data('w2p_remote');
                        component_url = component_url;
                        $.web2py.component(component_url, target_id);
                        return false;
                    }
                });
            }
        },

        load: function () {
            var input_value = this.$element.data()[this.options.kw_param_name] || '';
            var form = this.create_form(input_value);
            form.appendTo(this.$element);

            if (input_value && this.options.clear_search_link) {
                this.create_clear_link();
            }

            if (this.options.clearable_input) {
                this.create_clearable();
            }

            this.set_search_input_font();
        },

        set_search_input_font: function () {
            var style = this.$search_input.val() ? 'normal' : 'italic';
            this.$search_input.css('font-style', style);
        },

    };

    $.fn.grid_search_input = function (options) {
        var datakey = 'grid_search_input';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new GridSearchInput(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.grid_search_input.defaults = {
        form_class: 'grid_search_form',
        input_class: 'grid_search_input no_tab_on_enter',
        input_placeholder: 'search keyword',
        search_button_class: 'search_button',
        clearable_input: true,
        clearable_input_container_class: 'clearable_input_container',
        clearable_input_x_class: 'clearable_input_x',
        clear_search_link: true,
        clear_search_link_text: 'Clear search',
        clear_search_link_container_class: 'clear_search_link_container',
        clear_search_link_class: 'clear_search_link',
        kw_param_name: 'keywords',
    };

}(window.jQuery));
