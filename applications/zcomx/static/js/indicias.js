(function ($) {
    "use strict";

    var IndiciaPreview = function (element, url, options) {
        this.init(element, url, options);
    };

    IndiciaPreview.prototype = {
        constructor: IndiciaPreview,
        init: function (element, url, options) {
            this.$element = $(element);
            this.$url = url;
            this.options = $.extend(
                {},
                $.fn.indicia_preview.defaults,
                options
            );
            this.load();
        },

        create: function (urls) {
            var that = this;
            $.each(urls, function(orientation, url) {
                var div = that.$element.find('div#' + orientation).first();
                if (!div.length) {
                    div = $('<div></div>');
                    div.attr('id', orientation);
                    div.addClass('indicia_' + orientation + '_section');
                    div.addClass('col-sm-12');
                    div.addClass('col-md-4');
                    div.appendTo(that.$element)
                }
                if (url) {
                    div.find('div.portrait_placeholder').remove();
                    var img = div.find('img').first();
                    if (!img.length) {
                        img = $('<img />');
                        img.attr('title', 'Indicia preview: ' + orientation);
                        img.appendTo(div)
                    }
                    img.attr('src', url);
                } else {
                    div.find('img').remove();
                    var placeholder = div.find('div.portrait_placeholder').first();
                    if (!placeholder.length) {
                        placeholder = $('<div></div>');
                        placeholder.addClass('portrait_placeholder');
                        placeholder.appendTo(div)
                    }
                }
            });
        },

        load: function () {
            var that = this;
            that.loading('show');
            var jqxhr = $.getJSON(this.$url)
                .done(function(data) {
                    that.create(data.urls);
                })
                .fail(function() {
                    that.create({'portrait': null, 'landscape': null});
                })
                .always(function() {
                    that.loading('hide');
                });
        },

        loading: function (action) {
            var loading_div = this.$element.parent().find('div.loading').first();
            if (action == 'show') {
                loading_div.addClass('processing');
            } else if (action == 'hide') {
                loading_div.removeClass('processing');
            }
            this.$element.parent().find('.fileinput-button').each(function(i) {
                if (action == 'show') {
                    $(this).addClass('disabled');
                } else if (action == 'hide') {
                    $(this).removeClass('disabled');
                }
            });
        },
    };

    $.fn.indicia_preview = function (url, options) {
        var datakey = 'indicia_preview';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new IndiciaPreview(this, url, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.indicia_preview.defaults = {
        highlight: '#FFFF80'
    };

}(window.jQuery));
