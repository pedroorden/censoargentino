# censoargentino

[![PyPI version](https://img.shields.io/pypi/v/censoargentino)](https://pypi.org/project/censoargentino/)
[![Python](https://img.shields.io/pypi/pyversions/censoargentino)](https://pypi.org/project/censoargentino/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Cliente Python para consultar el **Censo Nacional de Población, Hogares y Viviendas 2022** de Argentina (INDEC).

Usa [DuckDB](https://duckdb.org/) para hacer consultas directas sobre archivos Parquet remotos, descargando **solo los datos que necesitás** sin bajar el dataset completo (~137 MB).

---

## Instalación

```bash
pip install censoargentino
```

---

## Uso rápido

```python
import censoargentino as censo

# Tabla resumida con N y % — una sola línea
censo.tabla("PERSONA_P02")
#           categoria         N     %
# Mujer / Femenino     23607906  51.8
# Varón / Masculino    22010881  48.2

# Filtrado por provincia
censo.tabla("HOGAR_NBI_TOT", provincia="Chaco")

# Filtrado por departamento — por nombre o código INDEC
censo.tabla("HOGAR_NBI_TOT", provincia="Buenos Aires", departamento="Lanús")
censo.tabla("HOGAR_NBI_TOT", provincia="Buenos Aires", departamento="490")  # equivalente

# Comparación entre provincias
censo.comparar("HOGAR_NBI_TOT")
#               Con NBI  Sin NBI    Total
# Formosa          26.0     74.0   173500
# Chaco            24.9     75.1   393500
# ...

# Datos crudos (formato largo por radio censal)
df = censo.query(variables="PERSONA_P02", provincia="Córdoba")
```

---

## ¿De dónde vienen los datos?

Los datos corresponden a la **1ª entrega definitiva del CPV 2022** (publicada por INDEC en diciembre de 2024).

**Pipeline de procesamiento:**

```
INDEC (base REDATAM .rxdb)
        ↓
  redatamx (R)  →  extracción de variables
        ↓
  formato largo Parquet  →  censo-2022-largo.parquet
  metadatos Parquet      →  censo-2022-metadatos.parquet
  radios censales        →  radios-2022.parquet  (fuente: CONICET)
        ↓
  Hugging Face Datasets  →  pedroorden/censoargentino
        ↓
  censoargentino (este paquete)  →  consultas eficientes vía DuckDB
```

| Archivo | Tamaño | Contenido |
|---|---|---|
| `censo-2022-largo.parquet` | 137 MB | Variables × radios censales × conteos |
| `censo-2022-metadatos.parquet` | 1 MB | Catálogo de variables y categorías |

**Cobertura:** Vivienda · Hogar · Persona — desagregación hasta radio censal.

> La 2ª entrega (localidades y aglomerados) está prometida por INDEC sin fecha confirmada.

---

## Estructura del resultado

`query()` devuelve **formato largo pre-agregado**: cada fila es una combinación de *(radio censal × categoría × conteo)*.

```
id_geo     | codigo_variable | valor_categoria | etiqueta_categoria   | conteo | etiqueta_provincia | ...
460070101  | PERSONA_P02     | 1               | Mujer / Femenino     |    252 | La Rioja           | ...
460070101  | PERSONA_P02     | 2               | Varón / Masculino    |    231 | La Rioja           | ...
```

`tabla()` y `comparar()` hacen la agregación por vos.

---

## Referencia de la API

### Descubrimiento

| Función | Descripción |
|---|---|
| `censo.variables()` | Lista todas las variables del censo |
| `censo.variables(entidad="PERSONA")` | Filtra por entidad (`PERSONA`, `HOGAR`, `VIVIENDA`) |
| `censo.variables(buscar="texto")` | Busca por palabra clave en código o descripción |
| `censo.describe("VARIABLE")` | Muestra qué mide una variable y sus categorías |
| `censo.provincias()` | Tabla de provincias con códigos INDEC |
| `censo.departamentos("provincia")` | Tabla de departamentos de una provincia con códigos INDEC |

### Análisis

| Función | Descripción |
|---|---|
| `censo.tabla(variable, provincia, departamento)` | Tabla con N y % en un paso. `departamento` acepta nombre o código INDEC |
| `censo.comparar(variable, nivel, provincia)` | Pivot geográfico (provincia o departamento) |
| `censo.agregar(df, por)` | Agrega un DataFrame de `query()` con N y % |

### Datos crudos

| Función | Descripción |
|---|---|
| `censo.query(variables, provincia, departamento)` | Datos en formato largo por radio censal. `departamento` acepta nombre o código INDEC |

### Configuración

| Variable de entorno | Descripción |
|---|---|
| `CENSO_VERBOSE=0` | Silencia los mensajes de progreso (útil en pipelines y scripts) |

---

## Variables principales

| Variable | Descripción |
|---|---|
| `PERSONA_P02` | Sexo registrado al nacer |
| `PERSONA_EDAD` | Edad exacta |
| `PERSONA_EDADQUI` | Edad en grupos quinquenales |
| `PERSONA_EDADGRU` | Edad en grandes grupos (0-14, 15-64, 65+) |
| `PERSONA_MNI` | Máximo nivel de instrucción |
| `PERSONA_CONDACT` | Condición de actividad económica |
| `HOGAR_NBI_TOT` | Necesidades Básicas Insatisfechas |
| `HOGAR_NBI_VIV / ESC / SAN / HAC / SUB` | Componentes del NBI |
| `HOGAR_IPMH` | Índice de Privación Material del Hogar |
| `HOGAR_H24A/B/C` | Acceso a internet, celular, computadora |
| `VIVIENDA_TIPOVIVG` | Tipo de vivienda |
| `VIVIENDA_URP` | Área urbano/rural |
| `DPTO_NDPTO` | Nombres de departamentos |

Explorá el catálogo completo con `censo.variables()`.

---

## Ejemplos de análisis

```python
import censoargentino as censo

# NBI por provincia — tabla comparativa
censo.comparar("HOGAR_NBI_TOT")

# Nivel educativo en departamentos de Tucumán
censo.comparar("PERSONA_MNI", nivel="departamento", provincia="Tucumán")

# Distribución de sexo en CABA
censo.tabla("PERSONA_P02", provincia="02")

# Departamento por nombre
censo.tabla("VIVIENDA_TIPOVIVG", provincia="Buenos Aires", departamento="Lanús")

# Datos crudos + agregación manual
df = censo.query(variables="PERSONA_MNI", provincia="Santa Fe")
censo.agregar(df, por="departamento")
```

---

## Instalación con soporte MCP

Para usar el paquete como servidor [MCP](MCP.md) (compatible con Claude Desktop, Cursor, Cline y otros):

```bash
pip install "censoargentino[mcp]"
```

Configuración en cualquier cliente MCP:

```json
{
  "mcpServers": {
    "censoargentino": {
      "command": "python",
      "args": ["-m", "censoargentino.mcp_server"]
    }
  }
}
```

Ver [MCP.md](MCP.md) para documentación completa del servidor.

---

## Instalación con soporte geográfico

Para trabajar con geometrías de radios censales (requiere geopandas):

```bash
pip install "censoargentino[geo]"
```

```python
gdf = censo.query(variables="HOGAR_NBI_TOT", provincia="Tucumán", geometry=True)
```

---

## Créditos

La extracción de los datos desde la base REDATAM del INDEC fue realizada con R por [Nissim Lebovits](https://github.com/nlebovits) en el proyecto [`ciut-redatam`](https://github.com/nlebovits/ciut-redatam), usando [`redatamx`](https://ideasybits.github.io/redatamx4r/index.html). `censoargentino` construye sobre esa base para ofrecer acceso desde Python.

---

## Fuentes y documentación

- [Dataset en Hugging Face](https://huggingface.co/datasets/pedroorden/censoargentino)
- [Base REDATAM — INDEC](https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos-6)
- [Definiciones de variables (PDF)](https://redatam.indec.gob.ar/redarg/CENSOS/CPV2022/Docs/Redatam_Definiciones_de_la_base_de_datos.pdf)
- [redatamx — herramienta de procesamiento](https://ideasybits.github.io/redatamx4r/index.html)
- [Portal REDATAM online](https://redatam.indec.gob.ar/binarg/RpWebEngine.exe/Portal?BASE=CPV2022&lang=ESP)
