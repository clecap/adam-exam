

\begin{insDLJS}{library}{Library}
// The implementation of the JS engine by Adobe is heavily b**** damaged and needs VERY conservative programming and many fill-ins.
function trim(s) {return (s || "").replace(/^\s+|\s+$/g, "");}                                                 // trim leading and trailing white space
function norm(p) {return (p || "").replace(/\\/g, "/");}                                                       // normalize string p: and ensure / is path separator
function dirname(p) { var s = norm(p); var i = s.lastIndexOf("/"); return i >= 0 ? s.slice(0, i) : null; }     // extract directory portion
function basename(p) {var s = norm(p); var i = s.lastIndexOf("/"); return i >= 0 ? s.slice(i + 1) : s; }       // extract last part of a path
function join(dir, rel) {var d=norm(dir); var r=norm(rel); if (!d) return r; if (d.slice(-1) === "/") return d + r; return d + "/" + r;}
function splitLines(text) {return (text || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");}       // split text into individual lines for all OS conventions
function safeName(name) {      // sanitize names of some files
  var s = trim(name);
  if (!s) s = "unknown";
  s = s.replace(/[<>:"|?*\x00-\x1F]/g, "_");
  s = s.replace(/[\/\\]/g, "_");
  s = s.replace(/\s+/g, " ");
  s = trim(s);
  if (!s) s = "unknown";
  return s;
}

function cloneArray(a) {
  var b = [];
  for (var i = 0; i < a.length; i++) { b[i] = a[i]; }
  return b;
}

function ASSERT (bC, str) { if (!bC) {throw new Error ("Assertion Error: " + str);} }


function percentToMark (p) {
  if (typeof p != "number") { throw new Error ("percentToMark: assertion error: wrong type: " + typeof p); }

  var s = getSerial ();  ASSERT (s, "percentToMark could not obtain serial"); 
  var field = GET_FIELD ("note-" + s) ;
 
  if ( p > 100)  { field.fillColor = color.yellow; }
  else           { field.fillColor = color.white;  }

  if      ( p > 100)               {return "1.0";}
  else if ( p > 95 && p <= 100 )   {return "1.0"; }
  else if ( p > 90 && p <=  95 )   {return "1.3"; }
  else if ( p > 85 && p <=  90 )   {return "1.7"; }
  else if ( p > 80 && p <=  85 )   {return "2.0"; }
  else if ( p > 75 && p <=  80 )   {return "2.3"; }
  else if ( p > 70 && p <=  75 )   {return "2.7"; }
  else if ( p > 65 && p <=  70 )   {return "3.0"; }
  else if ( p > 60 && p <=  65 )   {return "3.3"; }    
  else if ( p > 55 && p <=  60 )   {return "3.7"; }     
  else if ( p > 50 && p <=  55 )   {return "4.0"; }
  else if ( p >= 0 && p <=  50 )   {return "5";   }
  else { throw new Error ("percentToMark: assertion error: wrong value of percentages: " + p); }

}


function endsWithStartPdf(s) {return /START\.pdf$/.test(s);}


function parentDirectory(path) {
  var i = path.lastIndexOf("/");
  if (i < 0) return "";
  return path.substring(0, i);
}


// "input-raw/0014.pdf"  ->  "completed-raw/0014.pdf"
// The queue lists the sheets as input-TAG/filename; their graded copies live in completed-TAG/filename.
// Returns null if the entry does not have that shape, so the caller can report a broken queue file.
function completedEntry (entry) {
  if (!/^input-[^\/]*\//.test(entry)) { return null; }
  return entry.replace(/^input-/, "completed-");
}


// Get the path to the grader directory: START.pdf lies in it, a sheet lies one level below in input-TAG/
function graderDirOf () {
  var baseDir = dirname (norm (this.path));
  if (endsWithStartPdf (this.documentFileName)) { return baseDir; }    // we are START.pdf, so we return baseDir
  return parentDirectory (baseDir);                                    // otherwise we return the parent directory
}

// The current document as it would appear in queue.txt: "input-TAG/filename". null for START.pdf.
function currentEntryOf () {
  var baseDir = dirname (norm (this.path));
  if (endsWithStartPdf (this.documentFileName)) { return null; }   // START.pdf is not a queue entry
  return basename (baseDir) + "/" + this.documentFileName;
}



// return a list of files to look at from the manifest file queue.txt; look inside directory baseDir
function getQueueEntries () {
  var currentBase  = this.documentFileName;   ASSERT (currentBase, "getQueueEntries could not obtain documentFileName");
  var currentFull  = norm(this.path);         ASSERT (currentFull, "getQueueEntries could not obtain normalized path");
  var baseDir      = dirname(currentFull);    ASSERT (baseDir,     "getQueueEntries could not obtain baseDir");

  var searchDir;

  // app.alert ("basedir is: " + baseDir + " and full is " + currentFull);

  if (endsWithStartPdf (currentBase)) {searchDir = baseDir;}  // current document is START.pdf so we have the right directory
  else {searchDir = parentDirectory (baseDir);}               // current directory is a sheet - which is liging inside a subdirectory - must go up one step
  
  var stm;
  try{ stm = ReadQueueFile (searchDir);} catch (x) { throw x;} // rethrow for proper UI exit; has already been notified to user in ReadQueueFile

  
  ASSERT (stm, "getQueueEntries could not read queue file at " + searchDir);
  var lines = splitLines(util.stringFromStream(stm, "utf-8"));
  var entries = [];
  for (var i = 0; i < lines.length; i++) {
     var line = trim(lines[i]);
    if (!line) {continue;}
    if (/^(#|\x25)/.test(line)) {continue;} // CAVE: must hex escape the percentage line as backslash x 25 or pdf gets corrupt
    entries.push(line);
  }
  if (entries.length === 0) {app.alert("ERROR: Queue file is empty."); return [];}
  return entries;
}




// perform a startup check if the required settings have been made
function checkProperSettings () {
  var msg = "Installation not complete\n  Read https://github.com/clecap/adam-exam/README.md\n ";
  var flag = false;
  var currentFull;
  
  try {
    currentFull = norm(this.path);
  } catch (x) { flag = true; msg += ("\n Exception: " + x); }

  try {
    AssertSafeAdamPath ( currentFull, ".pdf");
  } catch (x) { flag = true; msg += ("\n Exception: " + x); }

  if (flag) {app.alert (msg); return false;}   // bail out on error, info user and signal upstairs to exit

  return true;                                 // all ok
}




// given a list of entries, such as raw-TAG/filename return a list of ungraded entries not yet showing up in completed-TAG/filename
function getEligibles (entries) {
  var currentBase  = this.documentFileName;
  var currentFull  = norm(this.path);
  var baseDir      = dirname(currentFull);
  var searchDir;

  if (endsWithStartPdf (currentBase)) {searchDir = baseDir;}  // current document is START.pdf so we have the right directory
  else {searchDir = parentDirectory (baseDir);}               // current directory is a sheet - which is liging inside a subdirectory - must go up one step
  // NOW searchDir should be the directory with the correctors name only

  var eligibles   = [];
  var entry;
  for (var step = 0; step < entries.length; step++) {
    entry = entries[step];                                   // this now is of the form input-TAG/filename with an unknown TAG string

    var completedRel = completedEntry (entry);               // the same sheet as completed-TAG/filename
    if (!completedRel) {
      app.alert ("ERROR: malformed queue entry, expected input-TAG/filename : " + entry);
      continue;                                              // ignore the bad line, but keep going
    }

    if (TrustedFileExists (join (searchDir, completedRel))) continue;  // skip, since file is in the completed directory
    eligibles.push ( entry);                                 // keep the input-TAG/ form: that is what the caller opens
  }
  return eligibles;
}





function stillMissing () {
  var entries   = getQueueEntries (); 
  var eligibles = getEligibles (entries);     
  return eligibles.length;
}




// opt.save
// opt.close

function Process ( opt ) {
  var doc = this;

  try {

    var currentBase  = doc.documentFileName;
    var currentFull  = norm(doc.path);
    var searchDir    = graderDirOf ();                   // .../corrections/<grader>
    var currentEntry = currentEntryOf ();                // "input-TAG/filename", null for START.pdf

    var outPath = null;                                  // where the graded copy shall go
    if (currentEntry) {
      var completedRel = completedEntry (currentEntry);  // "completed-TAG/filename"
      if (completedRel) { outPath = join (searchDir, completedRel); }
    }

     var entries   = getQueueEntries (); 
     var eligibles = getEligibles (entries);     

    if (opt.save) {                                // command was to SAVE the file

      ASSERT (outPath, "Cannot save since outPath is not defined");

      // first do a safety check whether really all questions have been graded
      var s   = getSerial ();                 
      var inc = firstIncompleteQuestion (s);
      if (inc != -1) { app.alert ("Not yet graded all questions!"); return; }

      // app.alert ("saving: " + outPath + " removing: " + currentBase);

      // second do a safety check whether file has already been saved earlier
      if (TrustedFileExists(outPath)) { app.alert("NOT SAVING - file already has been processed. If you want to change grading, delete file in directory /complete :\n\n" + outPath ); } 
      else                     { try { TrustedSaveAs (outPath);} catch (eSave) { app.alert("Cannot save to:\n\n" + outPath + "\n\n" + "This usually means the user directory does not exist, is not writable, or the file is locked.\n\n" + "Acrobat error:\n" + eSave); }  }
    

      // remove file manually from the list of eligibles since it take a while for the file to settle on disc and we have no possibility to wait for that event
      for (var idx = 0; idx < eligibles.length; idx++) {
        if (eligibles[idx] === currentEntry) { eligibles.splice (idx, 1); break; }
      }
    }

    if (opt.close) {                                                                 // On save error we still continue queueing to next eligible file.
      if (global && global.openedByScript) {delete global.openedByScript[doc.path];} // delete opening time stamp
      doc.closeDoc(true);                                                            // close this document without saving it // TODO: CHECK AND TEST NOT SAVING....
     }

    if (opt.next) { // command was to move on to the next item
      if (eligibles.length) {  // we are NOT yet done, still some files eligibe for grading

        // app.alert ( entries.length + " exam sheets \n " + eligibles.length + " not yet graded" ); 

        // Pick the first eligible entry that is NOT the document we are in right now (and might be in the process of closing)
        // Re-opening the current document would either do nothing or fight with the close that may still be in progress, so it is skipped explicitly here.
        var nextName = null;
        for (var k = 0; k < eligibles.length; k++) {
          if (eligibles[k] !== currentEntry) { nextName = eligibles[k]; break; }
        }

 
        if (!nextName) {  // this means we still have another eligible docu but the only one is exactly this document
          if (opt.skipnext) { app.alert ("Cannot 'Skip & Next' since this is the last sheet to grade. \n  Grade it or 'Skip & Stop' "); return;}
          else { 
            ASSERT (false, "SHOULD THAT REALLY HAPPEN??? we get: " + nextName);
          }
        }

        var nextPath = join (searchDir, nextName);        // nextName already carries input-TAG/


        if (!TrustedFileExists(nextPath)) {app.alert ("ERROR: Exam sheet " + nextPath + " contained in queue.txt file but missing in directory"); return;}
        try {
          if (!global.openedByScript) {global.openedByScript = {};}        // ensure existence of a global time stamp tracker
          global.openedByScript[nextPath] = (new Date()).getTime();        // store time stamp of opening the next 
          // app.alert ("attempting to open: " + nextPath);
          var newDoc = app.openDoc( {cPath: nextPath, bHidden: false});    // app.alert ("Newly opened is: " + newDoc);
        }
        catch (exe) {app.alert ("ERROR: exception opening " + nextPath + " due to: " + exe + " STACK: " + exe.stack);}
      }
      else {  // we are done - no more files eligible for grading
        app.alert ("DONE grading " + entries.length + " sheets \n  Thank you!");
      }
    }


  } catch (e) {app.alert("ERROR: Process failed. \n\n Exception reported was:" + e + " STACK: " + e.stack);}
}

\end{insDLJS}
