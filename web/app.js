"use strict";

const $ = (selector) => document.querySelector(selector);
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const price = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });

const safe = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function signedMoney(value) {
  const absolute = money.format(Math.abs(Number(value) || 0));
  return `${Number(value) >= 0 ? "+" : "−"}${absolute}`;
}

function signedPercent(value) {
  const number = Number(value) || 0;
  return `${number >= 0 ? "+" : "−"}${Math.abs(number * 100).toFixed(2)}%`;
}

function toneClass(value) {
  return Number(value) >= 0 ? "positive" : "negative";
}

function setText(selector, value) {
  const node = $(selector);
  if (node) node.textContent = value;
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.className = `toast show${isError ? " error" : ""}`;
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => { toast.className = "toast"; }, 4200);
}

function renderStages(stages) {
  $("#stage-list").innerHTML = (stages || []).map((stage, index) => `
    <div class="stage ${safe(stage.status)}">
      <span class="stage-index">${stage.status === "done" ? "✓" : index + 1}</span>
      <span class="stage-copy"><strong>${safe(stage.name)}</strong><small>${safe(stage.detail)}</small></span>
      <span class="stage-status">${stage.status === "active" ? "executing" : safe(stage.status)}</span>
    </div>
  `).join("");
}

function renderLastAction(action) {
  const approved = action?.status === "approved" || action?.status === "submitted";
  $("#last-action").innerHTML = `
    <span class="status-icon">${approved ? "✓" : "!"}</span>
    <div><small>LATEST CONCLUSION</small><strong>${safe(action?.title || "Agent is ready")}</strong><p>${safe(action?.detail || "Waiting for the next cycle.")}</p></div>
  `;
}

