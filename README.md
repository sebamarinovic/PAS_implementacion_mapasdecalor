# PAS — Levantamiento Operacional y Mapa de Calor

Sistema operacional para las Plantas de Ácido y Oxígeno (PAS) de la
División Chuquicamata: GCP-2, GCP-4, CAP-3, CAP-4 y Circuito de Aguas.

Nace del levantamiento en terreno de **Leonardo Paredes** (Jefe de Turno) y
**Eleazar Avendaño** (Operador Consola), y responde al encargo del
Superintendente **Cristián Rivas** de transformarlo en un estándar
operacional vivo, con mapa de calor de vulnerabilidades por planta.

Regla de diseño no negociable: **actualizar un equipo debe tomar menos de
15 segundos.**

## Qué hace

- Registra el estado de los ~163 equipos de las 5 plantas por turno.
- Calcula automáticamente disponibilidad, criticidad y prioridad.
- Muestra un mapa de calor por planta y por área/sistema.
- Evalúa redundancia por grupo (bombas principal/spare, etc.).
- Mantiene historial completo (append-only, nunca se borra ni sobreescribe).
- Genera informes PDF por área, consolidado PAS y semanal comparativo, con
  gráficos (torta de criticidad, barras de disponibilidad).
- Detecta problemas de calidad de datos (TAG duplicados, contradicciones,
  valores fuera de catálogo, etc.) sin corregirlos automáticamente.
- Muestra la línea de proceso entre plantas (GCP-2→CAP-3, GCP-4→CAP-4) y
  el enfriamiento cruzado entre torres (pendiente de confirmación).

## Arquitectura

```
app.py                     -> entrada Streamlit (redirige a Resumen PAS)
pages/
  1_Resumen_PAS.py          KPIs generales + condición por planta
  2_Actualizar_Equipos.py   actualización rápida por turno (<15s por equipo)
  3_Mapa_de_Calor.py        mapa de calor con filtros y drill-down por área
  4_Historial.py            línea de tiempo y confiabilidad por equipo
  5_Informes.py             PDF por área / consolidado / semanal
  6_Administracion.py       control de calidad, reglas, cierres, auditoría
core/
  database.py       acceso SQLite (única capa que sabe SQL)
  rules.py          motor de reglas (config/rules.yaml)
  analytics.py      KPIs, mapa de calor, comparación de periodos
  validators.py     control de calidad (sección 14)
  reports.py        generación de PDF (ReportLab: KPIs, heatmap, gráficos)
  pi_connector.py   interfaz preparada para PI System (aún no conectado)
  process_lines.py  línea de proceso entre plantas (config/process_lines.yaml)
  session.py        conexión cacheada + widgets compartidos (Streamlit)
  ui_resumen.py     contenido de la página Resumen (compartido con app.py)
  ui_charts.py      tarjetas de mapa de calor y gráficos Plotly compartidos
  utils.py          turnos, colores, helpers
config/
  catalogs.yaml       valores controlados (estado, disponibilidad, etc.)
  rules.yaml          grupos de redundancia y clasificación de criticidad
  process_lines.yaml  líneas de proceso y enfriamiento cruzado (ver decisión 7)
data/
  pas.db            base SQLite (se crea/actualiza con import_initial_data.py)
  source/           Excel(es) fuente del levantamiento original
reports/            PDFs generados (no versionar los que generes tú)
import_initial_data.py  importación inicial desde el Excel fuente
```

La capa de datos está aislada en `core/database.py` a propósito: el día
que SQLite se reemplace por SharePoint/Microsoft Lists, SQL Server, una
API corporativa, PI System o SAP, sólo ese archivo debería cambiar. El
resto de la aplicación (páginas, reglas, analítica, informes) no sabe ni
le importa dónde viven los datos.

## Modelo de datos

**`equipos`** (catálogo maestro, 1 fila por equipo): `equipment_id`,
`legacy_id`, `planta`, `area_sistema`, `tag`, `tipo_elemento`,
`descripcion`, `grupo_redundancia`, `rol_grupo`, `regla_grupo`, `activo`,
`requiere_validacion`, `observacion_calidad`, `fuente_origen`,
`pi_tag`/`pi_variable`/`pi_unidad`/`pi_disponible`/`pi_validado` (para la
futura integración PI System).

**`evaluaciones`** (histórico *append-only*, 1 fila por actualización):
`evaluation_id`, `equipment_id`, `fecha_hora`, `tipo_turno`,
`codigo_turno`, `usuario`, `estado`, `disponibilidad`, `modo_operacion`,
`criticidad`, `prioridad` (calculadas, no editables a mano), `hallazgo`,
`aviso_sap`, `ot`, `evidencia`, `comentario`, `rule_version`,
`estado_dato` (`OK` / `Contradictorio` / `Pendiente` / `Falta responsable`).

**`cierres_turno`**: snapshot de cobertura/críticos/pendientes al cerrar
un turno (equivalente a `PAS_CierresTurno` del diseño SharePoint original).

**`auditoria`**: quién cambió qué, cuándo y con qué valor anterior/nuevo.

Un equipo puede tener N evaluaciones; nunca se hace `UPDATE`/`DELETE`
sobre evaluaciones ya guardadas.

## Decisiones tomadas (y por qué)

