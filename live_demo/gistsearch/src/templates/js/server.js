//var SERVER_URL = "http://gistsearch.darkwebmonitor.eu";
var SERVER_URL = "http://192.168.99.100:5000";
var SERVER_AVAILABLE = true;

function executeQuery(query, expand, callbackFunction) {
  if (SERVER_AVAILABLE) return executeQueryOnServer(query, expand, callbackFunction);
  else readData(callbackFunction);
}

function readData(callbackFunction) {
  d3.json("data/result.json", function(error, json) {
    if (error) return console.warn(error);
    data = json;
    callbackFunction(data);
  });
}

function executeQueryOnServer(query, expand, callbackFunction) {
  var url = SERVER_URL + "/get_json?expand=" + (expand?"1" : "0") + "&query=" + query;
  $.ajax({
    type:"POST",
    url: url,
    accepts: "application/json",
    dataType: "json",
    contentType:"application/json",
    headers: {
      "X-Stream": "true"
    },
    data: JSON.stringify({
       "query" : query
     }),
    success: callbackFunction,
    error: function(jqXHR, textStatus, errorThrown){
    	console.log("error while executing query " + query + ": " + textStatus);
    }
  });
 }
