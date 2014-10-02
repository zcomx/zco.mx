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
            this.$element = $(element);
            this.$type = type;
            this.options = $.extend(
                {},
                $.fn.book_reader.defaults,
                options
            );
            this.init_listeners();
            setTimeout(function() {
                this.to_page(this.options.start_page_no);
            }.bind(this), 1000);
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

        show_slide: function(num) {
            $('#reader_section .slide').hide();
            $('#reader_section').height('100%');

            /* Resize the container div to fit viewport. */
            var section_h = $(window).height();
            var buffer = 10;
            $('#reader_section').height(section_h - buffer);

            var left_cursor = num == 0 ? 'auto' : 'w-resize';
            $('#reader_section_left').css({cursor: left_cursor});
            var right_cursor = num == this.image_count() ? 'auto' : 'e-resize';
            $('#reader_section_right').css({cursor: right_cursor});

            $('#reader_section #img-' + num).css( "display", "inline-block")
            $('#page_nav_page_no').val(num + 1);
        },

        to_page: function(page_no) {
            this.show_slide(page_no - 1);
            $.fn.zco_utils.scroll_to_anchor('reader_section');
        }
    });

    var ScrollerReader = function (element, action, options) {
        this.init(element, action, options);
    }
    $.fn.zco_utils.inherit(ScrollerReader, BookReader);
    $.extend(ScrollerReader.prototype, {
        init_listeners: function() {
            return;
        },
        to_page: function(page_no) {
            console.log('page_no: %o', page_no);
            var anchor = 'page_no_' + ('000'+page_no).slice(-3);
            console.log('anchor: %o', anchor);
            $.fn.zco_utils.scroll_to_anchor(anchor);
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
