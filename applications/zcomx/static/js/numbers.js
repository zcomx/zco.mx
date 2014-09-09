(function( $ ) {
    $.fn.format_number = function (options) {
        var settings = $.extend( {
            'places': 2,
            'group': '',
            'point': '.',
            'suffix': '',
            'prefix': '',
            'nan': 0
        }, options);

        var methods = {
            format: function(num) {
                var regex = /(\d+)(\d{3})/;
                var result = '';
                var sign = '';
                var value = parseFloat(num);
                if (! isNaN(value)) {
                    result = ((Math.abs(value)).toFixed(settings.places))
                            .toString();
                    for (result = result.replace('.', settings.point);
                        regex.test(result) && settings.group;
                        result=result.replace(regex, '$1'+settings.group+'$2')
                        ) { var filler=1;  }
                    sign = value < 0 ? '-' : '';
                }
                else {
                    result = settings.nan === null ? num : settings.nan;
                }
                return [
                        sign,
                        settings.prefix,
                        result,
                        settings.suffix
                    ].join('');
            }
        };

        return this.each( function(index, elem) {
            $(elem).change( function (e) {
                this.value = methods.format.apply(this, [this.value]);
            });
        });
    };
}( jQuery ));

(function () {
    "use strict";

    jQuery(document).ready( function (){
        jQuery('.currency').format_number();
        jQuery('.currency_or_blank').format_number({'nan': ''});
    });
}());
