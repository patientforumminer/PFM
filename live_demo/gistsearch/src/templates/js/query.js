var queryWords; //this var is set in index.html after query results have come in
var newQueryWords = [];

var queryWordsSVG;

function showQueryWords() {
    newQueryWords = queryWords.slice(0);
    d3.select("#queryWordsDIV").selectAll("svg").remove();
    queryWordsSVG = d3.select("#queryWordsDIV")
      .append("svg");
    queryWordsSVG.selectAll("text")
      .data(queryWords)
      .enter()
      .append("text")
      .style("font-family","verdana")
      .style("font-size","8pt")
      .style("-webkit-user-select", "none")
      .attr("x", 10)
      .attr("y", function(d,i) { return i*10})
      .text(function(d) { return d })
      .on("click", function(d) {
        var index = newQueryWords.indexOf(d)
        if (index == -1) {
          newQueryWords.push(d);
        } else {
          newQueryWords.splice(index, 1);
        }
        updateQueryWords(); //adapt color of query words
      });
}

function updateQueryWords() {
  queryWordsSVG = d3.select("#queryWordsDIV").selectAll("text")
    .style("fill", function(d) {
        return newQueryWords.indexOf(d) == -1 ? "#eeeeee" : "#333333";
    })

}

function sendNewQuery() {
  var keywordString = newQueryWords.join(" ");
	search(keywordString, expand, function(result) {
		console.log("result",result);
		queryWords = result.queryWords;
		showQueryWords(); //defined in query.js
		messages = result.messages;
		entityCounts = getEntityCounts(messages); //defined in message.js, used to size the graph's nodes
		createGraph(result.graph); //
		drawMessages();
		initCategoryMenu(); //in categories.js
	})
}
