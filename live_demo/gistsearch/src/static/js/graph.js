var WEIGHT_THRESHOLD = 0.0; //factor of max weight
var HIGHLIGHT_COLOR = "#ffcc00";
var NODE_RADIUS_MIN = 6;
var NODE_RADIUS_MAX = 20;

var graph; //has attributes nodes and links
var hoveredNode = null;
var highlightedNodeIDs = [];

var linkCanvas;
var nodeCanvas;
var labelCanvas;

var dragStarted; //to keep track whether a click was part of a drag, or is a single click
var isSingleClick; //to keep track whether a click is a single mouse click, or part of a double click

var force = d3.layout.force()
  .charge(-320)
  .gravity(.05)
  .linkDistance(function(l,i) {
    var dist = 500 / l.weight;
    if (dist < 100) dist = 100;
    else if (dist > 300) dist = 300;
    return dist;
  });
  //  .alpha(0.1);

var node, link; //svg objects representing nodes and links

var currentZoomLevel = 1.0; //is updated from index.html

function tick() {
    link.attr("x1", function(d) {return d.source.x;})
        .attr("y1", function(d) {return d.source.y;})
        .attr("x2", function(d) {return d.target.x;})
        .attr("y2", function(d) {return d.target.y;});

    node.attr("transform", function(d) {
      return "translate(" + d.x + "," + d.y + ")";
    });

    label.attr("transform", function(d) {
      return "translate(" + d.x + "," + d.y + ")";
    });
  };

//called from index.html
function initGraph(graphG) {
  //draw nodes on top of all links
	linkCanvas  = graphG.append("g");
	nodeCanvas  = graphG.append("g");
  labelCanvas = graphG.append("g");

	link = linkCanvas.selectAll(".link");
  node = nodeCanvas.selectAll(".node");
  label = labelCanvas.selectAll(".nodelabel");

  force.on("tick", tick);
}

function setGraphSize(width, height) {
  force.size([width, height]);
  force.start();
}

function populateGraph() {
  console.log("populateGraph()");
  //delete any nodes, labels and lines from a previous graph
//  linkCanvas.selectAll("*").remove();
//  nodeCanvas.selectAll("*").remove();
//  labelCanvas.selectAll("*").remove();

  force.nodes(graph.nodes);
  force.links(graph.links);
  //set initial nodes' position around center of screen
  //distribute nodes equally on circle around center
  var centerPointX = force.size()[0]/2,
      centerPointY = force.size()[1]/2;
  var r = 150;
  for (var nodeIndex=0; nodeIndex<force.nodes().length; nodeIndex++) {
    var angle = nodeIndex * ((2*Math.PI)/force.nodes().length);
    force.nodes()[nodeIndex].x = centerPointX + r*Math.cos(angle);
    force.nodes()[nodeIndex].y = centerPointY + r*Math.sin(angle);
  }

  maxEntityCount = 0;
  for (i=0; i<entityCounts.length; i++) {
    //only check the entities in the graph
    var nodes = $.grep(graph.nodes, function(o) { return o.id == entityCounts[i].entityId});
    if (nodes.length > 0) {
      //entity is in graph
      if (entityCounts[i].count > maxEntityCount) maxEntityCount = entityCounts[i].count;
    }
  }
  console.log("maxEntityCount",maxEntityCount);
  drawGraph(true);
}

function updateZoomLevel(zoomLevel) {
	currentZoomLevel = zoomLevel;
}


