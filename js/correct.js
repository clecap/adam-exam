
\begin{insDLJS}{myJS}{Summation}



function computeAll(q, s) {
  init();
  var points = determineCompletedAndZ(q, s);
  try {
    writeAll(s); 
  } catch (x) {
    app.alert ("Program Error. Shutting Down. Inform Developer providing this information: \n Error " + x);
    this.closeDoc (true);
  }
  return;
}





// returns   false   if discretionary grading is not used
//           number  if discretionary grading is used; returns the specific number of points
// CAVE:     0 qualifies as falsish, so tests must use === false 
function usingDiscretionaryGrading (q, s) {
  var discVal = GET_FIELD ("D" + q + "-" + s).value;  // value of field containing points for discretionary grading, if used
  // NOTE: discVal now is a string value, but we may assume it has been reasonably sanitized

//  app.alert ("discVal is " + discVal);

  if (discVal === "") {return false;}   // no discretionary grading used

  var numVal = Number (discVal);
  ASSERT (typeof numVal === "number", "Assertion error: numVal is not a number");
  ASSERT ( !isNaN(numVal), "Assertion error: numVal does not translate to a numeric value")

  return numVal;
}




function determineCompletedAndZ (q, s) {   // check the zero point boxesand discretionary fields  and set the Z, D and the completed arrays accordingly
  var val;
  var pointName, pointField, pointVal;
  var qpField;                             // field displaying the points for a question
  var bmName, bmField, bmVal;              // bonus malus adjustment

  var sum = 0;
  
  var discVal = usingDiscretionaryGrading (q, s);   // status of discretionary grading

  if (discVal === false) {                // CASE: not using discretionary grading
    // app.alert ("no discretionary grading used");
    isCompleted = GET_FIELD ("Z" + q + "-" + s).isBoxChecked(0);  // structured is complete when the complete box is set
    for (var i=1; i< 500; i++) { // summing up points, speculatively assuming a max of 500 options, breaking out when no more is found
      pointName = q + "X" + i + "-" + s;
      pointField = this.getField (pointName); if (!pointField) { break; }  // done with all we might be using
      pointVal = pointField.value;
      if (pointVal === "Off") {val = 0;} else { val =  pointField.attachedAdam; }     // determine value to be used here
      ASSERT (typeof val == "number", "Incorrect type of val");
      sum += val;
    }

    // now calculate the bonus / malus adjustment points
     bmName = "grp" + q + "-" + s; 
     bmField = this.getField(bmName);
     bmVal = bmField.value;
     if (bmVal === "Off") { // app.alert ("Strange: None of the adjustment buttons is active in question " + q + " serial " + s); 
     }
     else {
        bmVal = pdfStringToNumber (bmVal);
        // app.alert ("grading adjustment for question " + q + " serial " + s + " is " + val + " type is " + typeof val);
        sum += bmVal;
      }
    }
    else {  // CASE: USING discretionary grading
      // app.alert ("disc grading value is: " + discVal);
      sum = discVal;
      isCompleted = true;
    }

  if (sum < 0) {sum=0;}  // post-calculation correction: german exam regulations forbid negative points in one task affecting other tasks

  // set the calculated sum of points for question q of serial s into the box displaying the points for this question
  qpField = GET_FIELD ("punkte"+q + "-" + s);
  qpField.value = sum; 
  // app.alert ("punkte set to " + sum);

   updateNextQuestButton ();

  return sum;
}



// write punkteSumme, prozente and note for serial s
function writeAll (s) {
  var punkteSumme = 0; 
  var field, punkteSummeField, prozentField, noteField, val;

  for (var i = 1; i <= numQuestions; i++) {          
    field = GET_FIELD ("punkte"+i + "-" + s);  // get the field displaying the sum of the points for this question number
     val = field.value;
     if (typeof val != "number") {val = 0;}   // uninitialized fields may have string value and must be sanitized
     ASSERT ( typeof punkteSumme == "number", "writeAll: assertion error: punkteSumme is not numeric at 1");
     punkteSumme += val;  
     ASSERT (typeof punkteSumme == "number", "writeAll: assertion error: punkteSumme is not numeric at 2");
  }
  
  var raw                = (100*punkteSumme) / maxPoints;  //  raw percentage
  var rounded            = Math.ceil ( raw * 10) / 10;     //  rounded percentage, ceiling

  // punktesume, prozent, note
  punkteSummeField = GET_FIELD ("punktesumme-" + s);   punkteSummeField.value = punkteSumme; 
  prozentField     = GET_FIELD ("prozent-" + s);       prozentField.value     = rounded;
  noteField        = GET_FIELD ("note-" + s);          noteField.value        = percentToMark ( rounded );
}



