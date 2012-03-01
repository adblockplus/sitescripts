/*
  This Source Code is subject to the terms of the Mozilla Public License
  version 2.0 (the "License"). You can obtain a copy of the License at
  http://mozilla.org/MPL/2.0/.
*/

(function ($)
{
  $.extend(true, window,
  {
    ReportsView: ReportsView
  });

  $.extend(true, window,
  {
    "ReportFormatters":
    {
      "Number": NumberFormatter,
      "Time": TimeFormatter,
      "Screenshot": ScreenshotFormatter,
      "Checkmark": CheckmarkFormatter,
      "Link": UrlFormatter,
      "Subcsriptions": SubscriptionFormatter
    }
  });

  $.extend(true, window,
  {
    "ReportFilters":
    {
      "Checkbox": CheckboxFilter,
      "Text": TextFilter,
      "Subscriptions": SubscriptionsFilter,
      "YesNo": YesNoFilter,
      "Screenshot": ScreenshotFilter,
      "Type": TypeFilter,
      "TimePeriod": TimePeriodFilter
    }
  });

  function encodeEntities(value)
  {
    return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  
  function NumberFormatter(row, cell, value, columnDef, dataContext)
  {
    return value.toFixed(1);
  }

  function TimeFormatter(row, cell, value, columnDef, dataContext)
  {
    var date = new Date(value * 1000);
    return "<span title=\"" + encodeEntities(date.toLocaleString()) + "\">" + encodeEntities(date.toLocaleDateString()) + "</span>";
  }
  
  function ScreenshotFormatter(row, cell, value, columnDef, dataContext)
  {
    return value == 2 ? "✔" : value == 1 ? "✓" : "";
  }

  function CheckmarkFormatter(row, cell, value, columnDef, dataContext)
  {
    return value ? "✓" : "";
  }
  
  function UrlFormatter(row, cell, value, columnDef, dataContext)
  {
    return "<a href=\"" + encodeEntities(value) + "\">view</a>";
  }

  function SubscriptionFormatter(row, cell, value, columnDef, dataContext)
  {
    var title = value.map(function(x) {return x.name;}).join(", ");
    return "<span title=\"" + encodeEntities(title) + "\">" + value.length + "</span>";
  }

  function CheckboxFilter(column)
  {
    var $el;

    this.init = function ()
    {
      $el = $("<input type=\"checkbox\" class=\"filter-checkbox\" hideFocus>");
      $el.data("columnId", column.id);
    }
    
    this.update = function(header)
    {
    }

    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")] === 'true';
        $el.attr("checked", f);
      }
    }

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.is(":checked");
    };

    this.filter = function(value)
    {
      var f = $el.is(":checked");
      if (value)
        return true;
      else
        return ! f;
    }

    this.get = function()
    {
      return $el;
    }

    this.init();
  }

  function TextFilter(column)
  {
    var $el;
    
    this.init = function ()
    {
      $el = $("<input type=\"text\">");
      $el.data("columnId", column.id);
    }

    this.update = function(header)
    {
      $el.width($(header).width() - 4)
    }
    
    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")];
        $el.val(f);
      }
    };

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.val();
    };

    this.filter = function(value)
    {
      var f = $.trim($el.val());
      return f == "" || (value != null && value.toLowerCase().indexOf(f.toLowerCase()) >= 0);
    }
    
    this.get = function()
    {
      return $el;
    }
    
    this.init();
  }

  function SubscriptionsFilter(column)
  {
    var $el;
    
    this.init = function ()
    {
      $el = $("<input type=\"text\">");
      $el.data("columnId", column.id);
    }

    this.update = function(header)
    {
      $el.width($(header).width() - 4)
    }
    
    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")];
        $el.val(f);
      }
    }

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.val();
    };

    this.filter = function(value)
    {
      var f = $.trim($el.val()).toLowerCase();
      if (f == "")
        return true;
      if (value == null)
        return false;
      var n = parseInt(f);
      if (isNaN(n))
      {
        for (var i = 0; i < value.length; i++)
        {
          if (value[i]["name"].toLowerCase().indexOf(f) >= 0)
            return true;
        }
        return false;
      } 
      else
      {
        return f == value.length;
      }
    }
    
    this.get = function()
    {
      return $el;
    }
    
    this.init();
  }

  function YesNoFilter(column)
  {
    var $el;
    
    this.init = function ()
    {
      $el = $("<select><option value=\"-1\"></option><option value=\"1\">yes</option><option value=\"0\">no</option></select>");
      $el.data("columnId", column.id);
    }

    this.update = function(header)
    {
      $el.width($(header).width() - 4)
    }
    
    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")];
        $el.val(f);
      }
    };

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.val();
    };

    this.filter = function(value)
    {
      var f = $el.val();
      return f < 0 || (f == 0 && ! value) || (f == 1 && value);
    }
    
    this.get = function()
    {
      return $el;
    }
    
    this.init();
  }

  function ScreenshotFilter(column)
  {
    var $el;
    
    this.init = function ()
    {
      $el = $("<select><option value=\"\"></option><option value=\"0\">without screenshot</option><option value=\"1\">with screenshot</option><option value=\"2\">modified screenshot</option></select>");
      $el.data("columnId", column.id);
    }

    this.update = function(header)
    {
      $el.width($(header).width() - 4)
    }
    
    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")];
        $el.val(f);
      }
    };

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.val();
    };

    this.filter = function(value)
    {
      var f = $el.val();
      return f == "" || (f == "1" && value) || f == value
    }
    
    this.get = function()
    {
      return $el;
    }
    
    this.init();
  }

  function TypeFilter(column)
  {
    var $el;
    
    this.init = function ()
    {
      $el = $("<select><option value=\"\"></option><option value=\"false negative\">false negative</option><option value=\"false positive\">false positive</option></select>");
      $el.data("columnId", column.id);
    }

    this.update = function(header)
    {
      $el.width($(header).width() - 4)
    }
    
    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")];
        $el.val(f);
      }
    };

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.val();
    };

    this.filter = function(value)
    {
      var f = $el.val();
      return f == "" || f == value;
    }
    
    this.get = function()
    {
      return $el;
    }
    
    this.init();
  }

  function TimePeriodFilter(column)
  {
    var $el;
    var currentTime;
    
    this.init = function ()
    {
      currentTime = parseInt(new Date().getTime() / 1000);
      $el = $("<select><option value=\"8760\"></option><option value=\"24\">last 24 hours</option><option value=\"168\">last week</option></select>");
      $el.data("columnId", column.id);
    }

    this.update = function(header)
    {
      $el.width($(header).width() - 4)
    }
    
    this.restore = function ()
    {
      if ($el.data("columnId") in window.localStorage)
      {
        var f = window.localStorage[$el.data("columnId")];
        $el.val(f);
      }
      else
      {
        $el.val("24");
      }
    };

    this.persist = function ()
    {
      window.localStorage[$el.data("columnId")] = $el.val();
    };

    this.filter = function(value)
    {
      var f = currentTime - parseInt($el.val()) * 3600;
      return f <= value;
    }
    
    this.get = function()
    {
      return $el;
    }
    
    this.init();
  }

  function ReportsView(options)
  {
    var self = this;

    // private
    var idProperty = "guid";  // property holding a unique row id
    var items = [];         // data by index
    var rows = [];          // data by row
    var idxById = {};       // indexes by id
    var rowsById = null;    // rows by id; lazy-calculated
    var filter = null;      // filter function
    var updated = null;     // updated item ids
    var suspend = false;    // suspends the recalculation
    var refreshHints = {};
    var prevRefreshHints = {};
    var filteredItems = [];
    var filterCache = [];

    var totalRows = 0;

    // events
    var onRowCountChanged = new Slick.Event();
    var onRowsChanged = new Slick.Event();

    function beginUpdate()
    {
      suspend = true;
    }

    function endUpdate()
    {
      suspend = false;
      refresh();
    }

    function setRefreshHints(hints)
    {
      refreshHints = hints;
    }

    function updateIdxById(startingIndex)
    {
      startingIndex = startingIndex || 0;
      var id;
      for (var i = startingIndex, l = items.length; i < l; i++)
      {
        id = items[i][idProperty];
        if (id === undefined)
        {
          throw "Each data element must implement a unique 'id' property";
        }
        idxById[id] = i;
      }
    }

    function ensureIdUniqueness()
    {
      var id;
      for (var i = 0, l = items.length; i < l; i++)
      {
        id = items[i][idProperty];
        if (id === undefined || idxById[id] !== i)
        {
          throw "Each data element must implement a unique 'id' property";
        }
      }
    }

    function getItems()
    {
      return items;
    }

    function setItems(data, objectIdProperty)
    {
      if (objectIdProperty !== undefined)
      {
        idProperty = objectIdProperty;
      }
      items = filteredItems = data;
      idxById = {};
      updateIdxById();
      ensureIdUniqueness();
      refresh();
    }

    function sort(cols)
    {
      var hasSite = Array.prototype.some.call(cols, function(c) {return "site" == c.sortCol.field});
      var sites = {};
      if (hasSite)
      {
        for (var i = 0; i < items.length; i++)
        {
          if (! sites[items[i].site])
            sites[items[i].site] = 1;
          else
            sites[items[i].site]++;
        }
      }
    
      items.sort(function (dataRow1, dataRow2)
      {
        for (var i = 0, l = cols.length; i < l; i++)
        {
          var field = cols[i].sortCol.field;
          var sign = cols[i].sortAsc ? 1 : -1;
          var value1 = dataRow1[field], value2 = dataRow2[field];
          var result = 0;
          if (field == "site")
          {
            if (sites[value1] != sites[value2])
              result = sites[value2] - sites[value1];
            else if (value1 < value2)
              result = -1;
            else if (value1 > value2)
              result = 1;
          } 
          else
          {
            result = (value1 == value2 ? 0 : (value1 > value2 ? 1 : -1)) * sign;
          }
          if (result != 0)
          {
            return result;
          }
        }
        return 0;
      });

      idxById = {};
      updateIdxById();
      refresh();
    }

    function setFilter(filterFn)
    {
      filter = filterFn;
      refresh();
    }

    function getItemByIdx(i)
    {
      return items[i];
    }

    function getIdxById(id)
    {
      return idxById[id];
    }

    function ensureRowsByIdCache()
    {
      if (!rowsById)
      {
        rowsById = {};
        for (var i = 0, l = rows.length; i < l; i++)
        {
          rowsById[rows[i][idProperty]] = i;
        }
      }
    }

    function getRowById(id)
    {
      ensureRowsByIdCache();
      return rowsById[id];
    }

    function getItemById(id)
    {
      return items[idxById[id]];
    }

    function mapIdsToRows(idArray)
    {
      var rows = [];
      ensureRowsByIdCache();
      for (var i = 0; i < idArray.length; i++)
      {
        var row = rowsById[idArray[i]];
        if (row != null)
        {
          rows[rows.length] = row;
        }
      }
      return rows;
    }

    function mapRowsToIds(rowArray)
    {
      var ids = [];
      for (var i = 0; i < rowArray.length; i++)
      {
        if (rowArray[i] < rows.length)
        {
          ids[ids.length] = rows[rowArray[i]][idProperty];
        }
      }
      return ids;
    }

    function updateItem(id, item)
    {
      if (idxById[id] === undefined || id !== item[idProperty])
      {
        throw "Invalid or non-matching id";
      }
      items[idxById[id]] = item;
      if (!updated)
      {
        updated = {};
      }
      updated[id] = true;
      refresh();
    }

    function insertItem(insertBefore, item)
    {
      items.splice(insertBefore, 0, item);
      updateIdxById(insertBefore);
      refresh();
    }

    function addItem(item)
    {
      items.push(item);
      updateIdxById(items.length - 1);
      refresh();
    }

    function deleteItem(id)
    {
      var idx = idxById[id];
      if (idx === undefined)
      {
        throw "Invalid id";
      }
      delete idxById[id];
      items.splice(idx, 1);
      updateIdxById(idx);
      refresh();
    }

    function getLength()
    {
      return rows.length;
    }

    function getItem(i)
    {
      return rows[i];
    }

    function getItemMetadata(i)
    {
//    var item = rows[i];
      return null;
    }

    function uncompiledFilter(items)
    {
      var retval = [], idx = 0;

      for (var i = 0, ii = items.length; i < ii; i++)
      {
        if (filter(items[i]))
        {
          retval[idx++] = items[i];
        }
      }

      return retval;
    }

    function uncompiledFilterWithCaching(items, cache)
    {
      var retval = [], idx = 0, item;

      for (var i = 0, ii = items.length; i < ii; i++)
      {
        item = items[i];
        if (cache[i])
        {
          retval[idx++] = item;
        } else if (filter(item))
        {
          retval[idx++] = item;
          cache[i] = true;
        }
      }

      return retval;
    }

    function getFilteredAndPagedItems(items)
    {
      if (filter)
      {
        var batchFilter = uncompiledFilter;
        var batchFilterWithCaching = uncompiledFilterWithCaching;

        if (refreshHints.isFilterNarrowing)
        {
          filteredItems = batchFilter(filteredItems);
        }
        else if (refreshHints.isFilterExpanding)
        {
          filteredItems = batchFilterWithCaching(items, filterCache);
        }
        else if (!refreshHints.isFilterUnchanged)
        {
          filteredItems = batchFilter(items);
        }
      } 
      else
      {
        // special case:  if not filtering and not paging, the resulting
        // rows collection needs to be a copy so that changes due to sort
        // can be caught
        filteredItems = items.concat();
      }

      return {totalRows: filteredItems.length, rows: filteredItems};
    }

    function getRowDiffs(rows, newRows)
    {
      var item, r, eitherIsNonData, diff = [];
      var from = 0, to = newRows.length;

      if (refreshHints && refreshHints.ignoreDiffsBefore)
      {
        from = Math.max(0,
            Math.min(newRows.length, refreshHints.ignoreDiffsBefore));
      }

      if (refreshHints && refreshHints.ignoreDiffsAfter)
      {
        to = Math.min(newRows.length,
            Math.max(0, refreshHints.ignoreDiffsAfter));
      }

      for (var i = from, rl = rows.length; i < to; i++)
      {
        if (i >= rl)
        {
          diff[diff.length] = i;
        }
        else
        {
          item = newRows[i];
          r = rows[i];

          if (item[idProperty] != r[idProperty] || (updated && updated[item[idProperty]]))
          {
            diff[diff.length] = i;
          }
        }
      }
      return diff;
    }

    function recalc(_items)
    {
      rowsById = null;

      if (refreshHints.isFilterNarrowing != prevRefreshHints.isFilterNarrowing ||
          refreshHints.isFilterExpanding != prevRefreshHints.isFilterExpanding)
      {
        filterCache = [];
      }

      var filteredItems = getFilteredAndPagedItems(_items);
      totalRows = filteredItems.totalRows;
      var newRows = filteredItems.rows;

      var diff = getRowDiffs(rows, newRows);

      rows = newRows;

      return diff;
    }

    function refresh()
    {
      if (suspend)
      {
        return;
      }

      var countBefore = rows.length;
      var totalRowsBefore = totalRows;

      var diff = recalc(items, filter); // pass as direct refs to avoid closure perf hit

      updated = null;
      prevRefreshHints = refreshHints;
      refreshHints = {};

      if (countBefore != rows.length)
      {
        onRowCountChanged.notify({previous: countBefore, current: rows.length}, null, self);
      }
      if (diff.length > 0)
      {
        onRowsChanged.notify({rows: diff}, null, self);
      }
    }

    function syncGridSelection(grid, preserveHidden)
    {
      var self = this;
      var selectedRowIds = self.mapRowsToIds(grid.getSelectedRows());;
      var inHandler;

      grid.onSelectedRowsChanged.subscribe(function(e, args)
      {
        if (inHandler) { return; }
        selectedRowIds = self.mapRowsToIds(grid.getSelectedRows());
      });

      this.onRowsChanged.subscribe(function(e, args)
      {
        if (selectedRowIds.length > 0)
        {
          inHandler = true;
          var selectedRows = self.mapIdsToRows(selectedRowIds);
          if (!preserveHidden)
          {
            selectedRowIds = self.mapRowsToIds(selectedRows);
          }
          grid.setSelectedRows(selectedRows);
          inHandler = false;
        }
      });
    }

    function syncGridCellCssStyles(grid, key)
    {
      var hashById;
      var inHandler;

      // since this method can be called after the cell styles have been set,
      // get the existing ones right away
      storeCellCssStyles(grid.getCellCssStyles(key));

      function storeCellCssStyles(hash)
      {
        hashById = {};
        for (var row in hash)
        {
          var id = rows[row][idProperty];
          hashById[id] = hash[row];
        }
      }

      grid.onCellCssStylesChanged.subscribe(function(e, args)
      {
        if (inHandler) { return; }
        if (key != args.key) { return; }
        if (args.hash)
        {
          storeCellCssStyles(args.hash);
        }
      });

      this.onRowsChanged.subscribe(function(e, args)
      {
        if (hashById)
        {
          inHandler = true;
          ensureRowsByIdCache();
          var newHash = {};
          for (var id in hashById)
          {
            var row = rowsById[id];
            if (row != undefined)
            {
              newHash[row] = hashById[id];
            }
          }
          grid.setCellCssStyles(key, newHash);
          inHandler = false;
        }
      });
    }

    return {
      // methods
      "beginUpdate": beginUpdate,
      "endUpdate": endUpdate,
      "getItems": getItems,
      "setItems": setItems,
      "setFilter": setFilter,
      "sort": sort,
      "getIdxById": getIdxById,
      "getRowById": getRowById,
      "getItemById": getItemById,
      "getItemByIdx": getItemByIdx,
      "mapRowsToIds": mapRowsToIds,
      "mapIdsToRows": mapIdsToRows,
      "setRefreshHints": setRefreshHints,
      "refresh": refresh,
      "updateItem": updateItem,
      "insertItem": insertItem,
      "addItem": addItem,
      "deleteItem": deleteItem,
      "syncGridSelection": syncGridSelection,
      "syncGridCellCssStyles": syncGridCellCssStyles,

      // data provider methods
      "getLength": getLength,
      "getItem": getItem,
      "getItemMetadata": getItemMetadata,

      // events
      "onRowCountChanged": onRowCountChanged,
      "onRowsChanged": onRowsChanged
    };
  }
})(jQuery);
