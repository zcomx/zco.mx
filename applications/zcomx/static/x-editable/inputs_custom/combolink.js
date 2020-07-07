/**
Link name/url combo editable input.
Internally value stored as {name: "wikipedia", url: "http://en.wikipedia.org/wiki/X-Men"}

@class combolink
@extends abstractinput
@final
@example
<a href="#" id="link" data-type="link" data-pk="1">x-men</a>
<script>
$(function(){
    $('#link').editable({
        url: '/post',
        title: 'Enter a link name and url',
        value: {
            name: "wikipedia",
            url: "http://en.wikipedia.org/wiki/X-Men",
        }
    });
});
</script>
**/

(function ($) {
    "use strict";

    var ComboLink = function (options) {
        this.init('combolink', options, ComboLink.defaults);
    };

    //inherit from Abstract input
    $.fn.editableutils.inherit(ComboLink, $.fn.editabletypes.abstractinput);

    $.extend(ComboLink.prototype, {

        /**
        Renders input from tpl

        @method render()
        **/
        render: function() {
           this.$input.closest('form').find('.editable-error-block').last().remove();
           this.$input = this.$tpl.find('input');
        },

        /**
        Default method to show value in element. Can be overwritten by display option.

        @method value2html(value, element)
        **/
        value2html: function(value, element) {
            if(!value) {
                $(element).empty();
                return;
            }

            var link = $(
                        '    <div class="field_container field_label editable-click">'
                      + '        <div>' + value.name + '</div>'
                      + '    </div>'
                      + '    <div class="field_container editable-click">'
                      + '        <div>' + value.url + '</div>'
                      + '    </div>'
                    );
            $(element).html(link);
        },

        /**
        Gets value from element's html

        @method html2value(html)
        **/
        html2value: function(html) {
          return null;
        },

       /**
        Converts value to string.
        It is used in internal comparing (not for sending to server).

        @method value2str(value)
       **/
       value2str: function(value) {
           var str = '';
           if(value) {
               for(var k in value) {
                   str = str + k + ':' + value[k] + ';';
               }
           }
           return str;
       },

       /*
        Converts string to value. Used for reading value from 'data-value' attribute.

        @method str2value(str)
       */
       str2value: function(str) {
           /*
           this is mainly for parsing value defined in data-value attribute.
           If you will always set value by javascript, no need to overwrite it
           */
           return str;
       },

       /**
        Sets value of input.

        @method value2input(value)
        @param {mixed} value
       **/
       value2input: function(value) {
           if(!value) {
             return;
           }
           this.$input.filter('[name="name"]').val(value.name);
           this.$input.filter('[name="url"]').val(value.url);
       },

       /**
        Returns value of input.

        @method input2value()
       **/
       input2value: function() {
           return {
              name: this.$input.filter('[name="name"]').val(),
              url: this.$input.filter('[name="url"]').val(),
           };
       },

        /**
        Activates input: sets focus on the first field.

        @method activate()
       **/
       activate: function() {
            this.$input.filter('[name="name"]').focus();
       },

       /**
        Attaches handler to submit form in case of 'showbuttons=false' mode

        @method autosubmit()
       **/
       autosubmit: function() {
           this.$input.keydown(function (e) {
                if (e.which === 13) {
                    $(this).closest('form').submit();
                }
           });
       }
    });

    ComboLink.defaults = $.extend({}, $.fn.editabletypes.abstractinput.defaults, {
        tpl: '<div class="editable_combolink_container">'
           + '  <div class="editable-combolink">'
           + '    <label for="name">Name: </label>'
           + '    <input type="text" name="name" class="form-control input-sm">'
           + '  </div>'
           + '  <div class="editable-combolink">'
           + '    <label for="url">Url: </label>'
           + '    <input type="text" name="url" class="form-control input-sm">'
           + '  </div>'
           + '  <div class="editable-error-block help-block"></div>'
           + '  <div class="panel panel-default instruction">'
           + '    <div class="panel-heading">'
           + '      <h4 class="panel-title">Example</h4>'
           + '    </div>'
           + '    <div class="panel-body">'
           + '      <div class="text-muted">'
           + '          <dl class="dl-horizontal">'
           + '          <dt>Name:</dt><dd>grand comics</dd>'
           + '          <dt>URL:</dt><dd>http://www.comics.org/issue/862697</dd>'
           + '          </dl>'
           + '          The resulting link is: <a href="http://www.comics.org/issue/862697" target="_blank" rel="noopener noreferrer">grand comics</a>'
           + '      </div>'
           + '    </div>'
           + '  </div>'
           + '</div>',

        inputclass: ''
    });

    $.fn.editabletypes.combolink = ComboLink;

}(window.jQuery));
