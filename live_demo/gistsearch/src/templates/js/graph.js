var HIGHLIGHT_COLOR = "#ffcc00";
var NODE_RADIUS_MIN = 6;
var NODE_RADIUS_MAX = 20;

var graph; //has attributes nodes and links
var hoveredNode = null;


var force = d3.layout.force()
  .charge(-220)
  .gravity(.05)
  .linkDistance(70);
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
	var linkCanvas  = graphG.append("g");
	var nodeCanvas  = graphG.append("g");
  var labelCanvas = graphG.append("g");
	link = linkCanvas.selectAll(".link");
  node = nodeCanvas.selectAll(".node");
  label = labelCanvas.selectAll(".nodelabel");

  force.on("tick", tick);
}

function setGraphSize(width, height) {
  force.size([width, height]);
  force.start();
}

function createGraph(g) {
  graph = g;

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

  }
  drawGraph();
}

function updateZoomLevel(zoomLevel) {
	currentZoomLevel = zoomLevel;
}

function drawGraph() {
  link = link
		.data(force.links(), function(d) {
    		return d.source.id + "-" + d.target.id;
    	});

    link
    	.enter()
    	.append("line")
      .attr("class", "link")
      .style("stroke","#ffffff")
      .style("opacity", 0.8)
      .style("stroke-width",function(d) {
        return 6*(d.weight/graph.maxWeight);
      })

    link
      .exit()
      .remove();

  node = node
		.data(force.nodes(), function(d) {return d.id});

	newnodes = node
		.enter()
		.append("g")
    .attr("class", "node")
    .on("click", function(d) {
      console.log("clicked node",d);
      d.isSelected = !d.isSelected;
      drawGraph();
      sortMessages();
      drawMessages();
    })
    .on("mouseover", function(d) {
    	d3.event.stopPropagation();
	    hoveredNode = d;
    })
		.on("mouseout", function(d) {
			d3.event.stopPropagation();
			hoveredNode = null;
		});


	newnodes.append("circle")
		.attr("class","nodecircle")
		.attr("r", function(d) {
      return 15;
    })
    .style("stroke", function(d) {
      return "#ffffff";
    });

  //adjust node colors

  node.selectAll(".nodecircle")
    .style("fill",function(d) {
      if (d.isSelected) {
        var foundCat = $.grep(categories, function(o) { return o.id.toLowerCase() == d.category.toLowerCase()});
        return foundCat.length > 0 ? foundCat[0].colour : "#dddddd"; //default color
      } else {
        return "#eeeeee";
      }
    })
    .style("stroke-width", function(d) {
      return d.isSelected ? 2 : 0;
    });

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
/*
  newLabels.append("rect")
    .attr("class","nodelabelbackground")
    .attr("fill", "white")
    .attr("stroke-width", 0)
    .attr("x", -25)
    .attr("y", -7)
    .attr("width", 50)
    .attr("height", 14)
    .attr("opacity", 0.5);
*/
  newLabels.append("text")
    .attr("class","nodelabel")
    .attr("text-anchor","middle")
    .attr("dx", 0)
    .attr("dy", 4)
    .style("font-family","verdana")
    .style("font-size","10pt")
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

	force.start();
}
