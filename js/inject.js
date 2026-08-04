

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




function GetUserDir () {
  var doc = this;
  var idName = TrustedGetId();                 //calls trusted function - TODO: check existence 
  var currentFull = norm(doc.path);
  var currentBase = doc.documentFileName;
  if (!currentBase || !currentFull) {app.alert("GetUserDir cannot determine current document path."); return "UNKNOWN"; }
  var baseDir = dirname(currentFull);
  if (!baseDir) {app.alert ("ERROR: Could not obtain baseDir in GetUserDir"); return;}
  var userDir = join(baseDir, safeName(idName));
 return userDir;
}




function percentToMark (p) {
  if      ( p > 95 && p <= 100 )   {return "1.0"; }
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
  else {return "NONE";}
//  else { app.alert ("ERROR: percentToMark cannot convert to a grade the value of " + p); return "ERROR";}
}


// return a list of files to look at from the diretory file queue.txt; look inside directory baseDir
function getQueueEntries (baseDir) {
  var stm;
  try{ stm = ReadQueueFile (baseDir);} catch (x) { throw x;} // rethrow for proper UI exit; has already been notified to user in ReadQueueFile
  if (!stm) {app.alert("ERROR: Cannot read queue file.\n\n Fix this and restart"); throw "getQueueEntries could not read queue file"; }  
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



// given a list of entries return a list of ungraded entries (ie entries eligible for grading)
function getEligibles (entries) {
  var userDir     = GetUserDir ();
  var eligibles   = [];
  var entry;
  for (var step = 0; step < entries.length; step++) {
    entry = entries[step];
    if (TrustedFileExists(join(userDir, entry))) continue;
    eligibles.push ( entry);
  }
  return eligibles;
}






// if shallSave true:  attempt to save ope file (if it exists already, show an error and continue with remaining queue)
//              false: do not attempt to save, just close this document and continue with remaining queue
// lock, save, close, next

function Process ( opt ) {
  var doc = this;

  try {
    var currentBase = doc.documentFileName;
    var currentFull = norm(doc.path);
    if (!currentBase || !currentFull) {app.alert("Cannot determine current document path."); return; }
    var baseDir = dirname(currentFull);

    var userDir = GetUserDir();
    var outPath = join(userDir, currentBase);

     var entries   = getQueueEntries (baseDir);
     var eligibles = getEligibles (entries);

    if (opt.save) {
      if (TrustedFileExists(outPath)) { app.alert("NOT SAVING - file already has been processed :\n\n" + outPath ); } 
      else                     { try { TrustedSaveAs (outPath);} catch (eSave) { app.alert("Cannot save to:\n\n" + outPath + "\n\n" + "This usually means the user directory does not exist, is not writable, or the file is locked.\n\n" + "Acrobat error:\n" + eSave); }  }
    }

    if (opt.close) { // On save error we still continue queueing to next eligible file.
      doc.closeDoc(true);    // close document
      if (global && global.openedByScript) {delete global.openedByScript[doc.path]} // delete opening time stamp
     }

    if (opt.close || opt.save) {  // if we just closed or saved the file it is no longer eligible; remove it from list of eligibles; moving getEligibles down does not help since saving and closing is async and takes some time
       var idx = eligibles.indexOf( currentBase );      
       if (idx !== -1) {eligibles.splice(idx, 1);}
    }

    if (opt.next) {
      app.alert ( entries.length + " exam sheets \n " + eligibles.length + " not yet graded" );  // ----- REPORT only in START 
      var nextName = (eligibles.length != 0 ? eligibles[0] : null);
      if (!nextName) {app.alert("No more eligible next PDF found."); return;}
      var nextPath = join ( baseDir, nextName);

      if (!TrustedFileExists(nextPath)) {app.alert ("ERROR: Exam sheet " + nextPath + " contained in queue.txt file but missing in directory"); return;}
      try {
        if (!global.openedByScript) {global.openedByScript = {};}   // ensure existence of a global time stamp tracker
        global.openedByScript[nextPath] = (new Date()).getTime();  // store time stamp of opening the next 
        var newDoc = app.openDoc( {cPath: nextPath, bHidden: false});  // app.alert ("Newly opened is: " + newDoc);
      }
      catch (exe) {app.alert ("ERROR: exception opening " + nextPath + " due to: " + exe);}
    }
  } catch (e) {app.alert("ERROR: Process failed. \n\n Exception reported was:" + e);}
}

\end{insDLJS}
