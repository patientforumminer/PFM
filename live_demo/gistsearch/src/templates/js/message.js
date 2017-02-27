
var MESSAGE_SPACING = 10; //space between messages in pixels
var MESSAGE_MARGIN = 30;
var COMMENT_INDENT = 50;

var messages = []; //set bij index.html after message have been received from the server
var entityCounts; //list of entities and their occurence in the messages

var messageSVG = d3.select("#messageDIV")
    .append("svg")
    .attr("width","100%"); //height is set when messages are known

function drawMessages() {
  console.log("width messageSVG",messageSVG.node().getBBox().width);
  messageSVG.selectAll(".messageText")
    .data(messages)
    .enter()
    .append("text")
    .attr("class","messageText")
    .attr("x", function(d) { return MESSAGE_MARGIN + (d.parentID == null ? 0 : COMMENT_INDENT)})
    .text(function(d) { return d.text })
    .each(function(d) { wrap(d3.select(this),
                        $("#messageDIV").width() - 2*MESSAGE_MARGIN - (d.parentID == null ? 0 : COMMENT_INDENT),
                        ["Exon","GIST","Gleevec"])}); //distribute text over tspan elements

  //update location of messages
  messageSVG.selectAll(".messageText")
    .data(messages)
    .transition()
    .attr("y", function(d,i) { return 30+calculateHeightOfMessageList(messageSVG, i-1) })

  //adapt height of svg to fit all messages
  messageSVG
    .attr("height",function() { return calculateHeightOfMessageList(messageSVG) });

}


function wrap(text, width, keywords) {
  text.each(function() {
    var text = d3.select(this),
        words = text.text().split(/\s+/).reverse(),
        word,
        previousWord = null,
        xPos = text.attr("x"),
        line = [],
        lineHeight = 1.3, // ems
        tspan = text.text(null).append("tspan").attr("x", xPos).attr("dy", "0");
    while (word = words.pop()) {
      line.push(word);
      tspan.text(line.join(" "));
      var lineTooLong = tspan.node().getComputedTextLength() > width;
      if (lineTooLong || (previousWord != null && keywordMatchesWord(word, keywords) != keywordMatchesWord(previousWord, keywords))) {
        line.pop();
        tspan.text(line.join(" ")); //remove word from tspan
        line = [word]; //start a new tspan
        if (lineTooLong) {
          tspan = text.append("tspan").attr("x", xPos).attr("dy", lineHeight + "em").text(word);
        } else {
          tspan = text.append("tspan").attr("dx", "0.2em").attr("dy", "0em").text(word);
        }
        if (keywordMatchesWord(word, keywords)) tspan.attr("class","keyword");
      }
      previousWord = word;
    }
  });
}

//calculates the sum of the height of all messages up to (and including) the message with the given number.
//if the message number is null, calculates the sum of the height of all messages.
function calculateHeightOfMessageList(svgElement, upToMessageNumber) {
  var sumHeight = 0;
  svgElement.selectAll("text")
    .each(function(d,i) { sumHeight += (i <= upToMessageNumber || upToMessageNumber == null) ? MESSAGE_SPACING + this.getBBox().height : 0});
  return sumHeight;
}

function keywordMatchesWord(word, keywords) {
  var matches = $.grep(keywords, function(o) { return (word.toLowerCase().startsWith(o.toLowerCase())) });
  return (matches.length > 0);
}

function getEntityCounts(messageList) {
    //counts the occurence of entities in the messages from the messageList.
    //this function is used to size the nodes in the graph, which should
    //reflect the occurence of entities in the resultset at the right hand of
    //the screen
    var entityCounts = [];
    for (var messageIndex=0; messageIndex<messageList.length; messageIndex++) {
      var message = messageList[messageIndex];
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
    return entityCounts;
}

function calculateEntityMatch(messageList, entityList) {
  //sets a match value for each message, depending on the entities present in each message
  //the more entities of the entityList present, the higher the value
  for (var messageIndex=0; messageIndex<messageList.length; messageIndex++) {
    var matchCount = 0;
    var nrEntities = messageList[messageIndex].entities.length;
    for (var entityIndex=0; entityIndex<nrEntities; entityIndex++) {
      var entity = messageList[messageIndex].entities[entityIndex].entity; //we need the label, not the object
      matchCount += (entityList.indexOf(entity) == -1 ? 0 : 1);
    }
    //divide the count by the total nr of entities
    matchCount = matchCount / nrEntities;
    messageList[messageIndex].entityMatchScore = matchCount;
  }
}

function sortMessages() {
  
}
