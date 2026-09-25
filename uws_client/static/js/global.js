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

    // A request refused by the server (401/403) while the visitor is not signed in (e.g. the
    // server does not allow anonymous users): go to the login page, then back to this page.
    // For a signed-in user, the error is shown by the page (e.g. no permission for a job).
    $(document).ajaxError(function (event, jqxhr) {
        if ((jqxhr.status == 401 || jqxhr.status == 403)
                && $('#authenticated').attr('value') != 'true' && !global.redirecting) {
            var login_url = $('#login_url').attr('value');
            if (login_url) {
                global.redirecting = true;
                var next = window.location.pathname + window.location.search;
                window.location.href = login_url + '?next=' + encodeURIComponent(next);
            }
        }
    });

    $(document).ready( function() {
        fadeOutAll();
    });

})(jQuery);