Siguiendo la instrucción de "no inventar reglas operacionales", estas
decisiones se documentan explícitamente en vez de dejarlas implícitas:

1. **Catálogos = los reales de la base**, no los sugeridos literalmente en
   el prompt (p. ej. "Buena/Regular/Mala" en vez de "Bueno/Malo") para no
   romper compatibilidad con los 163 registros ya levantados.
2. **Los 10 grupos de redundancia partieron con `validado: false`** en
   `config/rules.yaml`. La propia base original define una Fase 0 de
   "Saneamiento" antes de usar estas reglas para clasificar
   automáticamente, y varias reglas en texto libre (p. ej. "al menos un
   respaldo real") no traen un mínimo numérico exacto. Mientras no se
   validen, el sistema **muestra el conteo real pero no clasifica
   "Sin respaldo"** — evita inventar un criterio operacional.
   **Actualización 2026-09-11**: con documentos de ingeniería reales
   aportados por Sebastián (Manual DCDA, SP916744-53200-48EC-S0001 rev.2,
   SP916744-53203/53204-48ER-S0002/S0003 rev.2) se validaron 3 de los 10
   grupos (`CAP3-BHZ`, `AGUAS-BOC-901`, `AGUAS-BOC-904`) con citas
   textuales exactas en `fuente_validacion`. `CAP4-BHZ` sigue pendiente
   pese a que la regla ya está confirmada por diseño, porque su TAG
   `5327-BHZ-402` sigue duplicado con datos contradictorios — validar la
   regla no soluciona un dato ambiguo. Los grupos GCP2/GCP4-P101/P102/P110
   siguen pendientes: la nomenclatura de subtrenes (GCP-2A/2B, GCP-4A/4B)
   quedó confirmada, pero ningún documento recibido especifica el mínimo
   numérico exacto de bombas P-101 por subtren.
3. **Las evaluaciones del levantamiento inicial conservan la
   Criticidad/Prioridad ya calculadas por Paredes/Avendaño** (no se
   recalculan con el motor de reglas nuevo), para no reescribir un juicio
   experto ya hecho. Las evaluaciones nuevas (desde la app) sí usan
   `core/rules.classify_equipo()`.
4. **"Cerrar turno" registra un snapshot agregado** (cobertura, críticos,
   pendientes), no una copia de las 163 evaluaciones — igual que
   `PAS_CierresTurno` en el diseño original.
5. **Horario de cambio Día/Noche** (08:00 y 20:00 en `core/utils.py`) es
   una constante fácilmente ajustable: el archivo fuente no confirma el
   horario exacto, sólo los nombres "Día"/"Noche".
6. **Código de turno/cuadrilla** (A/B/C/D) se deja como catálogo
   provisional editable en `config/catalogs.yaml`: la hoja de diseño
   original advierte explícitamente que esa nomenclatura no está
   confirmada por Operaciones.
7. **Línea de proceso** (`config/process_lines.yaml`): GCP-2→CAP-3 y
   GCP-4→CAP-4 vienen confirmadas directamente por Sebastián. El
   **enfriamiento cruzado** entre torres (Torre Enf. 2/3 → CAP-4, Torre
   Enf. 4 → CAP-3) quedó **confirmado el 2026-09-11** por
   SP916744-53200-48EC-S0001 rev.2 (malla de shutdown SHUT1/SHUT2/SHUT3):
   las bombas BOC-901/902/903 son "Cold Well Pump - CW Tower 4" y las
   BOC-904/905/906 "CW Tower 2", y una planta de ácido sólo para si las 3
   bombas de su torre fallan simultáneamente por más de 180 segundos (con
   1 o 2 disponibles sigue operando normalmente). También se confirmó
   (interlock I-9) que las bombas de agua desmineralizada BHZ-305/BHZ-405
   tienen respaldo automático vía una bomba común (BHZ-001): si la
   dedicada de una planta se detiene, la común arranca sola y la planta
   no necesita pararse. Lo único que sigue sin confirmar documentalmente
   es el mínimo exacto de bombas P-101 (GCP) por subtren — ver punto 2.

Cuando una decisión es puramente operacional y no hay certeza (p. ej. el
mínimo exacto de bombas requeridas en un grupo), el sistema la deja
**"Pendiente de validación"** en vez de asumir un valor.

## Integraciones futuras

- **SharePoint / Microsoft Lists / SQL Server / API corporativa**:
  reemplazar `core/database.py` manteniendo las mismas firmas de función.
- **PI System**: `core/pi_connector.py` ya define la interfaz
  (`PIConnector.get_valor_actual`, `get_estado_operacional`) y los campos
  `pi_tag`/`pi_variable`/`pi_unidad` ya existen en `equipos`. No hay
  credenciales configuradas todavía, así que no se conecta a nada real.
- **SAP**: el campo `aviso_sap` ya se registra por evaluación; falta el
  conector cuando haya acceso a la API de SAP.

## Ejecución

Ver `INSTRUCCIONES_EJECUCION.md`.

## Reimportar o actualizar el catálogo maestro

```
python import_initial_data.py [ruta_a_otro_excel.xlsx]
```

Es idempotente: el catálogo se actualiza (upsert) y las evaluaciones
iniciales no se duplican si el script se vuelve a ejecutar.
