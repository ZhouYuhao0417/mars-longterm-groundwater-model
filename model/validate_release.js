const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");

function validatePage(filename, expectedLang, switchTarget, english) {
  const html = fs.readFileSync(path.join(root, filename), "utf8");
  const start = html.indexOf("<script>") + "<script>".length;
  const end = html.indexOf("</script>", start);
  if (start < "<script>".length || end < 0) {
    throw new Error(`${filename}: inline script block not found`);
  }
  new Function(html.slice(start, end));
  return {
    language: html.includes(`<html lang="${expectedLang}">`),
    languageSwitch: html.includes(`location.href='${switchTarget}'`),
    figureExport: english
      ? html.includes("function exportPaperFigureEnglish") &&
        html.includes("addEventListener('click',exportPaperFigureEnglish)")
      : html.includes("function exportPaperFigure") &&
        html.includes("addEventListener('click',exportPaperFigure)"),
    crismSites:
      html.includes("C1") && html.includes("P1") && html.includes("A1"),
    noPlaceholderPoints:
      !html.includes("中游检查点") && !html.includes("Jezero 西部"),
    selfContained:
      !/<script[^>]+src=|<link[^>]+href=|https?:\/\//.test(html),
  };
}

const checks = {
  english: validatePage("index.html", "en", "index_zh.html", true),
  chinese: validatePage("index_zh.html", "zh-CN", "index.html", false),
};

console.log(JSON.stringify(checks, null, 2));
if (Object.values(checks).some((page) => Object.values(page).some((v) => !v))) {
  process.exitCode = 2;
}
