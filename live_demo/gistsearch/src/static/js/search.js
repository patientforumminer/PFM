var NR_COLS = 5;

var queryWords = [];
var queryWordsSVG;

function searchButtonClicked(expand) {
  $("#expandedSearchDIV").css("visibility","visible");
  var query;
  if (expand) {
    query = $("#queryINPUT").val();
  } else {
    query = queryWords.join(" ");
    $("#queryINPUT").val(query); //show query terms in search field
    //$("#expandedSearchDIV").css("visibility","hidden");
  }
  var corpus = $("#corpusSelect").val();
	sendQueryAndUpdateGUI(query, expand, corpus, false); //false: this is not a 'search similar message' query
}

function sendQueryAndUpdateGUI(query, expand, corpus, similar) {
  executeQuery(query, expand, corpus, function(data) {
    console.log("data",data);
    queryWords = similar ? [] : data.query_words;
    showQueryWords();
    graph = convertToGraph(data.entity_matrix);
    messageBlocks = data.threads.slice(0,15);

    calculateEntityMatchAndSort(); //sorts and displays messages
    getEntityCounts(); //defined in message.js, used to size the graph's nodes. result is stored in entityCounts (declared in message.js)
    populateCategoryMenu(); //in categories.js. Reads the categories from the graph's entities
    //set sizes of DIVs corresponding to number of categories
    $("#categoryDIV").height(20 + Math.ceil(currentCategories.length / 2) * 16);
    $("#graphDIV").css("bottom", $("#categoryDIV").outerHeight())
    updateGraphSize();
    populateGraph();
  });
}

function showQueryWords() {
  //update sizes of DIVs corresponding to number of query words
    $("#queryWordsDIV").height(20 + Math.ceil(queryWords.length / NR_COLS) * 20);
    $("#graphDIV").css("top", $("#queryDIV").outerHeight());

    d3.select("#queryWordsDIV").selectAll("svg").remove();
    queryWordsSVG = d3.select("#queryWordsDIV")
      .append("svg")
      .attr("height","100%")
      .attr("width","100%");

    queryWordsSVG.selectAll(".queryWordEntry")
      .data(queryWords)
      .enter()
      .append("g")
      .attr("class","queryWordEntry")
      .each(function(d) {
        d3.select(this)
          .append("rect")
          .attr("x",0)
          .attr("y",0)
          .attr("height",16)
          .attr("width",70)
          .style("fill","#ffffff")
        d3.select(this)
          .append("text")
          .attr("x",4)
          .attr("y",11)
          .style("font-family","verdana")
          .style("font-size","8pt")
          .style("-webkit-user-select", "none")
          .text(function(d) { return d });
      })
      .on("click", function(d) {
        var index = queryWords.indexOf(d)
        if (index == -1) {
          queryWords.push(d);
        } else {
          queryWords.splice(index, 1);
        }
        updateQueryWords();
        drawMessages(); //update highlights in message text
      });

      queryWordsSVG.selectAll(".queryWordEntry")
        .data(queryWords)
        .exit()
        .remove();

      updateQueryWords();
}

//set of adapt color and position of query words
function updateQueryWords() {
  queryWordsSVG.selectAll(".queryWordEntry")
    .attr("transform", function(d, i) {
      var x = 20 + 80 * (i % NR_COLS);
      var y = 10 + 20 * Math.floor(i / NR_COLS);
      return "translate(" + x + "," + y + ")";
    })
    .each(function(d) {
      d3.select(this).selectAll("rect")
        .style("opacity", function(d) {
          return queryWords.indexOf(d) == -1 ? 0 : 1;
        });
      d3.select(this).selectAll("text")
        .style("fill", function(d) {
          return queryWords.indexOf(d) == -1 ? "#eeeeee" : "#333333";
        });
    })
}


function searchSimilarMessages(message) {
  console.log("searchSimilar | message = ",message);
  var query = "";
  for (var i=0; i<message.text.length; i++) {
    query += " " + message.text[i].sentence;
  }
  console.log("query",query);
  $("#queryINPUT").val(""); //empty search field
  $("#expandedSearchDIV").css("visibility","hidden");
  var corpus = $("#corpusSelect").val();
  sendQueryAndUpdateGUI(query, false, corpus, true); //false : no query expansion, true: this is a 'search similar message' query
}
