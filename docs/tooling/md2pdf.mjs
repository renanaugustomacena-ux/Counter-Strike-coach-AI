#!/usr/bin/env node
/**
 * md2pdf.mjs — High-fidelity Markdown-to-PDF converter with vector Mermaid diagrams.
 *
 * Usage:
 *   node md2pdf.mjs <input.md> [output.pdf]       # single file
 *   node md2pdf.mjs --batch <directory>            # all Book-Coach files
 *
 * Pipeline:
 *   1. Read Markdown source
 *   2. Convert to HTML via `marked` (GFM tables, code blocks)
 *   3. Wrap in styled HTML template with mermaid.js CDN + cover page
 *   4. Open in Puppeteer headless Chromium
 *   5. Wait for ALL mermaid diagrams to render as inline SVG
 *   6. Post-render: measure tables/diagrams, adjust page-break rules
 *   7. Print to PDF (SVGs remain vector — zoomable without loss)
 */

import { readFile } from "node:fs/promises";
import { resolve, basename, dirname } from "node:path";
import { Marked } from "marked";
import puppeteer from "puppeteer";

// --- Cover page data -------------------------------------------------------------
const COVER_DATA = {
  "Book-Coach-1A": {
    title: "Ultimate CS2 Coach",
    subtitle: "Parte 1A — Il Cervello",
    description:
      "Architettura neurale, addestramento, JEPA, VL-JEPA, Superposition Layer, LSTM + Mixture of Experts",
  },
  "Book-Coach-1B": {
    title: "Ultimate CS2 Coach",
    subtitle: "Parte 1B — I Sensi e lo Specialista",
    description:
      "RAP Coach Model, ChronovisorScanner, GhostEngine, Sorgenti Dati, HLTV, Steam, FACEIT",
  },
  "Book-Coach-2": {
    title: "Ultimate CS2 Coach",
    subtitle: "Parte 2 — Servizi, Analisi e Database",
    description:
      "Coaching Services, Knowledge & Retrieval, Analysis Engines, Database Schema, Training Pipeline",
  },
  "Book-Coach-3": {
    title: "Ultimate CS2 Coach",
    subtitle: "Parte 3 — Programma, UI, Tools e Build",
    description:
      "Logica Programma, UI Qt/PySide6, Ingestion Pipeline, 17 Tools Diagnostici, 81 Test Files, Remediation",
  },
};

function buildCoverHtml(fileBaseName) {
  const data = COVER_DATA[fileBaseName] || {
    title: fileBaseName,
    subtitle: "",
    description: "",
  };
  return `
<div class="cover-page">
  <div class="cover-content">
    <div class="cover-badge">CS2 AI COACHING SYSTEM</div>
    <h1 class="cover-title">${data.title}</h1>
    <div class="cover-divider"></div>
    <h2 class="cover-subtitle">${data.subtitle}</h2>
    <p class="cover-description">${data.description}</p>
    <p class="cover-author">Autore: Renan Augusto Macena</p>
    <p class="cover-date">Marzo 2026</p>
  </div>
</div>`;
}

// --- Markdown parsing -----------------------------------------------------------
const marked = new Marked({ gfm: true, breaks: false });

const renderer = {
  code({ text, lang }) {
    if (lang === "mermaid") {
      return `<pre class="mermaid">${text}</pre>\n`;
    }
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    const langClass = lang ? ` class="language-${lang}"` : "";
    return `<pre><code${langClass}>${escaped}</code></pre>\n`;
  },
};
marked.use({ renderer });

// --- HTML template ---------------------------------------------------------------
function wrapHtml(bodyHtml, title, fileBaseName) {
  const coverHtml = buildCoverHtml(fileBaseName);
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
    flowchart:  { useMaxWidth: true, htmlLabels: true, curve: 'basis', padding: 8 },
    sequence:   { useMaxWidth: true, showSequenceNumbers: false, wrap: true },
    er:         { useMaxWidth: true, fontSize: 10 },
    state:      { useMaxWidth: true },
    themeVariables: {
      fontFamily: 'Segoe UI, Roboto, sans-serif',
      fontSize: '12px'
    }
  });
</script>

