# AGENTS.md — Simulador del Mundial 2026

## Objetivo del proyecto

Este repositorio contiene una aplicación llamada **Simulador del Mundial 2026**.

La app permite:

- simular la **fase de grupos** del Mundial
- calcular tablas de posiciones
- aplicar clasificación de **primeros, segundos y mejores terceros**
- generar automáticamente las **llaves de eliminatoria**
- simular eliminatorias en **modo simple** y en **modo normal**
- exportar el resultado como imagen
- ejecutarse como **web estática**
- empaquetarse como **app Android con Capacitor**
- monetizar con **AdMob** en Android

## Stack real del proyecto

- **HTML, CSS y JavaScript puro**
- no usar frameworks a menos que el usuario lo pida explícitamente
- app web servida desde archivos estáticos
- versión Android creada con **Capacitor**
- `webDir` apunta a la carpeta estática del proyecto
- la app debe seguir siendo compatible con la versión Android ya publicada/probada

## Regla principal para cualquier cambio

### NO rehacer el proyecto desde cero

Este proyecto **ya funciona**.  
Los cambios deben ser **mínimos, puntuales y conservadores**.

Prioridad:

1. corregir sin romper lo existente
2. modificar lo mínimo posible
3. conservar ids, nombres, flujo y estructura actual siempre que se pueda
4. preferir **reemplazos concretos** sobre refactors grandes

## Preferencias del dueño del proyecto

- prefiere instrucciones del tipo **“reemplaza X por Y”**
- no quiere respuestas con cambios ambiguos tipo “agrega algo por aquí”
- valora mantener la lógica actual si ya funciona
- quiere mejoras puntuales de UX, UI y simulación
- quiere evitar que una mejora visual rompa las eliminatorias

## Qué no debe tocarse sin pedirlo explícitamente

### 1. Geometría base del bracket
Evitar tocar sin necesidad:

- estructura general del bracket
- posiciones base de rondas
- ids de partidos
- líneas SVG
- flujo entre rondas

### 2. Flujo base de grupos
No cambiar el reglamento ya implementado salvo instrucción explícita.

### 3. Conversión Android / Capacitor
No alterar configuración Android/Capacitor salvo que la tarea lo requiera.

### 4. AdMob
No tocar IDs, permisos o integración de anuncios salvo petición específica.

## Principios de trabajo para cambios visuales

### Si el usuario pide mejoras visuales:
- preferir cambios en **CSS**
- evitar tocar HTML/JS si el mismo resultado se puede lograr con CSS
- no duplicar barras, toolbars o capas visuales
- no dejar UI vieja y nueva activas al mismo tiempo

### En eliminatorias:
- cualquier mejora visual debe ser primero **cosmética**
- no romper los contenedores del bracket
- no mezclar dos sistemas de botones al mismo tiempo
- si se cambia la barra de simulación, debe existir **una sola fuente de verdad**

## Flujo funcional que debe conservarse

### Fase de grupos
- 12 grupos: A–L
- 4 selecciones por grupo
- edición manual de resultados
- simulación automática de grupo
- reinicio de grupo
- tabla dinámica con PJ, G, E, P, GF, GC, DG, PTS
- clasificación de:
  - 2 primeros
  - mejores terceros

### Desempates
Debe respetarse la lógica ya acordada por el dueño del proyecto:
- enfrentamiento directo como parte importante del reglamento
- fair play / tarjetas no se usan si no están implementadas

### Eliminatorias
- 16vos → 8vos → 4tos → semifinal → final
- en **modo simple** se elige clasificado
- en **modo normal** se usan:
  - 90 minutos
  - tiempo extra si empatan
  - penales si siguen empatados

### Regla importante de UX
Un botón de simulación de ronda **no debe estar disponible** si la ronda previa no está lista.

Ejemplo:
- no debe simular final si no se ha resuelto antes el flujo previo
- si se borra o reinicia una ronda anterior, debe invalidarse el downstream

## Exportación / compartir

La app ya tiene exportación de imagen con `html2canvas`.

Al tocar exportación o compartir:

- no romper captura de banderas
- no romper layout del campeón
- no romper la limpieza visual de la imagen final
- si se agrega texto para compartir, debe verse confiable y natural

## Android / producción

La app ya fue:

- convertida con Capacitor
- probada en Android Studio
- empaquetada como APK
- empaquetada como AAB firmado
- subida a Google Play Console

Por lo tanto:

- no introducir cambios que rompan la versión móvil
- toda mejora debe pensarse también para pantallas Android reales
- cuidar rendimiento, scroll horizontal y sticky bars

## Reglas para Codex al modificar este repositorio

1. **No reescribas `index.html` completo** salvo que el usuario lo pida.
2. Haz cambios pequeños y localizados.
3. Si un bloque ya funciona, no lo refactors “por limpieza”.
4. Antes de tocar eliminatorias, identifica si el cambio es:
   - visual
   - lógico
   - o mezcla de ambos
5. No dejes código viejo y código nuevo duplicados para la misma UI.
6. Si cambias una barra o toolbar, elimina la versión antigua correspondiente.
7. Si cambias una condición de bloqueo/desbloqueo, revisa:
   - render visual
   - handlers de click
   - función real que ejecuta la simulación
8. Si introduces un estado nuevo, asegúrate de que tenga una sola fuente de verdad.
9. Si algo falla, prioriza volver a un estado estable antes que añadir más capas.
10. Mantén compatibilidad con móvil como prioridad alta.

## Estrategia recomendada para cualquier tarea

### Orden correcto:
1. entender si el pedido es visual o lógico
2. localizar el bloque exacto
3. cambiar lo mínimo posible
4. validar que no se rompa:
   - grupos
   - eliminatorias
   - modo simple
   - modo normal
   - exportación
   - móvil

## Qué tipo de ayuda espera el usuario

El usuario suele trabajar mejor con:

- un diagnóstico claro
- una explicación breve de qué falló
- luego cambios concretos tipo:
  - “reemplaza esto”
  - “por esto”

No le sirve una respuesta abstracta o demasiado teórica.

## Resumen corto para cualquier agente

Este proyecto es una app estática de simulación del Mundial 2026 que ya funciona.  
Debe modificarse con cuidado extremo, sin reescribir desde cero, y con prioridad en mantener estable la fase de grupos, las llaves, el modo simple/normal, la exportación de imagen y la experiencia Android.

Si dudas entre:
- hacer un cambio grande elegante
- o un cambio pequeño seguro

elige el **cambio pequeño seguro**.
