/**
Color picker editable input.
Internally value stored as a string: '#ff0000'

@class colour_picker
@extends abstractinput
@final
@example
<script src="http://www.domain.com/static/js/bgrins-spectrum/spectrum.js'"> </script>
<a href="#" id="colour_picker" data-type="colour_picker" data-pk="1">#ff0000</a>
<script>
$(function(){
    $('#colour_picker').editable({
        url: '/post',
        title: 'Select a color for the background.',
        value: '#ff0000',
    });
});
</script>
**/
(function ($) {
    "use strict";

    var ColourPicker = function (options) {
        this.init('colour_picker', options, ColourPicker.defaults);
    };

    //inherit from Abstract input
    $.fn.editableutils.inherit(ColourPicker, $.fn.editabletypes.abstractinput);

    $.extend(ColourPicker.prototype, {
       init: function(type, options, defaults) {
           var that = this;
           this.type = type;
           this.options = $.extend({}, defaults, options);
           /* hide the x-editable form */
           $(options.scope).wrap( '<div style="display: none;"></div>' );
           var input = $('<input type="text">')
           input.insertAfter($(options.scope).parent());
           input.val($(options.scope).text());
           var spectrum_options = $.extend({},
               defaults.spectrum,
               options.spectrum,
               {
                   color: input.val(),
                   change: function(color) {
                       input.triggerHandler('colour_picker_submit', {newValue: input.val()});
                   },
                   beforeShow: function(color) {
                       /* activate x-editable */
                       $(options.scope).trigger('click');
                   },
               }
           );
           input.spectrum(spectrum_options);
           this.$colour_picker = input
           $(options.scope).off('save').on('save', function(e, params) {
               that.highlight(e);
           });
       },

       /**
        Returns value of input. Value can be object (e.g. datepicker)

        @method input2value()
       **/
       input2value: function() {
           return this.$colour_picker.val();
       },

       /**
        Attaches handler to submit form in case of 'showbuttons=false' mode

        @method autosubmit()
       **/
       autosubmit: function() {
           var that = this;
           this.$colour_picker.off('colour_picker_submit').on('colour_picker_submit', function(event, values) {
               that.$input.closest('form').submit();
           });
       },

       /*
        highlight element on save
       */
       highlight: function(elem) {
            var $e = this.$colour_picker.parent().find('.sp-replacer'),
                bgColor = $e.css('background-color');

            $e.css('background-color', this.options.highlight);
            setTimeout(function(){
                if(bgColor === 'transparent') {
                    bgColor = '';
                }
                $e.css('background-color', bgColor);
                $e.addClass('editable-bg-transition');
                setTimeout(function(){
                   $e.removeClass('editable-bg-transition');
                }, 1700);
            }, 10);
       },

    });

    ColourPicker.defaults = $.extend({}, $.fn.editabletypes.abstractinput.defaults, {
        tpl: '<div style="display: none;"><input type="hidden" class="editable-colour_picker" /></div>',
        showbuttons: false,
        highlight: '#FFFF80',
        mode: 'inline',
        /* spectrum config */
        spectrum:{
            appendTo: 'parent',
            cancelText: 'Cancel',
            chooseText: 'OK',
            preferredFormat: 'name',
            showInitial: true,
            showInput: true,
            showPalette: true,
            palette: [
                ["#000","#444","#666","#999","#ccc","#eee","#f3f3f3","#fff"],
                ["#f00","#f90","#ff0","#0f0","#0ff","#00f","#90f","#f0f"],
                ["#f4cccc","#fce5cd","#fff2cc","#d9ead3","#d0e0e3","#cfe2f3","#d9d2e9","#ead1dc"],
                ["#ea9999","#f9cb9c","#ffe599","#b6d7a8","#a2c4c9","#9fc5e8","#b4a7d6","#d5a6bd"],
                ["#e06666","#f6b26b","#ffd966","#93c47d","#76a5af","#6fa8dc","#8e7cc3","#c27ba0"],
                ["#c00","#e69138","#f1c232","#6aa84f","#45818e","#3d85c6","#674ea7","#a64d79"],
                ["#900","#b45f06","#bf9000","#38761d","#134f5c","#0b5394","#351c75","#741b47"],
                ["#600","#783f04","#7f6000","#274e13","#0c343d","#073763","#20124d","#4c1130"]
            ],
        }
    });

    $.fn.editabletypes.colour_picker = ColourPicker;

}(window.jQuery));
