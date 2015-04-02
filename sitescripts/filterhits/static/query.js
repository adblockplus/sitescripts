(function () {
  var table = $("#results").dataTable({
    serverSide: true,
    bFilter: false,
    "columns": [
      { data: "filter" },
      { data: "domain" },
      { data: "frequency" }
    ],
    order: [[2, "desc"]],
    fnServerData: function (source, data, callback, settings) {
      var sort = settings.aaSorting[0];
      $.ajax({
        dataType: "json",
        type: "GET",
        url: "/query",
        data: {
          echo: settings.iDraw,
          skip: settings._iDisplayStart,
          take: settings._iDisplayLength,
          filter: $("#filter").val(),
          domain: $("#domain").val(),
          order: sort[1],
          order_by: ["filter", "domain", "frequency"][sort[0]]
        },
        success: function(data, status, jqxhr) {
          callback({
            draw: data.echo,
            recordsTotal: data.total,
            recordsFiltered: data.total,
            data: data.results
          }, status, jqxhr);
        }
      });
    }
  });

  $("#filter, #domain").on("input", function () { table.fnDraw(); });
}());
