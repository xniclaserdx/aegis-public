// DataTable JavaScript
$(document).ready(function () {
    var table = $('#data-table').DataTable({
        "pageLength": 10,
        "ordering": true,
        "searching": true,
        initComplete: function () {
            // Add filter for each column
            this.api().columns().every(function () {
                var column = this;
                var select = $('select', column.header());
                column.data().unique().sort().each(function (d, j) {
                    select.append('<option value="' + d + '">' + d + '</option>')
                });
                select.on('change', function () {
                    var val = $.fn.dataTable.util.escapeRegex($(this).val());
                    column.search(val ? '^' + val + '$' : '', true, false).draw();
                });
            });
        }
    });
});
