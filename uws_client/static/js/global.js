/*!
 * Copyright (c) 2018 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

var global = {};

(function($) {
    "use strict";

    var fadeOutAll = function () {
        $('.fadeOut').delay(3000).fadeOut(2000);
    };
    global.fadeOutAll = fadeOutAll;

    var showMessage = function (msg, category) {
        if (category.length == 0) {
            category = 'info';
        }
        $("#messages").append('<div class="fadeOut alert alert-' + category + ' text-center">' + msg + '</div>');
        fadeOutAll();
    };
    global.showMessage = showMessage;

    $(document).ready( function() {
        fadeOutAll();
    });

})(jQuery);