function drawGraph(reposition) {
  link = link
		.data(force.links(), function(d) {
    		return d.source.id + "-" + d.target.id;
    	});

    link
    	.enter()
    	.append("line")
      .attr("class", "link");

    //adapt link colors
    link
      .style("stroke", function(d) {
        return (d.source == hoveredNode || d.target == hoveredNode) ?
        "#ffff00" : "#ffffff";
      })
      .style("opacity", function(d) {
        //check if one of the link's nodes is hovered
        return (d.source == hoveredNode || d.target == hoveredNode) ?
        1 : Math.min(1.0, 0.4 + 0.8*(d.weight/graph.maxWeight));
      })
      .style("stroke-width",function(d) {
        return 6*(d.weight/graph.maxWeight);
      });


    link
      .exit()
      .remove();

  node = node
		.data(force.nodes(), function(d) {return d.id});

	newnodes = node
		.enter()
		.append("circle")
    .attr("class", "node")
    .attr("r", function(d) {
      //get number of results that countain this entity
      var counts = $.grep(entityCounts, function(o) { return o.entityId.toLowerCase() == d.id.toLowerCase()});
      var n = (counts.length > 0) ? counts[0].count : 0; //some entities in the matrix are not in the result list
      return NODE_RADIUS_MIN + (n / maxEntityCount) * (NODE_RADIUS_MAX - NODE_RADIUS_MIN);
    })
    .on("click", function(d) {
      console.log("clicked node",d);
      if (dragStarted) {
        console.log("drag started");
        d3.event.stopPropagation();
        dragStarted = false;
      } else {
        //no drag; wait to see whether this is a double click, or a single click
        isSingleClick = true; //can be set to false by double click or drag
        setTimeout(function() {
          if (isSingleClick) {
            d.isSelected = !d.isSelected;
            drawGraph(false);
            calculateEntityMatchAndSort(); //update ranking of messages, and resort. Defined in messages.js
          }
        }, 200);
      }
    })
    .on("dblclick", function(d) {
      d3.event.stopPropagation();
      console.log("doubleclicked node",d);
      isSingleClick = false;
      if (queryWords.indexOf(d.id.toLowerCase()) == -1) {
        queryWords.push(d.id.toLowerCase());
        showQueryWords();
        drawMessages();
      }
    })
    .on("mouseover", function(d) {
      console.log("mouseover");
    	d3.event.stopPropagation();
	    hoveredNode = d;
      for (var i=0; i<graph.links.length; i++) {
        var l = graph.links[i];
        if (l.source == d) highlightedNodeIDs.push(l.target.id);
        else if (l.target == d) highlightedNodeIDs.push(l.source.id);
      }
      drawGraph(false);
    })
		.on("mouseout", function(d) {
			d3.event.stopPropagation();
      highlightedNodeIDs.length = 0;
			hoveredNode = null;
      drawGraph(false);
		});

  //adjust node colors
  node
    .style("fill",function(d) {
      if (d.isSelected) {
        var foundCat = $.grep(categories, function(o) { return o.id.toLowerCase() == d.category.toLowerCase()});
        return foundCat.length > 0 ? foundCat[0].colour : "#dddddd"; //default color
      } else {
        return "#eeeeee";
      }
    })
    .style("stroke-width", function(d) {
      if ((highlightedNodeIDs.indexOf(d.id) != -1) || d == hoveredNode) return 4;
      else if (d.isSelected) return 2;
      else return 0;
    })
    .style("stroke", function(d) {
      return ((highlightedNodeIDs.indexOf(d.id) != -1) || d == hoveredNode) ? "#ffff00" : "#ffffff";
    })

	node
	 .exit()
   .remove();

  //add labels in a separate layer, to prevent nodes overlapping labels
  label = label
    .data(force.nodes(), function(d) {return d.id});

  newLabels = label
    .enter()
    .append("g")
    .attr("class", "nodeLabel")
    .style("pointer-events","none");

  newLabels.append("text")
    .attr("class","nodelabel")
    .attr("text-anchor","middle")
    .attr("dx", 0)
    .attr("dy", 4)
    .style("font-family","verdana")
    .style("font-size","9pt")
    .style("pointer-events","none") //make test non-selectable
    .text(function(d) {
      var labelText = d.id;
      return labelText;
    });

//adjust label colors
  label
    .style("fill",function(d) {
      return d.isSelected ? "#222222" : "#777777";
    });

  label
   .exit()
   .remove();

	if (reposition) force.start();
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
