var categories;
//read categories from config/categories.json

var categoriesFile = "static/config/categories.json";
//var categoriesFile = "config/categories.json"
d3.json(categoriesFile, function(data) {
  categories = data;
  console.log("loaded categories", categories);
})

var categorySVG;
var currentCategories;

var categorySVG = d3.select("#categoryDIV")
  .append("svg")
  .attr("width","100%")
  .attr("height","100%");

function populateCategoryMenu() {
  currentCategories = [];

  /// take the categories present in the graph
  for (var i=0; i<graph.nodes.length; i++) {
    var cat = graph.nodes[i].category;
    //see if it is already in the currentCategories list
    if ($.grep(currentCategories, function(o) { return o.id.toLowerCase() == cat.toLowerCase() }).length == 0) {
      //get category object
      var catObjectsFound = $.grep(categories, function(o) { return o.id.toLowerCase() == cat.toLowerCase()});
      if (catObjectsFound.length > 0) {
        currentCategories.push(catObjectsFound[0]);
        //categories are selected by default
        catObjectsFound[0].isSelected = true;
      } else {
        console.log("could not find category for " + cat);
      }
    }
  }

  //add menu entry for each category
  categorySVG.selectAll(".categoryMenuEntry")
    .data(currentCategories, function(d) { return d.id })
    .enter()
    .append("g")
    .attr("class","categoryMenuEntry")
    .each(function(d) {
      d3.select(this)
        .append("circle")
        .attr("r",5)
        .style("stroke","#ffffff");

      d3.select(this)
        .append("text")
        .text(function(d) {
          return d.label;
        })
        .attr("x",8)
        .attr("y",4)
        .style("font-family","verdana")
        .style("font-size","8pt")
        .style("-webkit-user-select", "none");
    })
    .on("click", function(d) {
      console.log("clicked category",d);
      //toggle selection
      d.isSelected = !d.isSelected;
      for (var i=0; i<graph.nodes.length; i++) {
        if(graph.nodes[i].category.toLowerCase() == d.id)
          graph.nodes[i].isSelected = d.isSelected;
      }
      console.log("graph.nodes", graph.nodes);
      drawGraph();
      updateCategoryMenu();
      calculateEntityMatchAndSort(); //update ranking of messages, and resort. Defined in messages.js
    })

    categorySVG.selectAll(".categoryMenuEntry")
      .data(currentCategories, function(d) { return d.id })
      .exit()
      .remove();

    updateCategoryMenu();
}

function updateCategoryMenu() {
  //update colors of menu entries
  categorySVG.selectAll(".categoryMenuEntry")
    .data(currentCategories, function(d) { return d.id })
    .attr("transform", function(d,i) {
        //two colomns
        var x = i < currentCategories.length/2 ? 20 : 250;
        var y = 10 + (i % Math.ceil(currentCategories.length/2)) * 16;
        return "translate(" + x + "," + y + ")";
    })
    .each(function(d) {
      d3.select(this).selectAll("circle")
        .style("stroke-width", function() {
          return d.isSelected ? 3 : 0
        })
        .attr("fill", function(d) {
          return d.isSelected ? d.colour : "#eeeeee";
        });
      d3.select(this).selectAll("text")
        .style("fill",function(d) {
          return d.isSelected ? "#333333" : "#eeeeee";
        });
    })

}
