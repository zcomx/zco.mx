(function ($) {
    "use strict";

    var ImageSquarer = function (element, options) {
        this.init(element, options);
    };

    ImageSquarer.prototype = {
        constructor: ImageSquarer,
        init: function (element, options) {
            this.$container = $(element);
            this.$movable = this.$container.children('div').first();
            this.$movable_img = this.$movable.children('img').first();
            this.options = $.extend(
                {},
                $.fn.image_squarer.defaults,
                options
            );
            this.adj_pos_x = 0;
            this.adj_pos_y = 0;
            this.cur_pos_x = 0;
            this.cur_pos_y = 0;
            this.is_landscape = false;
            this.is_square = false;
            this.load();
            this.init_listeners();
        },

        load: function () {
            this.is_square = this.$movable.outerWidth() == this.$movable.outerHeight();
            this.is_landscape = this.$movable.outerWidth() > this.$movable.outerHeight();
            var new_left = 0;
            var new_top = 0;
            if (this.is_landscape) {
                this.$movable.css('height', this.$container.outerHeight());
                this.$movable.css('width', '');
                this.$movable_img.css('height', '100%');
                this.$movable_img.css('width', '');
                // center image
                var container_left = this.$container.offset().left;
                new_left = container_left - ((this.$movable.outerWidth() - this.$container.outerWidth()) / 2);
                new_top = this.$container.offset().top;
                if (new_left > container_left) { new_left = container_left; }
            } else {
                this.$movable.css('height', '');
                this.$movable.css('width', this.$container.outerWidth());
                this.$movable_img.css('height', '');
                this.$movable_img.css('width', '100%');
                // center image
                var container_top = this.$container.offset().top;
                new_left = this.$container.offset().left;
                new_top = container_top - ((this.$movable.outerHeight() - this.$container.outerHeight()) / 2);
                if (new_top > container_top) { new_top = container_top; }
            }

            this.$movable.offset({
                'left': new_left,
                'top': new_top
            });

            if (! this.is_square) {
                this.show_instructions();
            }
        },

        init_listeners: function () {
            var that = this;
            this.$container.on('mousedown', function(e) {
                e = e || window.event;
                e.preventDefault();
                that.cur_pos_x = e.clientX;
                that.cur_pos_y = e.clientY;
                that.$container.on('mouseup', function(e) {
                    that.close_drag(that);
                });
                that.$container.on('mousemove', function(e) {
                    that.drag_element(that, e);
                });
            });
        },

        clear_message: function() {
            var clear_func = this.options.clear_message_func;
            if ($.isFunction(clear_func)) {
                clear_func();
            }
        },

        display_message: function(msg, panel_class) {
            var display_func = this.options.display_message_func;
            if ($.isFunction(display_func)) {
                display_func(msg, panel_class);
            } else {
                console.log(msg);
            }
        },

        close_drag: function (that) {
            that.$container.off('mouseup');
            that.$container.off('mousemove');
        },

        drag_element: function (that, e) {
            e = e || window.event;
            e.preventDefault();

            that.adj_pos_x = that.cur_pos_x - e.clientX;
            that.adj_pos_y = that.cur_pos_y - e.clientY;
            that.cur_pos_x = e.clientX;
            that.cur_pos_y = e.clientY;

            var container_coords = that.get_container_coords();

            var offset = that.$movable.offset();
            var new_coords = {
                'left': offset.left - that.adj_pos_x,
                'right': offset.left - that.adj_pos_x + that.$movable.outerWidth(),
                'top': offset.top - that.adj_pos_y,
                'bottom': offset.top - that.adj_pos_y + that.$movable.outerHeight(),
            }

            if (that.is_landscape) {
                if (new_coords.left <= container_coords.left && new_coords.right >= container_coords.right) {
                    that.$movable.offset({
                        'left': new_coords.left,
                    });
                }
            }
            else {
                if (new_coords.top <= container_coords.top && new_coords.bottom >= container_coords.bottom) {
                    that.$movable.offset({
                        'top': new_coords.top,
                    });
                }
            }
        },

        get_adjustment: function () {
            var container_coords = this.get_container_coords();

            var img_offset = this.$movable_img.offset();
            var img_dimensions = {
                'height': this.$movable_img.outerHeight(),
                'width': this.$movable_img.outerWidth(),
            }

            var dimension = '';
            var percent = 0;
            var percent_float = 0;
            var adj = 0;
            if (this.is_landscape) {
                dimension = 'width';
                adj = container_coords.left - img_offset.left;
                percent_float = adj * 100 / img_dimensions.width;
                percent = parseInt(percent_float, 10);
            } else {
                dimension = 'height';
                adj = container_coords.top - img_offset.top;
                percent_float = adj * 100 / img_dimensions.height;
                percent = parseInt(percent_float, 10);
            }

            return {
                'dimension': dimension,
                'percent': percent,
            }
        },

        get_container_coords: function () {
            var offset = this.$container.offset();
            return {
                'left': offset.left,
                'right': offset.left + this.$container.outerWidth(),
                'top': offset.top,
                'bottom': offset.top + this.$container.outerHeight(),
            };
        },

        show_instructions: function () {
            var drag_directions = this.is_landscape ? 'left and right' : 'up and down';
            this.clear_message();
            this.display_message(
                '<ul>'
              + '<li>The image you selected is not square and will be cropped.</li>'
              + '<li>If the image is not centered properly, you can drag it '
              + drag_directions
              + '.</li>'
              + '<li>Once you are happy with it, click <i>OK</i>.</li>'
              + '</ul>',
              'panel-danger'
            );
        },
    };

    $.fn.image_squarer = function (options) {
        var datakey = 'image_squarer';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new ImageSquarer(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.image_squarer.defaults = {
        clear_message_func: null,
        display_message_func: null,
    };

}(window.jQuery));
