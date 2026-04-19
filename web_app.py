"""Servidor web minimalista para visualizar y editar grupos.

- Lee la información desde ResultadoGrupos.csv (o grupos.csv si no existe).
- Expone endpoints JSON para consultar y actualizar datos de cada grupo.
- Sirve una interfaz estática moderna y minimalista en ``/`` y ``/grupo.html``.

Ejecuta:
    python web_app.py
"""
from __future__ import annotations

import csv
import json
import os
from functools import partial
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
GRUPOS_CSV = BASE_DIR / "grupos.csv"
RESULTADO_CSV = BASE_DIR / "ResultadoGrupos.csv"
PARTIDOS_JSON = BASE_DIR / "partidos.json"
COMBINACIONES_CSV = BASE_DIR / "Combinaciones.csv"
LLAVES_CSV = BASE_DIR / "LLaves16.csv"
LLAVES_STATE = BASE_DIR / "llaves_state.json"

CSV_FIELDS = [
    "grupo",
    "pais",
    "pj",
    "w",
    "d",
    "l",
    "GF",
    "GC",
    "DG",
    "pts",
    "puesto",
]


def _leer_csv_activo() -> Path:
    """Devuelve el archivo de datos a usar, priorizando ResultadoGrupos.csv."""
    return RESULTADO_CSV if RESULTADO_CSV.exists() else GRUPOS_CSV


def _reset_bracket_state_if_needed() -> bool:
    """Elimina el estado de llaves si existe alguno guardado.

    Devuelve ``True`` si se eliminó algún archivo persistente de eliminatorias,
    lo que sirve para saber que el cuadro deberá recalcularse con los nuevos
    resultados de grupos.
    """

    removed = False
    for path in (LLAVES_STATE, LLAVES_CSV):
        if path.exists():
            path.unlink()
            removed = True
    return removed


def _cargar_partidos_guardados() -> Dict[str, List[dict]]:
    """Carga resultados de partidos persistidos en JSON si existe."""

    if not PARTIDOS_JSON.exists():
        return {}

    try:
        contenido = json.loads(PARTIDOS_JSON.read_text(encoding="utf-8"))
        return contenido if isinstance(contenido, dict) else {}
    except json.JSONDecodeError:
        return {}


def _guardar_partidos_guardados(data: Dict[str, List[dict]]) -> None:
    """Persiste los resultados de partidos en disco."""

    PARTIDOS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cargar_grupos_desde(ruta: Path) -> Dict[str, List[dict]]:
    """Carga grupos desde una ruta específica."""
    grupos: Dict[str, List[dict]] = {}
    with ruta.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            grupo = row["grupo"].strip()
            # Normalizar valores numéricos; si no están presentes, caer a cero.
            numeric_fields = {k: int(row.get(k, 0) or 0) for k in ["pj", "w", "d", "l", "GF", "GC", "DG", "pts", "puesto"]}
            equipo = {
                "grupo": grupo,
                "pais": row["pais"].strip(),
                **numeric_fields,
            }
            grupos.setdefault(grupo, []).append(equipo)
    return grupos


def cargar_grupos() -> Dict[str, List[dict]]:
    """Carga los grupos desde el CSV activo (ResultadoGrupos o grupos)."""
    ruta = _leer_csv_activo()
    return _cargar_grupos_desde(ruta)


def _ordenar_grupo(equipos: List[dict]) -> List[dict]:
    """Ordena un grupo por puntos, DG, GF y nombre de país."""
    return sorted(
        equipos,
        key=lambda e: (
            -int(e.get("pts", 0)),
            -int(e.get("DG", 0)),
            -int(e.get("GF", 0)),
            e.get("pais", ""),
        ),
    )


def recalcular_grupo(equipos: List[dict], mantener_orden: bool = False) -> List[dict]:
    """Recalcula DG, pts y puesto de un grupo.

    Si ``mantener_orden`` es ``True`` devuelve los equipos en el mismo orden en el
    que llegan, pero asignando el puesto según los criterios de desempate.
    """

    actualizados: List[dict] = []
    for eq in equipos:
        w = int(eq.get("w", 0))
        d = int(eq.get("d", 0))
        l = int(eq.get("l", 0))
        gf = int(eq.get("GF", 0))
        gc = int(eq.get("GC", 0))
        pj = int(eq.get("pj", 0)) or (w + d + l)
        dg = gf - gc
        pts = w * 3 + d
        actualizados.append({
            **eq,
            "pj": pj,
            "w": w,
            "d": d,
            "l": l,
            "GF": gf,
            "GC": gc,
            "DG": dg,
            "pts": pts,
        })

    ranking = _ordenar_grupo(actualizados)
    puestos = {eq["pais"]: idx for idx, eq in enumerate(ranking, start=1)}

    if mantener_orden:
        salida: List[dict] = []
        for eq in equipos:
            calculado = next((e for e in actualizados if e["pais"] == eq["pais"]), eq)
            calculado["puesto"] = puestos.get(calculado["pais"], 0)
            salida.append(calculado)
        return salida

    for eq in ranking:
        eq["puesto"] = puestos.get(eq["pais"], 0)
    return ranking


