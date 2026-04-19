const grid = document.getElementById("bracket-grid");
const thirdsGrid = document.getElementById("thirds-grid");
const syncBtn = document.getElementById("sync");
const statusEl = document.getElementById("status");
let saveTimer;

function shortName(name) {
  if (!name) return "";
  return name.length > 18 ? `${name.slice(0, 16)}…` : name;
}

function matchCard(match, roundLabel) {
  const card = document.createElement("div");
  card.className = "match-node";
  card.dataset.id = match.id;
  const needsPens = match.goles1 !== null && match.goles2 !== null && match.goles1 === match.goles2;

  const makeInput = (value, cls, name) => {
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.value = value ?? "";
    input.name = name;
    input.className = cls;
    input.addEventListener("input", () => scheduleSave(match.id));
    return input;
  };

  const row = (team, gKey, pKey) => {
    const wrap = document.createElement("div");
    wrap.className = "match-row";
    const chip = document.createElement("span");
    chip.className = "team-chip";
    chip.textContent = team ? team.slice(0, 1).toUpperCase() : "";

    const name = document.createElement("span");
    name.className = "team-name";
    name.textContent = team || "";

    const goals = makeInput(match[gKey], "score-input", gKey);
    goals.placeholder = "";

    const penBox = document.createElement("div");
    penBox.className = `pen-box ${needsPens || match[pKey] !== null ? "" : "hidden"}`;
    const pen = makeInput(match[pKey], "score-input pen", pKey);
    pen.placeholder = "p";
    penBox.append("P", pen);

    wrap.append(chip, name, goals, penBox);
    return wrap;
  };

  const header = document.createElement("div");
  header.className = "bracket-header";
  header.textContent = `${roundLabel} · Llave ${match.id}`;

  const rows = document.createElement("div");
  rows.className = "match-rows";
  rows.append(row(match.equipo1, "goles1", "pen1"), row(match.equipo2, "goles2", "pen2"));

  const winner = document.createElement("div");
  winner.className = "winner";
  winner.textContent = match.ganador ? `→ ${shortName(match.ganador)}` : "";

  card.append(header, rows, winner);
  return card;
}

function renderThirds(list) {
  thirdsGrid.innerHTML = "";
  if (!list?.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No se pudo calcular la lista de terceros.";
    thirdsGrid.appendChild(empty);
    return;
  }

  list.forEach((item, index) => {
    const chip = document.createElement("div");
    chip.className = "third-chip";
    chip.innerHTML = `<span class="rank">${index + 1}</span><span class="name">${item.pais}</span><span class="meta">${item.grupo} · ${item.pts} pts · DG ${item.DG} · GF ${item.GF}</span>`;
    thirdsGrid.appendChild(chip);
  });
}

function render(bracket) {
  if (!bracket) return;
  renderThirds(bracket.bestThirds);
  grid.innerHTML = "";
  if (!bracket.rounds?.length) return;

  bracket.rounds.forEach((round) => {
    const section = document.createElement("section");
    section.className = "round-block";

    const title = document.createElement("h3");
    title.className = "round-title";
    title.textContent = round.label;
    section.appendChild(title);

    const matchesWrap = document.createElement("div");
    matchesWrap.className = "round-matches";
    round.matches.forEach((match) => matchesWrap.appendChild(matchCard(match, round.label)));
    section.appendChild(matchesWrap);

    grid.appendChild(section);
  });
}

async function loadBracket() {
  statusEl.textContent = "Cargando...";
  try {
    const res = await fetch("/api/bracket");
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || "Error al cargar llaves");
    render(data);
    statusEl.textContent = "Listo";
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function save(matchId) {
  const card = grid.querySelector(`.match-node[data-id="${matchId}"]`);
  if (!card) return;
  const payload = { matchId };
  card.querySelectorAll("input").forEach((input) => {
    const value = input.value.trim();
    payload[input.name] = value === "" ? null : Number.parseInt(value, 10);
  });

  statusEl.textContent = "Actualizando...";
  const res = await fetch("/api/bracket", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    statusEl.textContent = data?.error || "No se pudo guardar";
    return;
  }
  render(data);
  statusEl.textContent = "Actualizado";
}

function scheduleSave(matchId) {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => save(matchId), 200);
}

syncBtn?.addEventListener("click", () => loadBracket());
grid?.addEventListener("input", (event) => {
  const card = event.target.closest(".match-node");
  if (!card) return;
  const matchId = Number(card.dataset.id);
  scheduleSave(matchId);
});

loadBracket();
