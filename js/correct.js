
\begin{insDLJS}{myJS}{Summation}


// if document has not been opened by the START script 
// and is inside a directory which contains a START.pdf file
// then issue a warning and close again
function checkOpenedByScript (doc) {
  var path        = norm(doc.path);
  var baseDir     = dirname(path);
  if (!baseDir) { app.alert ("ERROR: Could not obtain baseDir in checkOpenedByScript"); return;}
  var startPath   = join (baseDir, "START.pdf");
  var startExists = TrustedFileExists (startPath);
  // app.alert ("startExists=" + startExists + " at " + startPath);

  var openedByScript = false;                                                // default is false
  if (global && global.openedByScript && global.openedByScript[path]) {
    var ageMs = (new Date()).getTime() - global.openedByScript[path];        // optional: expire it quickly to avoid false positives
    delete global.openedByScript[path];
    openedByScript = (ageMs < 5000);
  }
  // app.alert ("openedByScript=" + openedByScript);
  
  if (startExists && !openedByScript) {
    app.alert ("ERROR: Adam PDF file  in a directory containing a START.pdf and not opened by START.pdf \n\n Please start Adam grading by opening START.pdf in workflow directory");

    var r = app.alert({cMsg: "Override warning?\n\n Yes keeps document open \n\n No closes it. ", cTitle: "Confirm Ignore?", nIcon: 2, nType: 2 });

    if ( r===1 ) {
        this.dirty=false;
        this.closeDoc (true);
        throw "Opening-Exception";  // signal the caller to shut down since we cannot do this here 
    }
    else {}
  }
}



function computeAll(q, s) {
  init();
  var points = determineCompletedAndZ(q, s);
  // writeAll(s); 
  return;
}


function writeCorr (q, s) {  // for question number q, write the identity of the corrector
  var corrField = this.getField("id"+q);
  var corr='No-Name-From-Tex';
  try { corr = TrustedGetId(); } catch (x) {}
  if (corrField) {corrField.value=corr;}
}



function determineCompletedAndZ (q, s) {   // check the zero point boxesand discretionary fields  and set the Z, D and the completed arrays accordingly
  var name, field, val;
  var sum = 0;

  // determine completion status
  name = "Z" + q + "-" + s;
  field = this.getField (name); if (!field) {app.alert ("FATAL ERROR 1: did not find: " + name); return;}  // TODO: EXCEPTION
  var completed = field.isBoxChecked(0);
  
    name = "D" + q + "-" + s;
    field = this.getField (name); if (!field) {app.alert ("FATAL ERROR 1: did not find: " + name); return;}  // TODO: EXCEPTION
    val = field.value;   // app.alert ("Discretionary field has value: " + val + " of type " + typeof val);
    if (typeof val === "number" ) {    // app.alert ("Using discretionary grading for question " + q + " serial " + s);
      sum = val;
    }
    else {          // app.alert ("Using structured grading for question " + q + " serial " + s);
      for (var i=1; i< 200; i++) { // summing up points
        name = q + "X" + i + "-" + s;
        field = this.getField (name); if (!field) { // app.alert ("exiting: did not find: " + name);
          break;}
        if (field.value === "Off") {val = 0;} else { val =  field.attachedAdam; }
        if (typeof val !== "number") { 
        
         // app.alert ("Error: val in summation has type " + typeof val); 
          app.alert ("Please reenter all grade points for this question");
          clearQuestionPoints (q, s);
           setAllCheckForQ (q, s, false);
           colorify (q, s, false);
          
          
          return;}
        sum += val;
      }
      name = "grp" + q + "-" + s; 
      field = this.getField(name);
      val = field.value;
      if (val === "Off") { // app.alert ("Strange: None of the adjustment buttons is active in question " + q + " serial " + s); 
      }
      else {
        val = pdfStringToNumber(val);
        // app.alert ("grading adjustment for question " + q + " serial " + s + " is " + val + " type is " + typeof val);
        sum += val;
      }
    }

  if (sum < 0) {sum=0;}  // german exam regulations forbid negative points in one task affecting other tasks

  name = "punkte"+q + "-" + s;
  // app.alert ("Question " + q + " of serial " + s + " has pointsum: " + sum + " injecting into field " + name);
  field =this.getField(name); if (!field) {app.alert ("FATAL ERROR 4: did not find: " + name); return;}
  field.value = sum;
  field.strokeColor = ( completed ? color.green : color.red );
  return sum;
}


