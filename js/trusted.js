/**  trusted.js
 *
 *   This file contains trusted Javascript required for the adam-exam grading workflow.
 *   It must be placed inside of the thrusted Javascript directory of Adobe Reader.
 *   It does open a few trusted calls to adobe Reader PDF documents.
 *   We argue below why we believe that this opens up no significant security risc.
 *   STILL YOU DO THIS AT YOU OWN RISC.
 */


// we open these functions up only to situations where we are called inside of adam-exam for proper file types
function AssertSafeAdamPath(cPath, cRequiredExt) {

  function fail(arg) { app.alert(arg); arg = new Error (arg); throw arg; }                              // function fail for alerting and throwing

try {

  if (typeof cPath !== "string") fail("cPath must be type string but is type " + typeof cPath);                   // fail non-string cPath argument
  if (cPath === "")              fail("cPath must not be empty");                          // fail non-string cPath argument


  var p = cPath.replace(/\\/g, "/");                                             // normalize number of separators

  if (p.charAt(0) !== "/") fail();                                               // fail on paths which are not absolute paths starting at root

  var parts = p.split("/");                                                      // split path into components
  var inTree = false;                                                            // are we inside of the adam-exam tree
  for (var i = 0; i < parts.length; i++) {
    if (parts[i] === "..") fail();                                               // fail fast on .. components
    if (parts[i].toLowerCase() === "adam-exam") inTree = true;                   // note that we are in the adam-exam tree
  }
  if (!inTree) fail("not in a subdirectory of adam-exam");                       // fail if we are not inside of the adam-exam tree

  if (cRequiredExt) {                                                            // did we require an extension as well, e.g. ".pdf"
    if (typeof cRequiredExt !== "string") fail ("cRequiredExt must be string");
    if (p.slice(-cRequiredExt.length).toLowerCase() !== cRequiredExt) fail("Incorrect file extension");    // fail on file extension
  }
  return p;
} catch (x) { fail ("failed on unexpected exception " + x);}

}




// no big security issue since the save function works only if the full path contains a sub-directory named adam-exam
TrustedSaveAs = app.trustedFunction(function(path, close) {
   AssertSafeAdamPath (path, ".pdf");
  try {
    app.beginPriv();
    this.saveAs(path);
    if (close === true) {this.closeDoc (true); }   // true: close without asking
  } catch (e) {app.alert("EXCEPTION in trusted.js/TrustedSaveAs: Save failed for path="+path+" and close="+close+ " \n\n Details: " + e); } 
  finally {app.endPriv();}
});


// no big security issue since we only access the name of an author
TrustedGetId = app.trustedFunction(function () {
  try {
    app.beginPriv();
    var ln = "";
    try {ln = identity.name} catch (e) { ln="No-Name-From-Trusted"; }
    return ln;
    } catch (e) {app.alert("EXCEPTION in trusted.js/TrustedGetId: Call failed. \n\n Details: " + e); } 
    finally { app.endPriv(); }
});


// no big security issue since we only check if a file exists and require sub-directory adam-exam
TrustedFileExists = app.trustedFunction ( function (path) {
   AssertSafeAdamPath (path);
  try {
    app.beginPriv();
    var res;
    try {res = util.readFileIntoStream(path);} catch (ex) { return false; }  // failure indicates that file does not exist
    if (res) {return true;} else {return false;}    // do not return file content but only IF we could access the file.
  } catch (e) { app.alert ("EXCEPTION in trusted.js/TrustedFileExists: Call failed. \n\n Parameter: " + path + " \n\n Details: " + e); return false;} 
  finally { app.endPriv(); }
});


// no big security risc since we only open a specific file of a specific name used in adam-exam
ReadQueueFile = app.trustedFunction ( function(baseDir) {
   AssertSafeAdamPath (baseDir);
  try {
    //need to locally define some helpers which are not included form user JS for security reasons
    function norm(p) {return (p || "").replace(/\\/g, "/");}                                                       // normalize string p: and ensure / is path separator
    function join(dir, rel) {var d=norm(dir); var r=norm(rel); if (!d) return r; if (d.slice(-1) === "/") return d + r; return d + "/" + r;}
  
    app.beginPriv();
    var queuePath = join(baseDir, "queue.txt");
    var s = util.readFileIntoStream (queuePath);
    return s; }
  catch (ex) { app.alert ("EXCEPTION in trusted.js/ReadQueueFile: Could not read file queue.txt. \n\n Does file exist? \n Are you in the correct directory? \n\n Details: " + ex); 
    this.dirty = false;     // avoid save prompt
    this.closeDoc(true);    // true = no UI (if permitted)
    throw new Error ("Missing-Queue-File");
  }
  finally {  app.endPriv(); }
} );


// no big security risc since this opens a document under the given path into a visible, non-hidden reader window
OpenFile = app.trustedFunction ( function (path) {
   AssertSafeAdamPath (path, ".pdf");
  try {
    app-beginPriv();
    app.openDoc( {cPath: path, bHidden: false}); 
  } catch (exc) { app.alert ("EXCEPTION in trusted.js/OpenFile: Could not open file: " + path);}
  finally {app.endpriv();}
});










