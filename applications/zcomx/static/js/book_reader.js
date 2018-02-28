(function ($) {
    "use strict";
    var ROTATE = true;
    var NO_ROTATE = false;

    var KEYCODE = {
        BACKSPACE: 8,
        ESC: 27,
        PAGE_UP: 33,
        PAGE_DOWN: 34,
        END: 35,
        HOME: 36,
        LEFT: 37,
        UP: 38,
        RIGHT: 39,
        DOWN: 40,
        F: 70,
        N: 78,
        Q: 81,
        Y: 89,
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

            this.ua = $.fn.zco_utils.userAgent();
            this.select_best_reader();

            this.origin_url = null;
            this.page_no = {
                'first': 1,
                'current': 1,
                'last_non_indicia': 1,
                'last': 1,
                'indicia': 1,
            }

            this.set_controls_overlay_on_show_slide = true;
            this.timers = {
                'controls_overlay_hide': undefined,
                'scroll': undefined,
            };
            this.size = 'web';
            if (this.options.max_h_for_web && $(window).height() > this.options.max_h_for_web) {
                this.size = 'cbz';
            }
            this.prev_document_width = document.body.offsetWidth;
            this.$reader_section = $('#reader_section');
            this.$controls_overlay = $('#reader_controls_overlay');
            this.page_no_input_has_focus = false;
            this.confirm_resume_active = false;

            this.init_listeners();
            if (this.options.img_container_class) {
                this.load_images();
            }

            this.$reader_section.css(
                {'background-color': this.options.book_background_colour}
            );
            this.$reader_section.find('img')
                .not('.indicia_preview_section img')
                .css({'border': "0.4em solid " + this.options.book_border_colour});
        },

        better_as_scroller: function() {
            if (this.ua.is_apple_mobile) {
                return false;
            }

            if (this.options.use_scroller_if_short_view !== 'True') {
                return false;
            }
            var slider_min_window_h = 600;
            if ($(window).height() > slider_min_window_h) {
                return false;
            }
            console.log('better_as_scroller enforced');
            return true;
        },

        better_as_slider: function() {
            if (this.ua.is_apple_mobile) {
                console.log('better_as_slider enforced');
                return true;
            }
            return false;
        },

        close: function() {
            this.set_book_mark();
            window.parent.postMessage(
                {'action': 'close'},
                this.get_origin_url()
            );
        },

        confirm_resume_keydown: function(e) {
            switch (e.which) {
                case KEYCODE.RIGHT:
                case KEYCODE.LEFT:
                case KEYCODE.ESC:
                case KEYCODE.N:
                case KEYCODE.Y:
                    e.preventDefault();
                    break;
            }
        },

        confirm_resume_keyup: function(e) {
            switch (e.which) {
                case KEYCODE.RIGHT:
                    e.preventDefault();
                    this.toggle_resume_button_focus();
                    break;
                case KEYCODE.LEFT:
                    e.preventDefault();
                    this.toggle_resume_button_focus();
                    break;
                case KEYCODE.ESC:
                case KEYCODE.N:
                    e.preventDefault();
                    this.set_resume_button_focus('cancel');
                    $('button.cancel').trigger('click');
                    break;
                case KEYCODE.Y:
                    e.preventDefault();
                    this.set_resume_button_focus('confirm');
                    $('button.confirm').trigger('click');
                    break;
            }
        },

        controls_overlay_show: function (options) {
            var data = {
                'action': 'show',
                'element': null,
                'hide_delay': this.options.controls_overlay_hide_delay.inactive,
            }
            $.extend(data, options);
            if (!data.element) {
                data.element = this.$controls_overlay.first();
            }

            if (data.action == 'hide') {
                if (! this.page_no_input_has_focus) {
                    this.timers.controls_overlay_hide = window.setTimeout( function() {
                        data.element.css({'opacity': 0});
                    }, data.hide_delay);
                }
            } else {
                // show
                if (this.ua.is_apple_mobile) {
                    $('.slider_scroller_button').hide();
                }
                if (typeof this.timers.controls_overlay_hide === 'number') {
                    window.clearTimeout(this.timers.controls_overlay_hide);
                    this.timers.controls_overlay_hide = undefined;
                }
                data.element.css({'opacity': 1});
            }
        },

        get_origin_url: function() {
            if(! this.origin_url) {
                var parts = window.location.href.split('?');
                var queries = parts[1].split('&');
                for (var i=0; i < queries.length; i++) {
                    var vars = queries[i].split('=');
                    if (vars[0] == 'zbr_origin') {
                        this.origin_url = decodeURIComponent(vars[1]);
                        break;
                    }
                }
            }
            return this.origin_url;
        },

        init_listeners: function() {
            var that = this;

            $('#page_nav_next').on('click', function(e) {
                that.next_slide(NO_ROTATE);
                that.on_page_nav_click(e);
            });

            $('#page_nav_prev').on('click', function(e) {
                that.prev_slide(NO_ROTATE);
                that.on_page_nav_click(e);
            });

            $('#page_nav_first').on('click', function(e) {
                that.set_n_show_page(that.page_no.first);
                that.on_page_nav_click(e);
            });

            $('#page_nav_last').on('click', function(e) {
                that.set_n_show_page(that.page_no.last);
                that.on_page_nav_click(e);
            });

            $('#page_nav_page_no').on('click', function(e) {
                that.on_page_nav_click(e);
            }).on('change', function(e) {
                var page_no = parseInt($(this).val(), 10);
                var orig_page_no = page_no;
                if (isNaN(page_no)) {
                    page_no = 1;
                }
                if (page_no < that.page_no.first) {
                    page_no = that.page_no.first;
                }
                if (page_no > that.page_no.last) {
                    page_no = that.page_no.last;
                }
                if (page_no !== orig_page_no) {
                    $(this).val(page_no);
                }
                that.set_n_show_page(page_no);
            }).on('focus', function(e) {
                that.page_no_input_has_focus = true;
                // setTimeout requird for Chrome/Safari
                var self = this;
                setTimeout( function() {
                    $(self).select();}
                , 100);
                if (typeof that.timers.controls_overlay_hide === 'number') {
                    window.clearTimeout(that.timers.controls_overlay_hide);
                    that.timers.controls_overlay_hide = undefined;
                }
            }).on('blur', function(e) {
                that.page_no_input_has_focus = false;
                that.controls_overlay_show({
                    'action': 'hide',
                    'element': that.$controls_overlay,
                    'hide_delay': that.options.controls_overlay_hide_delay.active,
                });
            });

            if (that.ua.is_mobile) {
                that.$controls_overlay.on('click', function(e) {
                    if (! that.is_controls_overlay_shown()) {
                        e.preventDefault();
                        that.set_current_page_no();
                        that.set_page_no_input();
                        that.controls_overlay_show({
                            'action': 'show',
                            'element': $(this),
                        });
                        that.controls_overlay_show({
                            'action': 'hide',
                            'element': $(this),
                            'hide_delay': that.options.controls_overlay_hide_delay.active,
                        });
                    } else {
                        that.controls_overlay_show({
                            'action': 'hide',
                            'element': $(this),
                            'hide_delay': 0,
                        });
                    }
                });

            } else {
                that.$controls_overlay.on('mouseenter', function(e) {
                    that.set_current_page_no();
                    that.set_page_no_input();
                    that.controls_overlay_show({
                        'action': 'show',
                        'element': $(this),
                    });
                });

                that.$controls_overlay.on('mouseleave', function(e) {
                    that.controls_overlay_show({
                        'action': 'hide',
                        'element': $(this),
                    });
                });
            }

            $('.overlay_close_button').on('click', function(e) {
                e.preventDefault();
                if (that.is_controls_overlay_shown()) {
                    e.stopPropagation();
                    that.close();
                }
            });

            $('.overlay_help_button').on('click', function(e) {
                e.preventDefault();
                if (that.is_controls_overlay_shown()) {
                    e.stopPropagation();
                    $('#reader_controls_help').css({
                        'opacity': 1,
                        'z-index': 101,
                    });
                }
            });

            $('.help_close_button').on('click', function(e) {
                e.preventDefault();
                $('#reader_controls_help').css({
                    'opacity': 0,
                    'z-index': -1,
                });
            });

            $('.scroller_slider_link').on('click', function(e) {
                e.preventDefault();
                var data = {
                    'action': 'switch',
                    'bg_colour': that.options.book_background_colour,
                    'src': location.protocol + '//' + location.host + $(e.target).parent().attr('href'),
                };
                window.parent.postMessage(data, that.get_origin_url());
            });
            that.post_init_listeners();
        },

        is_controls_overlay_shown: function () {
            var opacity = this.$controls_overlay.css('opacity');
            return opacity === '0' ? false : true;
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
                    that.page_no.last = that.$reader_section.find(that.options.img_container_class).length;
                    that.page_no.indicia = that.page_no.last;
                    that.page_no.last_non_indicia = that.page_no.last > 1 ? that.page_no.last - 1 : 1;
                    $('#page_nav_total').text((that.page_no.last).toString());
                    that.start_at_page(that.options.start_page_no);
                    $('.loading_gif_overlay').hide();
                    if (that.options.resume_page_no != that.options.start_page_no) {
                        that.confirm_resume_active = true;
                        $.confirm({
                            text: "Resume at page " + that.options.resume_page_no + "?",
                            confirmButton: 'Yes',
                            cancelButton: 'No',
                            dialogClass: 'modal-dialog modal-sm resume_page_no_modal',
                            confirm: function() {
                                that.set_n_show_page(that.options.resume_page_no);
                                that.confirm_resume_active = false;
                            },
                            cancel: function() {
                                that.confirm_resume_active = false;
                            },
                        });
                    }
                });
            } else {
                $('.loading_gif_overlay').hide();
            }
        },

        next_slide: function(rotate) {
            var slide = this.get_visible_slide();
            var page_no = this.slide_page_no(slide);
            page_no++;
            if (page_no > this.page_no.last) {
                if (rotate) {
                    page_no = this.page_no.first;
                } else {
                    return;
                }
            };
            this.set_n_show_page(page_no);
        },

        on_keydown: function(e) {
            if ($(e.target).prop('tagName') == 'INPUT') {
                return;
            }

            if (this.confirm_resume_active) {
                this.confirm_resume_keydown(e);
                return;
            }

            this.reader_keydown(e);
        },

        on_keyup: function(e) {
            if ($(e.target).prop('tagName') == 'INPUT') {
                return;
            }

            if (this.confirm_resume_active) {
                this.confirm_resume_keyup(e);
                return;
            }

            this.reader_keyup(e);
        },

        on_page_change: function() {
            this.set_book_mark();
        },

        on_page_nav_click: function(e) {
            e.preventDefault();
            e.stopPropagation();

            this.controls_overlay_show({
                'action': 'show',
                'element': this.$controls_overlay,
            });

            this.controls_overlay_show({
                'action': 'hide',
                'element': this.$controls_overlay,
                'hide_delay': this.options.controls_overlay_hide_delay.active,
            });
        },

        prev_slide: function(rotate) {
            var slide = this.get_visible_slide();
            var page_no = this.slide_page_no(slide);
            page_no--;
            if (page_no < this.page_no.first) {
                if (rotate) {
                    page_no = this.page_no.last;
                } else {
                    return;
                }
            };
            this.set_n_show_page(page_no);
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

        select_best_reader: function () {
            if (this.$type == 'slider' && this.better_as_scroller()) {
                var href = location.href.replace(/[?&]+reader=slider$/g, '');
                var dtr = href.indexOf('?') == -1 ? '?' : '&';
                href = href + dtr + 'reader=scroller';
                location.href = href;
            } else if (this.$type == 'scroller' && this.better_as_slider()) {
                var href = location.href.replace(/[?&]+reader=scroller$/g, '');
                var dtr = href.indexOf('?') == -1 ? '?' : '&';
                href = href + dtr + 'reader=slider';
                location.href = href;
            }
        },

        set_book_mark: function() {
            var that = this;
            var url = '/zcomx/books/set_book_mark.json';

            $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: {
                    'book_id': that.options.book_id,
                    'page_no': that.page_no.current,
                },
                success: function (data, textStatus, jqXHR) {
                    if (data.error) {
                        console.log('ERROR: ' + data.error, 'error');
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(errorThrown);
                }
            });
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
                this.set_controls_overlay_classes('wide');
            } else {
                this.set_controls_overlay_classes('narrow');
            }

            $('#reader_controls_container').css({
                'margin-left': left,
                'width': width,
            });
        },

        set_controls_overlay_classes: function(add_width) {
            var selectors = {
                'hlp': '.overlay_help_container',
                'cls': '.overlay_close_container',
                'pge': '.page_nav_container',
            }
            var cols = {
                'narrow': {
                    'hlp': 'col-xs-4',
                    'cls': 'col-xs-8',
                    'pge': 'hidden',
                },
                'wide': {
                    'hlp': 'col-xs-2',
                    'cls': 'col-xs-2',
                    'pge': 'col-xs-8',
                },
            }

            $.each( cols, function( k, v) {
                if (k != add_width) {
                    $.each( cols[k], function( key, value ) {
                        $(selectors[key]).removeClass(value);
                    });
                }
            });

            $.each( cols[add_width], function( key, value ) {
                $(selectors[key]).addClass(value);
            });
        },

        set_current_page_no: function() {
            var slide = this.get_visible_slide();
            this.page_no.current = this.slide_page_no(slide);
        },

        set_indicia_width: function() {
            return;
        },

        set_n_show_page: function(page_no) {
            this.page_no.current = page_no;
            this.show_slide();
        },

        set_page_no_input: function() {
            if (this.page_no_input_has_focus) {
                return;     // don't interfere with user entering value
            }
            var page_no_input = $('#page_nav_page_no');
            if (page_no_input.val() !== this.page_no.current) {
                page_no_input.val(this.page_no.current);
            }
        },

        set_resume_button_focus: function(button_class) {
            if (button_class === 'cancel') {
                $('button.cancel').addClass('btn-primary').removeClass('btn-default').focus();
                $('button.confirm').addClass('btn-default').removeClass('btn-primary');
            } else {
                $('button.confirm').addClass('btn-primary').removeClass('btn-default').focus();
                $('button.cancel').addClass('btn-default').removeClass('btn-primary');
            }
        },

        slide_page_no: function(slide) {
            var num = $(slide).attr('id').split('-')[1];
            num = ('000' + num) - 0;
            var page_no = num + 1;
            if (page_no < this.page_no.first) {
                page_no = this.page_no.first;
            }
            if (page_no > this.page_no.last) {
                page_no = this.page_no.last;
            }
            return page_no;
        },

        start_at_page: function(page_no) {
            this.set_indicia_width();
            this.set_n_show_page(page_no);
            if (! this.set_controls_overlay_on_show_slide) {
                this.set_controls_overlay();
            }
            this.set_page_no_input();
            this.controls_overlay_show({'action': 'show'});
            this.$element.focus();      // so key events are detected
            this.controls_overlay_show({
                'action': 'hide',
                'hide_delay': this.options.controls_overlay_hide_delay.active,
            });
        },

        toggle_resume_button_focus: function() {
            if ($('button.cancel').hasClass('btn-primary')) {
                this.set_resume_button_focus('confirm');
            } else {
                this.set_resume_button_focus('cancel');
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

        get_visible_slide: function() {
            var selector = this.options.img_container_class + ':visible';
            return this.$reader_section.find(selector).first();
        },

        post_init_listeners: function() {
            var that = this;

            if (that.ua.is_mobile) {
                that.$reader_section.hammer();
                that.$reader_section.data('hammer').get('swipe').set(
                    { direction: Hammer.DIRECTION_HORIZONTAL }
                );
                that.$reader_section.on('swipeleft', function(e) {
                    that.next_slide(NO_ROTATE);
                    that.controls_overlay_show({
                        'action': 'hide',
                        'element': that.$controls_overlay,
                        'hide_delay': that.options.controls_overlay_hide_delay.active,
                    });
                }).on('swiperight', function(e) {
                    that.prev_slide(NO_ROTATE);
                    that.controls_overlay_show({
                        'action': 'hide',
                        'element': that.$controls_overlay,
                        'hide_delay': that.options.controls_overlay_hide_delay.active,
                    });
                });
            } else {
                $('#slider_overlay_left').on('click', function(e) {
                    that.prev_slide(NO_ROTATE);
                    e.preventDefault();
                });

                $('#slider_overlay_right').on('click', function(e) {
                    that.next_slide(NO_ROTATE);
                    e.preventDefault();
                });
            }

            $(window).on('keydown', function(e) {
                that.on_keydown(e);
            }).on('keyup', function(e) {
                that.on_keyup(e);
            }).on('resize', _.debounce( function() {
                var current_document_width = document.body.offsetWidth;
                if (that.prev_document_width != current_document_width) {
                    that.prev_document_width = current_document_width;
                    var slide = that.get_visible_slide();
                    var page_no = that.slide_page_no(slide);
                    that.set_n_show_page(page_no);
                    that.set_slider_overlays();
                }
            }, 200, true));
        },

        reader_keydown: function(e) {
            switch (e.which) {
                case KEYCODE.BACKSPACE:
                case KEYCODE.RIGHT:
                case KEYCODE.PAGE_DOWN:
                case KEYCODE.LEFT:
                case KEYCODE.PAGE_UP:
                case KEYCODE.HOME:
                case KEYCODE.UP:
                case KEYCODE.END:
                case KEYCODE.DOWN:
                case KEYCODE.ESC:
                case KEYCODE.F:
                case KEYCODE.Q:
                    e.preventDefault();
                    break;
            }
        },

        reader_keyup: function(e) {
            switch (e.which) {
                case KEYCODE.RIGHT:
                case KEYCODE.PAGE_DOWN:
                    e.preventDefault();
                    this.next_slide(NO_ROTATE);
                    break;
                case KEYCODE.LEFT:
                case KEYCODE.PAGE_UP:
                case KEYCODE.BACKSPACE:
                    e.preventDefault();
                    this.prev_slide(NO_ROTATE);
                    break;
                case KEYCODE.HOME:
                case KEYCODE.UP:
                    e.preventDefault();
                    this.set_n_show_page(this.page_no.first);
                    break;
                case KEYCODE.END:
                case KEYCODE.DOWN:
                    e.preventDefault();
                    this.set_n_show_page(this.page_no.last);
                    break;
                case KEYCODE.ESC:
                case KEYCODE.Q:
                    e.preventDefault();
                    this.close();
                    break;
                case KEYCODE.F:
                    if (! this.ua.is_mobile) {
                        $(this).trigger('resize')
                    }
                    break;
            }
        },

        set_slider_overlays: function(page_no) {
            var that = this;
            var img = this.$reader_section.find('img:visible'),
                left_section = $('#slider_overlay_left'),
                right_section = $('#slider_overlay_right');

            if (typeof(page_no) === 'undefined') {
                var slide = this.get_visible_slide();
                page_no = that.slide_page_no(slide);
            }

            var left_cursor = page_no == this.page_no.first ? 'auto' : 'w-resize';
            left_section.css({cursor: left_cursor});
            var right_cursor = page_no == this.page_no.last ? 'auto' : 'e-resize';
            right_section.css({cursor: right_cursor});

            var img_h = img.outerHeight(true);
            var img_w = img.outerWidth(true);

            var gutter_w = 20; /* gutter in center has no overlay (allow right click on image) */
            if (gutter_w > img_w) {
                gutter_w = img_w;
            }

            var viewport_w;
            if (document.compatMode === 'BackCompat') {
                viewport_w = document.body.clientWidth;
            } else {
                viewport_w = document.documentElement.clientWidth;
            }

            var overlay_w = (viewport_w / 2.0) - (gutter_w / 2.0);

            left_section.css({
                'height': img_h,
                'width': overlay_w,
                'top': img.offset().top,
                'left': 0,
            })

            right_section.css({
                'height': img_h,
                'width': overlay_w,
                'top': img.offset().top,
                'left': (viewport_w / 2.0) + (gutter_w / 2.0),
            })

        },

        show_slide: function() {
            var page_no = this.page_no.current;
            var img_num = page_no - 1;

            var that = this;
            this.$reader_section.find(this.options.img_container_class).hide();
            this.$reader_section.height('100%');

            /* Resize the container div to fit viewport. */
            var section_h = $(window).height();
            var buffer = 0;
            if (page_no <= this.page_no.last_non_indicia) {
                this.$reader_section.height(section_h - buffer);
                this.$reader_section.css({
                    'background-color': that.options.book_background_colour,
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

            this.$reader_section.find('#img-' + img_num).css({
                'display': 'inline-block',
            });

            this.set_page_no_input();
            this.set_slider_overlays(page_no);
            this.set_controls_overlay();
            this.on_page_change();
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
            var overlay_offset = this.$controls_overlay.offset();
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
                that.on_keydown(e);
            }).on('keyup', function(e) {
                that.on_keyup(e);
            }).on('resize', _.debounce(function() {
                    that.set_indicia_width();
                    that.set_controls_overlay();
                }, 200)
            ).on('scroll', function(e) {
                if (that.timers.scroll) {
                    clearTimeout(that.timers.scroll);
                }
                that.timers.scroll = window.setTimeout( function() {
                    var slide = that.get_visible_slide();
                    var page_no = that.slide_page_no(slide);
                    if (that.page_no.current != page_no) {
                        that.page_no.current = that.slide_page_no(slide);
                        that.on_page_change();
                    }
                }, 300);
            });
        },

        reader_keydown: function(e) {
            switch (e.which) {
                case KEYCODE.BACKSPACE:
                case KEYCODE.RIGHT:
                case KEYCODE.PAGE_DOWN:
                case KEYCODE.LEFT:
                case KEYCODE.PAGE_UP:
                case KEYCODE.HOME:
                case KEYCODE.END:
                case KEYCODE.ESC:
                case KEYCODE.F:
                case KEYCODE.Q:
                    e.preventDefault();
                    break;
            }
        },

        reader_keyup: function(e) {
            switch (e.which) {
                case KEYCODE.RIGHT:
                case KEYCODE.PAGE_DOWN:
                    e.preventDefault();
                    this.next_slide(NO_ROTATE);
                    break;
                case KEYCODE.LEFT:
                case KEYCODE.PAGE_UP:
                case KEYCODE.BACKSPACE:
                    e.preventDefault();
                    this.prev_slide(NO_ROTATE);
                    break;
                case KEYCODE.HOME:
                    e.preventDefault();
                    this.set_n_show_page(this.page_no.first);
                    break;
                case KEYCODE.END:
                    e.preventDefault();
                    this.set_n_show_page(this.page_no.last);
                    break;
                case KEYCODE.ESC:
                case KEYCODE.Q:
                    e.preventDefault();
                    this.close();
                    break;
                case KEYCODE.F:
                    if (! this.ua.is_mobile) {
                        $(this).trigger('resize')
                    }
                    break;
            }
        },

        set_indicia_width: function() {
            var last_img_w = this.$reader_section.find('.book_page_img').last().outerWidth();
            var indicia_section = this.$reader_section.find('.indicia_preview_section');
            var css_min_width = parseInt(indicia_section.css('min-width'), 10) || this.$reader_section.width();
            indicia_section.width(Math.max(css_min_width, last_img_w));
        },

        show_slide: function() {
            var page_no = this.page_no.current;
            var anchor = 'page_no_' + ('000'+page_no).slice(-3);
            $.fn.zco_utils.scroll_to_element(anchor, 0);
            this.set_page_no_input();
            this.on_page_change();
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
        book_id: null,
        controls_overlay_hide_delay: {
            'active': 4000,
            'inactive': 2000,
        },
        img_container_class: null,
        img_server: '',
        max_h_for_web: 1200,
        resume_page_no: 1,
        start_page_no: 1,
        use_scroller_if_short_view: 'False',
    };

}(window.jQuery));
