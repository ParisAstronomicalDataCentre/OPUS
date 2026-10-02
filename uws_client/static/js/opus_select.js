/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

/*
 * Lists (select.selectpicker) displayed with Tom Select, with the API of bootstrap-select used by the pages:
 *   $(select).selectpicker()              create the list (done for select.selectpicker when the page is loaded)
 *   $(select).selectpicker('refresh')     read again the options and the selected values of the select
 *   $(select).selectpicker('val', value)  select a value (or a list of values)
 *   $(select).selectpicker('selectAll') / ('deselectAll')
 * The select element keeps the selected values (.val()) and sends the change events.
 */
(function($) {
    "use strict";

    // Order of the options of a select, as first seen (options added later are after the others): Tom Select moves
    // the selected options to the end, of the select and of its list
    function recordOrder(select) {
        select.opusOrder = select.opusOrder || {};
        Array.from(select.options).forEach(function (option) {
            if (!(option.value in select.opusOrder)) {
                select.opusOrder[option.value] = Object.keys(select.opusOrder).length + 1;
            }
        });
    }
    function restoreOrder(select, ts) {
        Object.keys(ts.options).forEach(function (value) {
            if (value in select.opusOrder) {
                ts.options[value].$order = select.opusOrder[value];
            }
        });
        ts.lastQuery = null;
    }

    function init(select) {
        if (select.tomselect) {
            return select.tomselect;
        }
        recordOrder(select);
        var title = select.getAttribute('title') || '';
        // single select without selected option: nothing selected, the title is shown
        var has_empty = Array.from(select.options).some(function (o) { return o.value === ''; });
        if (!select.multiple && title && !select.querySelector('option[selected]') && !has_empty) {
            var empty = document.createElement('option');
            empty.value = '';
            select.insertBefore(empty, select.firstChild);
            select.value = '';
        }
        select.classList.add('form-select');
        var options = {
            placeholder: title,
            maxOptions: null,
            create: false,
            plugins: select.multiple ? ['checkbox_options', 'remove_button'] : [],
            hidePlaceholder: true,
            onInitialize: function () { this.wrapper.title = title; }
        };
        if (select.getAttribute('data-container') == 'body') {
            options.dropdownParent = 'body';  // above the other elements (e.g. in a table)
        }
        var ts = new TomSelect(select, options);
        // the container gets the classes of the select: not selectpicker (the pages add options to .selectpicker)
        ts.wrapper.classList.remove('selectpicker');
        return ts;
    }

    $.fn.selectpicker = function (command, value) {
        return this.each(function () {
            if (this.tagName != 'SELECT') {
                return;
            }
            var ts = init(this);
            switch (command) {
                case 'refresh':
                    recordOrder(this);
                    ts.sync();
                    restoreOrder(this, ts);
                    break;
                case 'val':
                    ts.setValue(value, true);
                    break;
                case 'selectAll':
                    ts.setValue(Object.keys(ts.options), true);
                    break;
                case 'deselectAll':
                    ts.clear(true);
                    break;
            }
        });
    };

    $(document).ready(function () {
        $('select.selectpicker').selectpicker();
    });

})(jQuery);
