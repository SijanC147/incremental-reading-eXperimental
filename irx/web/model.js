var imagesSidebar = true;
var stylesVisible = true;
var highlightsVisible = true;
var removedVisible = false;
var lastImageUrl = "";

function markRange(identifier, attributes) {
    var range, sel = window.getSelection();
    if (sel.type == "Range") {
        range = sel.getRangeAt(0);
        var startNode = document.createElement('span');
        startNode.setAttribute('id', ('sx' + identifier));
        for (var attr in attributes) {
            if (attributes.hasOwnProperty(attr)) {
                if ((attr == "styles") & startNode.hasAttribute("irx-styles")) {
                    attrVal = startNode.getAttribute("irx-styles") + " " + attributes[attr];
                    attrVals = attrVal.split(" ");
                    attrVal = attrVals.filter(function (v, i, self) { return (self.indexOf(v) === i & v.length > 0) });
                    attrVal = attrVal.join(" ");
                } else {
                    attrVal = attributes[attr];
                }
                startNode.setAttribute('irx-' + attr, attrVal);
            }
        }
        range.insertNode(startNode);
        var endNode = document.createElement('span');
        endNode.setAttribute('id', ('ex' + identifier));
        range.collapse(false);
        range.insertNode(endNode);
        range.setStartAfter(startNode);
        range.setEndBefore(endNode);
        sel.removeAllRanges();
        sel.addRange(range);
    }
}

function selectMarkedRange(identifier) {
    var startNode, endNode, range, sel;
    startNode = document.getElementById('sx' + identifier);
    endNode = document.getElementById('ex' + identifier);
    if (startNode && endNode) {
        range = document.createRange();
        range.setStartAfter(startNode);
        range.setEndBefore(endNode);
        sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        return startNode;
    }
    return false;
}

function execCommandOnRange(identifiers, attrs, clear) {
    if (!Array.isArray(identifiers) & !selectMarkedRange(identifiers)) {
        identifier = identifiers;
        markRange(identifier, attrs);
        identifiers = Array();
        identifiers.push(identifier);
    }
    for (var i in identifiers) {
        identifier = identifiers[i]
        var startNode = selectMarkedRange(identifier);
        if (startNode) {
            var range, sel = window.getSelection();

            if (sel.rangeCount && sel.getRangeAt) {
                range = sel.getRangeAt(0);
            }

            document.designMode = "on";
            if (range) {
                sel.removeAllRanges();
                sel.addRange(range);
            }

            if (clear) {
                document.execCommand("removeFormat", false, null);
            }

            if (startNode.hasAttribute("irx-remove")) {
                docImgs = document.getElementsByTagName('img');
                selImgs = Array();
                for (i = 0; i < docImgs.length; i++) {
                    if (sel.containsNode(docImgs.item(i))) {
                        selImgs.push(docImgs.item(i));
                    }
                }
                if (removedVisible) {
                    document.execCommand("hiliteColor", false, "grey");
                    document.execCommand("foreColor", false, "white");
                    for (var im in selImgs) {
                        selImgs[im].setAttribute("style", "width: 30%; border: 5px solid grey;");
                    }
                } else {
                    for (var im in selImgs) {
                        selImgs[im].setAttribute("style", "display: initial;");
                    }
                    document.execCommand("hiliteColor", false, "black");
                    document.execCommand("foreColor", false, "white");
                }
            } else {
                if (startNode.hasAttribute("irx-link")) {
                    var irx_link = startNode.getAttribute("irx-link");
                    document.execCommand("createLink", false, "irxnid:" + irx_link);
                }
                if (startNode.hasAttribute("irx-styles") & stylesVisible) {
                    var irx_styles = startNode.getAttribute("irx-styles").split(" ");
                    for (var s in irx_styles) {
                        document.execCommand(irx_styles[s], true, true);
                    }
                }
                if (startNode.hasAttribute("irx-bg") & highlightsVisible) {
                    var irx_bg = startNode.getAttribute("irx-bg");
                    document.execCommand("hiliteColor", false, irx_bg);
                }
                if (startNode.hasAttribute("irx-fg") & highlightsVisible) {
                    var irx_fg = startNode.getAttribute("irx-fg");
                    document.execCommand("foreColor", false, irx_fg);
                }
            }
            document.designMode = "off";
            sel.removeAllRanges();
        }
    }
}

function rangeIdsWithAttr(irx_attr) {
    var xPathQuery = '//*[@' + irx_attr + ']';
    var xPathResult = document.evaluate(xPathQuery, document, null, XPathResult.ANY_TYPE, null);
    var node_ids = [];
    while (node = xPathResult.iterateNext()) {
        node_ids.push(node.id.substring(2));
    }
    return node_ids;
}

function toggleStyles(manual) {
    prev_state = stylesVisible;
    if (!manual | manual == "toggle") {
        stylesVisible = !stylesVisible;
    } else {
        stylesVisible = manual;
    }
    if (prev_state != stylesVisible) {
        execCommandOnRange(rangeIdsWithAttr('irx-styles'), null, true);
    }
}

function toggleHighlights(manual) {
    prev_state = highlightsVisible;
    if (!manual | manual == "toggle") {
        highlightsVisible = !highlightsVisible;
    } else {
        highlightsVisible = manual;
    }
    if (prev_state != highlightsVisible) {
        execCommandOnRange(rangeIdsWithAttr('irx-bg'), null, true);
    }
}

function toggleRemoved(manual) {
    prev_state = removedVisible;
    if (!manual | manual == "toggle") {
        removedVisible = !removedVisible;
    } else {
        removedVisible = manual;
    }
    if (prev_state != removedVisible) {
        execCommandOnRange(rangeIdsWithAttr('irx-remove'), null, true);
    }
}

function toggleImagesSidebar(manual) {
    var prev_state = imagesSidebar;
    if (!manual | manual == "toggle") {
        imagesSidebar = !imagesSidebar;
    } else {
        imagesSidebar = manual;
    }
    if (prev_state != imagesSidebar) {
        var attrVal = imagesSidebar ? "yes" : "no";
        var text = document.getElementsByClassName("irx-text")[0];
        var images = document.getElementsByClassName("irx-images")[0];
        text.setAttribute("irx-images-sidebar", attrVal);
        images.setAttribute("irx-images-sidebar", attrVal);
    }
}