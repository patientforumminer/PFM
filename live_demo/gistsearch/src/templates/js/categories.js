var categories = [
  {id:"medicines", label:"Medicines", colour:"#1f77b4"},
  {id:"neoplastic process", label:"Neoplastic Process", colour:"#ff7f0e"},
  {id:"cell or molecular dysfunction", label:"Molecular Dysfunction", colour:"#2ca02c"},
  {id:"gene or genome", label:"Gene / Genome", colour:"#d62728"},
  {id:"disease or syndrome", label:"Disease or Syndrome", colour:"#9467bd"},
  {id:"therapeutic or preventive procedure", label:"Therapeutic / Preventive", colour:"#8c564b"},
  {id:"organic chemical,pharmacologic substance", label:"Organic Chemical", colour:"#e377c2"},
  {id:"medical device", label:"Medical Device", colour:"#9edae5"},
  {id:"body part, organ, or organ component", label:"Body Part / Organ", colour:"#bcbd22"},
  {id:"biologically active substance,pharmacologic substance", label:"Biologically Active Substance,Pharmacologic Substance", colour:"#17becf"},
  {id:"amino acid, peptide, or protein,immunologic factor,pharmacologic substance", label:"Amino Acid, Peptide, or Protein,Immunologic Factor,Pharmacologic Substance", colour:"#aec7e8"},
  {id:"amino acid, peptide, or protein,pharmacologic substance", label:"Amino Acid, Peptide, or Protein,Pharmacologic Substance", colour:"ffbb78"},
  {id:"pharmacologic substance", label:"Pharmacologic Substance", colour:"#98df8a"},
  {id:"sign or symptom", label:"Sign or Symptom", colour:"#ff9896"},
  {id:"food", label:"Food", colour:"#c5b0d5"},
  {id:"diagnostic procedure", label:"Diagnostic Procedure", colour:"#c49c94"},
  {id:"supplements", label:"Supplements", colour:"#f7b6d2"},
  {id:"finding", label:"Finding", colour:"#dbdb8d"}
]

var categorySVG;
var currentCategories = [];

function initCategoryMenu() {
  categorySVG = d3.select("#categoryDIV")
    .append("svg")
    .attr("width","100%")
    .attr("height","100%");

  /// take the categories present in the graph
  for (var i=0; i<graph.nodes.length; i++) {
    var cat = graph.nodes[i].category;
    //see if it is already in the currentCategories list
    if ($.grep(currentCategories, function(o) { return o.id.toLowerCase() == cat.toLowerCase() }).length == 0) {
      //get category object
      var catObject = $.grep(categories, function(o) { return o.id.toLowerCase() == cat.toLowerCase()})[0];
      currentCategories.push(catObject);
      //categories are selected by default
      catObject.isSelected = true;
    }

  }

  console.log("currentCategories", currentCategories);
  //add entry for each category
  categorySVG.selectAll(".categoryMenuEntry")
    .data(currentCategories)
    .enter()
    .append("g")
    .attr("class","categoryMenuEntry")
    .attr("transform", function(d,i) {
        //two colomns
        var x = i < currentCategories.length/2 ? 20 : 200;
        var y = 10 + (i % Math.ceil(currentCategories.length/2)) * 16;

        /*
        //one column
        var x = 30;
        var y = 20 + i * 20;
        */
        return "translate(" + x + "," + y + ")";
    })
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
    })
    updateCategoryMenu();
}

function updateCategoryMenu() {
  //update borders of menu entries
  categorySVG.selectAll(".categoryMenuEntry")
    .data(currentCategories)
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
