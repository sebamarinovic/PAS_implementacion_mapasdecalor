---
name: pas-obsidian-sync
description: >
  Exporta el estado actual del proyecto PAS (decisiones tomadas, reglas de
  redundancia validadas/pendientes, hallazgos de los documentos de ingeniería,
  despliegue, pendientes, contactos) a un set de notas en formato Obsidian
  (frontmatter YAML + [[wikilinks]] + callouts) listas para copiar a un vault
  local. Úsala siempre que el usuario mencione Obsidian, "vault", "notas del
  proyecto", "documentar esto en mis notas", "alimentar nuestro proyecto" o
  pida dejar un registro navegable del avance de PAS — incluso si no dice la
  palabra "Obsidian" explícitamente pero describe el mismo patrón (notas
  enlazadas, frontmatter, un índice central). También aplica cuando pide
  "actualizar" las notas después de haber generado un set anteriormente.
---

# Sincronizar PAS con Obsidian

## Por qué existe esta skill

Claude no tiene acceso al vault de Obsidian del usuario — vive en su
computador. Esta skill no puede "escribir directamente en Obsidian"; lo que
sí puede es generar el mismo set de notas, bien estructurado, cada vez que
se le pida, para que el usuario las arrastre a su vault. Por eso cada nota
debe quedar completa y autocontenida en cada ejecución (no un diff): el
usuario decide si reemplaza sus archivos o combina a mano.

## Qué hacer al invocarse

1. **Reunir el estado actual del proyecto** leyendo lo que haga falta:
   - `config/rules.yaml` y `config/process_lines.yaml` del repo (grupos de
     redundancia, validado/pendiente, citas de fuente)
   - `README.md` (decisiones de diseño documentadas)
   - El historial de la conversación: qué se decidió, qué documentos llegaron,
     qué se desplegó, qué quedó pendiente, quién es cada persona mencionada
   - Si algo cambió desde el último export (nuevas validaciones, nuevos
     documentos, nuevo estado de despliegue), reflejarlo — estas notas son
     una fotografía del estado más reciente, no un archivo histórico inmutable.

2. **Generar los archivos** en `<scratchpad>/obsidian/<carpeta-del-proyecto>/`
   (nunca dentro del repo de código — son notas personales, no parte de la
   app). Reutilizar los nombres de archivo ya establecidos si es una
   actualización, para que al arrastrarlos al vault reemplacen las notas
   existentes en vez de duplicarlas:
   - `<Proyecto> - Índice.md` (mapa de contenido / MOC)
   - `<Proyecto> - Resumen del Sistema.md`
   - `<Proyecto> - Decisiones de Diseño.md`
   - `<Proyecto> - Reglas de Redundancia.md` (o el equivalente temático del proyecto)
   - `<Proyecto> - Documentos de Ingeniería.md` (fuentes y citas textuales)
   - `<Proyecto> - Despliegue.md`
   - `<Proyecto> - Pendientes.md`
   - `<Proyecto> - Contactos.md`

   Ajustar esta lista al contenido real disponible — no crear una nota vacía
   sólo por completar la lista. Si aparece un tema nuevo que no encaja en
   ninguna (por ejemplo, presupuesto o cronograma), es preferible una nota
   temática nueva bien enlazada que forzarlo dentro de una existente.

3. **Empaquetar y entregar**: comprimir la carpeta en un `.zip` y enviarla
   con la herramienta de entrega de archivos, con una instrucción breve de
   dónde debe dejarlas el usuario (arrastrar la carpeta a su vault).

## Convenciones de formato (seguir en cada nota)

- **Frontmatter YAML** al inicio: `tags`, `up: "[[Nota Índice]]"` y cualquier
  metadato útil para filtrar/buscar en Obsidian (fecha, estado, fuente).
- **Wikilinks `[[Nota]]`** entre notas relacionadas, no URLs ni rutas de
  archivo — es lo que hace que Obsidian dibuje el grafo de conexiones. Cerrar
  cada nota con una sección "## Notas relacionadas" listando sus enlaces.
- **Un índice central** (`- Índice.md`) que enlaza a todas las demás y
  resume el estado con una lista de tareas (`- [x]` / `- [ ]`) — es lo
  primero que el usuario va a abrir.
- **Callouts** (`> [!info]`, `> [!warning]`, `> [!danger]`, `> [!tip]`,
  `> [!caution]`) para destacar lo que importa a primera vista: riesgos de
  seguridad, cosas no confirmadas, principios de gobernanza del proyecto.
- **Tablas** para comparar entidades (grupos de redundancia, documentos,
  contactos) — se leen mucho más rápido que listas largas.
- **Checkboxes** (`- [ ]` / `- [x]`) para cualquier cosa pendiente o que ya
  se resolvió, sobre todo en la nota de Pendientes.

## Principio heredado del proyecto: no inventar, citar la fuente

Igual que el resto del trabajo en PAS, estas notas no deben presentar como
confirmado algo que no lo está. Cuando un dato viene de un documento de
ingeniería, cita el documento y (si existe) la frase textual. Cuando algo
sigue sin confirmar, dejarlo explícitamente en la nota de Pendientes en vez
de omitirlo o suavizarlo. El valor de estas notas es que alguien pueda
confiar en ellas sin tener que releer toda la conversación.

## Ejemplo de referencia

El primer set de notas generado para este proyecto (2026-09-21) está en
`docs/ejemplo-obsidian/` dentro de este mismo directorio de skill — úsalo
como plantilla de tono, extensión y estructura para los próximos exports,
en vez de empezar desde cero cada vez.
