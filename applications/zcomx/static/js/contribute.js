(function( $ ) {
    "use strict";

    $.fn.contribute_button = function (options) {
        var settings = $.extend(
            true,
            {},
            $.fn.contribute_button.defaults,
            options
        );

        var methods = {
            _load: function(elem) {
                $(elem).click(function (e) {
                    var url = $(elem).attr('href');
                    var dialog = new BootstrapDialog({
                        title: ' ',
                        message: $('<div></div>').load(url),
                        buttons: [],
                        cssClass: settings.cssClass,
                    });
                    dialog.open();
                    e.preventDefault();
                })
            },
        };

        return this.each( function(index, elem) {
            var $this = $(this);
            methods._load.apply(this, [elem]);
        });
    };

    $.fn.contribute_button.defaults = {
        cssClass: 'contribute_modal no_rclick_menu',
    };

}(window.jQuery));

(function( $ ) {
    "use strict";

    $.fn.contribute_widget = function (amount, paypal_url, options) {
        var settings = $.extend(
            true,
            {},
            $.fn.contribute_widget.defaults,
            {amount: amount, paypal_url: paypal_url},
            options
        );

        var methods = {
            _clear_error_msg: function(elem) {
                elem.removeClass('alert');
                elem.removeClass('alert-danger');
                elem.html('');
            },

            _load: function(elem) {
                var container = $(
                      '<div class="input_group_container">'
                    + '    <div class="input-group">'
                    + '        <span class="input-group-addon">$</span>'
                    + '        <input type="text" id="contribute_amount" name="amount" class="decimal currency indented input-sm" placeholder="' + settings.amount + '"/>'
                    + '    </div>'
                    + '</div>'
                    + '<div class="contribute_link_container">'
                    + '    <a href="' + settings.paypal_url + '" id="contribute_link">contribute</a>'
                    + '</div>'
                    + '<div class="contribute_error"></div>'
                );
                container.appendTo(elem);
                var input = $(elem).find('#contribute_amount');
                var link = $(elem).find('#contribute_link');
                var link_type = $(elem).data('link_type') || settings.link_type;
                if (link_type === 'button') {
                    link.addClass('btn')
                        .addClass('btn-default')
                        .addClass('contribute_widget_button');
                }
                link.addClass('no_rclick_menu');
                var error = $(elem).find('.contribute_error').first();
                input.focus(function(e) {
                    $(this).removeClass('indented');
                    methods._clear_error_msg(error);
                });
                input.blur(function(e) {
                    if ($(this).val()) {
                        $(this).removeClass('indented');
                    } else {
                        $(this).addClass('indented');
                    }
                });
                input.keypress(function (e) {
                    if (e.which == 13) {
                        link.focus().click();
                        e.preventDefault();
                        e.stopPropagation();
                    }
                });
                link.click( function(e) {
                    var amount = input.val() || settings.amount;
                    var validate_amount = methods._validate(amount);
                    if (validate_amount) {
                        var href = link.attr('href');
                        var dtr = href.indexOf('?') == -1 ? '?' : '&';
                        location.href = href + dtr + 'amount=' + validate_amount.toString();
                    }
                    else {
                        methods._set_error_msg(error);
                    }
                    e.preventDefault();
                });
            },

            _set_error_msg: function (elem) {
                elem.addClass('alert');
                elem.addClass('alert-danger');
                elem.html('<span class="glyphicon glyphicon-remove"></span>Invalid amount');
            },

            _validate: function (value) {
                var zero = value.replace(/[^\d]/gi, '');
                if ( parseInt(zero, 10) === 0) {
                    return null;
                }
                var regex = /^[0-9]\d*(((,\d{3}){1})?(\.\d{0,2})?)$/;
                if (regex.test(value)) {
                    var twoDecimalPlaces = /\.\d{2}$/g;
                    var oneDecimalPlace = /\.\d{1}$/g;
                    var noDecimalPlacesWithDecimal = /\.\d{0}$/g;
                    if (value.match(twoDecimalPlaces)) {
                        return value;
                    }
                    if (value.match(oneDecimalPlace)) {
                        return value+'0';
                    }
                    if (value.match(noDecimalPlacesWithDecimal)) {
                        return value+'00';
                    }
                    return value+'.00';
                }
                return null;
            },
        };

        return this.each( function(index, elem) {
            var $this = $(this);
            methods._load.apply(this, [elem]);
        });
    };

    $.fn.contribute_widget.defaults = {
        link_type: 'link',
    };

}(window.jQuery));
