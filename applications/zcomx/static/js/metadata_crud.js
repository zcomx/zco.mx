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

        var containers = {};
        var form = null;
        var _data = null;

        var methods = {
            _append_error: function(container, msg) {
                var error_wrapper = container.find('.error_wrapper');
                if (error_wrapper.length === 0) {
                    error_wrapper = $(
                            '<div class="error_wrapper has-error">'
                          + '    <div class="help-block"></div>'
                          + '</div>'
                        );
                    container.append(error_wrapper);
                }
                error_wrapper.show();
                var error_div = error_wrapper.find('.help-block');
                error_div.text(msg);
            },

            _append_row: function(elem, input_data, options) {
                var input, option_tag, row_options, row;
                if (input_data.type === 'select'){
                    input = $('<select class="form-control"></select>');
                    $.each(input_data.source, function(idx, source_data) {
                        option_tag = $("<option></option>")
                             .val(source_data.value)
                             .attr('style', 'color:#333;')
                             .text(source_data.text);
                        if ('value' in source_data && source_data.value === options.value) {
                             option_tag.attr('selected', 'selected');
                        }
                        if (source_data.value === '' ) {
                             option_tag.attr('disabled', 'disabled');
                             option_tag.attr('style', 'display:none;');
                             option_tag.text('Click to edit');
                        }
                        input.append(option_tag);
                    });
                } else {
                    input = $('<input class="form-control" type="text">');
                    input.attr('value', options.value);
                }

                input.attr('name', input_data._input_name)
                    .addClass('metadata_crud')
                    .addClass(input_data._class_name + '_input')

                if (options.events) {
                    $.each(options.events, function(event, callback) {
                        input.on(event, callback);
                    });
                }

                row_options = {'label': input_data.label};
                row = methods._row_container(input, input_data._class_name, row_options);
                if (options.class) {
                    row.addClass(options.class);
                };
                row.appendTo(elem);

                return row;
            },

            _create_form: function(elem, data) {
                var metadata_fields = data.publication_metadata;
                var metadata = data.metadata;
                var serial_fields = data.publication_serial;
                var serials = data.serials;
                var derivative_fields = data.derivative_fields;
                var derivative = data.derivative;

                var row;
                var form_div = $(
                    '<div>'
                  + '<form id="idForm">'
                  + '</form>'
                  + '</div>'
                );
                form_div.appendTo(elem);
                form = form_div.find('form');

                $.each(metadata_fields, function(idx, option) {
                    metadata_fields[option.name]._class_name = 'publication_metadata_' + option.name;
                    metadata_fields[option.name]._input_name = 'publication_metadata_' + option.name;
                });

                var republished = '';
                if (metadata.republished !== '') {
                    republished = metadata.republished ? 'repub' : 'first';
                }

                row = methods._append_row(
                    form,
                    metadata_fields.republished,
                    {
                        value: republished,
                        events: {
                            'change': function(e) {
                                methods._show();
                            }
                        }
                    }
                );
                containers['republished'] = row;

                row = methods._append_row(
                    form,
                    metadata_fields.published_type,
                    {
                        value: metadata.published_type,
                        class: 'hidden',
                        events: {
                            'change': function(e) {
                                methods._show();
                            }
                        }
                    }
                );
                containers['published_type'] = row;

                var whole_container = $('<div class="whole_container"></div>')
                    .addClass('hidden')
                    .appendTo(form);
                containers['whole_container'] = whole_container;
                methods._append_row(whole_container, metadata_fields.published_name,
                    {
                        value: metadata.published_name,
                    }
                );
                methods._append_row(whole_container, metadata_fields.published_format,
                    {
                        value: metadata.published_format,
                        events: {
                            'change': function(e) {
                                methods._show_published_format($(e.target));
                            }
                        }
                    }
                );
                methods._append_row(whole_container, metadata_fields.publisher_type,
                    {
                        value: metadata.publisher_type,
                        events: {
                            'change': function(e) {
                                methods._show_publisher_type($(e.target));
                            }
                        }
                    }
                );
                methods._append_row(whole_container, metadata_fields.publisher,
                    {
                        value: metadata.publisher,
                    }
                );

                methods._append_row(whole_container, metadata_fields.from_year,
                    {
                        value: metadata.from_year,
                    }
                );

                methods._append_row(whole_container, metadata_fields.to_year,
                    {
                        value: metadata.to_year,
                    }
                );


                var serials_container = $('<div class="serials_container"></div>')
                    .addClass('hidden')
                    .appendTo(form);
                containers['serials_container'] = serials_container;


                if (! serials.length) {
                    serials = [data.default.publication_serial];
                }

                $.each(serials, function(index, record) {
                    methods._serial_container(serial_fields, record).appendTo(serials_container);
                });

                $.each(derivative_fields, function(idx, option) {
                    var prefix = option.name == 'is_derivative' ?  '' : 'derivative_';
                    derivative_fields[option.name]._class_name = prefix + option.name;
                    derivative_fields[option.name]._input_name = prefix + option.name;
                });

                row = methods._append_row(
                    form,
                    derivative_fields.is_derivative,
                    {
                        value: derivative.is_derivative,
                        events: {
                            'change': function(e) {
                                methods._show();
                            }
                        }
                    }
                );
                containers['is_derivative'] = row;

                var derivative_container = $('<div class="derivative_container"></div>')
                    .addClass('hidden')
                    .appendTo(form);
                containers['derivative_container'] = derivative_container;
                methods._append_row(derivative_container, derivative_fields.title,
                    {
                        value: derivative.title,
                    }
                );
                methods._append_row(derivative_container, derivative_fields.from_year,
                    {
                        value: derivative.from_year,
                    }
                );
                methods._append_row(derivative_container, derivative_fields.to_year,
                    {
                        value: derivative.to_year,
                    }
                );
                methods._append_row(derivative_container, derivative_fields.creator,
                    {
                        value: derivative.creator,
                    }
                );
                methods._append_row(derivative_container, derivative_fields.cc_licence_id,
                    {
                        value: derivative.cc_licence_id,
                    }
                );

                $('<input type="hidden" name="_action" value="update"/>').appendTo(form);
                $('<button id="done-btn" class="btn btn-default">done</button>').appendTo(form);
                $('#done-btn').click(function(e){
                    $(this).closest('form').submit();
                    e.preventDefault();
                });

                form.submit(function(e){
                    methods._hide_errors();
                    methods._sequence_serials(form);
                    $.ajax({
                        url: settings.url,
                        type: 'POST',
                        dataType: 'json',
                        data: $(this).serialize(),
                        complete: function (jqXHR, textStatus) {
                            if($.web2py !== undefined) {
                                var done_button = form.find('button#done-btn').first();
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

            _endswith: function(str, suffix) {
                return str.indexOf(suffix, str.length - suffix.length) !== -1;
            },

            _hide_errors: function(data) {
                form.find('.error_wrapper').hide();
            },

            _load: function(elem) {
                var metadata, derivative_data;
                $.ajax({
                    url: settings.url,
                    type: 'POST',
                    dataType: 'json',
                    data: $.param({_action: 'get'}),
                    success: function (data, textStatus, jqXHR) {
                        _data = data.data;
                        methods._create_form(elem, data.data);
                        methods._show();
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log('textStatus: %o', textStatus);
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
                    link.find('.field_info').html(options.info);
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
                        var last_serial = containers['serials_container'].find('.serial_container').last();
                        if (last_serial) {
                            var klon = last_serial.clone(true).appendTo(containers['serials_container']);
                            last_serial.find('select').each(function(i) {
                                klon.find('select').eq(i).val($(this).val())
                            })
                            var story_num = 'input[name=publication_serial_story_number]';
                            if (!isNaN(last_serial.find(story_num).val())) {
                                klon.find(story_num).val(last_serial.find(story_num).val() / 1 + 1);
                            }
                            klon.find('.serial_button_container').replaceWith(methods._serial_button('minus'));
                            klon.appendTo(containers['serials_container']);
                        }
                        e.preventDefault();
                    });
                }

                if (type == 'minus') {
                    button.find('a').first().click(function(e) {
                        $(this).closest('.serial_container').remove();
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
                methods._append_row(serial_container, fields.published_name,
                    {
                        value: record.published_name,
                    }
                );
                methods._append_row(serial_container, fields.published_format,
                    {
                        value: record.published_format,
                        events: {
                            'change': function(e) {
                                methods._show_published_format($(e.target));
                            }
                        }
                    }
                );
                methods._append_row(serial_container, fields.publisher_type,
                    {
                        value: record.publisher_type,
                        events: {
                            'change': function(e) {
                                methods._show_publisher_type($(e.target));
                            }
                        }
                    }
                );
                methods._append_row(serial_container, fields.publisher,
                    {
                        value: record.publisher,
                    }
                );

                methods._append_row(serial_container, fields.story_number,
                    {
                        value: record.story_number,
                    }
                );
                methods._append_row(serial_container, fields.serial_title,
                    {
                        value: record.serial_title,
                    }
                );
                methods._append_row(serial_container, fields.serial_number,
                    {
                        value: record.serial_number,
                    }
                );
                methods._append_row(serial_container, fields.from_year,
                    {
                        value: record.from_year,
                    }
                );

                methods._append_row(serial_container, fields.to_year,
                    {
                        value: record.to_year,
                    }
                );
                return serial_container;
            },

            _show: function() {
                var shows = {
                    'republished': true,
                    'published_type': false,
                    'whole_container': false,
                    'serials_container': false,
                    'is_derivative': true,
                    'derivative_container': false,
                }
                var republished = containers['republished'].find('select').val();
                if (!republished) {
                    shows['is_derivative'] = false;
                } else if (republished == 'repub') {
                    shows['published_type'] = true;
                    var published_type = containers['published_type'].find('select').val();
                    if (published_type == 'whole') {
                        shows['whole_container'] = true;
                        var published_format_ddm = containers['whole_container'].find('select[name=publication_metadata_published_format]').first();
                        methods._show_published_format(published_format_ddm);
                        var publisher_type_ddm = containers['whole_container'].find('select[name=publication_metadata_publisher_type]').first();
                        methods._show_publisher_type(publisher_type_ddm);
                    } else if (published_type == 'serial') {
                        shows['serials_container'] = true;
                        $.each(containers['serials_container'].find('select[name=publication_serial_published_format]'), function(idx, published_format_ddm) {
                            methods._show_published_format($(published_format_ddm));
                        });
                        $.each(containers['serials_container'].find('select[name=publication_serial_publisher_type]'), function(idx, publisher_type_ddm) {
                            methods._show_publisher_type($(publisher_type_ddm));
                        });
                    } else {
                        shows['is_derivative'] = false;
                    }
                }

                if (shows['is_derivative'] == true) {
                    var is_derivative = containers['is_derivative'].find('select').val();
                    if (is_derivative === 'yes') {
                        shows['derivative_container'] = true;
                    }
                }

                $.each(shows, function(selector, is_shown) {
                    if (is_shown) {
                        containers[selector].removeClass('hidden');
                    } else {
                        containers[selector].addClass('hidden');
                    }
                });
            },

            _show_errors: function(data) {
                if (data.msg) {
                    methods._append_error(form, data.msg);
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
                var publisher_type = elem.closest('.whole_container, .serial_container')
                    .find('select[name=publication_metadata_publisher_type], select[name=publication_serial_publisher_type]').first();
                var publisher = elem.closest('.whole_container, .serial_container')
                    .find('input[name=publication_metadata_publisher], input[name=publication_serial_publisher]').first();
                var publisher_label = publisher.closest('.row_container').find('.field_label').first();
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
                var published_format = elem.closest('.whole_container, .serial_container')
                    .find('select[name=publication_metadata_published_format], select[name=publication_serial_published_format]').first();
                var publisher = elem.closest('.whole_container, .serial_container')
                    .find('input[name=publication_metadata_publisher], input[name=publication_serial_publisher]').first();
                if (published_format.val() == 'paper' && value == 'self') {
                    publisher.closest('.row_container').addClass('hidden');
                } else {
                    publisher.closest('.row_container').removeClass('hidden');
                }
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
