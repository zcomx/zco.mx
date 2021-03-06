/*
 * MetadataCrudInput: input for metadata_crud
 */
(function ($) {
    "use strict";

    var MetadataCrudInput = function (element, type, options) {
        this.init(element, type, options);
    };

    MetadataCrudInput.prototype = {
        constructor: MetadataCrudInput,
        init: function (element, type, options) {
            this.$element = $(element);
            this.$type = type;
            this.options = $.extend(
                {},
                $.fn.metadata_crud_input.defaults,
                options
            );
            this.$input = this.create();
            this.$element.append(this.$input);
            this.post_create();
        },

        create: function () {
            return;
        },

        post_create: function () {
            var that = this;

            this.$input.attr('name', this.options.name)
                .addClass('metadata_crud')
                .addClass(this.options.class)

            if (this.options.events) {
                $.each(this.options.events, function(event, callback) {
                    that.$input.on(event, callback);
                });
            }
        },
    };

    var SelectMetadataCrudInput = function (element, type, options) {
        this.init(element, type,
            $.extend(
                {'display_zero': false},
                options
            )
        );
    }
    $.fn.zco_utils.inherit(SelectMetadataCrudInput, MetadataCrudInput);
    $.extend(SelectMetadataCrudInput.prototype, {
        create: function () {
            var input, option_tag;
            var that = this;
            input = $('<select class="form-control"></select>');
            $.each(this.options.source, function(idx, source_data) {
                option_tag = $("<option></option>")
                     .val(source_data.value)
                     .attr('style', 'color:#333;')
                     .text(source_data.text);
                if ('value' in source_data && source_data.value === that.options.value) {
                     option_tag.attr('selected', 'selected');
                }
                if (!that.options.display_zero) {
                    if (source_data.value === '' ) {
                        option_tag.attr('disabled', 'disabled');
                        option_tag.attr('style', 'display:none;');
                        option_tag.text('Click to edit');
                    }
                }
                input.append(option_tag);
            });
            return input;
        },
    });

    var TextMetadataCrudInput = function (element, type, options) {
        this.init(element, type, options);
    }
    $.fn.zco_utils.inherit(TextMetadataCrudInput, MetadataCrudInput);
    $.extend(TextMetadataCrudInput.prototype, {
        create: function () {
            var input;
            input = $('<input class="form-control" type="text">');
            input.attr('value', this.options.value || '');
            return input;
        },

        post_create: function () {
            TextMetadataCrudInput.superclass.post_create.call(this);
            this.renderClear();
        },


        /*
         * renderClear, toggleClear, and clear copied from
         * ! X-editable - v1.5.1
         * In-place editing with Twitter Bootstrap, jQuery UI or pure jQuery
         * http://github.com/vitalets/x-editable
         * Copyright (c) 2013 Vitaliy Potapov; Licensed MIT
         */
        //render clear button
        renderClear:  function() {
           this.$clear = $('<span class="editable-clear-x"></span>');
           this.$input.after(this.$clear)
                      .css('padding-right', 24)
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
           this.$clear.click($.proxy(this.clear, this));
        },

        //show / hide clear button
        toggleClear: function(e) {
            if(!this.$clear) {
                return;
            }
            var len = this.$input.val().length,
            visible = this.$clear.is(':visible');
            if(len && !visible) {
                this.$clear.show();
            }
            if(!len && visible) {
                this.$clear.hide();
            }
        },

        clear: function() {
           this.$clear.hide();
           this.$input.val('').focus();
        }
    });

    $.fn.metadata_crud_input = function (type, options) {
        var datakey = 'metadata_crud_input';
        return this.each(function () {
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                var obj = null;
                switch(type) {
                    case 'select':
                        obj = new SelectMetadataCrudInput(this, type, options);
                        break;
                    default:
                        obj = new TextMetadataCrudInput(this, type, options);
                }
                $this.data(datakey, (data = obj));
            }
        });
    };

    $.fn.metadata_crud_input.defaults = {
        'class': '',
        events: [],
        'name': '',
        source: null,
        value: null,
    };

}(window.jQuery));

