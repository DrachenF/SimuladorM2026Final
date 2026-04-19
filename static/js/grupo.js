const params = new URLSearchParams(window.location.search);
let currentGroup = (params.get("g") || "A").toUpperCase();
let gruposDisponibles = [];
let partidosVigentes = [];

const title = document.getElementById("title");
const tablaContainer = document.getElementById("tabla-container");
const matchesContainer = document.getElementById("matches-container");
const journeyNav = document.getElementById("journey-nav");
const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");
const resetBtn = document.getElementById("reset-group");
const simulateBtn = document.getElementById("simulate-group");
const statusEl = document.getElementById("status");
const stepper = document.getElementById("stepper");
let saveTimeout;
let equiposActuales = [];

function renderTabla(equipos) {
  const table = document.createElement("table");
  table.className = "table wide";
  table.innerHTML = `
    <thead>
      <tr>
        <th>País</th>
        <th>PJ</th>
        <th>W</th>
        <th>D</th>
        <th>L</th>
        <th>GF</th>
        <th>GC</th>
        <th>DG</th>
        <th>Pts</th>
      </tr>
    </thead>
    <tbody>
      ${equipos
        .map(
          (t) => `
        <tr>
          <td>${t.puesto}. ${t.pais}</td>
          <td>${t.pj}</td>
          <td>${t.w}</td>
          <td>${t.d}</td>
          <td>${t.l}</td>
          <td>${t.GF}</td>
          <td>${t.GC}</td>
          <td>${t.DG}</td>
          <td>${t.pts}</td>
        </tr>`
        )
        .join("")}
    </tbody>
  `;
  tablaContainer.innerHTML = "";
  tablaContainer.appendChild(table);
}

