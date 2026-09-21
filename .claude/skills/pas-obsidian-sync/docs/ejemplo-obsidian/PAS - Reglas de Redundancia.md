---
tags: [PAS, redundancia, reglas, validacion]
up: "[[PAS - Índice]]"
fuente: config/rules.yaml
rule_version: 1.1.0-parcialmente-validado
---

# Reglas de redundancia

← [[PAS - Índice]] · Fuente viva: `config/rules.yaml` en el repo (editable sin tocar código)

> [!info] Principio
> Mientras un grupo esté `validado: false`, el sistema muestra el conteo real de equipos disponibles pero **no** lo clasifica como "Sin respaldo" — evita inventar un criterio operacional. Ver [[PAS - Documentos de Ingeniería]] para la evidencia detrás de cada validación.

## ✅ Validados (3 de 10) — 2026-09-11

### CAP3-BHZ
- **Planta:** CAP3 · Balance ácido
- **Regla:** "Una operativa y una reserva verificable" → `minimo_disponible = 2`
- **Evidencia:** Manual DCDA, Tabla 6.2-20 — cita textual: *"5327-BHZ-301A/302A... una bomba en operación y la otra bomba en espera"*
- Significa: ambas (1 operando + 1 en espera) deben estar disponibles para "Con respaldo".

### AGUAS-BOC-901 → Torre de Enfriamiento 4
- **Planta:** Circuito de aguas · Agua torre/desmineralizada
- **Regla:** "Mínimo dos disponibles; cadena de descarga completa" → `minimo_disponible = 2`
- **Evidencia:** SP916744-53200-48EC-S0001 rev.2, §13 (malla SHUT1/SHUT2/SHUT3) + diagrama "SHUTDOWN GRID": BOC-901/902/903 = *"Cold Well Pump - CW Tower 4"*. Trip real sólo si las 3 bombas caen simultáneamente >180s; 1 bomba en trip = sólo alarma.
- ⚠️ Alerta de calidad de dato independiente: BOC901 tiene Estado/Disponibilidad contradictorios (control de calidad #17).

### AGUAS-BOC-904 → Torre de Enfriamiento 2/3
- Igual que AGUAS-BOC-901. **Evidencia:** BOC-904/905/906 = *"Cold Well Pump - CW Tower 2"* en el mismo documento.

## ⏳ Pendientes (7 de 10)

| Grupo | Planta | Regla original | Por qué sigue pendiente |
|---|---|---|---|
| GCP2-P101 | GCP2 | Parejas A-B y C-D; al menos 1 respaldo real | Subtrenes GCP-2A/2B confirmados por doc. de ingeniería, pero sin mínimo numérico de bombas P-101. **Crítico funcional**: enfrían la totalidad de gases de entrada. |
| GCP4-P101 | GCP4 | Ídem | Análogo a GCP2-P101. **Crítico funcional.** |
| GCP2-P102 | GCP2 | Parejas A-B y C-D | TAG duplicado `P102C(II)` con datos distintos (control de calidad #3) |
| GCP4-P102 | GCP4 | Parejas A-B y C-D | Análogo a GCP2-P102 |
| GCP2-P110 | GCP2 | Grupos A-B-C y D-E-F; evitar operar con sólo 1 de 3 | Sugiere mínimo 2 de cada trío, sin confirmar |
| GCP4-P110 | GCP4 | Ídem | Análogo a GCP2-P110 |
| **CAP4-BHZ** | CAP4 | Una operativa y una reserva verificable | **La regla YA está confirmada** (gemela de CAP3-BHZ, mismo proyecto EPC) — bloqueada sólo por el TAG duplicado `5327-BHZ-402` con datos contradictorios. Ver [[PAS - Pendientes]]. |

## Notas relacionadas

- [[PAS - Documentos de Ingeniería]] — el detalle completo de cada cita
- [[PAS - Línea de Proceso y Enfriamiento]] — cómo se conectan AGUAS-BOC-901/904 con las torres
- [[PAS - Pendientes]]
