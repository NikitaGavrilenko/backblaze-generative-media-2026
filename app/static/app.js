const form = document.querySelector("#brief-form");
const generateButton = document.querySelector("#generate-button");
const refreshButton = document.querySelector("#refresh-button");
const verifyButton = document.querySelector("#verify-button");
const emptyState = document.querySelector("#empty-state");
const runView = document.querySelector("#run-view");
const errorState = document.querySelector("#error-state");
const historyGrid = document.querySelector("#history-grid");

let activeRun = null;

function setError(message = "") {
  errorState.hidden = !message;
  errorState.textContent = message;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderRun(run) {
  activeRun = run;
  emptyState.hidden = true;
  runView.hidden = false;
  setError();
  document.querySelector("#run-status").textContent = run.status;
  document.querySelector("#run-provider").textContent = run.provider;
  document.querySelector("#run-model").textContent = run.model;
  document.querySelector("#run-prompt").textContent = run.prompt;
  document.querySelector("#run-parameters").textContent = JSON.stringify(run.parameters);
  document.querySelector("#run-provider-job").textContent = run.provider_job_ids.join(", ") || "Not applicable";
  document.querySelector("#run-verified").textContent = run.verified ? "Verified" : "Unverified";
  document.querySelector("#manifest-hash").textContent = run.manifest_hash;
  document.querySelector("#manifest-link").href = `/api/runs/${run.id}/manifest`;
  const assetGrid = document.querySelector("#asset-grid");
  assetGrid.replaceChildren();
  run.assets.forEach((asset) => {
    const card = element("article", "asset-card");
    const image = element("img");
    image.src = asset.url;
    image.alt = `Campaign variant ${asset.variant}`;
    const meta = element("div", "asset-meta");
    meta.append(
      element("span", "", `Variant ${asset.variant}`),
      element("span", "", `SHA ${asset.sha256.slice(0, 10)}…`),
    );
    card.append(image, meta);
    assetGrid.append(card);
  });
}

function renderHistory(runs) {
  if (!runs.length) {
    historyGrid.replaceChildren(element("p", "form-note", "No saved runs yet."));
    return;
  }
  historyGrid.replaceChildren();
  runs.forEach((run) => {
    const card = element("article", "history-card");
    card.dataset.runId = run.id;
    card.append(
      element("p", "", new Date(run.created_at).toLocaleString()),
      element("h3", "", run.campaign.name),
      element(
        "p",
        "",
        `${run.assets.length} assets · ${run.verified ? "verified" : "unverified"} · ${run.demo_mode ? "demo" : "live"}`,
      ),
    );
    historyGrid.append(card);
  });
  historyGrid.querySelectorAll("[data-run-id]").forEach((card) => {
    card.addEventListener("click", () => loadRun(card.dataset.runId));
  });
}

async function loadHistory() {
  const response = await fetch("/api/runs");
  if (!response.ok) throw new Error("Could not load run history.");
  renderHistory(await response.json());
}

async function loadHealth() {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error("Could not load application status.");
  const health = await response.json();
  const indicator = document.querySelector("#mode-indicator");
  const modeNote = document.querySelector("#mode-note");
  const historyNote = document.querySelector("#history-note");
  const storageIndicator = document.querySelector("#storage-indicator");
  const liveReady = health.mode === "live" && health.live_configured;
  indicator.querySelector("strong").textContent = `${health.mode} mode`;
  indicator.classList.toggle("mode-live", liveReady);
  if (liveReady) {
    modeNote.textContent =
      "Live mode generates two images with Cloudflare Workers AI and stores them in private Backblaze B2.";
    historyNote.textContent = "Run metadata, assets, and manifests are restored from Backblaze B2.";
    storageIndicator.textContent = "Backblaze B2 durable storage active";
  } else {
    modeNote.textContent =
      "Demo mode creates local fixtures and a real Genblaze manifest. No external AI call is made.";
    historyNote.textContent = "Demo runs are stored in the local development repository.";
    storageIndicator.textContent = "Local demo storage active";
  }
  if (health.mode === "live" && !health.live_configured) {
    setError(`Live mode is missing: ${health.missing_settings.join(", ")}`);
  }
}

async function loadRun(runId) {
  const response = await fetch(`/api/runs/${runId}`);
  if (!response.ok) throw new Error("Could not load the selected run.");
  renderRun(await response.json());
  window.scrollTo({ top: document.querySelector(".workspace").offsetTop - 24, behavior: "smooth" });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setError();
  generateButton.disabled = true;
  generateButton.firstElementChild.textContent = "Building provenance…";
  const data = new FormData(form);
  const payload = {
    name: data.get("name"),
    audience: data.get("audience"),
    message: data.get("message"),
    tone: data.get("tone"),
    aspect_ratio: data.get("aspect_ratio"),
    visual_constraints: String(data.get("visual_constraints"))
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };

  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Generation failed.");
    }
    renderRun(await response.json());
    await loadHistory();
  } catch (error) {
    setError(error.message);
  } finally {
    generateButton.disabled = false;
    generateButton.firstElementChild.textContent = "Generate traceable variants";
  }
});

refreshButton.addEventListener("click", () => loadHistory().catch((error) => setError(error.message)));

verifyButton.addEventListener("click", async () => {
  if (!activeRun) return;
  const response = await fetch(`/api/runs/${activeRun.id}/verify`, { method: "POST" });
  const result = await response.json();
  if (!response.ok) {
    setError(result.detail || "Verification failed.");
    return;
  }
  document.querySelector("#run-verified").textContent = result.verified ? "Verified" : "Failed";
  setError(result.errors.join(" "));
});

Promise.all([loadHealth(), loadHistory()]).catch((error) => setError(error.message));
