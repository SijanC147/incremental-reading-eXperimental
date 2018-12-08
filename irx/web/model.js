var imagesSidebar = true;
var stylesVisible = true;
var highlightsVisible = true;
var removedVisible = false;

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
                if (removedVisible) {
                    document.execCommand("hiliteColor", false, "grey");
                    document.execCommand("foreColor", false, "white");
                } else {
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

// function removeText() {
//     var selection = window.getSelection().getRangeAt(0);
//     var selectedText = selection.extractContents();
//     var span = document.createElement("span");

//     span.className = "irx-removed";
//     span.setAttribute("irx-show-removed", displayRemoved);
//     span.appendChild(selectedText);

//     selection.insertNode(span);
// }

// function linkToNote(note_id, extract_type) {
//     var selection = window.getSelection().getRangeAt(0);
//     var selectedText = selection.extractContents();

//     var note_link = document.createElement("a");
//     note_link.className = "irx-link"
//     note_link.setAttribute("href", "irxnid:" + note_id)
//     note_link.appendChild(selectedText);

//     var note_span = document.createElement("span");
//     var extract_span_class = "irx-extract-link-" + extract_type
//     note_span.className = "irx-extract " + extract_span_class;
//     note_span.setAttribute("irx-show-extracts", showExtracts);
//     note_span.appendChild(note_link)

//     selection.insertNode(note_span);
// }

// function format(style) {
//     var selection = window.getSelection().getRangeAt(0);
//     var selectedText = selection.extractContents();
//     var span = document.createElement("span");

//     span.className = "irx-format " + style;
//     span.setAttribute("irx-show-formatting", showFormatting);
//     span.appendChild(selectedText);

//     selection.insertNode(span);
// }


// function toggleShowExtracts(manual) {
//     if (manual == "toggle") {
//         if (showExtracts == "no") {
//             showExtracts = "yes";
//         } else {
//             showExtracts = "no";
//         }
//     } else {
//         showExtracts = manual
//     }
//     var elems = document.getElementsByClassName("irx-extract");
//     for (var i = 0; i < elems.length; i++) {
//         elems[i].setAttribute("irx-show-extracts", showExtracts)
//     }
// }


// function toggleShowRemoved(manual) {
//     if (manual == "toggle") {
//         if (showRemoved == "no") {
//             showRemoved = "yes";
//         } else {
//             showRemoved = "no";
//         }
//     } else {
//         showRemoved = manual
//     }
//     var elems = document.getElementsByClassName("irx-removed");
//     for (var i = 0; i < elems.length; i++) {
//         elems[i].setAttribute("irx-show-removed", showRemoved)
//     }
// }

// function toggleShowFormatting(manual) {
//     if (manual == "toggle") {
//         if (showFormatting == "yes") {
//             showFormatting = "no";
//         } else {
//             showFormatting = "yes";
//         }
//     } else {
//         showFormatting = manual
//     }
//     var elems = document.getElementsByClassName("irx-format");
//     for (var i = 0; i < elems.length; i++) {
//         elems[i].setAttribute("irx-show-formatting", showFormatting)
//     }
// }