<style>
  /* === PAGE SETUP === */
  @page {
    size: A4;
    margin: 20mm 18mm 22mm 18mm;
  }

  * { box-sizing: border-box; }

  body {
    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 100%;
    margin: 0;
    padding: 0;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
  }

  /* === HEADINGS === */
  h1 {
    font-size: 22pt; color: #0d47a1;
    border-bottom: 3px solid #0d47a1; padding-bottom: 6px;
    margin-top: 28px; margin-bottom: 12px;
    page-break-after: avoid; break-after: avoid;
    page-break-inside: avoid; break-inside: avoid;
  }
  h2 {
    font-size: 17pt; color: #1565c0;
    border-bottom: 2px solid #e0e0e0; padding-bottom: 4px;
    margin-top: 24px; margin-bottom: 10px;
    page-break-after: avoid; break-after: avoid;
    page-break-inside: avoid; break-inside: avoid;
  }
  h3 {
    font-size: 14pt; color: #1976d2;
    margin-top: 20px; margin-bottom: 8px;
    page-break-after: avoid; break-after: avoid;
  }
  h4 {
    font-size: 12pt; color: #1e88e5;
    margin-top: 16px; margin-bottom: 6px;
    page-break-after: avoid; break-after: avoid;
  }
  h5, h6 {
    font-size: 11pt; color: #42a5f5;
    margin-top: 12px; margin-bottom: 4px;
    page-break-after: avoid; break-after: avoid;
  }

  /* Keep heading glued to the element that follows it */
  h1 + *, h2 + *, h3 + *, h4 + * {
    page-break-before: avoid;
    break-before: avoid;
  }

  /* === PARAGRAPHS === */
  p {
    margin: 6px 0;
    widows: 3;
    orphans: 3;
  }

  /* === TABLES === */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 9pt;
    page-break-inside: avoid;
    break-inside: avoid;
  }
  thead {
    display: table-header-group;   /* repeat header on each page */
    background-color: #e3f2fd;
  }
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
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  tr:nth-child(even) { background-color: #fafafa; }
  tr {
    page-break-inside: avoid;
    break-inside: avoid;
  }

  /* === CODE === */
  code {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace;
    background-color: #f5f5f5;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9pt;
    color: #c62828;
  }
  pre {
    background-color: #263238;
    color: #eeffff;
    padding: 12px 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 8.5pt;
    line-height: 1.45;
    page-break-inside: avoid;
    break-inside: avoid;
    margin: 12px 0;
  }
  pre code {
    background: none;
    color: inherit;
    padding: 0;
    font-size: inherit;
  }
  /* Inline code inside table cells */
  td code, th code {
    font-size: 8pt;
    padding: 1px 3px;
  }

  /* === MERMAID DIAGRAMS === */
  pre.mermaid {
    background: #ffffff;
    color: #1a1a1a;
    text-align: center;
    padding: 14px 6px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    page-break-inside: avoid;
    break-inside: avoid;
    overflow: hidden;
    margin: 16px 0;
  }
  pre.mermaid svg {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
  }

  /* === BLOCKQUOTES (analogie) === */
  blockquote {
    border-left: 4px solid #42a5f5;
    background-color: #e3f2fd;
    margin: 14px 0;
    padding: 12px 16px;
    color: #1a1a1a;
    font-style: normal;
    page-break-inside: avoid;
    break-inside: avoid;
    border-radius: 0 6px 6px 0;
  }
  blockquote strong { color: #0d47a1; }
  blockquote p:first-child { margin-top: 0; }
  blockquote p:last-child { margin-bottom: 0; }

  /* === LISTS === */
  ul, ol { margin: 8px 0; padding-left: 24px; }
  li { margin-bottom: 3px; }

  /* === LINKS === */
  a { color: #1565c0; text-decoration: none; }

  /* === HORIZONTAL RULES === */
  hr { border: none; border-top: 2px solid #e0e0e0; margin: 20px 0; }

  /* === IMAGES === */
  img { max-width: 100%; height: auto; }

  /* === COVER PAGE === */
  .cover-page {
    page-break-after: always;
    break-after: always;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    text-align: center;
    padding: 40px 20px;
  }
  .cover-content { max-width: 80%; }
  .cover-badge {
    display: inline-block;
    background: #0d47a1;
    color: #fff;
    padding: 6px 22px;
    border-radius: 20px;
    font-size: 10pt;
    letter-spacing: 2px;
    margin-bottom: 40px;
  }
  .cover-title {
    font-size: 36pt !important;
    color: #0d47a1 !important;
    border: none !important;
    margin: 20px 0 10px 0 !important;
    padding: 0 !important;
    line-height: 1.2;
  }
  .cover-divider {
    width: 120px;
    height: 4px;
    background: linear-gradient(90deg, #0d47a1, #42a5f5);
    margin: 24px auto;
    border-radius: 2px;
  }
  .cover-subtitle {
    font-size: 20pt !important;
    color: #1565c0 !important;
    border: none !important;
    margin: 10px 0 24px 0 !important;
    padding: 0 !important;
    font-weight: 400;
  }
  .cover-description {
    font-size: 11pt;
    color: #555;
    margin: 24px 0;
    line-height: 1.7;
  }
  .cover-author {
    font-size: 13pt;
    color: #333;
    margin-top: 60px;
    font-weight: 500;
  }
  .cover-date {
    font-size: 10pt;
    color: #999;
    margin-top: 8px;
  }

  /* === PRINT UTILITIES === */
  .page-break { page-break-before: always; }
</style>
</head>
<body>
${coverHtml}
${bodyHtml}

<script>
  // ---- Mermaid readiness: wait for ALL diagrams to finish ----
  document.addEventListener('DOMContentLoaded', () => {
    const allMermaid = document.querySelectorAll('pre.mermaid');
    const totalDiagrams = allMermaid.length;

    if (totalDiagrams === 0) {
      window.__mermaidReady = true;
      return;
    }

    console.log('[mermaid] Total diagrams to render: ' + totalDiagrams);

    const checkReady = setInterval(() => {
      // Mermaid v11 adds data-processed attribute and injects SVG
      const processed = document.querySelectorAll('pre.mermaid[data-processed="true"]').length;
      const withSvg = document.querySelectorAll('pre.mermaid svg').length;
      const done = Math.max(processed, withSvg);
      console.log('[mermaid] Progress: ' + done + '/' + totalDiagrams);
      if (done >= totalDiagrams) {
        clearInterval(checkReady);
        console.log('[mermaid] All diagrams rendered!');
        window.__mermaidReady = true;
      }
    }, 500);

    // Hard timeout: 138 diagrams × ~2s each ≈ 276s; use 180s as upper bound
    setTimeout(() => {
      if (!window.__mermaidReady) {
        console.warn('[mermaid] Hard timeout reached — proceeding with available diagrams');
        clearInterval(checkReady);
        window.__mermaidReady = true;
      }
    }, 180000);
  });
</script>
</body>
</html>`;
}

// --- Post-render page adjustments ------------------------------------------------
async function postRenderAdjustments(page) {
  await page.evaluate(() => {
    const PAGE_CONTENT_HEIGHT = 900; // px — conservative for A4 with margins

    // --- Handle long tables: allow break but repeat headers ---
    document.querySelectorAll("table").forEach((table) => {
      if (table.offsetHeight > PAGE_CONTENT_HEIGHT) {
        table.style.pageBreakInside = "auto";
        table.style.breakInside = "auto";
        const thead = table.querySelector("thead");
        if (thead) {
          thead.style.display = "table-header-group";
        }
        // Individual rows still never split
        table.querySelectorAll("tr").forEach((tr) => {
          tr.style.pageBreakInside = "avoid";
          tr.style.breakInside = "avoid";
        });
      }
    });

    // --- Handle oversized Mermaid diagrams ---
    document.querySelectorAll("pre.mermaid").forEach((container) => {
      const svg = container.querySelector("svg");
      if (!svg) return;

      const rect = svg.getBoundingClientRect();
      const containerWidth = container.getBoundingClientRect().width;

      // Very tall diagram: allow page break (vector stays crisp when split)
      if (rect.height > PAGE_CONTENT_HEIGHT) {
        container.style.pageBreakInside = "auto";
        container.style.breakInside = "auto";
      }

      // Too wide: constrain
      if (rect.width > containerWidth) {
        svg.style.width = "100%";
        svg.style.height = "auto";
      }
    });
  });
}

// --- Convert a single file -------------------------------------------------------
async function convertFile(browser, inputPath, outputPath) {
  const fileBaseName = basename(inputPath, ".md");

  console.log(`\n${"=".repeat(60)}`);
  console.log(`[md2pdf] Reading: ${inputPath}`);
  const mdContent = await readFile(inputPath, "utf-8");

  console.log(`[md2pdf] Parsing Markdown (${(mdContent.length / 1024).toFixed(0)} KB)...`);
  const htmlBody = await marked.parse(mdContent);

  const title = fileBaseName.replace(/-/g, " ");
  const fullHtml = wrapHtml(htmlBody, title, fileBaseName);

  console.log(`[md2pdf] Opening page in Chromium...`);
  const page = await browser.newPage();

  // Log mermaid progress from within the page
  page.on("console", (msg) => {
    const text = msg.text();
    if (text.includes("[mermaid]")) {
      console.log(`  ${text}`);
    }
  });
  page.on("pageerror", (err) => {
    console.error(`  [page error] ${err.message}`);
  });

  // Load HTML
  await page.setContent(fullHtml, {
    waitUntil: "networkidle0",
    timeout: 120000,
  });

  // Wait for all mermaid diagrams to render
  console.log(`[md2pdf] Waiting for Mermaid diagrams...`);
  await page.waitForFunction(() => window.__mermaidReady === true, {
    timeout: 200000,
  });

  // Extra delay for final SVG paint operations
  await new Promise((r) => setTimeout(r, 3000));

  // Post-render adjustments: handle oversized tables and diagrams
  console.log(`[md2pdf] Applying post-render adjustments...`);
  await postRenderAdjustments(page);

  // Small delay after DOM adjustments
  await new Promise((r) => setTimeout(r, 500));

  const bookTitle = COVER_DATA[fileBaseName]
    ? `${COVER_DATA[fileBaseName].title} — ${COVER_DATA[fileBaseName].subtitle}`
    : title;

  console.log(`[md2pdf] Generating PDF: ${outputPath}`);
  await page.pdf({
    path: outputPath,
    format: "A4",
    printBackground: true,
    margin: { top: "20mm", right: "18mm", bottom: "22mm", left: "18mm" },
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:7.5pt; color:#aaa; width:100%; text-align:right; padding:4px 18mm 0 18mm; font-family: 'Segoe UI', sans-serif;">
      <span>${bookTitle}</span>
    </div>`,
    footerTemplate: `<div style="font-size:7.5pt; color:#aaa; width:100%; text-align:center; padding:0 18mm 4px 18mm; font-family: 'Segoe UI', sans-serif;">
      Pagina <span class="pageNumber"></span> di <span class="totalPages"></span>
    </div>`,
  });

  await page.close();
  console.log(`[md2pdf] Done! → ${basename(outputPath)}`);
}

// --- Main ------------------------------------------------------------------------
async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error("Usage:");
    console.error("  node md2pdf.mjs <input.md> [output.pdf]");
    console.error("  node md2pdf.mjs --batch <directory>");
    process.exit(1);
  }

  console.log("[md2pdf] Launching Chromium...");
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
    ],
  });

  try {
    if (args[0] === "--batch") {
      // Batch mode: process all Book-Coach files
      const docsDir = resolve(args[1] || ".");
      const files = [
        "Book-Coach-1A.md",
        "Book-Coach-1B.md",
        "Book-Coach-2.md",
        "Book-Coach-3.md",
      ];

      console.log(`[md2pdf] Batch mode: ${files.length} files from ${docsDir}`);

      for (const file of files) {
        const inputPath = resolve(docsDir, file);
        const outputPath = resolve(docsDir, file.replace(".md", ".pdf"));
        try {
          await convertFile(browser, inputPath, outputPath);
        } catch (err) {
          console.error(`[md2pdf] FAILED: ${file}: ${err.message}`);
        }
      }
    } else {
      // Single file mode
      const inputPath = resolve(args[0]);
      const outputPath = args[1]
        ? resolve(args[1])
        : resolve(dirname(inputPath), basename(inputPath, ".md") + ".pdf");

      await convertFile(browser, inputPath, outputPath);
    }
  } finally {
    await browser.close();
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log("[md2pdf] All done!");
}

main().catch((err) => {
  console.error("[md2pdf] FATAL:", err);
  process.exit(1);
});
