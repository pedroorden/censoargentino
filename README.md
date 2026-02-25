# censoargentino

Cliente Python para consultar el **Censo Nacional de Población, Hogares y Viviendas 2022** de Argentina (INDEC).

Usa [DuckDB](https://duckdb.org/) para hacer consultas directas sobre los archivos Parquet almacenados en [Hugging Face](https://huggingface.co/datasets/pedroorden/censoargentino), descargando solo los datos que necesitás sin bajar el dataset completo.

## Instalación

```bash
# Desde PyPI
pip install censoargentino

# Con soporte de mapas (geopandas)
pip install "censoargentino[geo]"

# Desde GitHub (última versión)
pip install git+https://github.com/pedroorden/censoargentino.git
```

## Uso rápido

```python
import censoargentino as censo

# Ver variables disponibles
censo.variables()
censo.variables(entidad="PERSONA")
censo.variables(buscar="edad")

# Entender una variable
censo.describe("PERSONA_P02")      # Sexo
censo.describe("PERSONA_EDADQUI")  # Edad quinquenal
censo.describe("HOGAR_NBI_TOT")    # NBI

# Consultar datos (solo baja lo que filtrás)
df = censo.query(variables="PERSONA_P02", provincia="Córdoba")
df = censo.query(variables=["PERSONA_P02", "PERSONA_EDADGRU"], provincia="02")  # CABA

# Con polígonos de radios censales
gdf = censo.query(variables="PERSONA_EDADGRU", provincia="Mendoza", geometry=True)
```

## Datos disponibles

Los archivos están en [Hugging Face](https://huggingface.co/datasets/pedroorden/censoargentino):

| Archivo | Tamaño | Contenido |
|---|---|---|
| `censo-2022-largo.parquet` | 137 MB | Datos del censo en formato largo |
| `radios-2022.parquet` | 58 MB | Polígonos de radios censales |
| `censo-2022-metadatos.parquet` | 1 MB | Catálogo de variables y categorías |

Fuente: [INDEC](https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos-6) · Procesado con [redatamx](https://ideasybits.github.io/redatamx4r/index.html)

## Estructura del resultado

Los datos vienen en **formato largo pre-agregado**: cada fila es una combinación de *(radio censal × categoría × conteo)*.

```
id_geo     | codigo_variable | valor_categoria | etiqueta_categoria   | conteo
460070101  | PERSONA_P02     | 1               | Mujer / Femenino     | 252
460070101  | PERSONA_P02     | 2               | Varón / Masculino    | 231
```

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
| `HOGAR_H24A/B/C` | Acceso a internet, celular, computadora |
| `VIVIENDA_TIPOVIVG` | Tipo de vivienda |
| `VIVIENDA_URP` | Área urbano/rural |
| `DPTO_NDPTO` | Nombres de departamentos |

## Referencia de la API

| Función | Descripción |
|---|---|
| `censo.variables()` | Lista todas las variables del censo |
| `censo.variables(entidad="PERSONA")` | Filtra por entidad |
| `censo.variables(buscar="texto")` | Busca por palabra clave |
| `censo.describe("VARIABLE")` | Muestra categorías de una variable |
| `censo.provincias()` | Tabla de provincias con códigos INDEC |
| `censo.query(variables, provincia, departamento, geometry)` | Consulta datos |

## Documentación INDEC

- [Definiciones de variables (PDF)](https://redatam.indec.gob.ar/redarg/CENSOS/CPV2022/Docs/Redatam_Definiciones_de_la_base_de_datos.pdf)
- [Cuestionario del censo (PDF)](https://www.indec.gob.ar/ftp/cuadros/poblacion/Censo2022_cuestionario_viviendas_particulares.pdf)
- [Portal REDATAM online](https://redatam.indec.gob.ar/binarg/RpWebEngine.exe/Portal?BASE=CPV2022&lang=ESP)
