const Parser = require("@postlight/parser");
const fs = require("fs");
const htmlContent = fs.readFileSync(
  "C:\\\\Users\\\\scott\\\\OneDrive\\\\share\\\\ref\\\\refwrangle\\\\test\\\\Blake25infightMAGA.html",
  "utf8"
);
Parser.parse(htmlContent, { contentType: "markdown" })
  .then((result) => {
    if (!result || !result.content) {
      console.error("Parser returned no content");
      process.exit(1);
    }
    fs.writeFileSync(
      "C:\\\\Users\\\\scott\\\\OneDrive\\\\share\\\\ref\\\\refwrangle\\\\test\\\\output.md",
      result.content,
      "utf8"
    );
    console.log("Parsing completed successfully");
  })
  .catch((error) => {
    console.error("Parsing failed:", error);

    process.exit(1);
  });
