---
tags: [PAS, pendientes, TODO]
up: "[[PAS - Índice]]"
---

# Pendientes

← [[PAS - Índice]] · Lista viva — marcar `[x]` a medida que se resuelvan

## Requieren a Operaciones / Jefatura

- [ ] **Mínimo exacto de bombas P-101** por subtrén (GCP-2A/2B, GCP-4A/4B) y comportamiento del spare compartido. Ningún documento recibido lo especifica. → [[PAS - Reglas de Redundancia]]
- [ ] **Sanear TAG duplicado `5327-BHZ-402`** (CAP4-BHZ, control de calidad #10/#16). La regla ya está confirmada; sólo falta este dato para poder validar el grupo.
- [ ] **Confirmar discrepancia de TAG** `5320-BHZ-001` (catálogo) vs `5328-BHZ-001` (documentos de ingeniería) — probablemente el mismo activo.
- [ ] **Confirmar prefijo exacto** de los intercambiadores de la Torre de Enfriamiento 2/3 (INC-401/402/403/404) — sólo se confirmaron por analogía con CAP3.
- [ ] Confirmar si la bomba común `BHZ-001` puede cubrir **ambas plantas simultáneamente** si fallan las dos dedicadas a la vez.
- [ ] Sanear los otros hallazgos de control de calidad pendientes (duplicados, contradicciones) — ver página Administración de la app.

## Requieren decisión de gestión

- [ ] Mergear [[PAS - Despliegue|PR #1]] a `main`
- [ ] Enviar el correo a jefatura (texto ya redactado, bloqueado el envío automático)
- [ ] Evaluar con TI/Ciberseguridad la infraestructura definitiva antes de escalar el piloto
- [ ] Decidir si se activa la integración con PI System (requiere credenciales corporativas)
- [ ] Formalizar la rutina de "cierre de turno" diario por parte de los Jefes de Turno

## Verificaciones recurrentes

- [ ] Antes de cada envío de link de revisión: confirmar que "Make this app public" esté **apagado** en Streamlit Cloud

## Notas relacionadas

- [[PAS - Reglas de Redundancia]]
- [[PAS - Línea de Proceso y Enfriamiento]]
- [[PAS - Despliegue]]
