//MAC:
var SERVER_URL = "http://localhost:5000";
//PC:
var SERVER_URL = "http://192.168.99.100:5000";

//for testing without backend server set this variable to false
var SERVER_AVAILABLE = true;

function executeQuery(query, expand, corpus, callbackFunction) {
  if (SERVER_AVAILABLE) return executeQueryOnServer(query, expand, corpus, callbackFunction);
  else readData(callbackFunction);
}

function readData(callbackFunction) {
  d3.json("data/json_example_query_results.summary.json", function(error, json) {
    if (error) return console.warn(error);
    data = json;
    callbackFunction(data);
  });
}

function executeQueryOnServer(query, expand, corpus, callbackFunction) {
  console.log("executeQueryOnServer | corpus = " + corpus);
  var url = SERVER_URL + "/get_json_summarized?expand="
            + (expand?"1" : "0") + "&query=" + query
            + "&corpus=" + corpus;
  console.log("executeQueryOnServer: url=", url);
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
    	console.log("error while executing query " + query + ": " + textStatus + " " + errorThrown);
    }
  });
 }
