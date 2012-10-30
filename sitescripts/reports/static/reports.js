if (typeof localStorage == "undefined")
  window.localStorage = {};
var templates;

function migrateCookies()
{
  var cookies = document.cookie.split(/\s*;\s*/);
  for (var i = 0; i < cookies.length; i++)
  {
    if (/^(.*?)=(.*)/.test(cookies[i]))
    {
      var key = decodeURIComponent(RegExp.$1);
      var value = decodeURIComponent(RegExp.$2);
      var needDelete = true;
      if (key == "templates")
        localStorage.templates = value;
      else if (/^secret-(.*)/.test(key))
        saveSecret(RegExp.$1, value);
      else
        needDelete = false;
      if (needDelete)
        document.cookie = encodeURIComponent(key) + "=;expires=Thu, 01-Jan-1970 00:00:01 GMT";
    }
  }
}

function escapeHTML(value)
{
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function setRadio(radio, value)
{
  for (var i = 0; i < radio.length; i++)
  {
    if (radio[i].value == value)
      radio[i].checked = true;
    else
      radio[i].checked = false;
  }
}

function setRadioListener(radio, listener)
{
  for (var i = 0; i < radio.length; i++)
    radio[i].addEventListener("click", listener, false);
}

function getCheckedRadio(radio)
{
  for (var i = 0; i < radio.length; i++)
  {
    if (radio[i].checked)
      return radio[i];
  }
  return undefined;
}

function saveSecret(guid, secret)
{
  var secrets = localStorage.secrets;
  if (secrets)
    secrets = JSON.parse(secrets);
  else
    secrets = {};
  secrets[guid] = {value: secret, expiration: new Date().getTime() + 1000*60*60*24*30};
  localStorage.secrets = JSON.stringify(secrets);
}

function setSecret(guid, secret)
{
  saveSecret(guid, secret);

  var status = "";
  var statusCell = document.getElementById("statusCell");
  if (statusCell)
    status = statusCell.textContent;
  
  var div = document.createElement("div");
  div.className = "updateLink"
  var link = document.createElement("a");
  link.setAttribute("href", "javascript:void(0);");
  link.textContent = "Update status"
  div.appendChild(link);

  if (statusCell)
    statusCell.appendChild(div);
  else
    document.body.insertBefore(div, document.body.firstChild);

  link.onclick = function()
  {
    var notifyBox = "";
    if (document.getElementById("emailCell"))
      notifyBox = '<span id="notifyField"><input type="checkbox" id="notify" name="notify" value="1" /> <label for="notify">Notify user</label></span>';

    div.innerHTML = '<form id="updateForm" action="/updateReport" method="POST">' +
      '<input type="hidden" name="secret" value="' + escapeHTML(secret) + '" />' +
      '<input type="hidden" name="guid" value="' + escapeHTML(guid) + '" />' +
      '<p>' +
        'Status templates: <br />' +
        '<select id="templatesField"><option value="" selected="selected" disabled="true">(select one)</option></select>' +
      '</p>' +
      '<p>' +
        'Enter new status:' + notifyBox + '<br />' +
        '<textarea id="statusField" name="status" oninput="updateTemplateButtons();"></textarea>' + 
        '<br />Usefulness: <input type="radio" name="usefulness" value="0" checked="checked" /> not established <input type="radio" name="usefulness" value="1" /> useful <input type="radio" name="usefulness" value="-1" /> useless' +
      '</p>' +
      '<div>' +
        '<button id="addTemplateButton" type="button" onclick="addTemplate();">Add as template</button>' +
        '<button id="removeTemplateButton" type="button" onclick="removeTemplate();">Remove template</button>' +
        '<input type="submit" value="Change status"/>' +
      '</div>' +
    '</form>';
    var radios = document.getElementById("updateForm").elements.usefulness;
    document.getElementById("templatesField").addEventListener("change", function()
    {
      if (this.selectedIndex > 0)
      {
	var template = this.options[this.selectedIndex].value.split("\1");
        var displayText = template[template.length - 1];
        if (template.length > 1)
          setRadio(radios, template[0]);
        document.getElementById("statusField").value = displayText;
        var notifyField = document.getElementById("notify");
        if (notifyField)
          notifyField.checked = true;
        updateTemplateButtons();
      }
    }, false);

    var statusField = document.getElementById("statusField");
    statusField.value = status;

    var usefulness = 0;
    var usefulnessCell = document.getElementById("usefulnessCell");
    if (usefulnessCell)
      usefulness = usefulnessCell.getAttribute("value");
    setRadio(radios, usefulness);
    setRadioListener(radios, updateTemplates);

    updateTemplates();
    statusField.focus();
  }
}

function updateTemplates()
{
  var templatesField = document.getElementById("templatesField");
  while (templatesField.options.length > 1)
    templatesField.remove(1);
  for (var i = 0; i < templates.length; i++)
  {
    var template = templates[i].split("\1");
    var displayText = template[template.length - 1];
    if (displayText.length > 150)
      displayText = displayText.substr(0, 75) + "..." + displayText.substr(displayText.length - 75, displayText.length);
    if (template.length > 1)
    {
      usefulnessText = template[0] > 0 ? "useful" : template[0] < 0 ? "useless" : null;
      if (usefulnessText != null)
        displayText = "[" + usefulnessText + "] " + displayText;
    }
    templatesField.add(new Option(displayText, templates[i], false, false), null);
  }
  updateTemplateButtons();
}

function updateTemplateButtons()
{
  var currentText = document.getElementById("statusField").value;
  var usefulnessValue = "0";
  var usefulnessButton = getCheckedRadio(document.getElementById("updateForm").elements.usefulness);
  if (usefulnessButton)
    usefulnessValue = usefulnessButton.value;

  var options = document.getElementById("templatesField").options;
  for (var i = 1; i < options.length; i++)
  {
    var template = options[i].value.split("\1");
    var text = template[template.length - 1];
    var usefulness = template.length > 1 ? template[0] : "0";
      
    if (text == currentText && usefulness == usefulnessValue)
    {
      document.getElementById("templatesField").selectedIndex = i;
      document.getElementById("addTemplateButton").style.display = "none";
      document.getElementById("removeTemplateButton").style.display = "";
      return;
    }
  }

  document.getElementById("templatesField").selectedIndex = 0;
  document.getElementById("addTemplateButton").disabled = !/\S/.test(currentText) || currentText == "unknown";
  document.getElementById("addTemplateButton").style.display = "";
  document.getElementById("removeTemplateButton").style.display = "none";
}

function addTemplate()
{
  var usefulnessValue = "0";
  var usefulnessButton = getCheckedRadio(document.getElementById("updateForm").elements.usefulness);
  if (usefulnessButton)
    usefulnessValue = usefulnessButton.value;

  var value =  usefulnessValue + "\1" + document.getElementById("statusField").value;
  templates.push(value);
  templates.sort();
  localStorage.templates = templates.join("\0");
  updateTemplates();
}

function removeTemplate()
{
  var currentText = document.getElementById("statusField").value;
  var usefulnessValue = "0";
  var usefulnessButton = getCheckedRadio(document.getElementById("updateForm").elements.usefulness);
  if (usefulnessButton)
    usefulnessValue = usefulnessButton.value;
  for (var i = 0; i < templates.length; i++)
  {
    var template = templates[i].split("\1");
    var text = template[template.length - 1];
    var usefulness = template.length > 1 ? template[0] : "0";
    if (text == currentText && usefulness == usefulnessValue)
      templates.splice(i--, 1);
  }
  localStorage.templates = templates.join("\0");
  updateTemplates();
}

function selectTab(tab)
{
  document.documentElement.setAttribute("selectedTab", tab);
  window.location.replace(window.location.href.replace(/#.*|$/, "#tab=" + tab));
}

function initialSelect()
{
  var guid = "";
  if (/([\w\-]+)$/.test(location.pathname))
    guid = RegExp.$1;

  migrateCookies();

  templates = localStorage.templates;
  if (templates)
    templates = templates.split("\0");
  else
    templates = [];

  var secrets = localStorage.secrets;
  if (secrets)
  {
    secrets = JSON.parse(secrets);

    // Expire outdated secrets
    var now = new Date().getTime();
    var changed = false;
    for (var key in secrets)
    {
      if (secrets[key].expiration < now)
      {
        delete secrets[key];
        changed = true;
      }
    }
    if (changed)
      localStorage.secrets = JSON.stringify(secrets);
  }
  else
    secrets = {};

  if (/secret=(\w+)/.test(window.location.hash))
    setSecret(guid, RegExp.$1);
  else if (secrets.hasOwnProperty(guid))
    setSecret(guid, secrets[guid].value);

  if (/tab=(\w+)/.test(window.location.hash))
    selectTab(RegExp.$1);
  else
    document.getElementsByClassName('tab')[0].onclick();
}

function sortTable(event)
{
  var node = event.target;
  var header, table;
  while (node && (typeof header == "undefined" || typeof table == "undefined"))
  {
    if (typeof header == "undefined" && node.localName == "th")
      header = node;
    if (typeof table == "undefined" && node.localName == "table")
      table = node;
    node = node.parentNode;
  }

  if (typeof header == "undefined" || typeof table == "undefined" || typeof table._originalRows == "undefined")
    return;

  var sortDir = "ascending";
  if (header.getAttribute("sortDir") == "ascending")
    sortDir = "descending";
  else if (header.hasAttribute("sortDir"))
    sortDir = null;

  var sortedRows = table._originalRows.slice();
  if (sortDir)
  {
    for (var i = 0; i < sortedRows.length; i++)
      sortedRows[i]._sortKey = sortedRows[i].cells[header.cellIndex].textContent.toLowerCase();

    sortedRows.sort(function(a, b)
    {
      var result = 0;
      if (a._sortKey < b._sortKey)
        result = -1;
      else if (a._sortKey > b._sortKey)
        result = 1;

      if (sortDir == "descending")
        result = -result;

      return result;
    });
  }

  var body = table.tBodies[0];
  while (body.firstChild)
    body.removeChild(body.firstChild);
  for (var i = 0; i < sortedRows.length; i++)
    body.appendChild(sortedRows[i]);

  if (typeof table._sortCol != "undefined")
  {
    table._sortCol.removeAttribute("sortDir");
    delete table._sortCol;
  }

  if (sortDir)
  {
    table._sortCol = header;
    header.setAttribute("sortDir", sortDir);
  }
}

function initTables()
{
  var tables = document.getElementsByClassName("sortable");
  for (var i = 0; i < tables.length; i++)
  {
    var table = tables[i];
    if (table.localName.toLowerCase() != "table" || !table.tHead || table.tBodies.length < 1)
      continue;

    var headRow = table.tHead.rows[0];
    for (var j = 0; j < headRow.cells.length; j++)
      headRow.cells[j].addEventListener("click", sortTable, false);

    var body = table.tBodies[0];
    var originalRows = [];
    for (var j = 0; j < body.rows.length; j++)
      originalRows.push(body.rows[j]);
    table._originalRows = originalRows;
  }
}

function toLocalDate(str)
{
  if (!/^(\d+)-(\d+)-(\d+)\s+(.*)/.test(str))
    return str;

  var mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][RegExp.$2 - 1];
  var date = new Date(RegExp.$3 + " " + mon + " " + RegExp.$1 + " " + RegExp.$4);
  return date.toLocaleString();
}

function changeDates()
{
  var row = document.getElementById("timeRow");
  if (row && row.cells && row.cells.length >= 2)
    row.cells[1].textContent = toLocalDate(row.cells[1].textContent);

  var classes = ["subscriptionLastDownloadAttempt", "subscriptionLastDownloadSuccess", "subscriptionExpiration"];
  for (var i = 0; i < classes.length; i++)
  {
    var nodes = document.getElementsByClassName(classes[i]);
    for (var j = 0; j < nodes.length; j++)
    {
      var spans = nodes[j].getElementsByTagName("span");
      for (var k = 0; k < spans.length; k++)
        if (spans[k].hasAttribute("title"))
          spans[k].setAttribute("title", toLocalDate(spans[k].getAttribute("title")));
    }
  }
}

window.addEventListener("DOMContentLoaded", initTables, false);
window.addEventListener("DOMContentLoaded", changeDates, false);
