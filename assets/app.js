const live = document.getElementById("live-region");
const numberFormat = new Intl.NumberFormat();

async function api(path, options = {}) {
  const res = await fetch(path, options);
  let body = null;
  try {
    body = await res.json();
  } catch (_) {}
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    if (body && typeof body.detail === "string") {
      detail = body.detail;
    } else if (body && Array.isArray(body.detail) && body.detail.length) {
      detail = body.detail[0].msg || detail;
    }
    throw new Error(detail);
  }
  return body;
}

function safeUrl(value) {
  return /^https?:\/\//i.test(value) ? value : null;
}

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    node.append(child);
  }
  return node;
}

async function copyText(value, button) {
  try {
    await navigator.clipboard.writeText(value);
  } catch (_) {
    const helper = document.createElement("textarea");
    helper.value = value;
    helper.setAttribute("readonly", "");
    helper.style.position = "absolute";
    helper.style.left = "-9999px";
    document.body.append(helper);
    helper.select();
    try {
      document.execCommand("copy");
    } finally {
      helper.remove();
    }
  }
  if (button) {
    button.textContent = "Copied";
    button.classList.add("copied");
    window.setTimeout(() => {
      button.textContent = "Copy";
      button.classList.remove("copied");
    }, 1600);
  }
}

function timeAgo(iso) {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function clockTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function emptyState(title, body, linkHref, linkText) {
  const wrap = el("div", { class: "empty" }, [el("p", { class: "empty-title", text: title })]);
  if (body) wrap.append(el("p", { text: body }));
  if (linkHref && linkText) {
    const link = el("a", { href: linkHref, class: "btn btn-ghost btn-sm", style: "margin-top:0.9rem" }, [el("span", { text: linkText })]);
    wrap.append(link);
  }
  return wrap;
}

if (document.getElementById("shorten-form")) {
  initHome();
}

if (document.getElementById("statband")) {
  initDashboard();
}

function initHome() {
  const form = document.getElementById("shorten-form");
  const input = document.getElementById("url-input");
  const errorBox = document.getElementById("form-err");
  const button = document.getElementById("snap-btn");
  const buttonLabel = button.querySelector(".btn-label");
  const result = document.getElementById("result");
  const resultUrl = document.getElementById("result-url");
  const resultOriginal = document.getElementById("result-original");
  const resultClicks = document.getElementById("result-clicks");
  const copyBtn = document.getElementById("copy-btn");
  const visitBtn = document.getElementById("visit-btn");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = input.value.trim();
    errorBox.textContent = "";
    if (!value) {
      errorBox.textContent = "Paste a URL first.";
      input.focus();
      return;
    }
    button.disabled = true;
    buttonLabel.textContent = "Snapping…";
    try {
      const link = await api("/api/links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: value }),
      });
      renderResult(link);
      if (live) live.textContent = "Link shortened.";
    } catch (err) {
      errorBox.textContent = err.message;
      if (live) live.textContent = `Could not shorten: ${err.message}`;
    } finally {
      button.disabled = false;
      buttonLabel.textContent = "Snap it";
    }
  });

  function renderResult(link) {
    const lastSlash = link.short_url.lastIndexOf("/");
    const base = link.short_url.slice(0, lastSlash);
    const code = link.short_url.slice(lastSlash + 1);

    resultUrl.href = safeUrl(link.short_url) || "#";
    resultUrl.textContent = "";
    resultUrl.append(
      el("span", { class: "code-stamp", text: code }),
      document.createTextNode(base + "/"),
    );

    resultOriginal.textContent = link.original_url;
    resultOriginal.title = link.original_url;
    resultOriginal.href = safeUrl(link.original_url) || "#";
    visitBtn.href = safeUrl(link.short_url) || "#";
    copyBtn.onclick = () => copyText(link.short_url, copyBtn);
    resultClicks.textContent = "counting clicks…";
    result.hidden = false;

    fetch(`/api/links/${encodeURIComponent(code)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((stats) => {
        if (stats) {
          const n = numberFormat.format(stats.click_count);
          resultClicks.innerHTML = "";
          resultClicks.append(
            el("span", { text: `${n} click${stats.click_count === 1 ? "" : "s"}` }),
            document.createTextNode(" · last "),
            el("span", { text: stats.last_clicked_at ? timeAgo(stats.last_clicked_at) : "—" }),
          );
        }
      })
      .catch(() => {});

    copyBtn.focus();
  }
}

function initDashboard() {
  const statLinks = document.getElementById("stat-links");
  const statClicks = document.getElementById("stat-clicks");
  const statLast = document.getElementById("stat-last");
  const statLastDetail = document.getElementById("stat-last-detail");
  const topLinks = document.getElementById("top-links");
  const topAside = document.getElementById("top-aside");
  const recentClicks = document.getElementById("recent-clicks");

  loadDashboard().catch((err) => {
    topLinks.replaceChildren(emptyState("Could not load the dashboard", err.message));
    if (live) live.textContent = err.message;
  });

  async function loadDashboard() {
    const data = await api("/api/dashboard");
    statLinks.textContent = numberFormat.format(data.total_links);
    statClicks.textContent = numberFormat.format(data.total_clicks);

    const latest = data.recent_clicks[0];
    if (latest) {
      statLast.textContent = timeAgo(latest.clicked_at);
      statLast.title = clockTime(latest.clicked_at);
      statLastDetail.textContent = latest.referrer ? `referrer ${latest.referrer}` : "direct visit";
    } else {
      statLast.textContent = "none yet";
      statLastDetail.textContent = "go shorten a link";
    }

    renderTopLinks(data.top_links);
    renderRecentClicks(data.recent_clicks);
  }

  function renderTopLinks(links) {
    if (!links.length) {
      topLinks.replaceChildren(
        emptyState("No snaps yet", "Shorten your first link and it will appear here.", "/", "Shorten a link"),
      );
      topAside.textContent = "0 links";
      return;
    }
    topAside.textContent = `${links.length} shown`;

    const table = el("table", { class: "ledger" });
    const head = el("thead");
    const headerRow = el("tr");
    for (const label of ["#", "Code", "Original", "Created", "Clicks", "Last click", "Actions"]) {
      headerRow.append(el("th", { scope: "col", text: label }));
    }
    head.append(headerRow);

    const body = el("tbody");
    links.forEach((link, index) => {
      const row = el("tr");
      row.append(el("td", { class: "rank", text: String(index + 1) }));
      row.append(el("td", { class: "code" }, [el("a", { href: safeUrl(link.short_url) || "#", target: "_blank", rel: "noopener noreferrer", text: link.short_code })]));
      row.append(el("td", { class: "target" }, [el("a", { href: safeUrl(link.original_url) || "#", target: "_blank", rel: "noopener noreferrer", text: link.original_url })]));
      row.append(el("td", { class: "muted", text: clockTime(link.created_at) }));
      row.append(el("td", { class: "num strong", text: numberFormat.format(link.click_count) }));
      row.append(el("td", { class: "muted", text: link.last_clicked_at ? timeAgo(link.last_clicked_at) : "never" }));
      row.append(el("td", { class: "actions" }, [
        el("button", { class: "btn btn-ghost btn-sm", type: "button", text: "Copy", onclick: (e) => copyText(link.short_url, e.currentTarget) }),
        el("button", { class: "btn btn-ghost btn-sm", type: "button", text: "Details", "aria-expanded": "false", onclick: (e) => toggleDetails(e.currentTarget, row, link.short_code) }),
      ]));
      body.append(row);
    });

    table.append(head, body);
    topLinks.replaceChildren(table);
  }

  function toggleDetails(button, row, code) {
    const existing = row.nextElementSibling;
    if (existing && existing.classList.contains("row-detail")) {
      existing.remove();
      button.setAttribute("aria-expanded", "false");
      button.textContent = "Details";
      return;
    }
    if (existing && !existing.classList.contains("row-detail")) {
      return;
    }
    const detailRow = el("tr", { class: "row-detail" });
    const cell = el("td", { colspan: "7" });
    cell.append(el("p", { class: "step-d", text: "Loading timeline…" }));
    detailRow.append(cell);
    row.after(detailRow);
    button.setAttribute("aria-expanded", "true");
    button.textContent = "Details";
    loadTimeline(cell, code).catch((err) => {
      cell.replaceChildren(el("p", { class: "step-d", text: err.message }));
    });
  }

  async function loadTimeline(cell, code) {
    const data = await api(`/api/links/${encodeURIComponent(code)}/clicks`);
    const inner = el("div", { class: "detail-inner" });
    inner.append(el("h3", { text: `Daily clicks · ${code} · ${numberFormat.format(data.total)} total` }));
    if (!data.daily.length) {
      inner.append(el("p", { class: "step-d", text: "No clicks recorded for this link yet." }));
    } else {
      const max = Math.max(...data.daily.map((d) => d.count));
      const bars = el("div", { class: "bars" });
      for (const day of data.daily) {
        const date = new Date(day.date);
        const label = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
        const fill = el("div", { class: "bar-fill" });
        fill.style.width = `${max ? Math.round((day.count / max) * 100) : 0}%`;
        bars.append(
          el("div", { class: "bar-row" }, [
            el("span", { class: "bar-day", text: label }),
            el("div", { class: "bar-track" }, [fill]),
            el("span", { class: "bar-count", text: numberFormat.format(day.count) }),
          ]),
        );
      }
      inner.append(bars);
    }
    cell.replaceChildren(inner);
  }

  function renderRecentClicks(clicks) {
    if (!clicks.length) {
      recentClicks.replaceChildren(emptyState("No clicks yet", "Every visit is logged here with its timestamp and referrer."));
      return;
    }
    const list = el("ul", { class: "clicks" });
    for (const click of clicks) {
      const item = el("li", { class: "click" });
      const time = el("span", { class: "click-time", text: `${timeAgo(click.clicked_at)} · ${clockTime(click.clicked_at)}` });
      time.title = click.clicked_at;
      const main = el("div", { class: "click-main" });
      const codeLine = el("span", { class: "code-line" });
      codeLine.append(el("span", { text: click.short_code }), el("span", { class: "pill", text: click.referrer ? "referrer" : "direct" }));
      main.append(codeLine);
      const src = el("div", { class: "src" });
      src.append(document.createTextNode(click.referrer ? click.referrer : "direct visit"));
      if (click.referrer && safeUrl(click.referrer)) {
        src.append(" → ");
        src.append(el("a", { href: safeUrl(click.referrer), target: "_blank", rel: "noopener noreferrer", text: click.original_url }));
      } else {
        src.append(" · ");
        src.append(el("span", { text: click.original_url }));
      }
      main.append(src);
      item.append(time, main);
      list.append(item);
    }
    recentClicks.replaceChildren(list);
  }
}

const footerHealth = document.getElementById("footer-health");
if (footerHealth) {
  fetch("/api/health")
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      footerHealth.textContent = `database · ${data && data.database === "ok" ? "ok" : "unreachable"}`;
    })
    .catch(() => {
      footerHealth.textContent = "database · unreachable";
    });
}