function renderChart(points) {
  if (!Array.isArray(points) || points.length < 2) return;
  const width = 900;
  const height = 300;
  const pad = { left: 54, right: 22, top: 22, bottom: 35 };
  const values = points.map((point) => Number(point.value));
  const rawMin = Math.min(...values, 100000);
  const rawMax = Math.max(...values, 100000);
  const buffer = Math.max((rawMax - rawMin) * 0.18, 110);
  const min = rawMin - buffer;
  const max = rawMax + buffer;
  const x = (index) => pad.left + index * ((width - pad.left - pad.right) / (points.length - 1));
  const y = (value) => pad.top + (max - value) * ((height - pad.top - pad.bottom) / (max - min));
  const line = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(Number(point.value)).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(1)},${height - pad.bottom} L${x(0).toFixed(1)},${height - pad.bottom} Z`;
  $("#chart-line").setAttribute("d", line);
  $("#chart-line-glow").setAttribute("d", line);
  $("#chart-area").setAttribute("d", area);

  const grid = [];
  const labels = [];
  for (let index = 0; index < 5; index += 1) {
    const gridY = pad.top + index * ((height - pad.top - pad.bottom) / 4);
    const labelValue = max - index * ((max - min) / 4);
    grid.push(`<line x1="${pad.left}" y1="${gridY}" x2="${width - pad.right}" y2="${gridY}"></line>`);
    grid.push(`<text x="0" y="${gridY + 3}">${safe(`$${(labelValue / 1000).toFixed(1)}k`)}</text>`);
  }
  const labelIndexes = [0, Math.floor((points.length - 1) / 3), Math.floor((points.length - 1) * 2 / 3), points.length - 1];
  labelIndexes.forEach((pointIndex) => {
    const date = new Date(points[pointIndex].time);
    labels.push(`<text text-anchor="middle" x="${x(pointIndex)}" y="${height - 8}">${safe(date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))}</text>`);
  });
  $("#chart-grid").innerHTML = grid.join("");
  $("#chart-labels").innerHTML = labels.join("");
  const endX = x(points.length - 1);
  const endY = y(values.at(-1));
  $("#chart-endpoint").innerHTML = `<circle cx="${endX}" cy="${endY}" r="8" fill="rgba(185,255,102,.12)"></circle><circle cx="${endX}" cy="${endY}" r="3.5" fill="#b9ff66"></circle>`;

  let peak = values[0];
  let drawdown = 0;
  values.forEach((value) => {
    peak = Math.max(peak, value);
    drawdown = Math.min(drawdown, (value - peak) / peak);
  });
  setText("#max-drawdown", `−${Math.abs(drawdown * 100).toFixed(2)}%`);
}

function renderRisk(risk) {
  const used = Number(risk?.used) || 0;
  const budget = Math.max(Number(risk?.budget) || 1, 1);
  const ratio = Math.min(used / budget, 1);
  setText("#risk-used", money.format(used));
  setText("#risk-budget", `of ${money.format(budget)} budget`);
  $("#risk-progress").style.width = `${ratio * 100}%`;
  setText("#risk-ratio", `${Math.round(ratio * 100)}%`);
  $("#risk-ring").style.setProperty("--risk-angle", `${Math.round(ratio * 360)}deg`);
  setText("#risk-caption", `${money.format(used)} of ${money.format(budget)} defined risk`);
  setText("#loss-limit", `Agent pauses at −${money.format(risk?.daily_loss_limit || 0)} today`);
  $("#gate-list").innerHTML = (risk?.gates || []).map((gate) => `
    <div class="gate ${gate.passed ? "" : "failed"}">
      <span class="gate-icon">${gate.passed ? "✓" : "×"}</span>
      <span>${safe(gate.name)}</span>
      <small>${safe(gate.detail)}</small>
    </div>
  `).join("");
}

function renderCandidates(candidates) {
  $("#candidate-grid").innerHTML = (candidates || []).map((candidate, index) => {
    const votes = (candidate.votes || []).length ? candidate.votes : [
      { agent: "Regime", score: candidate.score },
      { agent: "Momentum", score: candidate.score * .82 },
      { agent: "Breakout", score: candidate.score * .66 },
      { agent: "Reversion", score: -candidate.score * .18 },
    ];
    return `
      <article class="candidate-card ${index === 0 ? "top" : ""}">
        <div class="candidate-topline">
          <div class="symbol-lockup"><span class="symbol-icon">${safe(candidate.symbol)}</span><div><strong>${safe(candidate.symbol)}</strong><small>${price.format(candidate.spot || 0)} SPOT</small></div></div>
          <span class="direction-badge ${safe(candidate.direction)}">${safe(candidate.direction).toUpperCase()}</span>
        </div>
        <div class="candidate-score"><div><small>COMMITTEE SCORE</small><strong class="${toneClass(candidate.score)}">${Number(candidate.score) >= 0 ? "+" : ""}${Number(candidate.score).toFixed(2)}</strong></div><span class="confidence-ring" style="--confidence:${Math.round(Number(candidate.confidence) * 100)}%">${Math.round(Number(candidate.confidence) * 100)}%</span></div>
        <p>${safe(candidate.summary)}</p>
        <div class="vote-row">${votes.slice(0, 4).map((vote) => `<span class="vote-chip"><small>${safe(vote.agent)}</small><strong class="${toneClass(vote.score)}">${Number(vote.score) >= 0 ? "+" : ""}${Number(vote.score).toFixed(2)}</strong></span>`).join("")}</div>
        <div class="candidate-footer"><span>RSI ${Number(candidate.rsi).toFixed(1)}</span><span>VOL ${(Number(candidate.volatility) * 100).toFixed(1)}%</span><span>AGREE ${Math.round(Number(candidate.agreement) * 100)}%</span></div>
      </article>
    `;
  }).join("");
}

function renderPositions(positions) {
  setText("#spread-count", `${(positions || []).length} OPEN`);
  $("#positions-body").innerHTML = (positions || []).map((position) => `
    <tr>
      <td><div class="underlying-cell"><span class="symbol-icon">${safe(position.symbol)}</span><strong>${safe(position.symbol)}</strong></div></td>
      <td><span class="structure-cell"><strong>${safe(position.strategy)}</strong><small>${safe(position.direction)} · DEBIT VERTICAL</small></span></td>
      <td>${safe(position.expiry)}</td>
      <td>${safe(position.qty)}</td>
      <td>${price.format(position.entry)} / ${price.format(position.mark)}</td>
      <td>${money.format(position.max_risk)}</td>
      <td><strong class="${toneClass(position.pnl)}">${signedMoney(position.pnl)}</strong><br><small class="${toneClass(position.pnl_pct)}">${Number(position.pnl_pct) >= 0 ? "+" : ""}${Number(position.pnl_pct).toFixed(1)}%</small></td>
      <td><span class="state-badge">${safe(position.status)}</span></td>
    </tr>
  `).join("") || `<tr><td colspan="8">No open spreads. Capital is protected until a setup clears every gate.</td></tr>`;
}

function renderLedger(ledger) {
  $("#ledger-list").innerHTML = (ledger || []).map((item) => `
    <article class="ledger-item ${safe(item.tone)}">
      <span class="ledger-time">${safe(item.time)}</span>
      <span class="ledger-node">${item.tone === "muted" ? "×" : "✓"}</span>
      <span class="ledger-copy"><small>${safe(item.event)}</small><strong>${safe(item.title)}</strong><p>${safe(item.detail)}</p></span>
      <span class="ledger-symbol">${safe(item.symbol)}</span>
    </article>
  `).join("");
}

function render(data) {
  setText("#mode-pill", data.mode_label);
  setText("#market-state", data.market?.is_open ? "Market open" : "Market closed");
  setText("#market-event", data.market?.next_event || "Status unavailable");
  $(".market-dot").style.background = data.market?.is_open ? "#b9ff66" : "#ff7c72";
  const account = data.account || {};
  setText("#equity", money.format(account.equity || 0));
  setText("#total-return", signedPercent(account.total_return));
  $("#total-return").className = `delta ${toneClass(account.total_return)}`;
  setText("#account-id", `ACCOUNT ${account.account_id || "PAPER"}`);
  setText("#day-pnl", signedMoney(account.day_pnl));
  $("#day-pnl").className = toneClass(account.day_pnl);
  setText("#day-return", `${signedPercent(account.day_return)} today`);
  setText("#buying-power", money.format(account.buying_power || 0));
  setText("#chart-return", signedPercent(account.total_return));
  renderStages(data.agent_stages);
  renderLastAction(data.last_action);
  renderChart(data.equity_curve);
  renderRisk(data.risk);
  renderCandidates(data.candidates);
  renderPositions(data.positions);
  renderLedger(data.ledger);
}

async function loadDashboard() {
  const response = await fetch("/api/dashboard", { cache: "no-store" });
  if (!response.ok) throw new Error(`Dashboard unavailable (${response.status})`);
  const data = await response.json();
  render(data);
  return data;
}

async function runCycle() {
  const button = $("#run-cycle");
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="button-icon">···</span><span class="button-copy"><strong>Agent is reasoning</strong><small>Reconciling data and risk gates</small></span>`;
  try {
    const response = await fetch("/api/cycle", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Cycle failed");
    if (result.account && result.equity_curve) render(result);
    else await loadDashboard();
    showToast(result.status ? `Agent cycle: ${result.status}. ${result.reason || "Decision logged."}` : "Agent cycle completed. Demo preview logged; no order transmitted.", result.status === "error");
  } catch (error) {
    showToast(error.message || "Agent cycle failed", true);
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

async function runPreflight() {
  try {
    const response = await fetch("/api/preflight", { cache: "no-store" });
    const report = await response.json();
    const passed = (report.checks || []).filter((check) => check.passed).length;
    showToast(`${report.ready ? "Ready" : "Attention needed"}: ${passed}/${(report.checks || []).length} preflight checks passed.`, !report.ready);
  } catch (error) {
    showToast(error.message || "Preflight unavailable", true);
  }
}

$("#run-cycle").addEventListener("click", runCycle);
$("#preflight-button").addEventListener("click", runPreflight);
loadDashboard().catch((error) => showToast(error.message, true));
window.setInterval(() => loadDashboard().catch(() => {}), 30000);

