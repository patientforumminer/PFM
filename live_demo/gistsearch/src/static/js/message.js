
var MESSAGE_SPACING = 10; //space between messages in pixels
var BLOCK_SPACING = 20; //space between messages in pixels
var MESSAGE_MARGIN = 30;
var COMMENT_INDENT = 50;

var messageBlocks = []; //set server.js, is equal to data.threads
var entityCounts = [];




function drawMessages() {
  //empty the message list
  d3.select("#messageDIV").selectAll("*").remove();
  //make a list of entities and query words. Those will be highlighted in the text of
  //messages and comments
  var markedWords = [];
  for (var i=0; i<graph.nodes.length; i++) if (graph.nodes[i].isSelected) {
    markedWords.push(graph.nodes[i].id);
    markedWords.push(graph.nodes[i].id + "s");
  }
  for (var i=0; i<queryWords.length; i++) if (markedWords.indexOf(queryWords[i]) == -1) {
    markedWords.push(queryWords[i]);
    markedWords.push(queryWords[i] + "s");
  }
  //pattern for marking entities and query words
  var pattern = new RegExp("\\b("+markedWords.join("|")+")\\b", "gi");
  var replacement = "<mark>$1</mark>";

  d3.select("#messageDIV").selectAll("div")
    .data(messageBlocks, function(d) {return d.thread_id})
    .enter()
    .append("div")
    .attr("class","messageBlock")
    .each(function(d) {
      var messageBlock = d; //store context. Its 'summarized' attribute will be used when showing comments

      d3.select(this)
        .append("div")
        .attr("class","threadHeader")
        .each(function(d) {
          d3.select(this)
            .append("div")
            .attr("class","threadHeaderTitel")
            .text(function(d) { return d.thread_title});
            /*
          d3.select(this)
            .append("label")
              .text("summarized")
            .append("input")
            .attr("type","checkbox")
            .property("checked", function(d) { return d.summarized })
            .attr("class","threadSummaryCheckbox")
            .on("change", function(d) {
                d.summarized = !d.summarized;
                drawMessages();
            });
            */
        })
      d3.select(this)
        .append("div")
        .attr("class","messageThreadStart")
        .each(function() {
          d3.select(this) //'this' is the messageThreadStart
            //add header with dot, date, and button
            .append("div")
            .attr("class","messageHeader")
            .each(function() {
              if (d.content.message.searchhit == 1) {
                //if first message in the thread is a search hit, show a black dot
                d3.select(this) //'this' is the div for dot, date, and button
                  .append("img")
                  .attr("src", "./resources/blackdot.png")
                  //.attr("src", "./static/resources/blackdot.png")
                  .style("display","inline-block")
                  .style("margin-right", "5px");
              }
              d3.select(this) //'this' is the div for dot, date, and button
                .append("div")
                .html("<b>" + d.content.message.time + "</b>")
                .style("display","inline-block")
                .style("margin-right", "10px");
              d3.select(this) //'this' is the div for dot, date, and button
                .append("button")
                .text("search similar")
                .on("click", function() {
                  searchSimilarMessages(d.content.message); //defined in search.js
                })
                .style("display","inline-block");

            })
          //append message text
          d3.select(this)
            .append("div")
            .each(function(d) { //d is a thread
              var sentenceObjects = d.content.message.text;
              d3.select(this).selectAll("span")
                .data(sentenceObjects)
                .enter()
                .append("span")
                /*
                .style("display", function(d) {
                  return d.sent_summary_include=="0" ? "none" : "inline";
                })
                */
                .html(function(d) { return (d.sentence + " ").replace(pattern, replacement)})
            })
        })


      if (d.content.comments.length > 0) {
        d3.select(this)
          .append("div")
          .attr("class","messageCommentSection")
          .each(function() {
            d3.select(this).selectAll("div")
              .data(d.content.comments)
              .enter()
              .append("div")
              .style("display", function(d) {
                //post is shown if its summary value is higher than the threshold
                //and at least one sentence if higher than the threshold.
                //do not take into account sentences shorter than 3 characters
                var foundSentenceHigherThanThreshold = false; //long variable names are better!
                for (var i=0; i<d.text.length; i++) {
                  if (d.text[i].sentence.length > 3 && d.text[i].sent_summary_predicted >= currentThreshold) {
                    foundSentenceHigherThanThreshold = true;
                    break;
                  }
                }
                return d.summary_predicted >= currentThreshold && foundSentenceHigherThanThreshold ? "inline" : "none";
              })
              .attr("class","messageComment")
              .each(function(d) {
                var comment = d;
                d3.select(this) //'this' is the messageComment
                  //add header with dot, date, and button
                  .append("div")
                  .attr("class","messageHeader")
                  .each(function() {
                    if (d.searchhit == 1) {
                      //if comment is a search hit, show a black dot
                      d3.select(this) //'this' is the div for dot, date, and button
                        .append("img")
                        .attr("src", "./resources/blackdot.png")
                        //.attr("src", "./static/resources/blackdot.png")
                        .style("display","inline-block")
                        .style("margin-right", "5px");
                    }
                    d3.select(this) //'this' is the div for dot, date, and button
                      .append("div")
                      .html("<b>" + d.time + "</b>")
                      .style("display","inline-block")
                      .style("margin-right", "10px");
                    d3.select(this) //'this' is the div for dot, date, and button
                      .append("button")
                      .text("search similar")
                      .on("click", function() {
                        searchSimilarMessages(d); //defined in search.js
                      })
                      .style("display","inline-block");
                      /*
                    d3.select(this)
                      .append("label")
                        .style("margin-left","15px")
                        .text("summarized")
                      .append("input")
                      .attr("type","checkbox")
                      .property("checked", function(d) { return d.summarized })
                      .attr("class","commentSummaryCheckbox")
                      .on("change", function(d) {
                          d.summarized = !d.summarized;
                          drawMessages();
                      });
                      */

                  })
                //append message text

                d3.select(this) //'this' is the messageComment div
                  .append("div")
                  .each(function(d) { //d is a comment
                    var sentenceObjects = d.text; //TODO filter on summery
                    d3.select(this).selectAll("span")
                      .data(sentenceObjects)
                      .enter()
                      .append("span")
                      .style("display", function(d) {
                        return d.sent_summary_predicted >= currentThreshold ? "inline" : "none";
                      })
                      .html(function(d) { return (d.sentence + " ").replace(pattern, replacement)})
                  })


              });


          })
      }
    }) //each messageBlock

    //color or marked words
    $(".messageBlock").find("mark").each(function() {
        $(this).css("background-color",getColorForTerm($(this).text()));
    })
}

