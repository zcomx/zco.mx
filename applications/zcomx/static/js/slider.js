(function () {
    "use strict";
    var ROTATE = true;
    var NO_ROTATE = false;

    function image_count() {
        return $('#reader_section .slide').length - 1;
    }

    function next_slide(rotate) {
        $('#reader_section .slide:visible').each( function(id, elem) {
            var num = $(this).attr('id').split('-')[1];
            num++;
            if (num > image_count()) {
                if (rotate) {
                    num = 0;
                } else {
                    return;
                }
            };
            show_slide(num);
        });
    }

    function prev_slide(rotate) {
        $('#reader_section .slide:visible').each( function(id, elem) {
            var num = $(this).attr('id').split('-')[1];
            num--;
            if (num < 0) {
                if (rotate) {
                    num = image_count();
                } else {
                    return;
                }
            };
            show_slide(num);
        });
    }

    function show_slide(num) {
        $('#reader_section .slide').hide();
        $('#reader_section').height('100%');

        /* Resize the container div to fit viewport. */
        var section_h = $(window).height();

        $('#reader_section').height(section_h);
        $('#reader_section #img-' + num).css( "display", "inline-block")
        $('#page_nav_page_no').val(num + 1);
    }

    $(document).ready(function(){

        $('#page_nav_total').text((image_count() + 1).toString());

        $('#reader_section .slide').click(function(e) {
            next_slide(NO_ROTATE);
            e.preventDefault();
        });

        $('#page_nav_next').click(function(e) {
            next_slide(NO_ROTATE);
            e.preventDefault();
        });

        $('#page_nav_prev').click(function(e) {
            prev_slide(NO_ROTATE);
            e.preventDefault();
        });

        $('#page_nav_first').click(function(e) {
            show_slide(0);
            e.preventDefault();
        });

        $('#page_nav_last').click(function(e) {
            show_slide(image_count());
            e.preventDefault();
        });

        $('#page_nav_page_no').change(function(e) {
            var value = parseInt($(this).val(), 10);
            if (isNaN(value)) {
                value = 1;
            }
            var page_no = value - 1;
            if (page_no < 0) {
                page_no = 0;
            }
            if (page_no > image_count()) {
                page_no = image_count();
            }
            show_slide(page_no);
        });

        setTimeout(function() {
            show_slide(0);
        }.bind(this), 1000);
    });

}());
