# Instrucciones de ejecución (simples)

## 1. Instalar Python

Se necesita Python 3.10 o superior. Verificar con:

```
python3 --version
```

Si no está instalado, descargarlo desde https://www.python.org/downloads/

## 2. Instalar dependencias

Abrir una terminal en la carpeta del proyecto y ejecutar:

```
pip install -r requirements.txt
```

## 3. (Sólo la primera vez) Cargar los datos iniciales

La base `data/pas.db` ya viene incluida con los 163 equipos y sus
evaluaciones iniciales. Si necesitas regenerarla desde el Excel fuente:

```
python import_initial_data.py
```

## 4. Ejecutar la aplicación

```
streamlit run app.py
```

Se abrirá automáticamente en el navegador (por defecto en
http://localhost:8501). Si no se abre solo, copiar esa dirección en el
navegador.

## 5. Uso básico durante un turno

1. En la barra lateral, escribir el nombre del Jefe de Turno / Operador.
2. Ir a **Actualizar Equipos**, elegir Planta y Área.
3. La tabla ya viene precargada con la última condición conocida
   (turno anterior): sólo modificar lo que cambió.
4. Presionar **GUARDAR ACTUALIZACIÓN DEL TURNO**.
5. Al finalizar el turno, abrir el desplegable **"Cerrar turno"** al pie
   de la misma página y presionar **Cerrar turno ahora**.

## 6. Generar un informe PDF

Ir a **Informes**, elegir el tipo (por área, consolidado o semanal) y
presionar **Generar PDF**. El archivo queda además guardado en la
carpeta `reports/`.

## Cerrar y volver a abrir la aplicación

Los datos quedan guardados en `data/pas.db`. Puedes cerrar la terminal y
volver a ejecutar `streamlit run app.py` en cualquier momento: toda la
información (equipos, evaluaciones, historial, cierres de turno)
seguirá disponible.
