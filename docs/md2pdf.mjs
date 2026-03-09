#!/usr/bin/env node
/**
 * md2pdf.mjs — Markdown-to-PDF converter with Mermaid vector SVG support.
 *
 * Usage: node md2pdf.mjs <input.md> [output.pdf]
 *
 * Pipeline:
 *   1. Read Markdown source
 *   2. Convert to HTML via `marked` (GFM tables, code blocks)
 *   3. Wrap in styled HTML template with mermaid.js CDN
 *   4. Open in Puppeteer headless Chromium
 *   5. Wait for mermaid to render all diagrams as inline SVG
 *   6. Print to PDF (SVGs remain vector — zoomable without loss)
 */

import { readFile } from "node:fs/promises";
import { resolve, basename, dirname } from "node:path";
import { Marked } from "marked";
import puppeteer from "puppeteer";

// --- Markdown parsing -----------------------------------------------------------
const marked = new Marked({
  gfm: true,
  breaks: false,
});

// Custom renderer: emit mermaid code blocks as <pre class="mermaid"> instead of <code>
const renderer = {
  code({ text, lang }) {
    if (lang === "mermaid") {
      return `<pre class="mermaid">${text}</pre>\n`;
    }
    // Escape HTML in code blocks
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return `<pre><code class="language-${lang || ""}">${escaped}</code></pre>\n`;
  },
};
marked.use({ renderer });

// --- HTML template ---------------------------------------------------------------
function wrapHtml(bodyHtml, title) {
  return `<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>${title}</title>

<!-- Mermaid.js — renders diagrams as inline SVG (vector) -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
    er: { useMaxWidth: true, fontSize: 11 },
    themeVariables: {
      fontFamily: 'Segoe UI, Roboto, sans-serif',
      fontSize: '13px'
    }
  });
</script>

<style>
  @page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
  }

  * { box-sizing: border-box; }

  body {
    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1a1a1a;
    max-width: 100%;
    margin: 0;
    padding: 0;
  }

  /* Headings */
  h1 { font-size: 22pt; color: #0d47a1; border-bottom: 3px solid #0d47a1; padding-bottom: 6px; margin-top: 28px; page-break-after: avoid; }
  h2 { font-size: 17pt; color: #1565c0; border-bottom: 2px solid #e0e0e0; padding-bottom: 4px; margin-top: 24px; page-break-after: avoid; }
  h3 { font-size: 14pt; color: #1976d2; margin-top: 20px; page-break-after: avoid; }
  h4 { font-size: 12pt; color: #1e88e5; margin-top: 16px; page-break-after: avoid; }
  h5, h6 { font-size: 11pt; color: #42a5f5; margin-top: 12px; page-break-after: avoid; }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
    page-break-inside: auto;
  }
  thead { background-color: #e3f2fd; }
  th {
    border: 1px solid #90caf9;
    padding: 6px 8px;
    text-align: left;
    font-weight: 600;
    color: #0d47a1;
  }
  td {
    border: 1px solid #e0e0e0;
    padding: 5px 8px;
    vertical-align: top;
  }
  tr:nth-child(even) { background-color: #fafafa; }
  tr { page-break-inside: avoid; }

  /* Code */
  code {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    background-color: #f5f5f5;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9.5pt;
    color: #c62828;
  }
  pre {
    background-color: #263238;
    color: #eeffff;
    padding: 12px 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.45;
    page-break-inside: avoid;
  }
  pre code {
    background: none;
    color: inherit;
    padding: 0;
  }

  /* Mermaid diagrams */
  pre.mermaid {
    background: #ffffff;
    color: #1a1a1a;
    text-align: center;
    padding: 16px 8px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    page-break-inside: avoid;
    overflow: visible;
  }
  pre.mermaid svg {
    max-width: 100%;
    height: auto;
  }

  /* Blockquotes (analogie) */
  blockquote {
    border-left: 4px solid #42a5f5;
    background-color: #e3f2fd;
    margin: 12px 0;
    padding: 10px 16px;
    color: #1a1a1a;
    font-style: normal;
    page-break-inside: avoid;
  }
  blockquote strong { color: #0d47a1; }

  /* Lists */
  ul, ol { margin: 8px 0; padding-left: 24px; }
  li { margin-bottom: 3px; }

  /* Links */
  a { color: #1565c0; text-decoration: none; }

  /* Horizontal rules */
  hr { border: none; border-top: 2px solid #e0e0e0; margin: 20px 0; }

  /* Images (if any remain) */
  img { max-width: 100%; height: auto; }

  /* Print utilities */
  .page-break { page-break-before: always; }
</style>
</head>
<body>
${bodyHtml}

<script>
  // Signal to Puppeteer that mermaid rendering is complete
  document.addEventListener('DOMContentLoaded', () => {
    // mermaid.run() is called automatically by startOnLoad
    // We add a fallback timeout to ensure the signal fires
    const checkReady = setInterval(() => {
      const pending = document.querySelectorAll('pre.mermaid:not([data-processed])');
      const svgs = document.querySelectorAll('pre.mermaid svg, pre.mermaid[data-processed]');
      if (pending.length === 0 || svgs.length > 0) {
        clearInterval(checkReady);
        window.__mermaidReady = true;
      }
    }, 200);
    // Hard timeout after 30s
    setTimeout(() => { window.__mermaidReady = true; }, 30000);
  });
</script>
</body>
</html>`;
}

// --- Main ------------------------------------------------------------------------
async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("Usage: node md2pdf.mjs <input.md> [output.pdf]");
    process.exit(1);
  }

  const inputPath = resolve(args[0]);
  const outputPath = args[1]
    ? resolve(args[1])
    : resolve(dirname(inputPath), basename(inputPath, ".md") + ".pdf");

  console.log(`[md2pdf] Reading: ${inputPath}`);
  const mdContent = await readFile(inputPath, "utf-8");

  console.log(`[md2pdf] Parsing Markdown...`);
  const htmlBody = await marked.parse(mdContent);

  const title = basename(inputPath, ".md").replace(/-/g, " ");
  const fullHtml = wrapHtml(htmlBody, title);

  console.log(`[md2pdf] Launching Chromium...`);
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
  });

  const page = await browser.newPage();

  // Load HTML content
  await page.setContent(fullHtml, { waitUntil: "networkidle0", timeout: 60000 });

  // Wait for mermaid to finish rendering all diagrams
  console.log(`[md2pdf] Waiting for Mermaid diagrams to render...`);
  await page.waitForFunction(() => window.__mermaidReady === true, {
    timeout: 45000,
  });

  // Small extra delay for any final SVG paint operations
  await new Promise((r) => setTimeout(r, 1500));

  console.log(`[md2pdf] Generating PDF: ${outputPath}`);
  await page.pdf({
    path: outputPath,
    format: "A4",
    printBackground: true,
    margin: { top: "20mm", right: "18mm", bottom: "20mm", left: "18mm" },
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:8pt; color:#999; width:100%; text-align:center; padding:0 18mm;">
      <span>${title}</span>
    </div>`,
    footerTemplate: `<div style="font-size:8pt; color:#999; width:100%; text-align:center; padding:0 18mm;">
      <span class="pageNumber"></span> / <span class="totalPages"></span>
    </div>`,
  });

  await browser.close();
  console.log(`[md2pdf] Done! → ${outputPath}`);
}

main().catch((err) => {
  console.error("[md2pdf] FATAL:", err);
  process.exit(1);
});
