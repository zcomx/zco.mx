(function ($) {
    "use strict";
    var ROTATE = true;
    var NO_ROTATE = false;

    var KEYCODE = {
        ESC: 27,
        PAGE_UP: 33,
        PAGE_DOWN: 34,
        END: 35,
        HOME: 36,
        LEFT: 37,
        UP: 38,
        RIGHT: 39,
        DOWN: 40,
        Q: 81,
    };

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
            this.set_controls_overlay_on_show_slide = true;
            this.size = 'web';
            this.timers = {
                'controls_overlay_hide': null,
            };

            if (this.options.max_h_for_web && $(window).height() > this.options.max_h_for_web) {
                this.size = 'cbz';
            }
            this.$reader_section = $('#reader_section');
            this.init_listeners();
            if (this.options.img_container_class) {
                this.load_images();
            }

            $('#reader_section').css(
                {'background-color': this.options.book_background_colour}
            );
            $('#reader_section').find('img')
                .not('.indicia_preview_section img')
                .css({'border': "0.4em solid " + this.options.book_border_colour});
        },

        controls_overlay_show: function (options) {
            var data = {
                'action': 'show',
                'element': null,
                'hide_delay': 2000,
            }
            $.extend(data, options);
            if (!data.element) {
                data.element = $('#reader_controls_overlay').first();
            }

            if (data.action == 'hide') {
                this.timers.controls_overlay_hide = setTimeout( function() {
                    data.element.css({'opacity': 0});
                }, data.hide_delay);
            } else {
                // show
                clearTimeout(this.timers.controls_overlay_hide);
                data.element.css({'opacity': 1});
            }

        },

        image_count: function() {
            return this.$reader_section.find(this.options.img_container_class).length - 1;
        },

        init_listeners: function() {
            var that = this;

            $('#page_nav_total').text((that.image_count() + 1).toString());

            $('#page_nav_next').on('click', function(e) {
                that.next_slide(NO_ROTATE);
                e.preventDefault();
            });

            $('#page_nav_prev').on('click', function(e) {
                that.prev_slide(NO_ROTATE);
                e.preventDefault();
            });

            $('#page_nav_first').on('click', function(e) {
                that.show_slide(0);
                e.preventDefault();
            });

            $('#page_nav_last').on('click', function(e) {
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

            $('#reader_controls_overlay').on('mouseenter', function(e) {
                that.set_page_no();
                that.controls_overlay_show({
                    'action': 'show',
                    'element': $(this),
                });
            });

            $('#reader_controls_overlay').on('mouseleave', function(e) {
                that.controls_overlay_show({
                    'action': 'hide',
                    'element': $(this),
                });
            });

            $('.overlay_close_button').on('click', function(e) {
                e.preventDefault();
                window.parent.postMessage('close', that.options.web_site_url);
            });

            $('.overlay_help_button').on('click', function(e) {
                e.preventDefault();
                $('#reader_controls_help').css({
                    'opacity': 1,
                    'z-index': 101,
                });
            });

            $('.help_close_button').on('click', function(e) {
                e.preventDefault();
                $('#reader_controls_help').css({
                    'opacity': 0,
                    'z-index': -1,
                });
            });

            that.post_init_listeners();
        },

        load_image: function($elem, i) {
            var div_img = $elem.find('div#img-' + i);
            if (div_img.length === 0) {
                return;
            }
            if (div_img.find('img').length > 0) {
                return;
            }

            var src = this.options.img_server + '/images/download/'
                + div_img.data("image") + '?size=' + this.size;

            $('<img />').attr('src', src)
                .addClass('book_page_img')
                .appendTo(div_img);
        },

        load_images: function(img_class) {
            var that = this;
            var img_containers = this.$reader_section.find(that.options.img_container_class);
            if (img_containers.length === 0) {
                return
            }

            var ids = [];

            img_containers.each( function(idx, elem) {
                ids.push($(elem).attr('id').replace('img-', ''));
            });

            if (that.options.start_page_no > 1) {
                // Reset so img loaded from start page and on.
                ids = ids.concat(
                    ids.splice(0, that.options.start_page_no - 1));
            }

            var prioritize = [];            //prioritize img on preset pages
            prioritize.push(that.options.start_page_no - 1);    // start
            prioritize.push(that.options.start_page_no);        // next
            prioritize.push(that.options.start_page_no - 2);    // prev
            prioritize.push(0);                                 // first
            prioritize.push(img_containers.length - 1);         // last

            ids = prioritize.concat(ids);

            for (var i=0; i < ids.length; i++) {
                that.queue_load_image(that.$reader_section, ids[i]);
            }
            this.$reader_section.dequeue('img');

            var div_img = this.$reader_section.find(
                'div#img-' + (that.options.start_page_no - 1)).first();

            if (div_img.length) {
                this.img_loaded_ee = div_img.imagesLoaded();
                this.img_loaded_ee.always(function(instance) {
                    that.start_at_page(that.options.start_page_no);
                    $('.loading_gif_overlay').hide();
                });
            } else {
                $('.loading_gif_overlay').hide();
            }
        },

        next_slide: function(rotate) {
            var slide = this.get_visible_slide();
            var num = this.slide_num(slide);
            num++;
            if (num > this.image_count()) {
                if (rotate) {
                    num = 0;
                } else {
                    return;
                }
            };
            this.show_slide(num);
        },

        prev_slide: function(rotate) {
            var slide = this.get_visible_slide();
            var num = this.slide_num(slide);
            num--;
            if (num < 0) {
                if (rotate) {
                    num = this.image_count();
                } else {
                    return;
                }
            };
            this.show_slide(num);
        },

        queue_load_image: function($elem, i, pos) {
            var that = this;

            var queue_func = function() {
                that.load_image($elem, i);
                return $elem.dequeue('img');
            };

            if (pos === 'first') {
                $elem.queue('img').unshift(queue_func);
            } else {
                $elem.queue('img', queue_func);
            }
        },

        set_controls_overlay: function() {
            var img = this.$reader_section.find('.book_page_img').filter(':visible').first();
            if (img.length === 0) {
                var indicia_container = this.$reader_section.find('.indicia_image_container').first();
                img = indicia_container.find('img').first();
            }

            if (img.length === 0) {
                console.log('Error: img not found. Unable to set controls overlay.');
                return;
            }

            var left = img.offset().left;
            var width = img.width()
                + parseInt(img.css('borderLeftWidth'), 10)
                + parseInt(img.css('borderRightWidth'), 10);

            if (width > 480) {
                $('.overlay_help_container').addClass('col-xs-3');
                $('.overlay_help_container').removeClass('col-xs-4');
                $('.overlay_close_container').addClass('col-xs-4');
                $('.overlay_close_container').removeClass('col-xs-8');
                $('.page_nav_container').addClass('col-xs-5');
                $('.page_nav_container').removeClass('hidden-xs');
            } else {
                $('.overlay_help_container').addClass('col-xs-4');
                $('.overlay_help_container').removeClass('col-xs-3');
                $('.overlay_close_container').addClass('col-xs-8');
                $('.overlay_close_container').removeClass('col-xs-4');
                $('.page_nav_container').addClass('hidden-xs');
                $('.page_nav_container').removeClass('col-xs-5');
            }

            $('#reader_controls_container').css({
                'margin-left': left,
                'width': width,
            });
        },

        set_indicia_width: function() {
            return;
        },

        set_page_no: function(page_no) {
            return;
        },

        slide_num: function(slide) {
            var num = $(slide).attr('id').split('-')[1];
            num = ('000' + num) - 0;

            if (num < 0) {
                num = 0;
            }

            if (num > this.image_count()) {
                num = this.image_count();
            }

            return num;
        },

        start_at_page: function(page_no) {
            this.set_indicia_width();
            this.show_slide(page_no - 1);
            if (! this.set_controls_overlay_on_show_slide) {
                this.set_controls_overlay();
            }
            this.set_page_no(page_no);
            this.controls_overlay_show({'action': 'show'});
            this.controls_overlay_show({'action': 'hide', 'hide_delay': 4000});
            this.$element.focus();      // so key events are detected
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

        get_visible_slide: function() {
            var selector = this.options.img_container_class + ':visible';
            return this.$reader_section.find(selector).first();
        },

        post_init_listeners: function() {
            var that = this;

            $('#slider_overlay_left').on('click', function(e) {
                that.prev_slide(NO_ROTATE);
                e.preventDefault();
            }).hammer().bind('swipeleft', function(e) {
                that.prev_slide(NO_ROTATE);
            }).hammer().bind('swiperight', function(e) {
                that.next_slide(NO_ROTATE);
            });

            $('#slider_overlay_right').on('click', function(e) {
                that.next_slide(NO_ROTATE);
                e.preventDefault();
            }).hammer().bind('swipeleft', function(e) {
                that.prev_slide(NO_ROTATE);
            }).hammer().bind('swiperight', function(e) {
                that.next_slide(NO_ROTATE);
            });

            $(window).on('keydown', function(e) {
                    if ($(e.target).prop('tagName') == 'INPUT') {
                        return;
                    }
                    switch (e.which) {
                        case KEYCODE.RIGHT:
                        case KEYCODE.PAGE_DOWN:
                        case KEYCODE.LEFT:
                        case KEYCODE.PAGE_UP:
                        case KEYCODE.HOME:
                        case KEYCODE.UP:
                        case KEYCODE.END:
                        case KEYCODE.DOWN:
                        case KEYCODE.ESC:
                        case KEYCODE.Q:
                            e.preventDefault();
                            break;
                    }
                }).on('keyup', function(e) {
                    if ($(e.target).prop('tagName') == 'INPUT') {
                        return;
                    }
                    switch (e.which) {
                        case KEYCODE.RIGHT:
                        case KEYCODE.PAGE_DOWN:
                            e.preventDefault();
                            that.next_slide(NO_ROTATE);
                            break;
                        case KEYCODE.LEFT:
                        case KEYCODE.PAGE_UP:
                            e.preventDefault();
                            that.prev_slide(NO_ROTATE);
                            break;
                        case KEYCODE.HOME:
                        case KEYCODE.UP:
                            e.preventDefault();
                            that.show_slide(0);
                            break;
                        case KEYCODE.END:
                        case KEYCODE.DOWN:
                            e.preventDefault();
                            that.show_slide(that.image_count());
                            break;
                        case KEYCODE.ESC:
                        case KEYCODE.Q:
                            e.preventDefault();
                            window.parent.postMessage('close', that.options.web_site_url);
                            break;
                    }
                })
                .on('resize', _.debounce(function() {
                        var slide = that.get_visible_slide();
                        var num = that.slide_num(slide);
                        that.show_slide(num);
                        that.set_slider_overlays();
                    }, 200)
                );
        },

        set_slider_overlays: function(num) {
            var that = this;
            var img = this.$reader_section.find('img:visible'),
                left_section = $('#slider_overlay_left'),
                right_section = $('#slider_overlay_right');

            if (typeof(num) === 'undefined') {
                var slide = this.get_visible_slide();
                var num = that.slide_num(slide);
            }

            var left_cursor = num == 0 ? 'auto' : 'w-resize';
            left_section.css({cursor: left_cursor});
            var right_cursor = num == this.image_count() ? 'auto' : 'e-resize';
            right_section.css({cursor: right_cursor});

            var img_h = img.outerHeight();
            var img_w = img.outerWidth();

            var gutter_w = 20; /* gutter in center has no overlay (allow right click on image) */
            if (gutter_w > img_w) {
                gutter_w = img_w;
            }

            var min_extend_w = 30;
            var extend_w = Math.round(img_w / 8);
            if (extend_w < min_extend_w) {
                extend_w = 0;
            }

            var overlay_w = (img_w / 2.0) - gutter_w + extend_w;

            left_section.css({
                height: img_h,
                width: overlay_w,
            })

            right_section.css({
                height: img_h,
                width: overlay_w,
            })

            $(left_section).jquery_ui_position(
                {
                my: 'left-' + extend_w + ' top',
                at: 'left top',
                of: $(img),
                collision: 'none',
                }
            );

            $(right_section).jquery_ui_position(
                {
                my: 'right+' + extend_w + ' top',
                at: 'right top',
                of: $(img),
                collision: 'none',
                }
            );
        },

        show_slide: function(num) {
            var that = this;

            this.$reader_section.find(this.options.img_container_class).hide();
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
            var max_indicia_img_h = 500;
            var indicia_img_h = (section_h - buffer - indicia_text_container_h);
            if (indicia_img_h > max_indicia_img_h) {
                indicia_img_h = max_indicia_img_h;
            }
            this.$reader_section.find('.indicia_image_container').first().find('img').css('max-height', indicia_img_h);

            this.$reader_section.find('#img-' + num).css({
                'display': 'inline-block',
            });

            $('#page_nav_page_no').val(num + 1);

            this.set_slider_overlays(num);

            this.set_controls_overlay();
        },
    });

    var ScrollerReader = function (element, action, options) {
        this.init(
            element,
            action,
            $.extend({'img_container_class': '.scroller'}, options)
        );
        this.set_controls_overlay_on_show_slide = false;
    }
    $.fn.zco_utils.inherit(ScrollerReader, BookReader);
    $.extend(ScrollerReader.prototype, {

        get_visible_slide: function() {
            var overlay = $('#reader_controls_overlay');
            var overlay_offset = overlay.offset();
            var overlay_top = overlay_offset.top;
            var current_slide = null;
            $(this.options.img_container_class).each(function(indx) {
                var $img_div = $(this);
                var img_offset = $img_div.offset();
                var img_top = img_offset.top;
                if (img_top <= overlay_top) {
                    current_slide = this;
                } else {
                    return false;
                }
            });
            return current_slide;
        },

        post_init_listeners: function() {
            var that = this;

            $(window).on('keydown', function(e) {
                    if ($(e.target).prop('tagName') == 'INPUT') {
                        return;
                    }
                    switch (e.which) {
                        case KEYCODE.RIGHT:
                        case KEYCODE.PAGE_DOWN:
                        case KEYCODE.LEFT:
                        case KEYCODE.PAGE_UP:
                        case KEYCODE.HOME:
                        case KEYCODE.END:
                        case KEYCODE.ESC:
                        case KEYCODE.Q:
                            e.preventDefault();
                            break;
                    }
                }).on('keyup', function(e) {
                    if ($(e.target).prop('tagName') == 'INPUT') {
                        return;
                    }
                    switch (e.which) {
                        case KEYCODE.RIGHT:
                        case KEYCODE.PAGE_DOWN:
                            e.preventDefault();
                            that.next_slide(NO_ROTATE);
                            break;
                        case KEYCODE.LEFT:
                        case KEYCODE.PAGE_UP:
                            e.preventDefault();
                            that.prev_slide(NO_ROTATE);
                            break;
                        case KEYCODE.HOME:
                            e.preventDefault();
                            that.show_slide(0);
                            break;
                        case KEYCODE.END:
                            e.preventDefault();
                            that.show_slide(that.image_count());
                            break;
                        case KEYCODE.ESC:
                        case KEYCODE.Q:
                            e.preventDefault();
                            window.parent.postMessage('close', that.options.web_site_url);
                            break;
                    }
                })
                .on('resize', _.debounce(function() {
                    that.set_indicia_width();
                    that.set_controls_overlay();
                }, 200)
            );
        },

        set_indicia_width: function() {
            var last_img_w = this.$reader_section.find('.book_page_img').last().outerWidth();
            var indicia_section = this.$reader_section.find('.indicia_preview_section');
            var css_min_width = parseInt(indicia_section.css('min-width'), 10) || this.$reader_section.width();
            indicia_section.width(Math.max(css_min_width, last_img_w));
        },

        set_page_no: function(page_no) {
            if (typeof(page_no) === 'undefined') {
                var slide = this.get_visible_slide();
                page_no = this.slide_num(slide) + 1;
            }
            $('#page_nav_page_no').val(page_no);
        },

        show_slide: function(num) {
            var page_no = num + 1;
            var anchor = 'page_no_' + ('000'+page_no).slice(-3);
            $.fn.zco_utils.scroll_to_element(anchor, 0);
            $('#page_nav_page_no').val(page_no);
        },

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
        book_background_colour: 'white',
        book_border_colour: 'white',
        img_container_class: null,
        img_server: '',
        max_h_for_web: 1200,
        start_page_no: 1,
        web_site_url: 'https://zco.mx',
    };

}(window.jQuery));
