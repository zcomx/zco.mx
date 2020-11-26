
(function ($) {
    "use strict";

    var DownloadsHandler = function (element, options) {
        this.init(element, options);
    };

    DownloadsHandler.prototype = {
        constructor: DownloadsHandler,
        init: function (element, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.downloads_handler.defaults,
                options
            );
            this.creators = [];
            this.creators_by_id = {};
            this.books = [];
            this.books_by_id = [];
            this.load();
            this.init_listeners();
        },

        init_listeners: function () {
            var that = this;
            $('#creators_ddm').on('change', function(e) {
                that.on_loading_show();
                that.on_change_creator();
                var creator_id = that.get_selected_creator_id();
                $.when(
                    that.get_books(creator_id)
                ).done(function() {
                    that.create_books_ddm(that.books);
                    that.on_loading_hide();
                });
            });

            $('#books_ddm').on('change', function(e) {
                that.on_loading_show();
                that.on_change_book();
                that.on_loading_hide();
            });
        },

        load: function () {
            var that = this;
            this.on_loading_show();
            $.when(
                that.get_creators()
            ).done(function() {
                that.create_creators_ddm(that.creators, that.options.default_creator_id);
                var creator_id = that.get_selected_creator_id();
                $.when(
                    that.get_books(creator_id)
                ).done(function() {
                    that.create_books_ddm(that.books, that.options.default_book_id)
                    that.on_loading_hide();
                });
            });
        },

        create_books_ddm: function(books, selected_book_id) {
            $('#books_ddm').find('option').remove();
            for (var i=0; i < books.length; i++) {
                var book = books[i];
                $('#books_ddm').append($('<option/>', {
                    value: book.id,
                    text : book.title
                }));
            }
            if (selected_book_id) {
                $('#books_ddm').val(selected_book_id);
            }
            this.on_change_book();
        },

        create_creators_ddm: function(creators, selected_creator_id) {
            $('#creators_ddm').find('option').remove();
            for (var i=0; i < creators.length; i++) {
                var creator = creators[i];
                $('#creators_ddm').append($('<option/>', {
                    value: creator.id,
                    text : creator.name
                }));
            }
            if (selected_creator_id) {
                $('#creators_ddm').val(selected_creator_id);
            }
            this.on_change_creator();
        },

        get_books: function(creator_id) {
            var that = this;

            return $.ajax({
                url: '/downloads/downloadable_books.json/' + creator_id,
                type: 'GET',
                dataType: 'json',
                success: function (data, textStatus, jqXHR) {
                    if (data.status == 'error') {
                        jQuery.web2py.flash('ERROR: ' + data.msg, 'error');
                        that.books = [];
                        that.books_by_id = {};
                        that.on_loading_hide();
                    } else {
                        that.books = data.books;
                        that.books_by_id = {};
                        for (var i=0; i < that.books.length; i++) {
                            var book = that.books[i];
                            that.books_by_id[book['id']] = book;
                        }
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(errorThrown);
                    jQuery.web2py.flash('ERROR: ' + errorThrown, 'error');
                    that.books = [];
                    that.books_by_id = {};
                    that.on_loading_hide();
                }
            });
        },

        get_creators: function() {
            var that = this;

            return $.ajax({
                url: '/downloads/downloadable_creators.json/',
                type: 'GET',
                dataType: 'json',
                success: function (data, textStatus, jqXHR) {
                    if (data.status == 'error') {
                        jQuery.web2py.flash('ERROR: ' + data.msg, 'error');
                        that.creators = [];
                        that.creators_by_id = {};
                        that.books = [];
                        that.books_by_id = {};
                        that.on_loading_hide();
                    } else {
                        that.creators = data.creators;
                        that.creators_by_id = {};
                        for (var i=0; i < that.creators.length; i++) {
                            var creator = that.creators[i];
                            that.creators_by_id[creator['id']] = creator;
                        }
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(errorThrown);
                    jQuery.web2py.flash('ERROR: ' + errorThrown, 'error');
                    that.creators = [];
                    that.creators_by_id = {};
                    that.books = [];
                    that.books_by_id = {};
                    that.on_loading_hide();
                }
            });
        },

        get_selected_book_id: function() {
            var book_id = $('#books_ddm').val();
            if (!book_id) {
                book_id = $('#books_ddm').find('option').first().val();
            }
            return book_id;
        },

        get_selected_creator_id: function() {
            var creator_id = $('#creators_ddm').val();
            if (!creator_id) {
                creator_id = $('#creators_ddm').find('option').first().val();
            }
            return creator_id;
        },

        on_change_book: function() {
            this.set_book_links()
        },

        on_change_creator: function() {
            this.set_creator_links()
        },

        on_loading_show: function() {
            this.$element.css('opacity', 0.2);
            $('.loading_gif_overlay').show();
        },

        on_loading_hide: function() {
            $('.loading_gif_overlay').hide();
            this.$element.css('opacity', 'inherit');
        },

        set_book_links: function() {
            $('#book_torrent_link').html('');
            $('#book_magnet_link').html('');
            $('#book_cbz_link').html('');

            var book_id = this.get_selected_book_id()
            if (!book_id) {return;}
            var book_data = this.books_by_id[book_id];
            if (!book_data) {return;}

            var anchor = $('<a href="#">torrent</a>');
            anchor.attr('href', book_data.torrent_url);
            $('#book_torrent_link').html(anchor);

            anchor = $('<a href="#">dc</a>');
            anchor.attr('href', book_data.magnet_uri);
            $('#book_magnet_link').html(anchor);

            anchor = $('<a href="#">direct</a>');
            anchor.attr('href', book_data.cbz_url);
            $('#book_cbz_link').html(anchor);
        },

        set_creator_links: function() {
            $('#creator_torrent_link').html('');

            var creator_id = this.get_selected_creator_id()
            if (!creator_id) {return;}
            var creator_data = this.creators_by_id[creator_id];
            if (!creator_data) {return;}

            var anchor = $('<a href="#">torrent</a>');
            anchor.attr('href', creator_data.torrent_url);
            $('#creator_torrent_link').html(anchor);
        }
    };

    $.fn.downloads_handler = function (options) {
        var datakey = 'downloads_handler';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new DownloadsHandler(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.downloads_handler.defaults = {
        default_book_id: 0,
        default_creator_id: 0,
    };

}(window.jQuery));