def _generar_partidos(paises: List[str]) -> List[dict]:
    """Devuelve los 6 partidos distribuidos en tres jornadas según el orden CSV."""

    if len(paises) != 4:
        raise ValueError("Se requieren exactamente 4 equipos para generar el calendario")

    cabeza, segundo, tercero, cuarto = paises
    return [
        {
            "jornada": 1,
            "partidos": [
                (cabeza, segundo),
                (tercero, cuarto),
            ],
        },
        {
            "jornada": 2,
            "partidos": [
                (cabeza, tercero),
                (segundo, cuarto),
            ],
        },
        {
            "jornada": 3,
            "partidos": [
                (cabeza, cuarto),
                (segundo, tercero),
            ],
        },
    ]


def _calendario_base(grupo_id: str, paises: List[str]) -> List[dict]:
    """Genera el calendario en blanco respetando el orden de los países."""

    base: List[dict] = []
    for jornada in _generar_partidos(paises):
        for local, visita in jornada["partidos"]:
            base.append(
                {
                    "grupo": grupo_id,
                    "jornada": jornada["jornada"],
                    "equipo1": local,
                    "equipo2": visita,
                    "goles1": None,
                    "goles2": None,
                }
            )
    return base


def _partidos_en_crudo(grupo_id: str, paises: List[str]) -> List[dict]:
    """Calendario plano con goles (persistidos si existen)."""

    base = _calendario_base(grupo_id, paises)

    guardados = _cargar_partidos_guardados().get(grupo_id, [])
    if not isinstance(guardados, list):
        return base

    index = {
        (int(p.get("jornada", 0) or 0), p.get("equipo1"), p.get("equipo2")): p
        for p in guardados
    }
    for partido in base:
        clave = (partido["jornada"], partido["equipo1"], partido["equipo2"])
        if clave not in index:
            continue
        partido["goles1"] = index[clave].get("goles1")
        partido["goles2"] = index[clave].get("goles2")
    return base


def _limpiar_goles(valor):
    """Convierte el marcador a entero o None si está vacío."""

    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if valor == "":
            return None
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError("Marcador inválido; usa números enteros")
    if numero < 0:
        raise ValueError("El marcador no puede ser negativo")
    return numero


def _partidos_por_jornada(partidos: List[dict]) -> List[dict]:
    """Agrupa partidos planos en la estructura esperada por el frontend."""

    jornadas: Dict[int, List[dict]] = {}
    for partido in partidos:
        jornada = int(partido.get("jornada", 0) or 0)
        jornadas.setdefault(jornada, []).append(partido)

    salida = []
    for jornada in sorted(jornadas):
        salida.append({"jornada": jornada, "partidos": jornadas[jornada]})
    return salida


def guardar_grupos(grupos: Dict[str, List[dict]]) -> None:
    """Guarda todos los grupos en ResultadoGrupos.csv con los puestos recalculados."""
    # Recalcular y aplanar en orden alfabético de grupo
    todas_filas: List[dict] = []
    for grupo in sorted(grupos):
        filas = recalcular_grupo(grupos[grupo], mantener_orden=True)
        for fila in filas:
            todas_filas.append({campo: fila.get(campo, 0) if campo != "pais" and campo != "grupo" else fila.get(campo, "") for campo in CSV_FIELDS})

    with RESULTADO_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(todas_filas)


