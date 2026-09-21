---
tags: [PAS, sistema, arquitectura]
up: "[[PAS - Índice]]"
---

# Resumen del sistema

← [[PAS - Índice]]

## Regla de diseño no negociable

**Actualizar un equipo debe tomar menos de 15 segundos.** Toda decisión de UI se subordina a esto: la tabla de "Actualizar Equipos" precarga la última condición conocida (copiar del turno anterior) y el Jefe de Turno sólo toca lo que cambió.

## Stack técnico

| Capa | Tecnología |
|---|---|
| Frontend | Streamlit (multipágina) |
| Backend / datos | SQLite (aislado en `core/database.py` para migrar después) |
| Análisis | Pandas |
| Gráficos | Plotly (Streamlit) + `reportlab.graphics` (PDF) |
| PDF | ReportLab |
| Reglas | YAML (`config/rules.yaml`, `config/process_lines.yaml`) — editable sin tocar código |

## Páginas de la app

1. **Resumen PAS** — KPIs generales, condición por planta (tarjetas de calor), distribución de criticidad, tendencia
2. **Actualizar Equipos** — la página de uso diario del Jefe de Turno; guardado en <15s/equipo; botón "Cerrar turno"
3. **Mapa de Calor** — filtros (planta, área, turno, fecha, estado, criticidad), drill-down por área, redundancia, línea de proceso
4. **Historial** — línea de tiempo por equipo, indicadores de confiabilidad (reincidencias, tiempo fuera de servicio)
5. **Informes** — PDF por área / consolidado PAS / semanal comparativo
6. **Administración** — control de calidad, reglas de redundancia, cierres de turno, auditoría

## Modelo de datos

- **`equipos`** — catálogo maestro, 1 fila por equipo (163 registros)
- **`evaluaciones`** — histórico *append-only* por turno; nunca se sobreescribe ni se borra
- **`cierres_turno`** — snapshot agregado al cerrar turno (cobertura, críticos, pendientes)
- **`auditoria`** — quién cambió qué, cuándo, valor anterior/nuevo

Ver detalle completo de campos en el `README.md` del repo — [[PAS - Despliegue]].

## Principio transversal

> [!warning] No inventar
> Nunca se corrige un dato automáticamente ni se asume un criterio operacional sin evidencia. Cuando no hay certeza, el sistema muestra **"Pendiente de validación"** en vez de clasificar. Ver [[PAS - Decisiones de Diseño]] y [[PAS - Reglas de Redundancia]].

## Notas relacionadas

- [[PAS - Decisiones de Diseño]]
- [[PAS - Reglas de Redundancia]]
- [[PAS - Despliegue]]