// write all fields for serial s
function writeAll (s) {
  var punkteSumme = 0; 
  var allDone   = true;
  var field, name, punkteSummeField, prozentField, noteField, val;
  
  for (var i = 1; i <= numQuestions; i++) {
    name = "punkte"+i + "-" + s;
    field =this.getField(name);             // get the field displaying the sum of the points for this question number
   if (field) {            // and if we really got a field object, then fill in the sum
     val = field.value;
     punkteSumme += val;   ////// TODO: ONLY IF COMPLETED ////////////////////////////////////////////
   }
   else {app.alert ("Could not find field for points " + name);}         
  }
  
  // punktesume, prozent, note
  punkteSummeField = this.getField ("punktesumme-" + s); if ( !punkteSummeField  ) {
    app.alert ("Error: Cannot find field punktesumme-"+s);
  }
  prozentField     = this.getField ("prozent-" + s);     if ( !prozentField      ) {
    app.alert ("Error: Cannot find field prozent-"+s);    
  }
  noteField        = this.getField ("note-" + s);        if ( !noteField         ) {
    app.alert ("Error: Cannot find field note-"+s);       
  }
  punkteSummeField.value = punkteSumme;
  var raw                = (100*punkteSumme) / maxPoints;  //   --------------------------
  var rounded            = Math.ceil ( raw * 10) / 10;
  prozentField.value     = rounded;
  noteField.value        = percentToMark ( rounded );  //   --------------------------  
  punkteSummeField.strokeColor = prozentField.strokeColor = noteField.strokeColor = ( allDone ? color.green : color.red);

//  var stringIncomplete = listOfIncomplete ();
//  var nextjobField = this.getField("nextjob");
  // nextjobField.alignment="left";
  // nextjobField.buttonSetCaption(stringIncomplete);
//  nextjobField.value = stringIncomplete;
}




/** HELPERS **/