/** HELPER FUNCTIONS **/

function pdfStringToNumber(v) {  // conversion function for bonus malus strings
  if (v === null || v === undefined) {return 0;}
  
  v = String(v);
  if (v === "Off" || v === "") {return 0;}
  
  //app.alert ("length: " + v.length + " string: " + v);
  v = v.substring (12); // removes \ 376\ 377 \ 000 in the string representation
  
  //app.alert ("length: " + v.length + " string: " + v);
  v = v.replace(/\\000/g, ""); // removes the \  000 prefix of the number 
  
  //app.alert ("length: " + v.length + " string: " + v);
  return Number(v);
}


function GET_FIELD (name) {
  var field;
  field = this.getField (name); 
  if (!field) {throw new Error ("Did not find field: " + name);}
  return field;
}


/** UI EVENT HANDLERS **/

function pointClick (q, s, e, val) {  // called by a click into a point carrying checkbox
  // app.alert (e.target);
  // app.alert ("pointClick " + q + " " + s +  "  " + val );
  if (val === null || val === undefined) { app.alert ("ERROR in pointClick");}
  e.target.attachedAdam = val;        // attach value, since the value, exportValue mechanism of PDF is not supported in hyperref
  // app.alert ("now setting completed to false");
  setCompleted (q, s, false);   // when we changed a checkbox, go back to unfinished to allow user a proper review of the status
  uncheckDisc(q, s);
  computeAll(q, s);
}


function completedClick(q, s, e) {   // called when a completion checkbox was clicked for question number q
  updateNextQuestButton ();
  if (e.target.isBoxChecked(0)) { // app.alert ("box completed is ticked");
    computeAll(q, s);
    colorify (q, s, true);  // color green
    app.setTimeOut ("goFirstIncomplete (s)", 500);  // a bit of a timeout to allow user a check
  }
  else { // app.alert ("box completed is unticked");
    uncheckDisc (q, s);      // clear any discretionary value which might have been set
    colorify (q, s, false);  // remove the coloring
  }
}


function numericKS(q, s, e) {          // called upon a keystroke, but we do not yet have a valid value in field.value
  // app.alert ("key " + e.value + " and change " + e.change);
  e.rc = /^[0-9]*$/.test(e.change);    // reject keystrokes different from 0, 1, ... 9
  return;
}


function onfocus (q, s, e) {     // called when discretionary gets the focus
  setCompleted (q, s, false);    // focusing the discretionary field clears completion checkbox
  setAllCheckForQ (q, s, false);  // focusing the discretionary field clears individual points checkboxes
  resetRadio (q, s);             // focusing the discretionary field clears completion checkbox
  return;
}


// called after value has been committed into the discretionary grading point field
// however, the value is not yet available in field.value, only AFTER the validate event has completed
function numericValidate(q, s, e) {

  // app.alert ("numericValidate called on value: " + e.value);
  var val = e.value.replace(/^\s+|\s+$/g, ""); // trim away white space in an ES3-safe manner
  if (val === "") {  // empty: we have NO discretionary grading value

    return;   
  }
  
  // Allow 0 or non-leading-zero integer
  if (!/^(0|[1-9][0-9]*)$/.test(val)) {
    app.alert("Enter 0 or an integer without leading zeros.");
    e.rc = false;      // reject the value
  }
  else { // we have a non-empty value which we shall use
    // app.alert ("value is: " + val + " and " + e.value);  // dev and debug
    setAllCheckForQ (q, s, false);  // uncheck all point-checkboxes 
    resetRadio (q, s);
   }
}


