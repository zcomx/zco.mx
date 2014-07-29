/**
 * X-Editable Radiolist extension for Bootstrap 3
 * @requires X-Editable, jquery, etc.
 * @example:
 $('.editable-earn-method').editable({
 name: 'earn_method',
 source: [
 {value: 'swipes', text: 'Number of swipes'},
 {value: 'spend', text: 'Spend Amount ($USD)'}
 ]
 });
 *
 * Adapted by taivo 2014.7.16
 * Adapted by Tomanow
 */
( function($) {
    var Radiolist = function(options) {
        this.init('radiolist', options, Radiolist.defaults);
    };
    $.fn.editableutils.inherit(Radiolist, $.fn.editabletypes.checklist);

    $.extend(Radiolist.prototype, {
        renderList : function() {
            var $label;
            this.$tpl.empty();
            if (!$.isArray(this.sourceData)) {
                return;
            }

            for (var i = 0; i < this.sourceData.length; i++) {
                $label = $('<label>', {'class':this.options.inputclass}).append($('<input>', {
                    type : 'radio',
                    name : this.options.name,
                    value : this.sourceData[i].value
                })).append($('<span>').text(this.sourceData[i].text));

                // Add radio buttons to template
                this.$tpl.append($label);
            }

            this.$input = this.$tpl.find('input[type="radio"]');
        },

        input2value : function() {
            return this.$input.filter(':checked').val();
        },

        //get text selected radio button
        value2htmlFinal : function(value, element) {
            var checked = $.fn.editableutils.itemsByValue(value, this.sourceData),
                escape = this.options.escape;

            if (checked.length) {
                var text = escape ? $.fn.editableutils.escape(checked[0].text) : checked[0].text;
                $(element).html(text);
            } else {
                $(element).empty();
            }
        },

        autosubmit: function() {
            this.$input.off('keydown.editable').on('change.editable', function(){
                $(this).closest('form').submit();
            });
        }
    });

    Radiolist.defaults = $.extend({}, $.fn.editabletypes.list.defaults, {
        /**
         @property tpl
         @default <div></div>
         **/
        tpl : '<div class="editable-radiolist"></div>',

        /**
         @property inputclass, attached to the <label> wrapper instead of the input element
         @type string
         @default null
         **/
        inputclass : '',

        /**
         Separator of values when reading from `data-value` attribute

         @property separator
         @type string
         @default ','
         **/
        separator : ',',

        name : 'defaultname'
    });

    $.fn.editabletypes.radiolist = Radiolist;
}(window.jQuery));
