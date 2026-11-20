(function () {
  "use strict";

  const form = document.getElementById("url-form");
  const urlInput = document.getElementById("url-input");
  const submitBtn = document.getElementById("submit-btn");
  const healthPill = document.getElementById("health-pill");
  const loadingCard = document.getElementById("loading-card");
  const errorCard = document.getElementById("error-card");
  const errorCodeEl = document.getElementById("error-code");
  const errorMsgEl = document.getElementById("error-message");
  const resultSection = document.getElementById("result-section");

  const companyNameEl = document.getElementById("company-name");
  const founderBadgeEl = document.getElementById("founder-badge");
  const validationBadgeEl = document.getElementById("validation-badge");
  const warningsBoxEl = document.getElementById("warnings-box");
  const openerLinesEl = document.getElementById("opener-lines");
  const signalsRowEl = document.getElementById("signals-row");
  const evidenceListEl = document.getElementById("evidence-list");
  const traceGridEl = document.getElementById("trace-grid");
  const pagesListEl = document.getElementById("pages-list");
  const copyBtn = document.getElementById("copy-btn");

  let latestLines = [];

  function isSafeHttpUrl(url) {
    return typeof url === "string" && /^https?:\/\//i.test(url.trim());
  }

  function clearElement(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function showError(code, message) {
    errorCodeEl.textContent = code || "error";
    errorMsgEl.textContent = message || "Unexpected error generating opener.";
    errorCard.classList.remove("hidden");
  }

  function hideFeedback() {
    errorCard.classList.add("hidden");
    resultSection.classList.add("hidden");
  }

  async function refreshHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) {
        throw new Error("Health check failed");
      }
      const data = await res.json();
      if (data.api_key_configured) {
        healthPill.textContent = `${data.model} · API key ready`;
        healthPill.className = "pill pill-ok";
      } else {
        healthPill.textContent = `${data.model} · Missing GEMINI_API_KEY`;
        healthPill.className = "pill pill-warn";
      }
    } catch (_err) {
      healthPill.textContent = "Server unavailable";
      healthPill.className = "pill pill-error";
    }
  }

  function renderResult(data) {
    latestLines = Array.isArray(data.opener_lines) ? data.opener_lines : [];
    companyNameEl.textContent = data.company_name || "Company";

    if (data.founder_name) {
      founderBadgeEl.textContent = `Founder verified: ${data.founder_name}`;
      founderBadgeEl.className = "pill pill-ok";
    } else {
      founderBadgeEl.textContent = "Founder name not listed on site";
      founderBadgeEl.className = "pill pill-muted";
    }

    const val = data.validation || {};
    if (val.passed) {
      validationBadgeEl.textContent = `Verified (${val.quotes_verified}/${val.quotes_total} quotes)`;
      validationBadgeEl.className = "pill pill-ok";
    } else {
      validationBadgeEl.textContent = `Check warnings (${val.quotes_verified || 0}/${val.quotes_total || 0} quotes)`;
      validationBadgeEl.className = "pill pill-warn";
    }

    clearElement(warningsBoxEl);
    if (Array.isArray(val.warnings) && val.warnings.length > 0) {
      warningsBoxEl.textContent = val.warnings.join(" ");
      warningsBoxEl.classList.remove("hidden");
    } else {
      warningsBoxEl.classList.add("hidden");
    }

    clearElement(openerLinesEl);
    latestLines.forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      openerLinesEl.appendChild(li);
    });

    clearElement(signalsRowEl);
    (data.signals || []).forEach((signal) => {
      const tag = document.createElement("span");
      tag.className = "signal-tag";
      tag.textContent = signal;
      signalsRowEl.appendChild(tag);
    });

    clearElement(evidenceListEl);
    (data.evidence || []).forEach((item) => {
      const li = document.createElement("li");
      li.className = "evidence-item";

      const claimEl = document.createElement("div");
      claimEl.className = "evidence-claim";
      claimEl.textContent = item.claim || "";

      const quoteEl = document.createElement("div");
      quoteEl.className = "evidence-quote";
      quoteEl.textContent = `"${item.quote || ""}"`;

      li.appendChild(claimEl);
      li.appendChild(quoteEl);

      if (isSafeHttpUrl(item.source_url)) {
        const linkEl = document.createElement("a");
        linkEl.className = "evidence-link";
        linkEl.href = item.source_url;
        linkEl.target = "_blank";
        linkEl.rel = "noopener noreferrer";
        linkEl.textContent = item.source_url;
        li.appendChild(linkEl);
      }
      evidenceListEl.appendChild(li);
    });

    const trace = data.trace_metrics || {};
    const stats = [
      ["Model", trace.model || "-"],
      ["Scrape (Code)", `${trace.scrape_ms ?? "-"} ms`],
      ["LLM (Model)", `${trace.llm_ms ?? "-"} ms`],
      ["Extracted Text", `${trace.extracted_chars ?? "-"} chars`],
      ["Quotes Verified", `${val.quotes_verified ?? 0}/${val.quotes_total ?? 0}`],
      ["Cache", trace.cached ? "Hit" : "Miss"],
    ];

    clearElement(traceGridEl);
    stats.forEach(([label, value]) => {
      const box = document.createElement("div");
      box.className = "trace-stat";

      const labelEl = document.createElement("span");
      labelEl.className = "trace-label";
      labelEl.textContent = label;

      const valueEl = document.createElement("span");
      valueEl.className = "trace-value";
      valueEl.textContent = String(value);

      box.appendChild(labelEl);
      box.appendChild(valueEl);
      traceGridEl.appendChild(box);
    });

    clearElement(pagesListEl);
    (trace.pages_fetched || []).forEach((pageUrl) => {
      const li = document.createElement("li");
      if (isSafeHttpUrl(pageUrl)) {
        const a = document.createElement("a");
        a.href = pageUrl;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = pageUrl;
        li.appendChild(a);
      } else {
        li.textContent = String(pageUrl);
      }
      pagesListEl.appendChild(li);
    });

    copyBtn.textContent = "Copy Opener";
    resultSection.classList.remove("hidden");
  }

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      urlInput.value = chip.getAttribute("data-url") || "";
      urlInput.focus();
    });
  });

  copyBtn.addEventListener("click", async () => {
    if (!latestLines.length) {
      return;
    }
    const text = latestLines.join("\n");
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied!";
    } catch (_err) {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      copyBtn.textContent = "Copied!";
    }
    setTimeout(() => {
      copyBtn.textContent = "Copy Opener";
    }, 1800);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = urlInput.value.trim();
    if (!url) {
      showError("invalid_url", "Please enter a company website URL.");
      return;
    }

    hideFeedback();
    loadingCard.classList.remove("hidden");
    submitBtn.disabled = true;

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(data.error_code, data.message);
        return;
      }
      renderResult(data);
    } catch (_err) {
      showError("network_error", "Could not reach the local FastAPI server.");
    } finally {
      loadingCard.classList.add("hidden");
      submitBtn.disabled = false;
    }
  });

  document.addEventListener("DOMContentLoaded", refreshHealth);
})();
