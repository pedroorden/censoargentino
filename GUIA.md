# Guía de uso — `ciut-censo`

Cliente Python para consultar el **Censo Nacional de Población, Hogares y Viviendas 2022** de Argentina (INDEC).

---

## Instalación

```bash
# Sin soporte de mapas
pip install git+https://github.com/pedroorden/censoargentino.git

# Con soporte de mapas (geopandas)
pip install "ciut-censo[geo] @ git+https://github.com/pedroorden/censoargentino.git"
```

---

## Dónde viven los datos

Los archivos del censo están almacenados en **Hugging Face Datasets**:

| Archivo | Tamaño | Contenido |
|---|---|---|
| `censo-2022-largo.parquet` | 137 MB | Todos los datos del censo en formato largo |
| `radios-2022.parquet` | 58 MB | Polígonos geográficos de radios censales |
| `censo-2022-metadatos.parquet` | 1 MB | Catálogo de variables y categorías |

[huggingface.co/datasets/pedroorden/censoargentino](https://huggingface.co/datasets/pedroorden/censoargentino)

Cuando ejecutás una consulta, **DuckDB descarga solo los bloques del Parquet que coinciden con tus filtros** — no baja el archivo completo. Una query típica con filtro de provincia tarda entre 2 y 6 segundos.

---

## Cómo están organizados los datos

El censo tiene tres **entidades**:

| Entidad | Qué representa | Código en variables |
|---|---|---|
| PERSONA | Cada persona relevada | `PERSONA_*` |
| HOGAR | Cada grupo familiar dentro de una vivienda | `HOGAR_*` |
| VIVIENDA | Cada vivienda particular | `VIVIENDA_*` |

### Formato largo

Los datos vienen **pre-agregados en formato largo**. Esto significa que en lugar de tener una fila por persona, cada fila representa cuántas personas de un radio censal tienen un determinado valor para una variable.

```
id_geo     | codigo_variable | valor_categoria | etiqueta_categoria   | conteo
460070101  | PERSONA_P02     | 1               | Mujer / Femenino     | 252
460070101  | PERSONA_P02     | 2               | Varón / Masculino    | 231
460070102  | PERSONA_P02     | 1               | Mujer / Femenino     | 418
460070102  | PERSONA_P02     | 2               | Varón / Masculino    | 389
```

Cada fila responde a: *"En el radio censal X, hay N personas/hogares/viviendas con la categoría Y de la variable Z".*

### Columnas del resultado

| Columna | Tipo | Descripción |
|---|---|---|
| `id_geo` | string | Código del radio censal (9 dígitos). Combina prov + dpto + fracción + radio. Ej: `460070101` |
| `valor_provincia` | string | Código INDEC de la provincia (2 dígitos). Ej: `"46"` |
| `etiqueta_provincia` | string | Nombre de la provincia. Ej: `"La Rioja"` |
| `valor_departamento` | string | Código del departamento (3 dígitos). Ej: `"007"` |
| `etiqueta_departamento` | string | **Código numérico**, no nombre. Ej: `"007"` ⚠️ |
| `valor_fraccion` | string | Código de la fracción censal |
| `etiqueta_fraccion` | string | Código de la fracción (no nombre) |
| `valor_radio` | string | Código del radio dentro de la fracción |
| `etiqueta_radio` | string | Código del radio (no nombre) |
| `codigo_variable` | string | Identificador de la variable. Ej: `"PERSONA_P02"` |
| `valor_categoria` | string | Código de la categoría. Ej: `"1"` |
| `etiqueta_categoria` | string | Nombre legible de la categoría. Ej: `"Mujer / Femenino"` |
| `conteo` | int | Cantidad de personas/hogares/viviendas en esa combinación |

> **⚠️ Importante:** `etiqueta_departamento` contiene el código numérico del departamento (ej. `"007"`), no su nombre geográfico. Para obtener nombres de departamentos hay que cruzar con la variable `DPTO_NDPTO`. Ver ejemplo en la sección [Nombres de departamentos](#nombres-de-departamentos).

---

## Funciones disponibles

### `ciut.variables()`

Descarga y devuelve el catálogo completo de variables del censo. El resultado se cachea automáticamente: la segunda llamada es instantánea.

```python
ciut.variables()
```

**Resultado:** DataFrame con columnas `codigo_variable`, `etiqueta_variable`, `entidad`.

```
   codigo_variable                          etiqueta_variable  entidad
0      DPTO_IDPTO                               Departamento     DPTO
1      DPTO_NDPTO                               Departamento     DPTO
2   HOGAR_EDUHOG              Clima educativo del hogar        HOGAR
3   HOGAR_NBI_TOT         Necesidades básicas insatisfechas    HOGAR
...
```

**Filtrar por entidad:**

```python
ciut.variables(entidad="PERSONA")   # solo variables de personas
ciut.variables(entidad="HOGAR")     # solo variables de hogares
ciut.variables(entidad="VIVIENDA")  # solo variables de viviendas
```

**Buscar por texto** (busca en código y descripción):

```python
ciut.variables(buscar="edad")        # variables relacionadas con edad
ciut.variables(buscar="nbi")         # variables de NBI
ciut.variables(buscar="instruccion") # nivel educativo
ciut.variables(buscar="internet")    # conectividad
```

---

### `ciut.describe(variable)`

Muestra la descripción completa de una variable: qué mide, a qué entidad pertenece y todos sus valores posibles con sus códigos. Útil para saber qué números hay que usar al filtrar resultados.

```python
ciut.describe("PERSONA_P02")
```

**Salida:**

```
  Variable    : PERSONA_P02
  Nombre INDEC: P02
  Descripción : Sexo registrado al nacer
  Entidad     : PERSONA  (aplica a personas)
  Referencia  : https://redatam.indec.gob.ar/.../Redatam_Definiciones_de_la_base_de_datos.pdf

  Categorías (2 valores):
  Código      Etiqueta
  --------    ----------------------------------------
  1           Mujer / Femenino
  2           Varón / Masculino
```

> **Nota sobre nombres de variables:** Los nombres no siempre son intuitivos. `PERSONA_P02` es el sexo, no `PERSONA_SEXO`. Usá `ciut.variables(buscar="...")` para encontrar el código correcto antes de consultar.

**Ejemplos frecuentes:**

```python
ciut.describe("PERSONA_P02")       # Sexo registrado al nacer
ciut.describe("PERSONA_EDAD")      # Edad exacta en años
ciut.describe("PERSONA_EDADGRU")   # Edad: 3 grandes grupos (0-14, 15-64, 65+)
ciut.describe("PERSONA_EDADQUI")   # Edad: 22 grupos quinquenales (00-04, 05-09...)
ciut.describe("PERSONA_MNI")       # Máximo nivel de instrucción (12 categorías)
ciut.describe("PERSONA_CONDACT")   # Condición de actividad: Ocupado/Desocupado/Inactivo
ciut.describe("HOGAR_NBI_TOT")     # NBI total del hogar
ciut.describe("HOGAR_H24A")        # ¿Tiene internet en la vivienda?
ciut.describe("VIVIENDA_TIPOVIVG") # Tipo de vivienda agrupado
ciut.describe("VIVIENDA_URP")      # Área urbana o rural
```

---

### `ciut.provincias()`

Devuelve la tabla de provincias con código INDEC y nombre. No hace ninguna consulta a la red — es una tabla local.

```python
ciut.provincias()
```

**Resultado:**

```
   codigo                          provincia
0      02   Ciudad Autónoma De Buenos Aires
1      06                      Buenos Aires
2      10                         Catamarca
3      14                          Córdoba
...
23     94                  Tierra Del Fuego
```

Los valores de la columna `codigo` y `provincia` son los que acepta el parámetro `provincia` en `ciut.query()`.

---

### `ciut.query()`

Consulta los datos del censo filtrando solo lo que necesitás. Es la función principal del paquete.

```python
ciut.query(
    variables=None,       # str o lista de str
    provincia=None,       # str: nombre o código INDEC
    departamento=None,    # str: código de 3 dígitos
    geometry=False        # bool: agregar polígonos de radios
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `variables` | `str` o `list[str]` | Código/s de variable. Ej: `"PERSONA_P02"` o `["PERSONA_P02", "PERSONA_EDAD"]` |
| `provincia` | `str` | Nombre o código INDEC. Acepta: `"Córdoba"`, `"córdoba"`, `"14"` |
| `departamento` | `str` | Código de 3 dígitos. Ej: `"007"` |
| `geometry` | `bool` | Si `True`, devuelve GeoDataFrame con polígonos (requiere `[geo]`) |

> **⚠️ Requerido:** Al menos uno de `variables`, `provincia` o `departamento` debe estar presente. Sin filtros, se intentaría bajar el dataset completo (~137 MB).

**Ejemplos:**

```python
# Una variable, una provincia
df = ciut.query(variables="PERSONA_P02", provincia="Córdoba")
df = ciut.query(variables="PERSONA_P02", provincia="14")      # mismo resultado

# Varias variables a la vez
df = ciut.query(
    variables=["PERSONA_P02", "PERSONA_EDADGRU"],
    provincia="Buenos Aires"
)

# Todo el país para una variable (más lento, ~5-15s)
df = ciut.query(variables="HOGAR_NBI_TOT")

# Con filtro de departamento
df = ciut.query(variables="PERSONA_MNI", provincia="14", departamento="014")

# Con geometría de radios censales
gdf = ciut.query(variables="PERSONA_P02", provincia="Mendoza", geometry=True)
```

---

## Trabajar con los resultados

### Contar totales por categoría

```python
df = ciut.query(variables="PERSONA_P02", provincia="Salta")

df.groupby("etiqueta_categoria")["conteo"].sum()
# Mujer / Femenino    657842
# Varón / Masculino   634291
```

### Tabla porcentual

```python
total = df["conteo"].sum()
df.groupby("etiqueta_categoria")["conteo"].sum().div(total).mul(100).round(1)
```

### Comparar provincias

```python
frames = [ciut.query(variables="PERSONA_EDADGRU", provincia=p) for p in ["02", "06", "14"]]
df_multi = pd.concat(frames)

df_multi.groupby(["etiqueta_provincia", "etiqueta_categoria"])["conteo"] \
    .sum().unstack().fillna(0).astype(int)
```

### Nombres de departamentos

`etiqueta_departamento` tiene códigos numéricos, no nombres. Para obtener los nombres:

```python
# 1. Descargar el lookup de nombres
dpto_nombres = (
    ciut.query(variables="DPTO_NDPTO", provincia="14")  # Córdoba
    [["valor_departamento", "etiqueta_categoria"]]
    .drop_duplicates()
    .rename(columns={"etiqueta_categoria": "nombre_departamento"})
)

# 2. Unir con tus datos
df = ciut.query(variables="PERSONA_MNI", provincia="14")
df = df.merge(dpto_nombres, on="valor_departamento", how="left")
```

---

## Variables más usadas

| Variable | Descripción | Categorías destacadas |
|---|---|---|
| `PERSONA_P02` | Sexo registrado al nacer | 1=Mujer/Femenino, 2=Varón/Masculino |
| `PERSONA_EDAD` | Edad exacta en años | 0 a 110+ |
| `PERSONA_EDADGRU` | Edad en grandes grupos | 1=0-14, 2=15-64, 3=65+ |
| `PERSONA_EDADQUI` | Edad en grupos quinquenales | 1=00-04, 2=05-09, ..., 22=105+ |
| `PERSONA_MNI` | Máximo nivel de instrucción | 1=Sin instrucción ... 9=Universitario completo |
| `PERSONA_CONDACT` | Condición de actividad económica | 1=Ocupado, 2=Desocupado, 3=Inactivo |
| `HOGAR_NBI_TOT` | Necesidades Básicas Insatisfechas | Con NBI / Sin NBI |
| `HOGAR_H20CP` | Hacinamiento del hogar | Sin hacinamiento / Con hacinamiento |
| `HOGAR_H24A` | Internet en la vivienda | Sí / No |
| `HOGAR_H24B` | Celular con internet | Sí / No |
| `HOGAR_H24C` | Computadora o tablet | Sí / No |
| `VIVIENDA_TIPOVIVG` | Tipo de vivienda agrupado | Particular, Colectiva |
| `VIVIENDA_URP` | Área urbano/rural | Urbano, Rural |
| `DPTO_NDPTO` | Nombres de departamentos | (lookup) |

---

## Documentación oficial INDEC

- [Definiciones de variables (PDF)](https://redatam.indec.gob.ar/redarg/CENSOS/CPV2022/Docs/Redatam_Definiciones_de_la_base_de_datos.pdf)
- [Cuestionario del censo (PDF)](https://www.indec.gob.ar/ftp/cuadros/poblacion/Censo2022_cuestionario_viviendas_particulares.pdf)
- [Portal REDATAM online](https://redatam.indec.gob.ar/binarg/RpWebEngine.exe/Portal?BASE=CPV2022&lang=ESP)
