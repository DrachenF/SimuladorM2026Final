const groupsContainer = document.getElementById("groups");
const refreshBtn = document.getElementById("refresh");
const statusPill = document.getElementById("status-pill");

async function fetchGroups() {
  const res = await fetch("/api/groups");
  if (!res.ok) throw new Error("No se pudieron cargar los grupos");
  return res.json();
}

async function fetchGroupsFromCsv() {
  const opciones = ["/ResultadoGrupos.csv", "/grupos.csv"];
  let ultimoError;

  for (const url of opciones) {
    try {
      const res = await fetch(url);
      if (!res.ok) {
        ultimoError = new Error(`No se pudo leer ${url}`);
        continue;
      }
      const texto = await res.text();
      return parseCsv(texto);
    } catch (err) {
      ultimoError = err;
    }
  }

  throw ultimoError ?? new Error("No se pudieron cargar los CSV locales");
}

function parseCsv(texto) {
  const lineas = texto.trim().split(/\r?\n/);
  const encabezados = lineas.shift()?.split(",");
  if (!encabezados) throw new Error("CSV vacío");

  const grupos = {};
  lineas.forEach((linea) => {
    if (!linea.trim()) return;
    const cols = linea.split(",");
    if (cols.length < 10) return;
    const [grupo, pais, pj, w, d, l, GF, GC, DG, pts, puesto, nivel] = cols;
    const equipo = {
      grupo: grupo.trim(),
      pais: pais.trim(),
      pj: Number(pj) || 0,
      w: Number(w) || 0,
      d: Number(d) || 0,
      l: Number(l) || 0,
      GF: Number(GF) || 0,
      GC: Number(GC) || 0,
      DG: Number(DG) || 0,
      pts: Number(pts) || 0,
      puesto: Number(puesto) || 0,
      nivel: Number(nivel) || 50,
    };
    grupos[equipo.grupo] = grupos[equipo.grupo] || [];
    grupos[equipo.grupo].push(equipo);
  });

  const ordenados = {};
  Object.keys(grupos)
    .sort()
    .forEach((g) => {
      ordenados[g] = ordenarGrupo(grupos[g]);
    });
  return { grupos: ordenados, gruposDisponibles: Object.keys(ordenados) };
}

function ordenarGrupo(equipos) {
  const recalculados = equipos.map((e) => ({
    ...e,
    DG: Number(e.GF || 0) - Number(e.GC || 0),
    pts: Number(e.w || 0) * 3 + Number(e.d || 0),
  }));

  const ordenados = recalculados.sort((a, b) => {
    if (b.pts !== a.pts) return b.pts - a.pts;
    if (b.DG !== a.DG) return b.DG - a.DG;
    if (b.GF !== a.GF) return b.GF - a.GF;
    return a.pais.localeCompare(b.pais);
  });

  return ordenados.map((e, idx) => ({ ...e, puesto: idx + 1 }));
}

function renderGroupCard(groupId, teams) {
  const card = document.createElement("article");
  card.className = "card";

  const header = document.createElement("header");
  const link = document.createElement("a");
  link.href = `/grupo.html?g=${encodeURIComponent(groupId)}`;
  link.className = "group-link";
  link.textContent = `Grupo ${groupId}`;
  header.append(link);

  const table = document.createElement("table");
  table.className = "table";
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
      ${teams
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
    </tbody>`;

  card.append(header, table);
  return card;
}

function setStatus(text, tone = "neutral") {
  if (!statusPill) return;
  statusPill.textContent = text;
  statusPill.style.borderColor = tone === "error" ? "rgba(255, 99, 132, 0.4)" : "var(--border)";
  statusPill.style.background =
    tone === "error"
      ? "rgba(255, 99, 132, 0.08)"
      : "linear-gradient(135deg, rgba(95,230,201,0.08), rgba(111,163,255,0.08))";
}

async function resetData() {
  setStatus("Reiniciando con grupos.csv...", "neutral");
  try {
    const res = await fetch("/api/reset", { method: "POST" });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ error: "Error al reiniciar" }));
      throw new Error(error.error || "No se pudo reiniciar");
    }
    setStatus("Datos reiniciados", "neutral");
    await render();
  } catch (err) {
    console.error(err);
    setStatus(err.message, "error");
  }
}

async function render() {
  groupsContainer.innerHTML = "<p class='subtitle'>Cargando grupos…</p>";
  setStatus("Sincronizando", "neutral");
  try {
    let data;
    try {
      data = await fetchGroups();
    } catch (apiError) {
      console.warn("Fallo la API, usando CSV local", apiError);
      data = await fetchGroupsFromCsv();
      setStatus("Datos desde CSV", "neutral");
    }
    groupsContainer.innerHTML = "";
    const groups = data.grupos;
    const keys = Object.keys(groups).sort();
    if (!keys.length) {
      groupsContainer.innerHTML = "<p class='subtitle'>No hay grupos registrados. Verifica que el CSV tenga datos.</p>";
    } else {
      keys.forEach((g) => {
        groupsContainer.appendChild(renderGroupCard(g, groups[g]));
      });
    }
    const source = data.gruposDisponibles?.length ? "Datos listos" : "Sin datos";
    setStatus(source, "neutral");
  } catch (err) {
    groupsContainer.innerHTML =
      "<p class='subtitle'>No pudimos cargar los grupos. ¿Ejecutaste <code>python web_app.py</code>?" +
      " También asegúrate de tener <strong>grupos.csv</strong> o <strong>ResultadoGrupos.csv</strong> en la carpeta raíz.</p>";
    setStatus("Error de carga", "error");
  }
}

refreshBtn?.addEventListener("click", resetData);
render();