function radioChange (q, s, e) {  // called when a bonus / malus radio buton is clicked
  var field = GET_FIELD ("grp" + q + "-" + s);
  var v = field.value;
  uncheckDisc (q, s);        // remove discretionary points
  computeAll(q, s);
}



/** UI MODIFICATION FUNCTIONS: Functions which change the UI, partially to make it consistent **/

function resetRadio(q, s) { // reset radio group adjustment for question q to its default
  var field = GET_FIELD ("grp" + q + "-" + s);
  field.value = "Off";
}

function setAllCheckForQ (q, s, flag) {  // uncheck all point-checkboxes for question q  (flag=false)
  for (var i = 1; i < 100; i++) {        // assuming at most 100 point checkboxes per question and contiguous numbering starting from 1
    var name = q + "X" + i + "-" + s;
    var field = this.getField ( name ); 
    if (field) {field.checkThisBox(0,flag);}
    else { // app.alert ("not found: " + name);  
      break;
    }
  }
}

function setCompleted (q, s, flag) {  // uncheck/uncheck the  "completed" checkbox for question q
  var field = GET_FIELD ("Z"+q + "-" + s);
  field.value = (flag ? "Yes" : "Off" );
  colorify (q, s, flag);      // ensure that the coloring always reflects the status of the completion checkbox
  updateNextQuestButton ();
}


function uncheckDisc (q, s) {  //  empty any discretionary field for question q
  var field = GET_FIELD ("D"+q+"-"+s);  
  field.value="";
}


function clearQuestionPoints (q, s) { // clears the field exhibit the number of points for question q in serial s
  var field = GET_FIELD ("punkte"+q + "-" + s);
  field.value = "";
  field.strokeColor = color.red;
}



// sets the color of all the question-specific elements for question q and serial s
function colorify (q, s, flag) {
  var field;
  var newColor = ( flag ? color.green : color.red );
  field = GET_FIELD ("Z" + q + "-" +s);  field.strokeColor =  newColor;  // completion checkbox

  for (var i=1; i< 500; i++) { // summing up points, maximal 500 grading options, speculative until we have no more fields to find 
    field = this.getField (q + "X" + i + "-" + s);   // individual solution items
    if (!field) { break;}
    field.strokeColor = newColor;
  }
  
  field = GET_FIELD ("grp" + q + "-" + s);     field.strokeColor = newColor;  // bonus malus
  field = GET_FIELD ("D" + q + "-" + s);       field.strokeColor = newColor;  // discretionary
  field = GET_FIELD ("grader" + q + "-" + s);  field.strokeColor = newColor;  // name of grader
  field = GET_FIELD ("punkte"+ q + "-" + s);   field.strokeColor = newColor;  // points achieved at this question
    field.fillColor = newColor;
}


// if the button exists, disable it - else ignore command
function disableButton (name) {
  var btn = this.getField(name);
  if (btn) { btn.readonly = true;  btn.fillColor = color.ltGray; btn.textColor = color.dkGray; 
    btn.buttonSetCaption ("",0); btn.buttonSetCaption ("",1); btn.buttonSetCaption ("",2);
  }
}

// if the button exists, enable it - else ignore command
function enableButton (name, caption) {
  var btn = this.getField(name);
  if (btn) { btn.readonly = false;  btn.fillColor = color.white; btn.textColor = color.black; 
    btn.buttonSetCaption (caption, 0);    btn.buttonSetCaption (caption, 1);    btn.buttonSetCaption (caption, 2);
    btn.strokeColor = color.green;
  }
}

function updateNextQuestButton () { // update button to display next question to be graded, or none, if none
  var s = getSerial ();
  var nextQuest = firstIncompleteQuestion (s);
  if (nextQuest != -1) {enableButton ("nextquest", "Next Question: " + nextQuest);} 
  else {disableButton ("nextquest");}
}


/** OTHER functions **/

// called by Checkbox
function injectValue (q, s, e, val) {  // need this to attach value also for the cases where we do not click but merely activate the ALL button
  e.target.attachedAdam = val; 
}