(function( $ ) {
    "use strict";
    $.fn.metadata_crud = function (url, book_id, options) {
        var settings = $.extend(
            true,
            {},
            $.fn.metadata_crud.defaults,
            {url: url, book_id: book_id},
            options
        );

        var vars = {
            'containers': {},
            'data': null,
            'form': null,
        };

        var _data = null;

        // table_field: tooltip title option
        var _tooltip_titles = {
            'publication_metadata_republished':
                  '<p><b>First Publication</b> - this work has never been published before</p> <p><b>Republication</b> - this work has been previously published online or on paper</p>',
            'publication_metadata_published_type':
                  '<p><b>Whole</b> - this work was previously published in whole (online or paper)<p><b>Serial</b> - this work is a collection of serialized stories or stories from anthologies previously published (online or paper)</p>',
            'publication_metadata_is_anthology':
                  '<p>Was this work previously published as part of an anthology?</p>',
            'publication_metadata_publisher': function() {
                  var published_format = methods._get_input($(this), 'published_format');
                  if (published_format.val() === 'digital') {
                      return '<p>The name of the site where the work was first published, eg username.tumblr.com or mydomain.com.</p><dl> <dt>Right</dt><dd>username.tumblr.com</dd> <dt>Wrong</dt><dd>https://www.tumblr.com/explore/trending?aaa=123</dd> </dl> ';
                  } else {
                      return '<p>The name of the small press/publishing company.</p>'
                  }
            },
            'publication_metadata_from_month': '<p>The month the work was first published (online or paper). If published in parts, the month publishing started.</p>',
            'publication_metadata_to_month': '<p>If published in parts, the year publishing was completed (online or paper).</p>',

            'publication_serial_serial_title': function() {
                  var is_anthology = vars.containers['is_anthology'].find('select').val();
                  if (is_anthology === 'yes') {
                      return '<p>The name of the anthology the work was published in.</p>';
                  } else {
                      return '<p>The name the book was originally published as.</p>';
                  }
            },
            'publication_serial_published_name': '<p>The name of your story as published in the anthology.</p>',
            'is_derivative': 'Is this work a derivative? A derivative is based on another creator`s work but adapted and modified. To publish a derivative, the other creator`s original work must have been published under a Creative Commons licence, ie BY, BY-SA, BY-NC or BY-NC-SA. </p>',
            'derivative_title': '<p>The title of the original work you adapted or modified.</p>',
            'derivative_creator': '<p>The name of the creator who`s work you adapted or modified.</p>',
            'derivative_from_year': '<p>The year the work you adapted or modified was published.</p>',
        }

        _tooltip_titles['publication_serial_publisher'] = _tooltip_titles['publication_metadata_publisher'];
        _tooltip_titles['publication_serial_from_month'] = _tooltip_titles['publication_metadata_from_month'];
        _tooltip_titles['publication_serial_to_month'] = _tooltip_titles['publication_metadata_to_month'];

        var methods = {
            _append_error: function(container, msg) {
                var error_wrapper = container.find('.error_wrapper');
                if (error_wrapper.length === 0) {
                    error_wrapper = $(
                            '<div class="error_wrapper">'
                          + '    <div class="help-block"></div>'
                          + '</div>'
                        );
                    container.append(error_wrapper);
                }
                if (msg) {
                    error_wrapper.addClass('has-error').show();
                    error_wrapper.find('.help-block').text(msg);
                }
            },

            _append_row: function(elem, input_data, options) {
                var icon, input, row_options, row;

                input = methods._create_input(input_data, options);

                icon = null;
                if (_tooltip_titles[input_data._input_name]) {
                    icon = $.fn.zco_utils.tooltip(
                        input_data._input_name,
                        _tooltip_titles[input_data._input_name]
                    );
                }

                row_options = {
                    'label': input_data.label,
                    'info': icon,
                };
                row = methods._row_container(input, input_data._class_name, row_options);
                options.class && row.addClass(options.class);
                row.appendTo(elem);

                return row;
            },

            _append_input: function(elem, input_data, options) {
                var input = methods._create_input(input_data, options);
                elem.append(input);
                return input;
            },

            _create_form: function(elem) {
                var form_div = $(
                    '<div><form></form></div>'
                ).appendTo(elem);
                vars.form = form_div.find('form');

                methods._whole_container(
                    _data.publication_metadata.fields,
                    _data.publication_metadata.record
                );

                var serials_container = $('<div class="serials_container"></div>')
                    .addClass('hidden')
                    .appendTo(vars.form);
                vars.containers['serials_container'] = serials_container;

                if (! _data.publication_serial.records.length) {
                    _data.publication_serial.records = [_data.publication_serial.default];
                }

                $.each(_data.publication_serial.records, function(index, record) {
                    methods._serial_container(_data.publication_serial.fields, record).appendTo(serials_container);
                });

                methods._sequence_serials(vars.form);

                methods._derivative_container(
                    _data.derivative.fields,
                    _data.derivative.record
                );

                $('<input type="hidden" name="_action" value="update"/>').appendTo(vars.form);
                $('<button id="done-btn" class="btn btn-default">done</button>').appendTo(vars.form);
                $('#done-btn').click(function(e){
                    $(this).closest('form').submit();
                    e.preventDefault();
                });

                vars.form.submit(function(e){
                    methods._hide_errors();
                    methods._sequence_serials(vars.form);
                    $.ajax({
                        url: settings.url,
                        type: 'POST',
                        dataType: 'json',
                        data: $(this).serialize(),
                        complete: function (jqXHR, textStatus) {
                            if($.web2py !== undefined) {
                                var done_button = vars.form.find('button#done-btn').first();
                                $.web2py.enableElement(done_button);
                            }
                        },
                        success: function (data, textStatus, jqXHR) {
                            if (data.status === 'error') {
                                methods._show_errors(data);
                            } else {
                                if (settings.on_submit_success) {
                                    settings.on_submit_success(elem);
                                }
                            }
                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            console.log('error textStatus: %o', textStatus);
                        }
                    });
                    e.preventDefault();
                });
            },

            _create_input: function(input_data, options) {
                var input;
                var input_options = {
                    'class': input_data._class_name + '_input',
                    events: options.events,
                    name: input_data._input_name,
                    source: input_data.source,
                    value: options.value,
                    display_zero: options.display_zero || false,
                };

                input = $('<div class="editable-input"></div>')
                    .metadata_crud_input(input_data.type, input_options);

                return input;
            },

            _derivative_container: function(fields, record) {
                $.each(fields, function(idx, option) {
                    var prefix = option.name == 'is_derivative' ?  '' : 'derivative_';
                    fields[option.name]._class_name = prefix + option.name;
                    fields[option.name]._input_name = prefix + option.name;
                });

                vars.containers['is_derivative'] = methods._append_row(
                    vars.form,
                    fields.is_derivative,
                    {
                        value: record.is_derivative,
                        events: {
                            'change': function(e) {
                                methods._show();
                            }
                        }
                    }
                );

                var derivative_container = $('<div class="derivative_container"></div>')
                    .addClass('hidden')
                    .appendTo(vars.form);
                vars.containers['derivative_container'] = derivative_container;

                var display_fields = [
                    'title',
                    'from_year',
                    'to_year',
                    'creator',
                    'cc_licence_id'
                ];

                $.each(display_fields, function(idx, field) {
                    methods._append_row(
                        derivative_container,
                        fields[field],
                        {value: record[field]}
                    );
                });
            },

            _endswith: function(str, suffix) {
                return str.indexOf(suffix, str.length - suffix.length) !== -1;
            },

            _get_input: function(context, name) {
                var container = context.closest('.whole_container');
                var table = 'publication_metadata';
                if (!container.length) {
                    container = context.closest('.serial_container');
                    table = 'publication_serial';
                }
                if (!container.length) {
                    return;
                }
                return container.find('.' + table + '_' + name + '_input').first();
            },

            _hide_errors: function(data) {
                vars.form.find('.error_wrapper').hide()
                    .removeClass('has-error');
            },

            _load: function(elem) {
                $.ajax({
                    url: settings.url,
                    type: 'POST',
                    dataType: 'json',
                    data: $.param({_action: 'get'}),
                    success: function (data, textStatus, jqXHR) {
                        _data = data.data;
                        methods._create_form(elem);
                        methods._show();
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log('textStatus: %o', textStatus);
                    }
                });
            },

            _onchange_is_anthology: function(input) {
                var that = this;
                var update_func = function() {};
                if (input.val() === 'yes') {
                    /* User switched to anthology */
                    update_func = function(input) {
                        input.val('');          //Clear
                    }
                } else {
                    /* User switched to serial */
                    update_func = function(input) {
                        // Don't overwrite existing value.
                        if (!input.val()) {
                            input.val(_data.publication_serial.default.serial_title);
                        }
                    }
                }

                $.each(vars.containers['serials_container'].find('.serial_container'), function(idx, container) {
                    var input = that._get_input($(container), 'serial_title');
                    if (input) {
                        update_func(input);
                    }
                });
            },

            _row_container: function(anchor, name, options) {
                var link = $(
                            '<div id="row_container_' + name + '" class="row_container">'
                          + '    <div class="arrow_container"></div>'
                          + '    <div class="field_label">' + options.label + '</div>'
                          + '    <div class="field_container"></div>'
                          + '    <div class="field_info"></div>'
                          + '</div>'
                        );

                var container = link.find('.field_container').eq(0);
                container.append(anchor);
                container.addClass('field_container_' + name);
                if (options.info) {
                    link.find('.field_info').append(options.info);
                }
                return link;
            },

            _sequence_serials: function(form){
                var base, suffix;
                $.each(form.find('.serial_container'), function(index, container) {
                    $.each($(container).find(':input'), function (idx, input){
                        suffix = '__' + index;
                        if (!methods._endswith($(input).attr('name'), suffix)) {
                            base = $(input).attr('name').split('__')[0];
                            $(input).attr('name', base + suffix);
                        }
                    });
                });
           },

            _serial_button: function(type) {
                var that = this;
                if (typeof type == 'undefined') {
                    type = 'plus';
                }

                var button = $(
                        '<div class="serial_button_container">'
                      + '<a class="btn btn-default btn-xs " href="#">'
                      + '<i class="glyphicon glyphicon-' + type + '"></i>'
                      + '</a>'
                      + '</div>'
                    )

                if (type == 'plus') {
                    button.find('a').first().click(function(e) {
                        var is_anthology = vars.containers['is_anthology'].find('select').val();
                        var last_serial = vars.containers['serials_container'].find('.serial_container').last();
                        if (last_serial) {
                            var klon = last_serial.clone(true).appendTo(vars.containers['serials_container']);
                            last_serial.find('select').each(function(i) {
                                klon.find('select').eq(i).val($(this).val());
                                if (is_anthology === 'yes' && $(this).hasClass('publication_serial_story_number_input')) {
                                    klon.find('select').eq(i).val($(this).val() / 1 + 1);
                                }
                                if (is_anthology === 'no' && $(this).hasClass('publication_serial_serial_number_input')) {
                                    klon.find('select').eq(i).val($(this).val() / 1 + 1);
                                }
                            })
                            klon.find('.serial_button_container').replaceWith(methods._serial_button('minus'));
                            klon.appendTo(vars.containers['serials_container']);
                            methods._sequence_serials(vars.form);
                            //clear cloned tooltips, so they are recreated
                            klon.find('.zco_tooltip').removeData('bs.tooltip');
                        }
                        e.preventDefault();
                    });
                }

                if (type == 'minus') {
                    button.find('a').first().click(function(e) {
                        $(this).closest('.serial_container').remove();
                        methods._sequence_serials(vars.form);
                        e.preventDefault();
                    });
                }
                return button;
            },

            _serial_container: function(fields, record) {
                $.each(fields, function(idx, option) {
                    fields[option.name]._class_name = 'publication_serial_' + option.name;
                    fields[option.name]._input_name = 'publication_serial_' + option.name;
                });

                var serial_count = $('.serial_container').length;
                var button_type = serial_count > 0 ? 'minus' : 'plus';
                var serial_container = $('<div class="serial_container"></div>')
                methods._serial_button(button_type).appendTo(serial_container);

                var display_fields = {
                    'serial_title': {},
                    'serial_number': {'display_zero': true},
                    'published_name': {},
                    'story_number': {'display_zero': true},
                    'published_format': {
                        events: {
                            'change': function(e) {
                                methods._show_published_format($(e.target));
                            }
                        }
                    },
                    'publisher_type': {
                        events: {
                            'change': function(e) {
                                methods._show_publisher_type($(e.target));
                            }
                        }
                    },
                    'publisher': {},
                    'from_month': {},
                    'to_month': {},
                }

                var append_fields = {
                    'from_month': ['from_year', {}],
                    'to_month': ['to_year', {}],
                }

                $.each(display_fields, function(field, options) {
                    var $row = methods._append_row(
                        serial_container,
                        fields[field],
                        $.extend({value: record[field]}, options)
                    );
                    if (append_fields[field]) {
                        var append_field = append_fields[field][0];
                        var $append_to = $row.find('.field_container').eq(0);
                        var options = append_fields[field][1];
                        methods._append_input(
                            $append_to,
                            fields[append_field],
                            $.extend({value: record[append_field]}, options)
                        );
                    }
                });

                return serial_container;
            },

            _show: function() {
                var shows = {
                    'republished': true,
                    'published_type': false,
                    'is_anthology': false,
                    'whole_container': false,
                    'serials_container': false,
                    'is_derivative': true,
                    'derivative_container': false,
                }
                var republished = vars.containers['republished'].find('select').val();
                if (!republished) {
                    shows['is_derivative'] = false;
                } else if (republished == 'repub') {
                    shows['published_type'] = true;
                    var published_type = vars.containers['published_type'].find('select').val();
                    if (published_type == 'whole') {
                        shows['whole_container'] = true;
                        methods._show_published_format(
                            methods._get_input(vars.containers['whole_container'], 'published_format')
                        );
                        methods._show_publisher_type(
                            methods._get_input(vars.containers['whole_container'], 'publisher_type')
                        );
                    } else if (published_type == 'serial') {
                        shows['is_anthology'] = true;
                        shows['serials_container'] = true;
                        var is_anthology = vars.containers['is_anthology'].find('select').val();
                        $.each(vars.containers['serials_container'].find('.serial_container'), function( idx, serial_container) {
                            methods._show_is_anthology($(serial_container), is_anthology);
                            methods._show_published_format(
                                methods._get_input($(serial_container), 'published_format')
                            );
                            methods._show_publisher_type(
                                methods._get_input($(serial_container), 'publisher_type')
                            );
                        });
                    } else {
                        shows['is_derivative'] = false;
                    }
                }

                if (shows['is_derivative'] == true) {
                    var is_derivative = vars.containers['is_derivative'].find('select').val();
                    if (is_derivative === 'yes') {
                        shows['derivative_container'] = true;
                    }
                }

                $.each(shows, function(selector, is_shown) {
                    if (is_shown) {
                        vars.containers[selector].removeClass('hidden');
                    } else {
                        vars.containers[selector].addClass('hidden');
                    }
                });
            },

            _show_is_anthology: function($serial, is_anthology) {
                var serial_title = methods._get_input($serial, 'serial_title');
                var serial_title_label = serial_title.closest('.row_container')
                    .find('.field_label').first();
                var serial_number = methods._get_input($serial, 'serial_number');
                var serial_number_label = serial_number.closest('.row_container')
                    .find('.field_label').first();
                var published_name = methods._get_input($serial, 'published_name');
                var story_number = methods._get_input($serial, 'story_number');
                if (is_anthology === 'yes') {
                    serial_title_label.text('Anthology Title');
                    serial_number_label.text('Anthology Number');
                    published_name.closest('.row_container').removeClass('hidden');
                    story_number.closest('.row_container').removeClass('hidden');
                } else {
                    serial_title_label.text('Original Book Title');
                    serial_number_label.text('Original Book Number');
                    published_name.closest('.row_container').addClass('hidden');
                    story_number.closest('.row_container').addClass('hidden');
                }
            },

            _show_errors: function(data) {
                if (data.msg) {
                    methods._append_error(vars.form, data.msg);
                }
                $.each(data.fields, function(field, msg) {
                    var parts = field.split('__');
                    var fieldname = parts[0];
                    var index = parts[1];
                    if (index) {
                        var s = $('.serial_container').eq(index)
                        var f = s.find('.field_container_' + fieldname).first();
                        var elem = $('.serial_container').eq(index).find('.field_container_' + fieldname).first();
                        if (elem) {
                            methods._append_error(elem, msg);
                        }
                    }else{
                        methods._append_error($('.field_container_' + fieldname), msg);
                    }
                });
            },

            _show_published_format: function(elem) {
                var value = elem.val();
                var publisher_type = methods._get_input(elem, 'publisher_type');
                var publisher = methods._get_input(elem, 'publisher');
                var publisher_label = publisher.closest('.row_container')
                    .find('.field_label').first();
                if (value == 'digital') {
                    publisher_type.closest('.row_container').addClass('hidden');
                    publisher_label.text('Site Name');
                    publisher.attr('placeholder', 'tumblr.com');
                    publisher.closest('.row_container').removeClass('hidden');
                } else {
                    publisher_type.closest('.row_container').removeClass('hidden');
                    publisher_label.text('Press Name');
                    publisher.attr('placeholder', 'Acme Publishing Inc');
                    methods._show_publisher_type(publisher_type);
                }

            },

            _show_publisher_type: function(elem) {
                var value = elem.val();
                var published_format = methods._get_input(elem, 'published_format');
                var publisher = methods._get_input(elem, 'publisher');
                if (published_format.val() == 'paper' && value == 'self') {
                    publisher.closest('.row_container').addClass('hidden');
                } else {
                    publisher.closest('.row_container').removeClass('hidden');
                }
            },

            _whole_container: function(fields, record) {
                $.each(fields, function(idx, option) {
                    fields[option.name]._class_name = 'publication_metadata_' + option.name;
                    fields[option.name]._input_name = 'publication_metadata_' + option.name;
                });

                var republished = '';
                if (record.republished != null && record.republished !== '') {
                    republished = record.republished ? 'repub' : 'first';
                }

                vars.containers['republished'] = methods._append_row(
                    vars.form,
                    fields.republished,
                    {
                        value: republished,
                        events: {
                            'change': function(e) {
                                methods._show();
                            }
                        },
                    }
                );

                vars.containers['published_type'] = methods._append_row(
                    vars.form,
                    fields.published_type,
                    {
                        value: record.published_type || '',
                        'class': 'hidden',
                        events: {
                            'change': function(e) {
                                methods._show();
                            }
                        }
                    }
                );

                vars.containers['is_anthology'] = methods._append_row(
                    vars.form,
                    fields.is_anthology,
                    {
                        value: record.is_anthology ? 'yes' : 'no',
                        'class': 'hidden',
                        events: {
                            'change': function(e) {
                                methods._onchange_is_anthology($(e.target));
                                methods._show();
                            }
                        }
                    }
                );

                var whole_container = $('<div class="whole_container"></div>')
                    .addClass('hidden')
                    .appendTo(vars.form);
                vars.containers['whole_container'] = whole_container;

                var display_fields = {
                    'published_name': {},
                    'published_format': {
                        events: {
                            'change': function(e) {
                                methods._show_published_format($(e.target));
                            }
                        }
                    },
                    'publisher_type': {
                        events: {
                            'change': function(e) {
                                methods._show_publisher_type($(e.target));
                            }
                        }
                    },
                    'publisher': {},
                    'from_month': {},
                    'to_month': {},
                }

                var append_fields = {
                    'from_month': ['from_year', {}],
                    'to_month': ['to_year', {}],
                }

                $.each(display_fields, function(field, options) {
                    var $row = methods._append_row(
                        whole_container,
                        fields[field],
                        $.extend({value: record[field]}, options)
                    );
                    if (append_fields[field]) {
                        var append_field = append_fields[field][0];
                        var $append_to = $row.find('.field_container').eq(0);
                        var options = append_fields[field][1];
                        methods._append_input(
                            $append_to,
                            fields[append_field],
                            $.extend({value: record[append_field]}, options)
                        );
                    }
                });
            }
        };

        return this.each( function(index, elem) {
            var datakey = 'metadata_crud';
            var $this = $(this),
                data = $this.data(datakey)

            if (!data) {
                methods._load.apply(this, [elem]);
                $this.data(datakey, true);
            }
        });
    };

    $.fn.metadata_crud.defaults = $.extend(
        true,
        {},
        {
            'on_submit_success': null,
        }
    );

}( jQuery ));
