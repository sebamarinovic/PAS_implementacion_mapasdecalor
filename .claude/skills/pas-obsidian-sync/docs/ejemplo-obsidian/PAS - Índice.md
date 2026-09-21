---
tags: [PAS, Codelco, MOC, proyecto]
proyecto: PAS - Levantamiento Operacional y Mapa de Calor
division: Chuquicamata
fecha_creacion: 2026-09-11
ultima_actualizacion: 2026-09-21
estado: piloto-en-revision
---

# PAS — Levantamiento Operacional y Mapa de Calor

> [!info] Qué es esto
> Sistema web (Streamlit + SQLite) para que los Jefes de Turno actualicen el estado operacional de los ~163 equipos de las Plantas de Ácido y Oxígeno de Chuquicamata en menos de 15 segundos por equipo, y generen automáticamente mapa de calor, análisis de redundancia, historial e informes PDF.

Nace del levantamiento en terreno de [[PAS - Contactos#Leonardo Paredes|Leonardo Paredes]] (Jefe de Turno) y [[PAS - Contactos#Eleazar Avendaño|Eleazar Avendaño]] (Operador Consola), por encargo de [[PAS - Contactos#Cristián Rivas|Cristián Rivas]] (Superintendente).

## Mapa de notas

- [[PAS - Resumen del Sistema]] — qué se construyó, arquitectura, funcionalidades
- [[PAS - Decisiones de Diseño]] — decisiones técnicas/operacionales documentadas, una por una
- [[PAS - Reglas de Redundancia]] — los 10 grupos de redundancia, cuáles están validados y con qué evidencia
- [[PAS - Línea de Proceso y Enfriamiento]] — topología GCP↔CAP y enfriamiento cruzado entre torres
- [[PAS - Documentos de Ingeniería]] — fuentes documentales recibidas y qué confirmó cada una
- [[PAS - Despliegue]] — repo, rama, URL pública de revisión, accesos
- [[PAS - Pendientes]] — qué falta confirmar/resolver, y quién debe hacerlo
- [[PAS - Contactos]] — personas involucradas

## Estado actual (2026-09-21)

- [x] MVP funcional: Resumen, Actualizar Equipos, Mapa de Calor, Historial, Informes, Administración
- [x] Importación del levantamiento original (163 equipos) sin pérdida de datos
- [x] 3 de 10 grupos de redundancia validados con documentos de ingeniería reales
- [x] Desplegado en Streamlit Community Cloud para revisión de jefatura (acceso restringido)
- [ ] Correo formal a jefatura con resumen y ruta de escalamiento — redactado, pendiente de envío manual
- [ ] Confirmar mínimo exacto de bombas P-101 (GCP) — ver [[PAS - Pendientes]]
- [ ] Sanear TAG duplicado `5327-BHZ-402` (CAP4-BHZ) — ver [[PAS - Pendientes]]
- [ ] Evaluar con TI/Ciberseguridad la infraestructura definitiva antes de escalar más allá del piloto

## Repositorio

`github.com/sebamarinovic/PAS_implementacion_mapasdecalor` (privado), rama `claude/pas-operational-heatmap-00f66p`. Detalle en [[PAS - Despliegue]].
