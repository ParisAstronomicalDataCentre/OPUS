/*!
 * Copyright (c) 2016 by Mathieu Servillat
 * Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
 */

/*
 * Sort and pages of a table (job list), without library:
 * - click on a header cell to sort the rows (except the cells with the class sorter-false), click again to reverse
 * - pager in the footer (class ts-pager): buttons first, prev, next, last, texts pagedisplay ("1–20 of 42") and
 *   pagecount ("of 3"), selects pagesize and pagenum
 * The rows added or removed later are taken into account (the table is observed).
 *
 *   opusTable.init(document.getElementById('job_list'));
 */
var opusTable = (function() {
    "use strict";

    function init(table) {
        var tbody = table.tBodies[0];
        if (table.opusTable) {
            if (table.opusTable.tbody === tbody) {
                table.opusTable.render();
                return table.opusTable;
            }
            table.opusTable.observer.disconnect();  // table built again (e.g. other job name)
        }
        var pager = table.querySelector('.ts-pager');
        var state = {sortColumn: null, sortAsc: true, page: 0, pageSize: 10};
        if (pager && pager.querySelector('.pagesize')) {
            var size = pager.querySelector('.pagesize').value;
            state.pageSize = (size == 'all') ? 0 : parseInt(size, 10);
        }

        function cellText(row, index) {
            var cell = row.cells[index];
            return cell ? cell.textContent.trim() : '';
        }

        function sort() {
            if (state.sortColumn === null) {
                return;
            }
            var rows = Array.from(tbody.rows);
            rows.sort(function (a, b) {
                var x = cellText(a, state.sortColumn), y = cellText(b, state.sortColumn);
                var nx = parseFloat(x), ny = parseFloat(y);
                var result = (!isNaN(nx) && !isNaN(ny) && String(nx) == x && String(ny) == y)
                    ? nx - ny : x.localeCompare(y);
                return state.sortAsc ? result : -result;
            });
            observer.disconnect();  // reordering the rows is not a change of the list
            rows.forEach(function (row) { tbody.appendChild(row); });
            observer.observe(tbody, {childList: true});
        }

        function render() {
            var rows = Array.from(tbody.rows);
            var total = rows.length;
            var size = state.pageSize || total || 1;
            var pages = Math.max(1, Math.ceil(total / size));
            state.page = Math.min(state.page, pages - 1);
            var start = state.page * size;
            rows.forEach(function (row, i) {
                row.style.display = (i >= start && i < start + size) ? '' : 'none';
            });
            // sort indicators
            Array.from(table.tHead.rows[0].cells).forEach(function (th, i) {
                var icon = th.querySelector('.sort-icon');
                if (icon) {
                    icon.className = 'sort-icon bi ' + (i === state.sortColumn
                        ? (state.sortAsc ? 'bi-caret-up-fill' : 'bi-caret-down-fill') : 'bi-chevron-expand text-muted');
                }
            });
            if (!pager) {
                return;
            }
            var display = pager.querySelector('.pagedisplay');
            if (display) {
                var end = Math.min(start + size, total);
                display.textContent = (total ? start + 1 : 0) + '\u2013' + end + ' of ' + total;
            }
            var pagecount = pager.querySelector('.pagecount');
            if (pagecount) {
                pagecount.textContent = 'of ' + pages;
            }
            var pagenum = pager.querySelector('.pagenum');
            if (pagenum) {
                pagenum.innerHTML = '';
                for (var p = 0; p < pages; p++) {
                    var option = document.createElement('option');
                    option.value = p;
                    option.textContent = p + 1;
                    option.selected = (p == state.page);
                    pagenum.appendChild(option);
                }
            }
        }

        function goTo(page) {
            state.page = Math.max(0, page);
            render();
        }

        // header cells: sort
        Array.from(table.tHead.rows[0].cells).forEach(function (th, index) {
            if (th.classList.contains('sorter-false')) {
                return;
            }
            th.style.cursor = 'pointer';
            th.insertAdjacentHTML('beforeend', ' <span class="sort-icon"></span>');
            th.addEventListener('click', function () {
                state.sortAsc = (state.sortColumn === index) ? !state.sortAsc : true;
                state.sortColumn = index;
                sort();
                render();
            });
        });

        // pager
        if (pager) {
            var on = function (selector, event, handler) {
                var element = pager.querySelector(selector);
                if (element) {
                    element.addEventListener(event, handler);
                }
            };
            on('.first', 'click', function () { goTo(0); });
            on('.prev', 'click', function () { goTo(state.page - 1); });
            on('.next', 'click', function () { goTo(state.page + 1); });
            on('.last', 'click', function () { goTo(Number.MAX_SAFE_INTEGER); });
            on('.pagenum', 'change', function () { goTo(parseInt(this.value, 10)); });
            on('.pagesize', 'change', function () {
                state.pageSize = (this.value == 'all') ? 0 : parseInt(this.value, 10);
                goTo(0);
            });
        }

        // rows added or removed (e.g. new job, job deleted)
        var observer = new MutationObserver(function () {
            sort();
            render();
        });
        observer.observe(tbody, {childList: true});

        table.opusTable = {render: render, tbody: tbody, observer: observer};
        render();
        return table.opusTable;
    }

    return {init: init};
})();
