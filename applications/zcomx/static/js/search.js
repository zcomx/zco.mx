(function( $ ) {
    "use strict";

    $(document).ready(function(){
        var typeahead_selected = false;

        var books = new Bloodhound({
          datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
          queryTokenizer: Bloodhound.tokenizers.whitespace,
          prefetch: {
            url: '/zcomx/static/data/books.json',
          },
          remote: {
            url: '/search/autocomplete_books.json?q=%Q%',
            ajax : {
                datatype: 'json',
            },
            wildcard: '%Q%',
            transform: function(response) {
                return response.results;
            },
          },
        });

        var creators = new Bloodhound({
          datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
          queryTokenizer: Bloodhound.tokenizers.whitespace,
          prefetch: {

            url: '/zcomx/static/data/creators.json',
          },
          remote: {
            url: '/search/autocomplete_creators.json?q=%Q%',
            ajax : {
                datatype: 'json',
            },
            wildcard: '%Q%',
            transform: function(response) {
                return response.results;
            },
          },
        });

        $('#search_kw_input.typeahead').typeahead({
            highlight: true,
            hint: false,
        },
        {
          name: 'creators',
          display: 'value',
          source: creators,
          templates: {
            header: '<span class="tt-header">Cartoonists</span>',
          }
        },
        {
          name: 'books',
          display: 'value',
          source: books,
          templates: {
            header: '<span class="tt-header">Books</span>'
          }
        }).bind('typeahead:selected', function(obj, datum) {
            typeahead_selected = true;
            window.location.href = '/search/autocomplete_selected/'
                + datum.table
                + '/'
                + datum.id;
        });

        var $clear = $('<span class="editable-clear-x"></span>');
        var $input = $('#search_kw_input.typeahead');

        function clear_input () {
            $input.val(null);
        }

        $input.after($clear)
            .css('padding-right', 24)
            .keydown(function(e) {
                if(e.keyCode === 13) {
                    if (!typeahead_selected) {
                        var $form_input = $('#form_kw_input');
                        $form_input.val($('#search_kw_input').val());
                        $form_input.closest('form').submit();
                    }
                }
            })
            .keyup($.proxy(function(e) {
                //arrows, enter, tab, etc
                if(~$.inArray(e.keyCode, [40,38,9,13,27])) {
                    return;
                }
                clearTimeout(this.t);
                var that = this;
                this.t = setTimeout(function() {
                    that.toggleClear(e);
                }, 100);
            }, this))
            .parent().css('position', 'relative');
        $clear.click($.proxy(clear_input, this));
    });


}(window.jQuery));