//takes a message text and adds <mark> tags for highlighting entities and query words
//entities and their colors are taken from the graph's nodes
//query words are taken from the queryWords variable defined in message.js
//we use regexp of the form: text.replace(/\b(drug|gleevec|kit)\b/ig,"<mark>$1</mark>")
function markEntitiesAndQueryWords(text) {
  //create a list of all entities and queryWords
  var markedWords = [];
  for (var i=0; i<graph.nodes.length; i++) if (graph.nodes[i].isSelected) markedWords.push(graph.nodes[i].id);
  for (var i=0; i<queryWords.length; i++) if (markedWords.indexOf(queryWords[i]) == -1) markedWords.push(queryWords[i]);
  console.log("markedWords", markedWords);
  var termList = markedWords.join("|");
  var pattern = new RegExp("\\b("+termList+")\\b", "gi");
  text = text.replace(pattern, "<mark>$1</mark>");
  return text;
}

function getColorForTerm(term) {
  if (queryWords.indexOf(term.toLowerCase()) != -1) return "#ffff00";
  else {
    var colour = "#888888";
    //entity comes from graph, get the category from the corresponding node
    var foundNodes = $.grep(graph.nodes, function(o) { return o.id.toLowerCase() == term.toLowerCase()});
    if (foundNodes.length > 0) {
      var category = foundNodes[0].category;
      var foundCategories = $.grep(categories, function(o) { return o.id.toLowerCase() == category.toLowerCase()});
      if (foundCategories.length > 0) {
        colour = foundCategories[0].colour;
      } //else console.log("could not find category for categoryname",category,". This category is not in categories.json");
    } //else console.log("could not find node for term",term,". This term is not in the entity_matrix");
    //get the coresponding color for the category
    return colour;
  }
}


function getEntityCounts() {
    entityCounts.length = 0;
    //counts the occurence of entities in the messages from the blocklist.
    //this function is used to size the nodes in the graph, which should
    //reflect the occurence of entities in the resultset at the right hand of
    //the screen

    //only take those messages that have a result score (those are the results from the query).
    //
    var messageList = [];
    for (var i=0; i<messageBlocks.length; i++) {
      messageList.push(messageBlocks[i].content.message);
      messageList.push.apply(messageList, messageBlocks[i].content.comments);
    }
    console.log("messageList",messageList);
    for (var messageIndex=0; messageIndex<messageList.length; messageIndex++) {
      var message = messageList[messageIndex];
      if (true) { //}(message.searchhit == 1) {
        if (typeof message.entities !== "undefined") { //not all messages have entities
          for (var entityIndex=0; entityIndex<message.entities.length; entityIndex++) {
            var entity = message.entities[entityIndex];
            var counts = $.grep(entityCounts, function(o) {return o.entityId == entity.entity});
            if (counts.length > 0) {
              counts[0].count++;
            } else {
              entityCounts.push({entityId:entity.entity, count:1});
            }
          }
        }
      }
    }
}

function calculateEntityMatchAndSort() {
  //construct entityList: these are the entities from each of the selected
  //nodes
  var entityList = [];
  for (var i=0; i<graph.nodes.length; i++) {
    if (graph.nodes[i].isSelected) entityList.push(graph.nodes[i].id);
  }


  //sets a value for each message block.
  //the value for a message block is the maximum score of its messages:
  //the tread start and the comments.
  //each message has an initial score (from the search engine)
  //if the message contains an entity from the negative list, this initial score
  //is divided by two
  for (var blockIndex=0; blockIndex<messageBlocks.length; blockIndex++) {
    var block = messageBlocks[blockIndex];
    //create list of messages in this block
    var mList = [block.content.message].concat(block.content.comments);
    var blockScore = 1;
    for (var i=0; i<mList.length; i++) {
      var negativeEntityFound = false;
      for (var nodeIndex=0; nodeIndex<graph.nodes.length && !negativeEntityFound; nodeIndex++) {
        //cycle through entities of this message
        if (typeof mList[i].entities != "undefined") {
          for (var entityIndex=0; entityIndex<mList[i].entities.length && !negativeEntityFound; entityIndex++) {
            negativeEntityFound = (mList[i].entities[entityIndex].entity.toLowerCase() == graph.nodes[nodeIndex].id.toLowerCase()
                && !graph.nodes[nodeIndex].isSelected);
          }
        }
      }
      if (negativeEntityFound) messageScore = 0.5;
    }
    block.blockScore = blockScore;
  }

  messageBlocks.sort(function(m1, m2) {
    return m2.blockScore - m1.blockScore; //sort descending
  });

  drawMessages();
}

function formatTime(t) {
  return "<b>" + t.substring(0,19).replace("T"," ") + "</b>";
}

//returns true if checkbox with id cbId is checked. returns false otherwise.
function isChecked(cbId) {
  return $('input[id="' + cbId + '"]:checked').length > 0;
}
