---
tags: [PAS, proceso, enfriamiento, GCP, CAP]
up: "[[PAS - Índice]]"
fuente: config/process_lines.yaml
---

# Línea de proceso y enfriamiento cruzado

← [[PAS - Índice]]

## Líneas de proceso (gas → ácido) — confirmadas por Sebastián

- **Línea 1:** GCP-2 → CAP-3
- **Línea 2:** GCP-4 → CAP-4

## Enfriamiento de gases de entrada (P-101) — crítico funcional

Bombas P-101: enfrían la **totalidad** de los gases de entrada de su planta. Pérdida total = crítico para toda la planta, no sólo el subtren.

| Planta | Subtren | TAGs |
|---|---|---|
| GCP2 | GCP-2A | P101A(II), P101B(II), P101S(II) |
| GCP2 | GCP-2B | P101C(II), P101D(II), P101S(II) |
| GCP4 | GCP-4A | P101A(IV), P101B(IV), P101S(IV) |
| GCP4 | GCP-4B | P101C(IV), P101D(IV), P101S(IV) |

Nomenclatura de subtrenes confirmada por `SP916744-53200-48EC-S0001` rev.2 §13.2 (además existe un **GCP-5** que no forma parte de PAS). El mínimo numérico exacto y el comportamiento del spare compartido siguen sin confirmar → [[PAS - Reglas de Redundancia#⏳ Pendientes (7 de 10)|pendiente]].

## Bombas de agua desmineralizada — respaldo automático confirmado ✅

Cada planta de ácido tiene una bomba dedicada respaldada por **una bomba común compartida** (`BHZ-001`), con arranque automático vía interlock **I-9**:

| Bomba dedicada | Enfría a | Respaldo común | Comportamiento confirmado |
|---|---|---|---|
| 5328-BHZ-305 | CAP3 | 5320-BHZ-001 (docs: 5328-BHZ-001) | Si se detiene → arranca la común automáticamente. **La planta NO se detiene.** |
| 5328-BHZ-405 | CAP4 | 5320-BHZ-001 (docs: 5328-BHZ-001) | Ídem |

> [!warning] Calidad de dato
> El catálogo maestro registra el respaldo como `5320-BHZ-001`; los documentos de ingeniería lo llaman consistentemente `5328-BHZ-001`. Es casi seguro el mismo activo con discrepancia de prefijo entre fuentes — no se corrigió automáticamente, debe confirmarlo Operaciones. Ver [[PAS - Pendientes]].

> [!caution] Límite no confirmado
> Si **ambas** bombas dedicadas (BHZ-305 y BHZ-405) fallaran a la vez, no está confirmado documentalmente que la bomba común tenga capacidad para cubrir a las dos plantas simultáneamente.

## Enfriamiento cruzado entre torres — confirmado ✅ (2026-09-11)

Cada torre enfría el sistema ácido/agua de la planta **contraria** a su numeración:

```
GCP-2 ──▶ CAP-3 ◀╌╌╌╌╌╌ Torre Enf. 4    (bombas BOC901/902/903)
GCP-4 ──▶ CAP-4 ◀╌╌╌╌╌╌ Torre Enf. 2/3  (bombas BOC904/905/906)
```

| Torre | Enfría a | Bombas | Grupo en rules.yaml | Intercambiadores |
|---|---|---|---|---|
| Torre de Enfriamiento 4 | CAP-3 | BOC901, BOC902, BOC903 | [[PAS - Reglas de Redundancia#AGUAS-BOC-901 → Torre de Enfriamiento 4|AGUAS-BOC-901]] ✅ | 5328-INC-301/302/303/304 (3-de-4, 1 spare instalado — N+1) |
| Torre de Enfriamiento 2/3 | CAP-4 | BOC904, BOC905, BOC906 | [[PAS - Reglas de Redundancia#AGUAS-BOC-904 → Torre de Enfriamiento 2/3|AGUAS-BOC-904]] ✅ | INC-401/402/403/404 (análogos; prefijo exacto de CAP4 no confirmado) |

### Consecuencia operacional confirmada — responde la pregunta original

- **1 bomba en trip** → sólo ALARMA (SHUT1). La planta sigue operando normal con las otras 2.
- **Las 3 bombas de una misma torre en trip por >180 segundos** → recién ahí ocurre el TRIP real (SHUT2/SHUT3) de esa planta.
- **Es decir: la planta NO para con 1 o 2 bombas fuera de servicio; sólo para si se pierden las 3 simultáneamente y de forma sostenida.**

## Notas relacionadas

- [[PAS - Reglas de Redundancia]]
- [[PAS - Documentos de Ingeniería]]
- [[PAS - Pendientes]]
