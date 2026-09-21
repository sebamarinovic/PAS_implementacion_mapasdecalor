---
tags: [PAS, decisiones, gobernanza-de-datos]
up: "[[PAS - Índice]]"
---

# Decisiones de diseño (y por qué)

← [[PAS - Índice]]

Cada una de estas decisiones se tomó de forma explícita y documentada, siguiendo la instrucción de "no inventar reglas operacionales". Fuente completa: `README.md` del repo.

1. **Catálogos = los reales de la base**, no los sugeridos literalmente en el encargo original (p. ej. "Buena/Regular/Mala" en vez de "Bueno/Malo") para no romper compatibilidad con los 163 registros ya levantados.

2. **Los 10 grupos de redundancia partieron con `validado: false`**. Ver detalle completo en [[PAS - Reglas de Redundancia]]. Actualización 2026-09-11: 3 de 10 ya se validaron con documentos de ingeniería reales.

3. **Las evaluaciones del levantamiento inicial conservan la Criticidad/Prioridad ya calculadas** por Paredes/Avendaño (no se recalculan con el motor de reglas nuevo). Las evaluaciones nuevas (desde la app) sí usan `core/rules.classify_equipo()`.

4. **"Cerrar turno" registra un snapshot agregado** (cobertura, críticos, pendientes), no una copia de las 163 evaluaciones — igual que `PAS_CierresTurno` en el diseño SharePoint original.

5. **Horario de cambio Día/Noche** (08:00 y 20:00) es una constante ajustable en `core/utils.py`: el archivo fuente no confirma el horario exacto, sólo los nombres "Día"/"Noche".

6. **Código de turno/cuadrilla** (A/B/C/D) es un catálogo provisional editable: la hoja de diseño original advierte que esa nomenclatura no está confirmada por Operaciones.

7. **Línea de proceso** ([[PAS - Línea de Proceso y Enfriamiento]]): GCP-2→CAP-3 y GCP-4→CAP-4 confirmadas por Sebastián. El enfriamiento cruzado entre torres quedó **confirmado documentalmente el 2026-09-11** — ver [[PAS - Documentos de Ingeniería]].

> [!tip] Criterio general
> Cuando una decisión es puramente operacional y no hay certeza (ej. el mínimo exacto de bombas requeridas en un grupo), el sistema la deja **"Pendiente de validación"** en vez de asumir un valor. Ver [[PAS - Pendientes]] para la lista viva de lo que falta confirmar.

## Notas relacionadas

- [[PAS - Reglas de Redundancia]]
- [[PAS - Pendientes]]
