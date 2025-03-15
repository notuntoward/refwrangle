// Example JavaScript to extract citation key and run Python script
var item = ZoteroPane.getSelectedItems()[0];
var citationKey = item.getExtra("citationKey"); // Assuming citationKey is stored as an extra field

// Execute Python script with citation key as parameter
var file = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
file.initWithPath("C:\\path\\to\\your\\python.exe");
var process = Components.classes["@mozilla.org/process/util;1"].createInstance(Components.interfaces.nsIProcess);
process.init(file);
var args = ["C:\\path\\to\\your\\script.py", citationKey];
process.run(false, args, args.length);
