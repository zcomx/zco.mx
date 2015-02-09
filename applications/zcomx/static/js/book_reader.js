(function ($) {
    "use strict";
    var ROTATE = true;
    var NO_ROTATE = false;

    var BookReader = function (element, type, options) {
        this.init(element, type, options);
    };

    BookReader.prototype = {
        constructor: BookReader,
        init: function (element, type, options) {
            var self = this;
            this.$element = $(element);
            this.$type = type;
            this.options = $.extend(
                {},
                $.fn.book_reader.defaults,
                options
            );
            this.init_listeners();
            this.img_loaded_ee = this.$element.imagesLoaded();
            this.img_loaded_ee.always(function(instance) {
                self.to_page(self.options.start_page_no);
            });
        },
    };

    var SliderReader = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(SliderReader, BookReader);
    $.extend(SliderReader.prototype, {
        image_count: function() {
            return $('#reader_section .slide').length - 1;
        },

        init_listeners: function() {
            var that = this;
            $('#page_nav_total').text((that.image_count() + 1).toString());

            $('#reader_section_right').click(function(e) {
                that.next_slide(NO_ROTATE);
                e.preventDefault();
            });

            $('#reader_section_left').click(function(e) {
                that.prev_slide(NO_ROTATE);
                e.preventDefault();
            });

            $('#page_nav_next').click(function(e) {
                that.next_slide(NO_ROTATE);
                e.preventDefault();
            });

            $('#page_nav_prev').click(function(e) {
                that.prev_slide(NO_ROTATE);
                e.preventDefault();
            });

            $('#page_nav_first').click(function(e) {
                that.show_slide(0);
                e.preventDefault();
            });

            $('#page_nav_last').click(function(e) {
                that.show_slide(that.image_count());
                e.preventDefault();
            });

            $('#page_nav_page_no').change(function(e) {
                var value = parseInt($(this).val(), 10);
                if (isNaN(value)) {
                    value = 1;
                }
                var page_no = value - 1;
                if (page_no < 0) {
                    page_no = 0;
                }
                if (page_no > that.image_count()) {
                    page_no = that.image_count();
                }
                that.show_slide(page_no);
            });

            $(window).keyup(function(e) {
                    if (e.which == 37) {
                        // left arrow
                        that.prev_slide(NO_ROTATE);
                        e.preventDefault();
                    }
                    if (e.which == 39) {
                        // right arrow
                        that.next_slide(NO_ROTATE);
                        e.preventDefault();
                    }
                })
                .resize(function(e) {
                    that.set_overlays();
            });
        },

        next_slide: function(rotate) {
            var that = this;
            $('#reader_section .slide:visible').each( function(id, elem) {
                var num = $(this).attr('id').split('-')[1];
                num++;
                if (num > that.image_count()) {
                    if (rotate) {
                        num = 0;
                    } else {
                        return;
                    }
                };
                that.show_slide(num);
            });
        },

        prev_slide: function(rotate) {
            var that = this;
            $('#reader_section .slide:visible').each( function(id, elem) {
                var num = $(this).attr('id').split('-')[1];
                num--;
                if (num < 0) {
                    if (rotate) {
                        num = that.image_count();
                    } else {
                        return;
                    }
                };
                that.show_slide(num);
            });
        },

        set_overlays: function(reader_section, num) {
            if (typeof(reader_section) === 'undefined') {
                reader_section = $('#reader_section');
            }

            var img = reader_section.find('img:visible'),
                left_section = $('#reader_section_left'),
                right_section = $('#reader_section_right');

            if (typeof(num) === 'undefined') {
                num = reader_section.find('.slide:visible').first().attr('id').split('-')[1];
            }

            var left_cursor = num == 0 ? 'auto' : 'w-resize';
            left_section.css({cursor: left_cursor});
            var right_cursor = num == this.image_count() ? 'auto' : 'e-resize';
            right_section.css({cursor: right_cursor});

            var img_h = img.outerHeight();
            var img_w = img.outerWidth();

            left_section.css({
                height: img_h,
                width: img_w/2.0,
            })

            right_section.css({
                height: img_h,
                width: img_w/2.0,
            })

            $(left_section).jquery_ui_position(
                {
                my: 'left top',
                at: 'left top',
                of: $(img),
                collision: 'none',
                }
            );

            $(right_section).jquery_ui_position(
                {
                my: 'right top',
                at: 'right top',
                of: $(img),
                collision: 'none',
                }
            );
        },

        show_slide: function(num) {
            var reader_section = $('#reader_section');
            reader_section.find('.slide').hide();
            reader_section.height('100%');

            /* Resize the container div to fit viewport. */
            var section_h = $(window).height();
            var buffer = 10;
            if (num < this.image_count()) {
                reader_section.height(section_h - buffer);
                reader_section.css({
                    'background-color': $.fn.zco_utils.settings.reader_background_colour,
                });
            }else {
                /* Auto height on indicia page */
                reader_section.height('auto');
                reader_section.css({
                    'min-height': section_h -buffer,
                });
                reader_section.css({'background-color': 'white'})

            }

            /* Set heights of indicia page containers. */
            var indicia_text_container_h = 300;
            var indicia_img_h = (section_h - buffer - indicia_text_container_h);
            reader_section.find('.indicia_text_container').height(indicia_text_container_h);
            reader_section.find('.indicia_image_container').first().find('img').css('max-height', indicia_img_h);

            reader_section.find('#img-' + num).css( "display", "inline-block")
            $('#page_nav_page_no').val(num + 1);

            this.set_overlays(reader_section, num);
        },

        to_page: function(page_no) {
            this.show_slide(page_no - 1);
            $.fn.zco_utils.scroll_to_element('reader_section');
        }
    });

    var ScrollerReader = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(ScrollerReader, BookReader);
    $.extend(ScrollerReader.prototype, {
        init_listeners: function() {
            var that = this;

            $(window).resize(function(e) {
                that.set_indicia();
            });
        },

        set_indicia: function() {
            var reader_section = $('#reader_section');
            var last_img_w = reader_section.find('.book_page_img').last().outerWidth();
            var indicia_section = reader_section.find('.indicia_preview_section');
            var css_min_width = parseInt(indicia_section.css('min-width'), 10) || reader_section.width();
            indicia_section.width(Math.max(css_min_width, last_img_w));
        },

        to_page: function(page_no) {
            this.set_indicia();
            var anchor = 'page_no_' + ('000'+page_no).slice(-3);
            $.fn.zco_utils.scroll_to_element(anchor);
        }
    });

    $.fn.book_reader = function (type, options) {
        var datakey = 'book_reader';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = null;
                switch(type) {
                    case 'scroller':
                        obj = new ScrollerReader(this, type, options);
                        break;
                    case 'slider':
                        obj = new SliderReader(this, type, options);
                        break;
                    default:
                        obj = new BookReader(this, type, options);
                }
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.book_reader.defaults = {
        start_page_no: 1,
    };

}(window.jQuery));