def _reiniciar_partidos(grupos: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """Crea el calendario base para todos los grupos con marcadores en cero."""

    resultados: Dict[str, List[dict]] = {}
    for grupo, equipos in grupos.items():
        paises = [e["pais"] for e in equipos]
        resultados[grupo] = _calendario_base(grupo, paises)
    _guardar_partidos_guardados(resultados)
    return resultados


def sincronizar_desde_grupos() -> Dict[str, List[dict]]:
    """Copia grupos.csv a ResultadoGrupos.csv recalculando estadísticas y puestos."""

    if not GRUPOS_CSV.exists():
        raise FileNotFoundError("No existe grupos.csv para sincronizar")

    grupos = _cargar_grupos_desde(GRUPOS_CSV)
    guardar_grupos(grupos)
    return grupos


def calcular_desde_partidos(
    grupo_id: str, partidos: List[dict], grupos_actuales: Dict[str, List[dict]]
) -> List[dict]:
    """Calcula estadísticas del grupo a partir de una lista de partidos."""

    equipos = {
        e["pais"]: {
            "grupo": grupo_id,
            "pais": e["pais"],
            "pj": 0,
            "w": 0,
            "d": 0,
            "l": 0,
            "GF": 0,
            "GC": 0,
        }
        for e in grupos_actuales[grupo_id]
    }

    for partido in partidos:
        eq1 = (partido.get("equipo1") or "").strip()
        eq2 = (partido.get("equipo2") or "").strip()
        if eq1 not in equipos or eq2 not in equipos:
            raise ValueError(f"Partido con equipo desconocido: {eq1} vs {eq2}")
        if eq1 == eq2:
            raise ValueError("Un partido no puede enfrentar al mismo equipo")

        g1_raw = partido.get("goles1")
        g2_raw = partido.get("goles2")

        if g1_raw is None or g2_raw is None or g1_raw == "" or g2_raw == "":
            # Partido no jugado todavía
            continue

        g1 = int(g1_raw)
        g2 = int(g2_raw)

        equipos[eq1]["pj"] += 1
        equipos[eq2]["pj"] += 1
        equipos[eq1]["GF"] += g1
        equipos[eq1]["GC"] += g2
        equipos[eq2]["GF"] += g2
        equipos[eq2]["GC"] += g1

        if g1 > g2:
            equipos[eq1]["w"] += 1
            equipos[eq2]["l"] += 1
        elif g1 < g2:
            equipos[eq2]["w"] += 1
            equipos[eq1]["l"] += 1
        else:
            equipos[eq1]["d"] += 1
            equipos[eq2]["d"] += 1

    return recalcular_grupo(list(equipos.values()), mantener_orden=True)


def _normalizar_partidos_para_guardar(
    grupo_id: str, partidos: List[dict], paises: List[str]
) -> List[dict]:
    """Valida y devuelve los partidos con goles listos para persistir."""

    agenda = {
        (local, visita): jornada["jornada"]
        for jornada in _generar_partidos(paises)
        for local, visita in jornada["partidos"]
    }

    normalizados: List[dict] = []
    for partido in partidos:
        eq1 = (partido.get("equipo1") or "").strip()
        eq2 = (partido.get("equipo2") or "").strip()
        if eq1 not in paises or eq2 not in paises:
            raise ValueError(f"Partido con equipo desconocido: {eq1} vs {eq2}")
        if eq1 == eq2:
            raise ValueError("Un partido no puede enfrentar al mismo equipo")

        jornada = int(partido.get("jornada", 0) or 0)
        if jornada == 0:
            jornada = agenda.get((eq1, eq2), 0)
        if (eq1, eq2) not in agenda:
            raise ValueError(f"Emparejamiento inválido: {eq1} vs {eq2}")

        normalizados.append(
            {
                "grupo": grupo_id,
                "jornada": jornada,
                "equipo1": eq1,
                "equipo2": eq2,
                "goles1": _limpiar_goles(partido.get("goles1")),
                "goles2": _limpiar_goles(partido.get("goles2")),
            }
        )

    return normalizados


# ======= Utilidades para llaves de eliminación =======


def _leer_resultados_finales() -> List[Dict[str, object]]:
    """Carga ResultadoGrupos.csv con los puestos ya calculados."""

    if not RESULTADO_CSV.exists():
        raise FileNotFoundError("No existe ResultadoGrupos.csv")

    registros: List[Dict[str, object]] = []
    with open(RESULTADO_CSV, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            registros.append(
                {
                    "grupo": (fila.get("grupo") or "").upper(),
                    "pais": (fila.get("pais") or "").strip(),
                    "pj": int(fila.get("pj") or 0),
                    "w": int(fila.get("w") or 0),
                    "d": int(fila.get("d") or 0),
                    "l": int(fila.get("l") or 0),
                    "GF": int(fila.get("GF") or 0),
                    "GC": int(fila.get("GC") or 0),
                    "DG": int(fila.get("DG") or 0),
                    "pts": int(fila.get("pts") or 0),
                    "puesto": int(fila.get("puesto") or 0),
                }
            )
    return registros


def _tabla_por_grupo(datos: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    """Agrupa por grupo y ordena por criterios de desempate."""

    tabla: Dict[str, List[Dict[str, object]]] = {}
    for fila in datos:
        grupo = fila.get("grupo", "").upper()
        tabla.setdefault(grupo, []).append(fila)

    for equipos in tabla.values():
        equipos.sort(key=lambda f: (-f["pts"], -f["DG"], -f["GF"], f["pais"]))

    return tabla


def _terceros_ordenados(datos: List[Dict[str, object]]) -> List[Dict[str, object]]:
    terceros = [fila for fila in datos if fila.get("puesto") == 3]
    return sorted(terceros, key=lambda f: (-f["pts"], -f["DG"], -f["GF"], f["pais"]))


def _cadena_ultimos_terceros(terceros: List[Dict[str, object]]) -> str:
    ultimos = terceros[-4:]
    return "".join(sorted(fila["grupo"] for fila in ultimos)) if ultimos else ""


def _leer_combinaciones() -> List[Dict[str, str]]:
    if not COMBINACIONES_CSV.exists():
        raise FileNotFoundError("No se encontró Combinaciones.csv")

    filas: List[Dict[str, str]] = []
    with open(COMBINACIONES_CSV, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames is None:
            raise ValueError("El archivo de combinaciones no tiene encabezados")
        for fila in lector:
            filas.append({k: (v or "").strip() for k, v in fila.items()})
    return filas


def _buscar_combinacion(cadena: str, combinaciones: List[Dict[str, str]]) -> Dict[str, str]:
    for fila in combinaciones:
        if fila.get("Cadena", "") == cadena:
            return fila
    raise ValueError(f"No se encontró combinación para la cadena {cadena!r}")


def _equipo_por_posicion(tabla: Dict[str, List[Dict[str, object]]], grupo: str, pos: int) -> str:
    equipos = tabla.get(grupo.upper(), [])
    if pos <= 0 or pos > len(equipos):
        raise ValueError(f"No hay equipo en la posición {pos} del grupo {grupo}")
    equipo = equipos[pos - 1]
    nombre = equipo.get("pais", "")
    pj = int(equipo.get("pj", 0))
    # Solo mostramos al equipo si completó sus tres partidos de grupo
    return nombre if pj >= 3 else ""


def _equipo_tercero(tabla: Dict[str, List[Dict[str, object]]], clave: Optional[str]) -> str:
    if not clave:
        raise ValueError("Valor de combinación inválido para tercero lugar")
    grupo = clave[-1]
    return _equipo_por_posicion(tabla, grupo, 3)


def _construir_llaves(tabla: Dict[str, List[Dict[str, object]]], combinacion: Dict[str, str]) -> List[Tuple[int, str, str]]:
    llaves: List[Tuple[int, str, str]] = []
    llaves.append((1, _equipo_por_posicion(tabla, "E", 1), _equipo_tercero(tabla, combinacion.get("1E"))))
    llaves.append((2, _equipo_por_posicion(tabla, "I", 1), _equipo_tercero(tabla, combinacion.get("1I"))))
    llaves.append((3, _equipo_por_posicion(tabla, "A", 2), _equipo_por_posicion(tabla, "B", 2)))
    llaves.append((4, _equipo_por_posicion(tabla, "F", 1), _equipo_por_posicion(tabla, "C", 2)))
    llaves.append((5, _equipo_por_posicion(tabla, "K", 2), _equipo_por_posicion(tabla, "L", 2)))
    llaves.append((6, _equipo_por_posicion(tabla, "H", 1), _equipo_por_posicion(tabla, "J", 2)))
    llaves.append((7, _equipo_por_posicion(tabla, "D", 1), _equipo_tercero(tabla, combinacion.get("1D"))))
    llaves.append((8, _equipo_por_posicion(tabla, "G", 1), _equipo_tercero(tabla, combinacion.get("1G"))))
    llaves.append((9, _equipo_por_posicion(tabla, "C", 1), _equipo_por_posicion(tabla, "F", 2)))
    llaves.append((10, _equipo_por_posicion(tabla, "E", 2), _equipo_por_posicion(tabla, "I", 2)))
    llaves.append((11, _equipo_por_posicion(tabla, "A", 1), _equipo_tercero(tabla, combinacion.get("1A"))))
    llaves.append((12, _equipo_por_posicion(tabla, "L", 1), _equipo_tercero(tabla, combinacion.get("1L"))))
    llaves.append((13, _equipo_por_posicion(tabla, "J", 1), _equipo_por_posicion(tabla, "H", 2)))
    llaves.append((14, _equipo_por_posicion(tabla, "D", 2), _equipo_por_posicion(tabla, "G", 2)))
    llaves.append((15, _equipo_por_posicion(tabla, "B", 1), _equipo_tercero(tabla, combinacion.get("1B"))))
    llaves.append((16, _equipo_por_posicion(tabla, "K", 1), _equipo_tercero(tabla, combinacion.get("1K"))))
    return llaves


def _guardar_llaves_csv(llaves: List[Tuple[int, str, str]]) -> None:
    with open(LLAVES_CSV, "w", newline="", encoding="utf-8") as archivo:
        campos = ["llave", "Equipo1", "Equipo2"]
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for llave, equipo1, equipo2 in llaves:
            escritor.writerow({"llave": llave, "Equipo1": equipo1, "Equipo2": equipo2})


def _llaves_base() -> List[Tuple[int, str, str]]:
    resultados = _leer_resultados_finales()
    tabla = _tabla_por_grupo(resultados)
    combinaciones = _leer_combinaciones()
    cadena = _cadena_ultimos_terceros(_terceros_ordenados(resultados))
    combinacion = _buscar_combinacion(cadena, combinaciones)
    llaves = _construir_llaves(tabla, combinacion)
    _guardar_llaves_csv(llaves)
    return llaves


ROUND_NAMES = {
    "R32": "Dieciseisavos",
    "R16": "Octavos",
    "QF": "Cuartos de final",
    "SF": "Semifinales",
    "F": "Final",
    "T3": "Tercer lugar",
}


def _round_for_match(match_id: int) -> str:
    if match_id <= 16:
        return "R32"
    if match_id <= 24:
        return "R16"
    if match_id <= 28:
        return "QF"
    if match_id <= 30:
        return "SF"
    if match_id == 32:
        return "T3"
    return "F"


PROGRESION = [
    (1, 17, 1),
    (2, 17, 2),
    (3, 18, 1),
    (4, 18, 2),
    (5, 19, 1),
    (6, 19, 2),
    (7, 20, 1),
    (8, 20, 2),
    (9, 21, 1),
    (10, 21, 2),
    (11, 22, 1),
    (12, 22, 2),
    (13, 23, 1),
    (14, 23, 2),
    (15, 24, 1),
    (16, 24, 2),
    (17, 25, 1),
    (18, 25, 2),
    (19, 26, 1),
    (20, 26, 2),
    (21, 27, 1),
    (22, 27, 2),
    (23, 28, 1),
    (24, 28, 2),
    (25, 29, 1),
    (26, 29, 2),
    (27, 30, 1),
    (28, 30, 2),
    (29, 31, 1),
    (30, 31, 2),
]


def _match_template(match_id: int, equipo1: str = "", equipo2: str = "") -> Dict[str, object]:
    return {
        "id": match_id,
        "round": _round_for_match(match_id),
        "equipo1": equipo1,
        "equipo2": equipo2,
        "goles1": None,
        "goles2": None,
        "pen1": None,
        "pen2": None,
        "ganador": "",
    }


def _bracket_skeleton() -> Dict[int, Dict[str, object]]:
    llaves = _llaves_base()
    matches: Dict[int, Dict[str, object]] = {}
    for match_id, eq1, eq2 in llaves:
        matches[match_id] = _match_template(match_id, eq1, eq2)

    for match_id in range(17, 33):
        if match_id not in matches:
            matches[match_id] = _match_template(match_id)

    return matches


def _winner(match: Dict[str, object]) -> Optional[str]:
    eq1 = match.get("equipo1") or ""
    eq2 = match.get("equipo2") or ""
    if not eq1 or not eq2:
        return None

    g1 = match.get("goles1")
    g2 = match.get("goles2")
    if g1 is None or g2 is None:
        return None
    if g1 > g2:
        return eq1
    if g2 > g1:
        return eq2

    p1 = match.get("pen1")
    p2 = match.get("pen2")
    if p1 is None or p2 is None:
        return None
    if p1 > p2:
        return eq1
    if p2 > p1:
        return eq2
    return None


def _loser(match: Dict[str, object]) -> Optional[str]:
    eq1 = match.get("equipo1") or ""
    eq2 = match.get("equipo2") or ""
    if not eq1 or not eq2:
        return None

    g1 = match.get("goles1")
    g2 = match.get("goles2")
    if g1 is None or g2 is None:
        return None
    if g1 < g2:
        return eq1
    if g2 < g1:
        return eq2

    p1 = match.get("pen1")
    p2 = match.get("pen2")
    if p1 is None or p2 is None:
        return None
    if p1 < p2:
        return eq1
    if p2 < p1:
        return eq2
    return None


def _merge_state(base: Dict[int, Dict[str, object]], saved: Dict[str, Dict[str, object]]) -> Dict[int, Dict[str, object]]:
    merged = {k: dict(v) for k, v in base.items()}
    for key, data in saved.items():
        try:
            mid = int(key)
        except ValueError:
            continue
        if mid not in merged:
            continue
        match = merged[mid]
        mismos = data.get("equipo1") == match.get("equipo1") and data.get("equipo2") == match.get("equipo2")
        libres = not match.get("equipo1") and not match.get("equipo2")
        if mismos or libres:
            if libres:
                match["equipo1"] = data.get("equipo1", "")
                match["equipo2"] = data.get("equipo2", "")
            for field in ("goles1", "goles2", "pen1", "pen2"):
                match[field] = data.get(field)
    return merged


def _propagar(matches: Dict[int, Dict[str, object]]) -> None:
    for _ in range(3):
        for mid in sorted(matches):
            matches[mid]["ganador"] = _winner(matches[mid]) or ""

        cambios = False
        for src, dst, slot in PROGRESION:
            ganador = matches[src]["ganador"]
            clave = "equipo1" if slot == 1 else "equipo2"
            actual = matches[dst].get(clave) or ""
            if ganador != actual:
                matches[dst][clave] = ganador
                matches[dst]["goles1"] = None
                matches[dst]["goles2"] = None
                matches[dst]["pen1"] = None
                matches[dst]["pen2"] = None
                cambios = True
        if not cambios:
            break

    for mid in sorted(matches):
        matches[mid]["ganador"] = _winner(matches[mid]) or ""

    tercer_partido = matches.get(32)
    if tercer_partido is not None:
        perdedor_izq = _loser(matches.get(29, {}))
        perdedor_der = _loser(matches.get(30, {}))
        for slot, nuevo in enumerate((perdedor_izq, perdedor_der), start=1):
            clave = "equipo1" if slot == 1 else "equipo2"
            if nuevo != tercer_partido.get(clave):
                tercer_partido[clave] = nuevo or ""
                tercer_partido["goles1"] = None
                tercer_partido["goles2"] = None
                tercer_partido["pen1"] = None
                tercer_partido["pen2"] = None
        tercer_partido["ganador"] = _winner(tercer_partido) or ""


def _load_bracket() -> Dict[int, Dict[str, object]]:
    base = _bracket_skeleton()
    guardado: Dict[str, Dict[str, object]] = {}
    if LLAVES_STATE.exists():
        try:
            guardado = json.loads(LLAVES_STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            guardado = {}

    merged = _merge_state(base, guardado)
    _propagar(merged)
    return merged


def _save_bracket(matches: Dict[int, Dict[str, object]]) -> None:
    LLAVES_STATE.write_text(json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8")


LEFT_R32 = [1, 2, 3, 4, 5, 6, 7, 8]
RIGHT_R32 = [9, 10, 11, 12, 13, 14, 15, 16]
LEFT_R16 = [17, 18, 19, 20]
RIGHT_R16 = [21, 22, 23, 24]
LEFT_QF = [25, 26]
RIGHT_QF = [27, 28]
LEFT_SF = [29]
RIGHT_SF = [30]


def _best_thirds_payload() -> List[Dict[str, object]]:
    try:
        terceros = _terceros_ordenados(_leer_resultados_finales())
    except Exception:
        return []
    top = terceros[:8]
    resultado: List[Dict[str, object]] = []
    for fila in top:
        resultado.append(
            {
                "grupo": fila.get("grupo", ""),
                "pais": fila.get("pais", ""),
                "pts": fila.get("pts", 0),
                "DG": fila.get("DG", 0),
                "GF": fila.get("GF", 0),
            }
        )
    return resultado


def _serialize_match(match: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": match["id"],
        "round": ROUND_NAMES.get(match["round"], match["round"]),
        "equipo1": match.get("equipo1", ""),
        "equipo2": match.get("equipo2", ""),
        "goles1": match.get("goles1"),
        "goles2": match.get("goles2"),
        "pen1": match.get("pen1"),
        "pen2": match.get("pen2"),
        "ganador": match.get("ganador", ""),
    }


def _matches_by_ids(matches: Dict[int, Dict[str, object]], ids: List[int]) -> List[Dict[str, object]]:
    serializados: List[Dict[str, object]] = []
    for mid in ids:
        if mid in matches:
            serializados.append(_serialize_match(matches[mid]))
    return serializados


def _bracket_payload(matches: Dict[int, Dict[str, object]]) -> Dict[str, object]:
    rounds = [
        {"label": ROUND_NAMES["R32"], "matches": _matches_by_ids(matches, list(range(1, 17)))},
        {"label": ROUND_NAMES["R16"], "matches": _matches_by_ids(matches, list(range(17, 25)))},
        {"label": ROUND_NAMES["QF"], "matches": _matches_by_ids(matches, list(range(25, 29)))},
        {"label": ROUND_NAMES["SF"], "matches": _matches_by_ids(matches, [29, 30])},
        {"label": ROUND_NAMES["T3"], "matches": _matches_by_ids(matches, [32])},
        {"label": ROUND_NAMES["F"], "matches": _matches_by_ids(matches, [31])},
    ]

    return {"rounds": rounds, "bestThirds": _best_thirds_payload()}


class GruposHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP con endpoints API y contenido estático."""

    def do_GET(self):  # noqa: N802 - API http
        if self.path.startswith("/api/groups"):
            return self._handle_api_get()
        if self.path.startswith("/api/bracket"):
            return self._handle_bracket_get()
        if self.path == "/":
            self.path = "/index.html"
        if self.path in {"/grupos.csv", "/ResultadoGrupos.csv"}:
            return self._serve_csv(Path(self.path.lstrip("/")))
        return super().do_GET()

    def do_POST(self):  # noqa: N802 - API http
        if self.path.startswith("/api/groups/") and self.path.endswith("/reset"):
            return self._handle_group_reset()
        if self.path.startswith("/api/groups/"):
            return self._handle_api_post()
        if self.path == "/api/reset":
            return self._handle_reset()
        if self.path.startswith("/api/bracket"):
            return self._handle_bracket_post()
        self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")

    def _handle_api_get(self):
        grupos = cargar_grupos()
        # Detalle de un grupo: /api/groups/A
        partes = self.path.split("/")
        if len(partes) >= 4 and partes[3]:
            grupo_id = partes[3].upper()
            data = grupos.get(grupo_id)
            if data is None:
                return self._send_json({"error": "Grupo no encontrado"}, status=HTTPStatus.NOT_FOUND)

            # La tabla se entrega ordenada por desempeño, pero los partidos
            # respetan el orden original de países del CSV.
            tabla = recalcular_grupo(data, mantener_orden=False)
            partidos = _partidos_por_jornada(
                _partidos_en_crudo(grupo_id, [e["pais"] for e in recalcular_grupo(data, mantener_orden=True)])
            )
            return self._send_json(
                {
                    "grupo": grupo_id,
                    "equipos": tabla,
                    "gruposDisponibles": sorted(grupos),
                    "partidos": partidos,
                }
            )

        # Listado completo
        payload = {g: recalcular_grupo(eq, mantener_orden=False) for g, eq in grupos.items()}
        return self._send_json({"grupos": payload, "gruposDisponibles": sorted(grupos)})

    def _handle_api_post(self):
        grupo_id = self.path.rsplit("/", 1)[-1].upper()
        longitud = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(longitud) if longitud else b""
        try:
            data = json.loads(cuerpo.decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json({"error": "JSON inválido"}, status=HTTPStatus.BAD_REQUEST)

        grupos = cargar_grupos()
        if grupo_id not in grupos:
            return self._send_json({"error": "Grupo no encontrado"}, status=HTTPStatus.NOT_FOUND)

        partidos = data.get("partidos")
        if partidos is not None:
            if not isinstance(partidos, list):
                return self._send_json({"error": "Formato de partidos inválido"}, status=HTTPStatus.BAD_REQUEST)
            try:
                normalizados = _normalizar_partidos_para_guardar(
                    grupo_id, partidos, [e["pais"] for e in grupos[grupo_id]]
                )
                actualizados = calcular_desde_partidos(grupo_id, normalizados, grupos)
            except ValueError as exc:  # errores de validación
                return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        else:
            equipos = data.get("equipos")
            if not isinstance(equipos, list):
                return self._send_json({"error": "Formato de equipos inválido"}, status=HTTPStatus.BAD_REQUEST)

            actualizados = []
            paises_validos = {e["pais"] for e in grupos[grupo_id]}
            for entrada in equipos:
                pais = entrada.get("pais", "").strip()
                if pais not in paises_validos:
                    return self._send_json({"error": f"Equipo desconocido: {pais}"}, status=HTTPStatus.BAD_REQUEST)
                actualizados.append(
                    {
                        "grupo": grupo_id,
                        "pais": pais,
                        "pj": int(entrada.get("pj", 0)),
                        "w": int(entrada.get("w", 0)),
                        "d": int(entrada.get("d", 0)),
                        "l": int(entrada.get("l", 0)),
                        "GF": int(entrada.get("GF", 0)),
                        "GC": int(entrada.get("GC", 0)),
                    }
                )

        grupos[grupo_id] = actualizados
        guardar_grupos(grupos)
        llaves_reset = _reset_bracket_state_if_needed()
        if partidos is not None:
            guardados = _cargar_partidos_guardados()
            guardados[grupo_id] = normalizados
            _guardar_partidos_guardados(guardados)
        return self._send_json(
            {"ok": True, "grupo": grupo_id, "equipos": recalcular_grupo(actualizados), "llavesReiniciadas": llaves_reset}
        )

    def _handle_group_reset(self):
        partes = self.path.strip("/").split("/")
        if len(partes) < 4:
            return self._send_json({"error": "Grupo no especificado"}, status=HTTPStatus.BAD_REQUEST)
        grupo_id = partes[2].upper()

        if not GRUPOS_CSV.exists():
            return self._send_json({"error": "No existe grupos.csv para reiniciar"}, status=HTTPStatus.NOT_FOUND)

        base = _cargar_grupos_desde(GRUPOS_CSV)
        if grupo_id not in base:
            return self._send_json({"error": "Grupo no encontrado"}, status=HTTPStatus.NOT_FOUND)

        grupos = cargar_grupos()
        grupos[grupo_id] = base[grupo_id]
        guardar_grupos(grupos)

        llaves_reset = _reset_bracket_state_if_needed()

        partidos_guardados = _cargar_partidos_guardados()
        partidos_guardados[grupo_id] = _calendario_base(grupo_id, [e["pais"] for e in base[grupo_id]])
        _guardar_partidos_guardados(partidos_guardados)

        data = recalcular_grupo(base[grupo_id], mantener_orden=False)
        partidos = _partidos_por_jornada(partidos_guardados[grupo_id])
        return self._send_json(
            {"ok": True, "grupo": grupo_id, "equipos": data, "partidos": partidos, "llavesReiniciadas": llaves_reset}
        )

    def _handle_reset(self):
        try:
            grupos = sincronizar_desde_grupos()
        except FileNotFoundError as exc:
            return self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        _reiniciar_partidos(grupos)
        llaves_reset = _reset_bracket_state_if_needed()
        return self._send_json(
            {"ok": True, "grupos": {g: recalcular_grupo(eq) for g, eq in grupos.items()}, "llavesReiniciadas": llaves_reset}
        )

    def _handle_bracket_get(self):
        try:
            matches = _load_bracket()
        except Exception as exc:  # noqa: BLE001
            return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        return self._send_json(_bracket_payload(matches))

    def _handle_bracket_post(self):
        longitud = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(longitud) if longitud else b""
        try:
            data = json.loads(cuerpo.decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json({"error": "JSON inválido"}, status=HTTPStatus.BAD_REQUEST)

        match_id = int(data.get("matchId", 0))
        if match_id <= 0:
            return self._send_json({"error": "matchId requerido"}, status=HTTPStatus.BAD_REQUEST)

        try:
            matches = _load_bracket()
        except Exception as exc:  # noqa: BLE001
            return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        if match_id not in matches:
            return self._send_json({"error": "Llave no encontrada"}, status=HTTPStatus.NOT_FOUND)

        match = matches[match_id]

        def _leer_campo(nombre: str) -> Optional[int]:
            valor = data.get(nombre)
            if valor is None:
                return None
            try:
                return int(valor)
            except (TypeError, ValueError):
                return None

        match["goles1"] = _leer_campo("goles1")
        match["goles2"] = _leer_campo("goles2")
        match["pen1"] = _leer_campo("pen1")
        match["pen2"] = _leer_campo("pen2")

        _propagar(matches)
        _save_bracket(matches)

        return self._send_json(_bracket_payload(matches))

    def _send_json(self, data, status: HTTPStatus = HTTPStatus.OK):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_csv(self, path: Path):
        """Sirve un CSV aun cuando no viva en el directorio estático."""

        target = BASE_DIR / path
        if not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "CSV no encontrado")
            return

        contenido = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)



def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    handler = partial(GruposHandler, directory=str(STATIC_DIR))
    with ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Servidor iniciado en http://{host}:{port}")
        print("Interfaz principal en / y API en /api/groups")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
