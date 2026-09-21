---
tags: [PAS, despliegue, repo, acceso]
up: "[[PAS - Índice]]"
---

# Despliegue y acceso

← [[PAS - Índice]]

## Repositorio

- **URL:** `github.com/sebamarinovic/PAS_implementacion_mapasdecalor` (privado)
- **Rama de desarrollo:** `claude/pas-operational-heatmap-00f66p` (todo el código vive aquí)
- **`main`:** rama base casi vacía, creada sólo para poder abrir el Pull Request
- **Pull Request:** #1, abierto, pendiente de mergear a `main`

### Ejecutar localmente

```bash
git clone https://github.com/sebamarinovic/PAS_implementacion_mapasdecalor.git
cd PAS_implementacion_mapasdecalor
git checkout claude/pas-operational-heatmap-00f66p
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue de revisión (Streamlit Community Cloud)

- **URL:** https://pasimplementacionmapasdecalor-nr5zhhxrxsnq9ussyv9kaq.streamlit.app/
- **Branch desplegada:** `claude/pas-operational-heatmap-00f66p`
- **Acceso:** restringido por correo (repo privado → app privada por defecto). Invitados vía Settings → Sharing en share.streamlit.io.
- **Correos invitados:** lpare004@codelco.cl, garay028@codelco.cl, criva006@codelco.cl

> [!danger] Decisión de riesgo aceptada — app pública (2026-09-21)
> El toggle "Make this app public" quedó **encendido a propósito**. Motivo: el modo restringido de Streamlit Cloud exige que cada invitado inicie sesión (Google/GitHub/email con link mágico), y las políticas de seguridad de Codelco bloquean ese tipo de login externo con el correo corporativo — los 3 invitados no lograban entrar. Sebastián evaluó el riesgo (datos operacionales reales expuestos a cualquiera con la URL) y decidió mantenerlo público para no bloquear la revisión de jefatura. Alternativa evaluada y descartada por ahora: agregar contraseña propia dentro de la app vía `st.secrets` (no requeriría login externo). Revisar si Streamlit Cloud ofrece una opción "público pero no listado/buscable" como punto medio.

> [!warning] Datos no persistentes en este despliegue
> Streamlit Community Cloud reinicia el sistema de archivos al dormir por inactividad o redesplegar. Sirve para **revisión/demo**, no reemplaza correr la app localmente (o en infraestructura definitiva) para uso operacional real turno a turno.

## Ruta a infraestructura definitiva

Pendiente evaluar con TI/Ciberseguridad antes de escalar más allá del piloto de revisión:

- Servidor interno Codelco, o
- Nube corporativa aprobada

Y migrar la base de datos de SQLite (piloto) a SharePoint/Microsoft Lists, SQL Server o API corporativa — la capa de datos ya está aislada en `core/database.py` para ese fin, sin necesidad de rediseñar la app.

## Correo a jefatura

Redactado 2026-09-21, para lpare004@codelco.cl, garay028@codelco.cl, criva006@codelco.cl. Cubre: qué se hizo, cómo escala (señales PI System, actualización diaria por responsables, migración de base de datos), y la nota de acceso fuera de red Codelco. **Bloqueado el envío automático por el clasificador de Claude Code** (acción hacia correo corporativo externo) — quedó como texto para copiar/pegar manualmente, no como borrador en Gmail.

## Notas relacionadas

- [[PAS - Resumen del Sistema]]
- [[PAS - Pendientes]]
- [[PAS - Contactos]]
