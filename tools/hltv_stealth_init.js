// hltv_stealth_init.js — runtime stealth injection for puppeteer-mcp.
//
// PURPOSE
// -------
// puppeteer-extra-plugin-stealth is the canonical fingerprint patcher for
// headless Chromium, but it must be applied at puppeteer.launch() time on
// the MCP server side. Inside Claude Code we cannot install npm packages
// into the MCP server, so this file holds a "best-effort runtime stealth"
// payload that can be passed to `mcp__puppeteer__puppeteer_evaluate`
// AFTER navigation to mask the most blatant headless tells.
//
// LIMITATIONS (read before assuming this is enough)
// --------------------------------------------------
// Real puppeteer-extra-stealth uses `evaluateOnNewDocument` — its overrides
// run BEFORE the page's first <script> executes. Cloudflare's challenge JS
// runs at HEAD time, so by the time `puppeteer_evaluate` fires, fingerprint
// detection has already happened. This payload therefore:
//   - cannot defeat the FIRST page-load Cloudflare challenge
//   - CAN reduce detection on SUBSEQUENT same-tab navigations
//   - is useful chiefly to make the page LOOK normal in screenshots so the
//     vision-LLM can read it (e.g. hide the "challenge platform" widget if
//     it sticks around)
//
// USAGE
// -----
// From Claude Code (or any MCP client):
//
//   mcp__puppeteer__puppeteer_navigate({ url: "https://www.hltv.org/..." })
//   // Wait ~10-15s for Cloudflare to auto-clear if it can.
//   mcp__puppeteer__puppeteer_evaluate({ script: <contents of this file> })
//   mcp__puppeteer__puppeteer_screenshot({ name: "player_<id>" })
//
// If the screenshot still shows "Just a moment...", fall back to FlareSolverr
// for that player and accept slow-but-reliable.

(() => {
  // 1. navigator.webdriver — tell-tale headless flag
  try {
    Object.defineProperty(Navigator.prototype, "webdriver", {
      get: () => undefined,
    });
  } catch (e) {
    /* already patched or sealed */
  }

  // 2. navigator.plugins — headless Chromium reports 0; real browsers report 3+
  try {
    Object.defineProperty(Navigator.prototype, "plugins", {
      get: () => [
        { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "" },
        { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: "" },
        { name: "Native Client", filename: "internal-nacl-plugin", description: "" },
      ],
    });
  } catch (e) {
    /* */
  }

  // 3. navigator.languages — should be non-empty
  try {
    Object.defineProperty(Navigator.prototype, "languages", {
      get: () => ["en-US", "en"],
    });
  } catch (e) {
    /* */
  }

  // 4. window.chrome — present on real Chrome, missing on headless
  try {
    if (!window.chrome) {
      window.chrome = { runtime: {}, app: {}, csi: () => ({}), loadTimes: () => ({}) };
    }
  } catch (e) {
    /* */
  }

  // 5. permissions.query — headless returns "denied" for notifications,
  //    real browsers return Notification.permission state
  try {
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
      params && params.name === "notifications"
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(params);
  } catch (e) {
    /* */
  }

  // 6. WebGL vendor / renderer — headless reports "Google Inc." / "Mesa"
  try {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function (parameter) {
      // UNMASKED_VENDOR_WEBGL=37445; UNMASKED_RENDERER_WEBGL=37446
      if (parameter === 37445) return "Intel Inc.";
      if (parameter === 37446) return "Intel Iris OpenGL Engine";
      return getParameter.call(this, parameter);
    };
  } catch (e) {
    /* */
  }

  // 7. Strip the "Just a moment..." element if it lingered (cosmetic — helps
  //    the vision-LLM read the actual stats page if Cloudflare double-rendered)
  try {
    const cf = document.querySelector(
      '#challenge-running, .cf-browser-verification, [data-cf-modal]'
    );
    if (cf) cf.remove();
  } catch (e) {
    /* */
  }

  return {
    ok: true,
    webdriver: navigator.webdriver,
    plugins_len: navigator.plugins.length,
    languages: navigator.languages,
    chrome_present: !!window.chrome,
    cf_widget_remaining: !!document.querySelector(
      '#challenge-running, .cf-browser-verification'
    ),
  };
})();
