(function () {

    "use strict";

    function clear_error_msg(elem) {
        elem.removeClass('alert');
        elem.removeClass('alert-danger');
        elem.html('');
    }

    function set_error_msg(elem) {
        elem.addClass('alert');
        elem.addClass('alert-danger');
        elem.html('<span class="glyphicon glyphicon-remove"></span>Invalid amount');
    }

    function validate(value) {
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
    }

    $(document).ready(function(){
        var default_amount = $('input#contribute_amount').attr('placeholder');
        $('#contribute_amount').focus(function(e) {
            $(this).removeClass('indented');
            var parent = $(this).closest('.contribute_widget');
            parent.find('.contribute_error').each( function() {
                clear_error_msg($(this));
            });
        });
        $('#contribute_amount').blur(function(e) {
            if ($(this).val()) {
                $(this).removeClass('indented');
            } else {
                $(this).addClass('indented');
            }
        });
        $('#contribute_link').click( function(e) {
            var amount = $('#contribute_amount').val() || default_amount;
            var validate_amount = validate(amount);
            if (validate_amount) {
                var href = $('#contribute_link').attr('href');
                window.open(href + '?amount=' + validate_amount.toString());
            }
            else {
                var parent = $(this).closest('.contribute_widget');
                parent.find('.contribute_error').each( function() {
                    set_error_msg($(this));
                });
            }
            e.preventDefault();
        });

        $('#contribute_amount').keypress(function (e) {
            if (e.which == 13) {
                var parent = $(this).closest('.contribute_widget');
                parent.find('#contribute_link').focus().click();
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });

}());