function renderJourneyNav(jornadas) {
  if (!journeyNav) return;
  journeyNav.innerHTML = "";
  jornadas.forEach((jornada) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill muted";
    btn.textContent = `J${jornada.jornada}`;
    btn.addEventListener("click", () => {
      const anchor = document.getElementById(`jornada-${jornada.jornada}`);
      anchor?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    journeyNav.appendChild(btn);
  });
}

function renderMatches(jornadas) {
  partidosVigentes = jornadas;
  matchesContainer.innerHTML = "";
  renderJourneyNav(jornadas);

  jornadas.forEach((jornada) => {
    const titulo = document.createElement("h3");
    titulo.className = "journey-title";
    titulo.id = `jornada-${jornada.jornada}`;
    titulo.textContent = `Jornada ${jornada.jornada}`;
    matchesContainer.appendChild(titulo);

    jornada.partidos.forEach((partido) => {
      const local = partido.equipo1;
      const visita = partido.equipo2;
      const goles1 = partido.goles1;
      const goles2 = partido.goles2;
      const row = document.createElement("div");
      row.className = "match-row";
      row.dataset.local = local;
      row.dataset.visita = visita;
      row.dataset.jornada = jornada.jornada;
      row.innerHTML = `
        <span class="team">${local}</span>
        <input type="number" name="goles1" min="0" value="${
          goles1 === undefined || goles1 === null ? "" : goles1
        }" aria-label="Goles de ${local}" />
        <input type="number" name="goles2" min="0" value="${
          goles2 === undefined || goles2 === null ? "" : goles2
        }" aria-label="Goles de ${visita}" />
        <span class="team">${visita}</span>
      `;
      matchesContainer.appendChild(row);
    });
  });
}

function renderGroup(data) {
  title.textContent = `Grupo ${data.grupo}`;
  stepper.textContent = data.grupo;
  gruposDisponibles = data.gruposDisponibles || gruposDisponibles;
  equiposActuales = data.equipos || [];
  renderTabla(equiposActuales);
  const partidos = data.partidos || [];
  renderMatches(partidos);
}

async function loadGroup(id) {
  statusEl.textContent = "Cargando...";
  try {
    const res = await fetch(`/api/groups/${id}`);
    if (!res.ok) throw new Error("Grupo no encontrado");
    const data = await res.json();
    currentGroup = data.grupo;
    renderGroup(data);
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

function cycleGroup(direction) {
  if (!gruposDisponibles.length) return;
  const idx = gruposDisponibles.indexOf(currentGroup);
  const nextIdx = (idx + direction + gruposDisponibles.length) % gruposDisponibles.length;
  const nextGroup = gruposDisponibles[nextIdx];
  window.location.search = `?g=${encodeURIComponent(nextGroup)}`;
}

function collectData() {
  const rows = Array.from(matchesContainer.querySelectorAll(".match-row"));
  return rows.map((row) => {
    const val1 = row.querySelector('input[name="goles1"]').value;
    const val2 = row.querySelector('input[name="goles2"]').value;

    const parsed1 = val1.trim() === "" ? null : Number.parseInt(val1, 10);
    const parsed2 = val2.trim() === "" ? null : Number.parseInt(val2, 10);
    const goles1 = Number.isNaN(parsed1) ? null : parsed1;
    const goles2 = Number.isNaN(parsed2) ? null : parsed2;
    return {
      equipo1: row.dataset.local,
      equipo2: row.dataset.visita,
      goles1,
      goles2,
      jornada: Number(row.dataset.jornada || 0),
    };
  });
}

const RESULTADOS_COMUNES = [
  { g1: 1, g2: 0, peso: 18 },
  { g1: 1, g2: 1, peso: 16 },
  { g1: 2, g2: 1, peso: 14 },
  { g1: 0, g2: 0, peso: 12 },
  { g1: 2, g2: 0, peso: 10 },
  { g1: 0, g2: 1, peso: 9 },
  { g1: 1, g2: 2, peso: 7 },
  { g1: 2, g2: 2, peso: 5 },
  { g1: 3, g2: 1, peso: 5 },
  { g1: 3, g2: 0, peso: 4 }
];

function randomWeighted(list) {
  const total = list.reduce((sum, item) => sum + item.peso, 0);
  let r = Math.random() * total;

  for (const item of list) {
    r -= item.peso;
    if (r <= 0) return item;
  }

  return list[list.length - 1];
}

function getNivelEquipo(nombre) {
  const equipo = equiposActuales.find((t) => t.pais === nombre);
  return Number(equipo?.nivel ?? 50);
}

function getResultadoSimulado(local, visita) {
  const nivelLocal = getNivelEquipo(local);
  const nivelVisita = getNivelEquipo(visita);
  const diff = nivelLocal - nivelVisita;

  const opciones = RESULTADOS_COMUNES.map((r) => {
    let peso = r.peso;

    if (diff >= 12) {
      if (r.g1 > r.g2) peso *= 1.8;
      if (r.g1 === r.g2) peso *= 0.8;
      if (r.g1 < r.g2) peso *= 0.45;
    } else if (diff >= 6) {
      if (r.g1 > r.g2) peso *= 1.4;
      if (r.g1 === r.g2) peso *= 0.9;
      if (r.g1 < r.g2) peso *= 0.7;
    } else if (diff <= -12) {
      if (r.g1 < r.g2) peso *= 1.8;
      if (r.g1 === r.g2) peso *= 0.8;
      if (r.g1 > r.g2) peso *= 0.45;
    } else if (diff <= -6) {
      if (r.g1 < r.g2) peso *= 1.4;
      if (r.g1 === r.g2) peso *= 0.9;
      if (r.g1 > r.g2) peso *= 0.7;
    }

    return { ...r, peso };
  });

  return randomWeighted(opciones);
}

async function simulateGroup() {
  const rows = Array.from(matchesContainer.querySelectorAll(".match-row"));
  if (!rows.length) return;

  rows.forEach((row) => {
    const local = row.dataset.local;
    const visita = row.dataset.visita;
    const resultado = getResultadoSimulado(local, visita);

    const input1 = row.querySelector('input[name="goles1"]');
    const input2 = row.querySelector('input[name="goles2"]');

    input1.value = resultado.g1;
    input2.value = resultado.g2;
  });

  await save();
  statusEl.textContent = "Grupo simulado";
}

async function save() {
  statusEl.textContent = "Actualizando...";
  try {
    const partidos = collectData();
    const res = await fetch(`/api/groups/${currentGroup}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ partidos }),
    });
    if (!res.ok) throw new Error("No se pudo guardar");
    const data = await res.json();
    if (data?.equipos) {
      renderTabla(data.equipos);
    }
    statusEl.textContent = "Actualizado";
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

function triggerAutoSave() {
  statusEl.textContent = "Actualizando...";
  if (saveTimeout) {
    clearTimeout(saveTimeout);
  }
  saveTimeout = setTimeout(() => {
    save();
  }, 250);
}

async function resetGroup() {
  statusEl.textContent = "Reiniciando grupo...";
  try {
    const res = await fetch(`/api/groups/${currentGroup}/reset`, { method: "POST" });
    if (!res.ok) throw new Error("No se pudo reiniciar el grupo");
    await loadGroup(currentGroup);
    statusEl.textContent = "Grupo reiniciado";
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

prevBtn?.addEventListener("click", () => cycleGroup(-1));
nextBtn?.addEventListener("click", () => cycleGroup(1));
prevBtn?.addEventListener("click", () => cycleGroup(-1));
nextBtn?.addEventListener("click", () => cycleGroup(1));
resetBtn?.addEventListener("click", resetGroup);
simulateBtn?.addEventListener("click", simulateGroup);
matchesContainer?.addEventListener("input", (event) => {
  if (event.target && event.target.matches("input[type='number']")) {
    triggerAutoSave();
  }
});
loadGroup(currentGroup);
