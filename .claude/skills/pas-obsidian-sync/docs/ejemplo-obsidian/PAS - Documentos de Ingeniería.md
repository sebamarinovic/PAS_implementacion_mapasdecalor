---
tags: [PAS, documentos, fuentes, ingenieria]
up: "[[PAS - Índice]]"
---

# Documentos de ingeniería recibidos

← [[PAS - Índice]] · Todos aportados por Sebastián el 2026-09-11

| # | Documento | Código | Qué confirmó |
|---|---|---|---|
| 1 | Manual DCDA | `4501661404-I-05320-0-MNLPR-0001` | Esquema 1 operando + 1 en espera para bombas BHZ-301/302 (Torre de Stripping de Ácido Producto); intercambiadores de agua de enfriamiento 5328-INC-301/302/303/304 (3-de-4, N+1); interlock I-9 (respaldo automático BHZ-305/405 ↔ BHZ-001) |
| 2 | Descripción del Control Lógico y Regulatorio | `SP916744-53200-48EC-S0001` rev.2 | Malla de shutdown SHUT1/SHUT2/SHUT3 (complejo completo); nomenclatura oficial de subtrenes GCP-2A/2B, GCP-4A/4B, GCP-5; diagrama "SHUTDOWN GRID" con la asignación exacta de bombas BOC-90x a cada torre de enfriamiento |
| 3 | Descripción de Enclavamientos Planta N°3 | `SP916744-53203-48ER-S0002` rev.2 | Interlock I-9 en detalle para CAP3 (respaldo automático de agua desmineralizada) |
| 4 | Descripción de Enclavamientos Planta N°4 | `SP916744-53204-48ER-S0003` rev.2 | Interlock I-9 en detalle para CAP4 |
| 5 | Diagrama de Plantas de Ácido Doble Contacto/Doble Absorción | — | Diagrama de proceso general (referencia visual) |

## Hallazgos clave extraídos

### 1. Malla de shutdown (SP916744-53200-48EC-S0001, §13)

> "Bombas Agua Torre de Enfriamiento: El grupo de señales corresponde al trip de cualquiera de las bombas que suministran el agua desde las torres de enfriamiento a los CAPs [...] 05316-BOC-901, 05316-BOC-902, 05316-BOC-903, 05316-BOC-904, 05316-BOC-905 y 05316-BOC-906."

> SHUT2/SHUT3: "se considera que las tres bombas que suministran de un CAP tienen estatus de trip y por un tiempo superior a 180 segundos."

### 2. Asignación torre ↔ bombas (diagrama "SHUTDOWN GRID")

> "05316-BOC-901 Trip (Cold Well Pump - CW1 - CW Tower 4)"
> "05316-BOC-904 Trip (Cold Well Pump - CW1 - CW Tower 2)"

→ Confirma exactamente lo que Sebastián había indicado de memoria: BOC-901/902/903 = Torre 4 (enfría CAP-3); BOC-904/905/906 = Torre 2/3 (enfría CAP-4).

### 3. Bombas de stripping (Manual DCDA, Tabla 6.2-20)

> "Bombas de la Torre de Stripping de Ácido Producto (5327-BHZ-301A/5327-BHZ-302A) [...] Se proporcionan dos bombas completas con motores: una bomba en operación y la otra bomba en espera."

### 4. Interlock I-9 — respaldo automático de agua desmineralizada (Manual DCDA §7.3)

> "Si la Bomba de Circulación de Agua de Enfriamiento se dispara (trip), el enclavamiento I-9 cierra su válvula de descarga (HV-25370) y hace funcionar la Bomba de Circulación del Agua de Enfriamiento Común."

### 5. Intercambiadores de agua de enfriamiento — N+1 (Manual DCDA §7.3)

> "Desde la descarga de la bomba, el agua fluye a través de 3 de 4 Intercambiadores de Calor de Agua de Enfriamiento (5328-INC-301/302/303/304), con un enfriador que actúa como un repuesto instalado."

## Notas relacionadas

- [[PAS - Reglas de Redundancia]]
- [[PAS - Línea de Proceso y Enfriamiento]]
