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
            this.$reader_section = $('#reader_section');
            this.init_listeners();
            if (this.options.img_container_class) {
                this.load_images();
            }
        },

        load_image: function($elem, i) {
            var div_img = $elem.find('div#img-' + i);
            if (div_img.length === 0) {
                return;
            }
            if (div_img.find('img').length > 0) {
                return;
            }
            var src = '/images/download/' + div_img.data("image") + '?size=web';
            $('<img />').attr('src', src)
                .addClass('book_page_img')
                .appendTo(div_img);
        },

        load_images: function(img_class) {
            var self = this;
            var img_containers = this.$reader_section.find(self.options.img_container_class);
            if (img_containers.length === 0) {
                return
            }

            var ids = [];

            img_containers.each( function(idx, elem) {
                ids.push($(elem).attr('id').replace('img-', ''));
            });

            if (self.options.start_page_no > 1) {
                // Reset so img loaded from start page and on.
                ids = ids.concat(
                    ids.splice(0, self.options.start_page_no - 1));
            }

            var prioritize = [];            //prioritize img on preset pages
            prioritize.push(self.options.start_page_no - 1);    // start
            prioritize.push(self.options.start_page_no);        // next
            prioritize.push(self.options.start_page_no - 2);    // prev
            prioritize.push(0);                                 // first
            prioritize.push(img_containers.length - 1);         // last

            ids = prioritize.concat(ids);

            for (var i=0; i < ids.length; i++) {
                self.queue_load_image(self.$reader_section, ids[i]);
            }
            this.$reader_section.dequeue('img');

            var div_img = this.$reader_section.find(
                'div#img-' + (self.options.start_page_no - 1)).first();

            if (div_img.length) {
                this.img_loaded_ee = div_img.imagesLoaded();
                this.img_loaded_ee.always(function(instance) {
                    self.to_page(self.options.start_page_no);
                    $('.centered_loading_gif').removeClass('processing');
                });
            } else {
                $('.centered_loading_gif').removeClass('processing');
            }
        },

        queue_load_image: function($elem, i, pos) {
            var self = this;

            var queue_func = function() {
                self.load_image($elem, i);
                return $elem.dequeue('img');
            };

            if (pos === 'first') {
                $elem.queue('img').unshift(queue_func);
            } else {
                $elem.queue('img', queue_func);
            }
        },

    };

    var SliderReader = function (element, action, options) {
        this.init(
            element,
            action,
            $.extend({'img_container_class': '.slide'}, options)
        );
    }
    $.fn.zco_utils.inherit(SliderReader, BookReader);
    $.extend(SliderReader.prototype, {
        image_count: function() {
            return this.$reader_section.find('.slide').length - 1;
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
            this.$reader_section.find('.slide:visible').each( function(id, elem) {
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
            this.$reader_section.find('.slide:visible').each( function(id, elem) {
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

        set_overlays: function(num) {
            var img = this.$reader_section.find('img:visible'),
                left_section = $('#reader_section_left'),
                right_section = $('#reader_section_right');

            if (typeof(num) === 'undefined') {
                num = this.$reader_section.find('.slide:visible').first().attr('id').split('-')[1];
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
                border: '1px solid red',
            })

            right_section.css({
                height: img_h,
                width: img_w/2.0,
                border: '1px solid blue',
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
            this.$reader_section.find('.slide').hide();
            this.$reader_section.height('100%');

            /* Resize the container div to fit viewport. */
            var section_h = $(window).height();
            var buffer = 10;
            if (num < this.image_count()) {
                this.$reader_section.height(section_h - buffer);
                this.$reader_section.css({
                    'background-color': $.fn.zco_utils.settings.reader_background_colour,
                });
            }else {
                /* Auto height on indicia page */
                this.$reader_section.height('auto');
                this.$reader_section.css({
                    'min-height': section_h -buffer,
                });
                this.$reader_section.css({'background-color': 'white'})

            }

            /* Set heights of indicia page containers. */
            var indicia_text_container_h = 300;
            var indicia_img_h = (section_h - buffer - indicia_text_container_h);
            this.$reader_section.find('.indicia_text_container').height(indicia_text_container_h);
            this.$reader_section.find('.indicia_image_container').first().find('img').css('max-height', indicia_img_h);

            this.$reader_section.find('#img-' + num).css( "display", "inline-block")
            $('#page_nav_page_no').val(num + 1);

            this.set_overlays(num);
        },

        to_page: function(page_no) {
            this.show_slide(page_no - 1);
            $.fn.zco_utils.scroll_to_element('reader_section');
        }
    });

    var ScrollerReader = function (element, action, options) {
        this.init(
            element,
            action,
            $.extend({'img_container_class': '.scroller'}, options)
        );
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
            var last_img_w = this.$reader_section.find('.book_page_img').last().outerWidth();
            var indicia_section = this.$reader_section.find('.indicia_preview_section');
            var css_min_width = parseInt(indicia_section.css('min-width'), 10) || this.$reader_section.width();
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
        img_container_class: null,
    };

}(window.jQuery));
