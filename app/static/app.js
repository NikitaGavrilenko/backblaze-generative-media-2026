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

function renderRun(run) {
  activeRun = run;
  emptyState.hidden = true;
  runView.hidden = false;
  setError();
  document.querySelector("#run-status").textContent = run.status;
  document.querySelector("#run-provider").textContent = run.provider;
  document.querySelector("#run-verified").textContent = run.verified ? "Verified" : "Unverified";
  document.querySelector("#manifest-hash").textContent = run.manifest_hash;
  document.querySelector("#manifest-link").href = `/api/runs/${run.id}/manifest`;
  document.querySelector("#asset-grid").innerHTML = run.assets.map((asset) => `
    <article class="asset-card">
      <img src="${asset.url}" alt="Campaign variant ${asset.variant}">
      <div class="asset-meta">
        <span>Variant ${asset.variant}</span>
        <span>SHA ${asset.sha256.slice(0, 10)}…</span>
      </div>
    </article>
  `).join("");
}

function renderHistory(runs) {
  if (!runs.length) {
    historyGrid.innerHTML = '<p class="form-note">No saved runs yet.</p>';
    return;
  }
  historyGrid.innerHTML = runs.map((run) => `
    <article class="history-card" data-run-id="${run.id}">
      <p>${new Date(run.created_at).toLocaleString()}</p>
      <h3>${run.campaign.name}</h3>
      <p>${run.assets.length} assets · ${run.verified ? "verified" : "unverified"} · ${run.demo_mode ? "demo" : "live"}</p>
    </article>
  `).join("");
  historyGrid.querySelectorAll("[data-run-id]").forEach((card) => {
    card.addEventListener("click", () => loadRun(card.dataset.runId));
  });
}

async function loadHistory() {
  const response = await fetch("/api/runs");
  if (!response.ok) throw new Error("Could not load run history.");
  renderHistory(await response.json());
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

loadHistory().catch((error) => setError(error.message));

