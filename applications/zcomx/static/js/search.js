(function ($) {
    "use strict";
    var DatasetSource = function (options) {
        this.init(options);
    };

    DatasetSource.prototype = {
        constructor: DatasetSource,
        init: function (options) {
            this.options = options;
            this.bloodhound_options = {
                datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
                queryTokenizer: Bloodhound.tokenizers.whitespace,
                identify: function(obj) { return obj.id; },
                prefetch: this.prefetch_options(),
                remote: this.remote_options(),
            };
            var opts = $.extend(
                {},
                this.bloodhound_options,
                this.options
            );
            this.bloodhound = new Bloodhound(opts);
        },

        prefetch_options: function () {
            return {}
        },

        remote_options: function () {
            return {
                ajax : {
                    datatype: 'json',
                },
                wildcard: '%Q%',
                transform: function(response) {
                    return response.results;
                },
            }
        },
    };

    var BooksDatasetSource = function (options) {
        this.init(options);
    }
    $.fn.zco_utils.inherit(BooksDatasetSource, DatasetSource);
    $.extend(BooksDatasetSource.prototype, {
        prefetch_options: function () {
            var opts = $.extend(
                {},
                BooksDatasetSource.superclass.prefetch_options.call(this),
                {url: '/zcomx/static/data/books.json'}
            );
            return opts
        },

        remote_options: function () {
            var opts = $.extend(
                {},
                BooksDatasetSource.superclass.remote_options.call(this),
                {url: '/search/autocomplete.json/book?q=%Q%'}
            );
            return opts
        },
    });

    var CreatorsDatasetSource = function (options) {
        this.init(options);
    }
    $.fn.zco_utils.inherit(CreatorsDatasetSource, DatasetSource);
    $.extend(CreatorsDatasetSource.prototype, {
        prefetch_options: function () {
            var opts = $.extend(
                {},
                CreatorsDatasetSource.superclass.prefetch_options.call(this),
                {url: '/zcomx/static/data/creators.json'}
            );
            return opts
        },

        remote_options: function () {
            var opts = $.extend(
                {},
                CreatorsDatasetSource.superclass.remote_options.call(this),
                {url: '/search/autocomplete.json/creator?q=%Q%'}
            );
            return opts
        },
    });

    var Dataset = function (options) {
        this.init(options);
    };

    Dataset.prototype = {
        constructor: Dataset,
        init: function (name, label, source_class, options) {
            this.name = name;
            this.label = label;
            this.source_class = source_class;
            this.options = options;
        },

        dataset_options: function () {
            var source = new this.source_class();
            var standard_opts = {
              name: this.name,
              display: 'value',
              source: source.bloodhound,
              templates: {
                header: '<div class="tt-header">' + this.label + '</div>',
              }
            };
            var opts = $.extend(
                {},
                standard_opts,
                this.options
            );
            return opts
        },
    };

    var BooksDataset = function (options) {
        this.init('books', 'Books', BooksDatasetSource, options);
    }
    $.fn.zco_utils.inherit(BooksDataset, Dataset);

    var CreatorsDataset = function (options) {
        this.init('creators', 'Cartoonists', CreatorsDatasetSource, options);
    }
    $.fn.zco_utils.inherit(CreatorsDataset, Dataset);

    var SearchAutoComplete = function (element, options) {
        this.init(element, options);
    };

    SearchAutoComplete.prototype = {
        constructor: SearchAutoComplete,
        init: function (element, options) {
            this.$element = $(element);
            this.options = $.extend(
                {},
                $.fn.search_autocomplete.defaults,
                options
            );
            this.load();
            this.init_listeners();
            this._typeahead_selected = false;
        },

        load: function () {
            var that = this;
            var books_dataset = new BooksDataset();
            var creators_dataset = new CreatorsDataset();
            this.$element.typeahead(
                that.options.typeahead_options,
                creators_dataset.dataset_options(),
                books_dataset.dataset_options()
            ).bind('typeahead:selected', function(obj, datum) {
                that._typeahead_selected = true;
                window.location.href = '/search/autocomplete_selected/'
                    + datum.table
                    + '/'
                    + datum.id;
            });
            this.map_tab_to_downkey();
        },

        init_listeners: function() {
            var that = this;
            this.$element.keydown(function(e) {
                var enter_keyCode = 13;
                if(e.keyCode === enter_keyCode) {
                    that.submit_input_form()
                }
            });
        },

        map_tab_to_downkey: function() {
            var that = this;
            var ttTypeahead = this.$element.data('ttTypeahead');
            ttTypeahead.constructor.prototype._onTabKeyed = function(type, e) {
                e.preventDefault();
                var downarrow_keyCode = 40;
                var event = $.Event("keydown", {keyCode: downarrow_keyCode});
                that.$element.trigger(event);
            }
        },

        submit_input_form: function() {
            if (!this.options.form_input_selector) {
                return;
            }
            if (!this._typeahead_selected) {
                var $form_input = $(this.options.form_input_selector);
                $form_input.val(this.$element.val());
                $form_input.closest('form').submit();
            }
        }
    };

    $.fn.search_autocomplete = function (options) {
        var datakey = 'SearchAutoComplete';

        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = new SearchAutoComplete(this, options);
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.search_autocomplete.defaults = {
        typeahead_options: {
            highlight: true,
            hint: false,
        },
        form_input_selector: null,
    };

}(window.jQuery));
