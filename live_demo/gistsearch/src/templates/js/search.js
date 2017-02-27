WEIGHT_THRESHOLD = 0.5; //factor of max weight

function search(query, expand, callbackFunction) {
  var results = {};
  executeQuery(query, expand, function(data) { //defined in server.js
    console.log("data",data);
    //convert entity matrix to graph format
    var graph = convertToGraph(data.entity_matrix);
    var messageList = convertToMessageList(data.hits);
    results = {graph:graph, messages:messageList, queryWords:data.query_words};
    callbackFunction(results);
  });
}

function convertToGraph(matrix) {
  var links = [];
  var nodes = [];
  var maxWeight;
//determine maxWeight
  for (var linkIndex=0; linkIndex<matrix.length; linkIndex++) {
    if (linkIndex == 0 || matrix[linkIndex].weight > maxWeight)
      maxWeight = matrix[linkIndex].weight;
  }
  for (var linkIndex=0; linkIndex<matrix.length; linkIndex++) {
    //check if fromNode exists, if not: create
    var fromNode = findNodeWithId(matrix[linkIndex].a.entity, nodes);
    if (fromNode == null) {
      fromNode = {id:matrix[linkIndex].a.entity, category:matrix[linkIndex].a.category};
      nodes.push(fromNode);
    }
    //check if toNode exists, if not: create
    var toNode = findNodeWithId(matrix[linkIndex].b.entity, nodes);
    if (toNode == null) {
      toNode = {id:matrix[linkIndex].b.entity, category:matrix[linkIndex].b.category};
      nodes.push(toNode);
    }
    //add link to graph if weight is above threshold
    if (matrix[linkIndex].weight >= maxWeight * WEIGHT_THRESHOLD)
      links.push({source:fromNode, target:toNode, weight:matrix[linkIndex].weight});
  }
  //by default all nodes are selected
  for (var i=0; i<nodes.length; i++) nodes[i].isSelected = true;
  return {nodes:nodes, links:links, maxWeight:maxWeight};
}

function findNodeWithId(nodeId, nodes) {
  var foundNodes = $.grep(nodes, function(o) {return o.id == nodeId});
  if (foundNodes.length > 0) return foundNodes[0]; else return null;
}

//converts the hit list from the server, into a message list suitable for
//displaying in the visualisation
function convertToMessageList(hits) {
  var messages = [];
  for (var hitIndex=0; hitIndex<hits.length; hitIndex++) {
    var hit = hits[hitIndex];
    //each hit has a message that is the first message of a thread
    //and zero or more comments
    var message = {};
    message.id = hit.message._id;
    message.text = hit.message._source.text;
    message.entities = hit.message._source.entities ? hit.message._source.entities : [];
    message.time = hit.message._source.time;
    message.parentID = null;
    message.score = hit.message._score ? hit.message._score : null;
    messages.push(message);
    //read comments, if any
    for (var commentIndex=0; commentIndex<hit.comments.length; commentIndex++) {
      var comment = hit.comments[commentIndex];
      var child = {};
      child.parentID = message.id;
      child.id = comment._id;
      child.text = comment._source.text;
      child.entities = comment._source.entities ? comment._source.entities : [];
      child.time = comment._source.time;
      child.score = comment._score;
      messages.push(child);
    }
  }
  return messages;
}