function init () {                    // initialize variables 

  disableButton ("savenext");
  disableButton ("savestop");
  enableButton ("skipstop", "Skip & Stop");  // to fix in the interest of unique fonts in all  3 buttons  // TODO: might move out of init to main initialoization

  var parts, question, name, f;
  numQuestions = 0;
  for (var i = 0; i < this.numFields; i++) {      // iterate over absolutely all fields
    name = this.getNthFieldName(i);               // get field name for field number i
    f = this.getField(name);                      // get field name for this field
    if (f && (f.type === "checkbox") ) {             // if we found this field and it is a checkbox
      parts = name.split("X");                    // split the name on the letter X
      question = parts[0] ? Number(parts[0]) : null; // obtain first part, which is the question to which the field belongs
      numQuestions = (question > numQuestions ? question : numQuestions);
    }
  }

  for (var i = 0; i < this.numFields; i++) {      // iterate over absolutely all fields
    name = this.getNthFieldName(i);               // get field name for field number i
    f = this.getField(name);                      // get field name for this field
    if (f && (f.type === "checkbox") ) {             // if we found this field and it is a checkbox
      parts = name.split("X");                    // split the name on the letter X
      question = parts[0] ? Number(parts[0]) : null; // obtain first part, which is the question to which the field belongs
    }
  }
}



/*** CODE to go to next ungraded question automagically ***/

// TEST if there is a value in discretionary field
function hasDiscretionary (q,s) {
  discVal = GET_FIELD ("D" + q + "-" + s).value;  // value of field containing points for discretionary grading, if used
  if (typeof discVal === "number" ) { return true; } else {return false;}
}



function isQuestionGraded (q, s) { // given a serial number s and a question number q, return if the question q has been graded for serial s

  var name = "punkte" + q + "-" + s;
  var field = this.getField (name); if (!field) { throw new Error ("ERROR: isQuestionGraded could not find field: " + name ); }
  var val = field.value;

  if (val === undefined || val === null) {return false;}
  if (typeof val === "string") { val=val.trim(); }
  if (val === "") {return false;}
  val = Number (val);
  if (isNaN (val)) { throw new Error ("ERROR: isQuestionGraded found a NaN for field: " + name); }
  if (val < 0)     { throw new Error ("ERROR: isQuestionGraded found a negative number for field: " + name); }  



  var completed = GET_FIELD ("Z" + q + "-" + s).isBoxChecked(0);  // structured is complete when the complete box is set
  if (!completed) {return false;}

  return true;
}


function shallQuestionBeGraded (q, s) {  // given question number q and serial id s, return if the question shall be graded as part of this PDF
  var name    = "grader" + q + "-" + s;
  var myColor = getBorderColor (name);     
  return !isBlackColor (myColor);
}


// Returns the border (stroke) color for a field/widget.
// fieldName can be:
// - "MyField" (single-widget fields, or whatever Acrobat returns at field level)
// - "MyRadio.0" / "MyField.0" (widget-specific, if the field has multiple widgets)
function getBorderColor (name) {
  var field = this.getField (name); 
  if (!field) { throw new Error ("getBorderColor: cannot find field: " + name ); }    

  // For AcroForm widgets, strokeColor is the border color.
  // Value is typically: ["RGB", r, g, b], ["G", gray], ["CMYK", c, m, y, k], or "transparent".
  // ["RGB", 0, 0, 0]  is black
  
  var myColor = field.strokeColor;
  // app.alert (color);
  return myColor;
}



function isBlackColor(c) {  // Returns true if the Acrobat color array represents pure black.
  if (!c) return false;
  if (c === "transparent") return false;
  if (!Array.isArray(c) || c.length === 0) return false;
  var space = c[0];

  function isZero(x) {return Math.abs(x) < 0.00001;}      // Helper to compare with tolerance (floating point safety)

  if (space === "RGB" && c.length >= 4) {return isZero(c[1]) && isZero(c[2]) && isZero(c[3]);}                                    // RGB: ["RGB", 0, 0, 0]
  if ((space === "G" || space === "gray") && c.length >= 2) {return isZero(c[1]);}                                                // Grayscale: ["G", 0]
  if (space === "CMYK" && c.length >= 5) {return isZero(c[1]) && isZero(c[2]) && isZero(c[3]) && Math.abs(c[4] - 1) < 0.00001;}   // CMYK black: ["CMYK", 0, 0, 0, 1]

  return false;
}