function pdfStringToNumber(v) {
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



/** UI HANDLING FUNCTIONS handle specific UI situations **/

function pointClick (q, s, e, val) {  // called by a click into a point carrying checkbox
  // app.alert (e.target);
  // app.alert ("pointClick " + q + " " + s +  "  " + val );
  if (val === null || val === undefined) { app.alert ("ERROR in pointClick");}
  e.target.attachedAdam = val;        // attach value, since the value, exportValue mechanism of PDF is not supported in hyperref
  // app.alert ("now setting completed to false");
  setCompleted (q, s, false); 
  // app.alert ("done");
  uncheckDisc(q, s);
  computeAll(q, s);
  //resetRadio (q, s);
  colorify (q, s, false);
  
}

function injectValue (q, s, e, val) {  // need this to attach value also for the cases where we do not click but merely activate the ALL button
  e.target.attachedAdam = val; 
}



function completedClick(q, s, e) {   // called when a completion checkbox was clicked for question number q
  computeAll(q, s);
  colorify (q, s, true);
  goFirstIncomplete (s);
}

function allButton(q, s, e) {   // called when an allbutton was clicked for question number q
  uncheckDisc (q,s);
  setAllCheckForQ (q, s, true);
  setCompleted (q, s, false);
  computeAll(q, s);
}

function onblur (q, s, e) { // called when losing the focus of the discretionary input field
  computeAll (q,s);
  goFirstIncomplete (s);
}

function buttonFocusOn(e) {   // make keyboard focus obvious
  var f = e.target;
  f.borderStyle = border.d;  // dashed border
}

function buttonFocusOff(e) {
  var f = e.target;
  // restore normal appearance (adjust to your defaults)
  //f.strokeColor = color.red;
  //f.lineWidth = 2;
  f.borderStyle = border.s;
}


// DEPRECATE also in field ????
function numericKS(q, s, e) {  // called when a value has been entered  /changed into a discretionary grading field

  return;

  // Build the would-be value after this keystroke
  // app.alert ("numericKS called");
  var v      = e.value;
  var before = v.substring(0, e.selStart);
  var after  = v.substring(e.selEnd, v.length);
  var next   = before + e.change + after;

  // Allow empty while editing; final check happens in validate
  if (!/^[0-9]*$/.test(next)) {
    e.rc = false;
  }
}


function numericValidate(q, s, e) {
  //app.alert ("numericValidate called on value: " + e.value);
  var val = e.value.replace(/^\s+|\s+$/g, ""); // trim (ES3-safe)
  if (val === "") {  // empty: we have NO discretionary grading value
    return;   
  }
  
  // Allow 0 or non-leading-zero integer
  if (!/^(0|[1-9][0-9]*)$/.test(val)) {
    app.alert("Enter 0 or an integer without leading zeros.");
    e.rc = false;
  }
  else { // we have a non-empty value which we shall use
    setAllCheckForQ (q, s, false);  // uncheck all point-checkboxes 
    resetRadio (q, s);
    setCompleted (q, s, true);
  //  app.alert ("will compute");
    computeAll (q,s);
  //  app.alert ("did compute");
    colorify (q,s, true);
 //   app.alert ("did color");
    goFirstIncomplete (s);
   }
}





function radioChange (q, s, e) {
  var name = "grp" + q + "-" + s;   // app.alert (name);
  var field = this.getField(name);  if (!field) { app.alert ("ERROR: radioChange could not find field: " + name);}   
  var v = field.value;
  uncheckDisc (q, s);
  setCompleted (q, s, true);
  computeAll(q, s);
  colorify (q, s, true);
  goFirstIncomplete (s);
}




/** UI MODIFICATION FUNCTIONS change UI to make it consistent **/

function resetRadio(q, s) { // reset radio group adjustment for question q to its default
  var name = "grp" + q + "-" + s;
  var field = this.getField(name); if (!field) {app.alert ("ERROR: resetRadio did not find field: " + name);}
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


function setCompleted (q, s, flag) {  // uncheck all completed checkboxes for question q
  var name = "Z"+q + "-" + s;
  var field = this.getField (name);     if (!field) { app.alert ("ERROR: setCompleted failed to find field: " + name);}
  field.value = (flag ? "Yes" : "Off" );
}


function uncheckDisc (q, s) {  //  empty any discretionary field for question q
  var name = "D"+q+"-"+s;
  var field = this.getField (name);  if (!field) { app.alert ("ERROR: uncheckDisc failed to find field: " + name);}
  field.value="";
}


function clearQuestionPoints (q, s) { // clears the field exhibit the number of points for question q in serial s
  var name = "punkte"+q + "-" + s;
  var field = this.getField (name); if (!field) { app.alert("ERROR: clearQuestionPoint failed to find field: " + name);}
  field.value = "";
  field.strokeColor = color.red;
}

// sets the color of all the elements for question q and serial s
function colorify (q, s, flag) {
  var name, field;
  
  name = "Z"+q +"-"+s;
  field = this.getField (name);
  field.strokeColor = ( flag ? color.green : color.red );
  

  for (var i=1; i< 200; i++) { // summing up points
    name = q + "X" + i + "-" + s;
    field = this.getField (name); if (!field) { // app.alert ("exiting: did not find: " + name);
      break;}
    field.strokeColor = ( flag ? color.green : color.red );
  }
  
  name = "grp" + q + "-" + s;
  field = this.getField (name);
  field.strokeColor = ( flag ? color.green : color.red );
  
  name = "D" + q + "-" + s;
  field = this.getField (name);
  field.strokeColor = ( flag ? color.green : color.red );
  
  name = "grader" + q + "-" + s;
  field = this.getField (name);
  field.strokeColor = ( flag ? color.green : color.red );
  
}



/** OTHER functions **/


function init () {                    // initialize variables 
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
  completed = new Array ( numQuestions+1 );            // no initialization // for (var i = 1; i <= numQuestions; i++) {completed[i] = false;}
  qP        = new Array ( numQuestions+1 );            for (var i = 1; i <= numQuestions; i++) {qP[i] = 99999;}   
  sums      = new Array ( numQuestions+1 );            for (var i = 1; i <= numQuestions; i++) {sums[i] = 0;}  
  Z         = new Array ( numQuestions+1 );            // no initialization
  D         = new Array ( numQuestions+1 );            // no initialization
  for (var i = 0; i < this.numFields; i++) {      // iterate over absolutely all fields
    name = this.getNthFieldName(i);               // get field name for field number i
    f = this.getField(name);                      // get field name for this field
    if (f && (f.type === "checkbox") ) {             // if we found this field and it is a checkbox
      parts = name.split("X");                    // split the name on the letter X
      question = parts[0] ? Number(parts[0]) : null; // obtain first part, which is the question to which the field belongs
      qP[question] = f.page;
    }
  }
}


function printStatus () {
  app.alert ("Number of questions=" + numQuestions );
  var txt ="Questions completed in grading: "; 
  for (var i =1; i <= numQuestions; i++) { txt += " " + completed[i]; } 
  app.alert (txt);
  txt = "Questions start on pages: ";
  for (var i =1; i <= numQuestions; i++) { txt += " " + qP[i]; } 
  app.alert (txt);
  txt = "Sums for each task are: ";
  for (var i =1; i <= numQuestions; i++) { txt += " " + sums[i]; } 
  app.alert (txt);
}

function transformString(s) {    //   ---------------------- TODO: maybe deprecated ???? 
  if (!s || s.length === 0) {return s;}
  var firstChar = s.charAt(0);
  if ( (firstChar >= "0" && firstChar <= "9") || (firstChar >= "a" && firstChar <= "z")) {return "A-" + s;}    // Case 1: starts with a digit or a lowercase letter
  if (firstChar >= "A" && firstChar <= "Z") {                     // Case 2: starts with a capital letter A–Z
    var code = firstChar.charCodeAt(0);
    if (code === 90) {return "A-" + s;}      // Wrap Z → A
    var nextLetter = String.fromCharCode(code + 1);
    return nextLetter + "-" + s;
  }
  return s;    // Otherwise unchanged
}




/*** CODE to go to next ungraded question automagically ***/


function isQuestionGraded (q, s) { // given a serial number and a question, return if the question has been graded for serial s
  var name = "punkte" + q + "-" + s;
  var field = this.getField (name); if (!field) {app.alert ("ERROR: isQuestionGraded could not find field: " + name ); return false;}// TODO: exception flow
  var val = field.value;
  if (val === undefined || val === null) {return false;}
  if (typeof val === "string") { val=val.trim(); }
  if (val === "") {return false;}
  val = Number (val);
  if (isNaN (val)) { app.alert ("ERROR: isQuestionGraded found a NaN for field: " + name); return false;}// TODO: exception flow
  if (val < 0) {  app.alert ("ERROR: isQuestionGraded found a negative number for field: " + name); return false;}  // TODO: exception flow
  return true;
}











function shallQuestionBeGraded (q, s) {  // given question number q and serial id s, return if the question shall be graded as part of this PDF
  var name = "grader" + q + "-" + s;
  var color = getBorderColor (name);
  return !isBlackColor (color);
}


// Returns the border (stroke) color for a field/widget.
// fieldName can be:
// - "MyField" (single-widget fields, or whatever Acrobat returns at field level)
// - "MyRadio.0" / "MyField.0" (widget-specific, if the field has multiple widgets)
function getBorderColor (name) {
  var field = this.getField (name); if (!field) { app.alert ("getBorderColor: cannot find field: " + name ); }    // TODO:  exception ??

  // For AcroForm widgets, strokeColor is the border color.
  // Value is typically: ["RGB", r, g, b], ["G", gray], ["CMYK", c, m, y, k], or "transparent".
  
  
  // ["RGB", 0, 0, 0]  is black
  
  var color = field.strokeColor;
  // app.alert (color);
  return color;
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
  // app.alert ("searching first incomplete question for " + s);
  var found = -1;
  for (i=1; i<=numQuestions; i++) { 
    if (  shallQuestionBeGraded (i,s) && !isQuestionGraded (i,s) ) {found = i; break;} }
  if (found === -1) {  app.alert ("All questions have been graded for serial " + s + "\n\n Please save result ");                
  }
  else                {  // app.alert ("next ungraded question for serial " + s + " is " + found); 
  }
  return found;
}





// if all questions have been graded which were available for grading in the entire exam
// calculate final parameters
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






function goFirstIncomplete (s) {  // navigate to the page with the first incompletely graded question for serial s, if s not defined, obtain it
                                  // return true if navigating to a page 
  if (s === null || s === undefined) {s = getSerial();}
  var q = firstIncompleteQuestion (s);
   // app.alert ("goFirstIncomplete: sees firstIncompleteQuestion: " + q);
  var page;
  if (q > 0) {
    var name = "grader" + q + "-" + s;  
    var field =this.getField(name);  if (!field) {app.alert ("ERROR: goFirstIncomplete did not find field: " + name); return;}
     // app.alert ("found field " + name);
    page = firstPageOfField (name);
     // app.alert ("found page " + page);
  }
  else {  // app.alert ("goFirstIncomplete: All questions graded for serial " + s); 
    return;
  }
  
  // app.alert ("goFirstIncomplete: Now going to " + page);
  //console.show();
  //console.println ("going to: " + page);

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


function getSerial () {  // obtain the serial number of the PDF - ONLY for those cases where there 
  var name = "Serial";
  var field = this.getField (name);  if (!field) {app.alert ("ERROR: getSerial did not find field: " + name); return;}
  var val = field.valueAsString;
  return val;
}




function goToNext () {
  // app.alert ("goToNext called");
  var s = getSerial ();
  //app.alert ("goToNext: found serial: " + s);
  goFirstIncomplete (s);
}




/* variables must be defined at the end or adobe vomits */
var numQuestions;  
var completed;       // maps number of question to boolean value indicating if this question has been graded completed  // TODO: deprecate ????
var qP;              // maps the number of question to the page where this question is placed or starts to be placed
var sums;            // maps the number of question to the sum of points achieved at this question
var Z;               // maps the number of question to a flag indicating if the zero point box is ticked
var D;               // maps the number of question to a flag indicating i the discretionary grading is used in this question

var maxPoints = \thetotalpointsfromfile;

init();

  // app.alert ("Viewer type=" + app.viewerType + "\n\n Platform="+app.platform + "\n\n Viewer Version=" + app.viewerVersion + "\n\n Language="+app.language);


try {
//  checkOpenedByScript (this);  // check for proper opening mode, if not bark at user

//  computeAll();                  // compute current status // TODO !!!!!

  var navigating = goFirstIncomplete();           // go to first ungraded question, obtain info, if we go asynchronously
  if (navigating) {  // there still is an ungraded question to which we are navigating now asynchronously
 
  }
  else {
   
    var s = getSerial ();
    // app.alert ("now finalizing serial: " + s);
    lastProcessing(s);
  }
  
} catch (x) { // need this to properly shut down this instance - peculiarity of adobe reader

}








\end{insDLJS}