function firstIncompleteQuestion (s) { // returns the number of the first question of serial s which has not yet been graded or -1 if all questions have been graded
  var i;
  var found = -1;
  for (i=1; i<=numQuestions; i++) { 
    if (  shallQuestionBeGraded (i,s) && !isQuestionGraded (i,s) ) {found = i; break;} }
  return found;
}



// if all questions have been graded which were available for grading in the entire exam calculate final parameters
function lastProcessing (s) {
  var i;
  var foundUngraded = -1;   // searching for an ungraded question
  for (i=1; i<=numQuestions; i++) { 
    if ( !isQuestionGraded (i,s) ) {foundUngraded = i; break;} 
  }
  if (foundUngraded !== -1) { app.alert ("Warning: Found ungraded question: " + foundUngraded); 
    return;}
  else {
    // app.alert ("COMPLETELY DONE! ");
    writeAll (s);
  }
}




function firstPageOfField (fieldName) { // returns the first page number in terms of PDF pages of the file which should be graded
  var f = this.getField(fieldName);
  if (!f) return -1; // field not found
  var p = f.page;

  if (typeof p === "number") return p;     // Single widget

  // Multiple widgets: page is an array of page indices
  if (p && p.length) {
    var minPage = p[0];
    for (var i = 1; i < p.length; i++) {
      if (p[i] < minPage) minPage = p[i];
    }
    return minPage;
  }
  return -1;
}


function isFullyAutomated () {  // return true if running in fully automated mode using START.pdf
  if ( global && global.openedByScript && global.openedByScript[this.path] ) {return true;} else {return false;}
}



function goFirstIncomplete (s) {  // navigate to the page with the first incompletely graded question for serial s, if s not defined, obtain it
                                  // return true if navigating to a page 

  if (s === null || s === undefined) {s = getSerial();}
  var q = firstIncompleteQuestion (s);

  if (q === 0 || q === undefined || q === null) { throw new Error ("goFirstIncomplete obtained illegal value for q");}

  if (q == -1) {   // all questions graded, nothing to do than to prepare exit modes
    enableButton ("savenext", "Save & Next of " + (stillMissing()-1) + "...");  
    enableButton ("savestop", "Save & Stop");
    disableButton ("nextquest" );

  if (!isFullyAutomated()) {  // if not in fully automated mode: remind user to save.
    app.alert ("All questions have been graded for serial " + s + "\n\n Please save result ");   
  }
    return;
  }

  var name = "grader" + q + "-" + s;  
  var page = firstPageOfField (name);
     // app.alert ("found page " + page);  
  goToPage (page);    // CAVE: This navigates asynchronously - beware of race conditions !
  return true;
}


function goToPage (requested) {// helper for proper redraw after jumping to a page. Defer the navigation so it happens AFTER the button event finishes
  app.setTimeOut(
    "try { " +
      " var d = app.activeDocs[0]; " +
      "d.pageNum = " + requested + "; " +
      "d.syncAnnotScan(); " +      // force/complete annot (widget) scan
      "d.calculateNow(); " +       // optional: refresh calculations/formatting
    "} catch (e) {}",
    10
  );
}


function getSerial () {  // obtain the serial number of the PDF 
  var field = GET_FIELD ("Serial");
  var val = field.valueAsString;
  return val;
}



/* variables must be defined at the end or adobe vomits */

var numQuestions;  
var maxPoints = \thetotalpointsfromfile;


checkProperSettings ();

init();
updateNextQuestButton();   // at the beginning, also already initialize this button properly

// app.alert ("Viewer type=" + app.viewerType + "\n\n Platform="+app.platform + "\n\n Viewer Version=" + app.viewerVersion + "\n\n Language="+app.language);


try {
//  checkOpenedByScript (this);  // check for proper opening mode, if not bark at user

  var navigating = goFirstIncomplete();           // go to first ungraded question, obtain info, if we go asynchronously
  if (navigating) {  // there still is an ungraded question to which we are navigating now asynchronously
  }
  else {
    var s = getSerial ();
    lastProcessing(s);
  }
  
} catch (x) { // need this to properly shut down this instance - peculiarity of adobe reader

}


\end{insDLJS}
