# censoargentino — Servidor MCP

`censoargentino` incluye un servidor [MCP (Model Context Protocol)](https://modelcontextprotocol.io) que permite a cualquier modelo de lenguaje compatible consultar datos del Censo 2022 directamente, sin que el usuario escriba código.

---

## ¿Qué es MCP?

MCP es un protocolo abierto (MIT) que estandariza cómo los modelos de IA se conectan a herramientas y fuentes de datos externas. Funciona sobre JSON-RPC 2.0 y es compatible con múltiples clientes:

| Cliente | Soporte MCP |
|---|---|
| Claude Desktop | ✓ |
| Cursor | ✓ |
| Cline (VS Code) | ✓ |
| Continue.dev | ✓ |
| Windsurf | ✓ |
| Zed | ✓ |

El servidor de `censoargentino` es agnóstico — funciona igual con cualquier cliente que implemente el protocolo.

---

## Instalación

```bash
pip install "censoargentino[mcp]"
```

Esto instala el paquete base más la dependencia `mcp` necesaria para el servidor.

---

## Configuración por cliente

### Claude Desktop

Editá `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

### Cursor / Cline / Windsurf

En la configuración MCP del cliente (archivo JSON o interfaz gráfica):

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

### Comando alternativo (si instalaste el script de entrada)

```json
{
  "mcpServers": {
    "censoargentino": {
      "command": "censoargentino-mcp"
    }
  }
}
```

### Verificar que el servidor funciona

```bash
python -m censoargentino.mcp_server
```

Si no hay errores de importación, el servidor está listo.

---

## Qué expone el servidor

### Resources — datos estáticos

El modelo puede leer estos recursos sin llamar ninguna tool:

| URI | Contenido |
|---|---|
| `censo://provincias` | Tabla de provincias con código INDEC y nombre |
| `censo://variables` | Catálogo completo de variables del censo |

### Tools — funciones que el modelo puede llamar

#### `buscar_variables`

Busca variables del censo por nombre o tema. Punto de entrada recomendado antes de cualquier consulta.

```
buscar_variables(buscar="nbi")
buscar_variables(buscar="internet", entidad="HOGAR")
buscar_variables(buscar="edad", entidad="PERSONA")
```

Parámetros:
- `buscar` — texto libre para buscar en código o descripción
- `entidad` — opcional: `"PERSONA"`, `"HOGAR"` o `"VIVIENDA"`

---

#### `describir_variable`

Devuelve los detalles de una variable: qué mide, entidad y todos sus valores posibles con códigos.

```
describir_variable(codigo_variable="HOGAR_NBI_TOT")
describir_variable(codigo_variable="PERSONA_MNI")
```

Parámetros:
- `codigo_variable` — código exacto, ej. `"PERSONA_P02"`

---

#### `tabla`

Devuelve una tabla con conteo (N) y porcentaje (%) para cada categoría de una variable. Es la función principal para obtener datos.

```
tabla(variable="HOGAR_NBI_TOT")
tabla(variable="HOGAR_NBI_TOT", provincia="Chaco")
tabla(variable="PERSONA_MNI", provincia="14", departamento="007")
```

Parámetros:
- `variable` — código de la variable
- `provincia` — opcional: nombre o código INDEC (`"Chaco"` o `"16"`)
- `departamento` — opcional: código de 3 dígitos (`"007"`), requiere `provincia`

---

#### `comparar`

Compara una variable entre unidades geográficas con porcentajes por categoría.

```
# Todas las provincias
comparar(variable="HOGAR_NBI_TOT", nivel="provincia")

# Subset de provincias
comparar(variable="HOGAR_NBI_TOT", nivel="provincia",
         provincias=["Chaco", "Formosa", "Buenos Aires"])

# Todos los departamentos del país
comparar(variable="HOGAR_NBI_TOT", nivel="departamento")

# Departamentos de una provincia
comparar(variable="HOGAR_NBI_TOT", nivel="departamento",
         provincias=["Chaco"])

# Departamentos de varias provincias
comparar(variable="HOGAR_NBI_TOT", nivel="departamento",
         provincias=["Chaco", "Formosa"])
```

Parámetros:
- `variable` — código de la variable
- `nivel` — `"provincia"` o `"departamento"`
- `provincias` — opcional: lista de provincias a incluir

---

#### `consultar`

Filtros específicos para casos que `tabla()` o `comparar()` no cubren. Por ejemplo: comparar departamentos puntuales de diferentes provincias.

```
# Departamentos específicos de dos provincias distintas
consultar(variable="HOGAR_NBI_TOT",
          provincias=["Chaco", "Formosa"],
          departamentos=["San Fernando", "Patiño"])

# Una provincia con todos sus departamentos
consultar(variable="PERSONA_MNI", provincias=["Córdoba"])
```

Parámetros:
- `variable` — código de la variable
- `provincias` — opcional: lista de provincias
- `departamentos` — opcional: lista de nombres de departamentos a filtrar

---

## Flujo recomendado

```
Usuario: "¿Cuántos hogares con NBI hay en el NEA?"

Modelo:
  1. buscar_variables("nbi") → encuentra HOGAR_NBI_TOT
  2. describir_variable("HOGAR_NBI_TOT") → entiende las categorías
  3. comparar("HOGAR_NBI_TOT", nivel="provincia",
              provincias=["Chaco", "Formosa", "Misiones", "Corrientes"])
  → Devuelve ranking de NBI en las cuatro provincias del NEA
```

---

## Ejemplos de interacción

Con el servidor activo en tu cliente MCP, podés hacer preguntas directas:

- *"Mostrá la distribución de NBI en todas las provincias"*
- *"¿Cuál es el nivel educativo más frecuente en Tucumán?"*
- *"Comparar acceso a internet entre Buenos Aires y CABA"*
- *"¿Qué departamentos de Chaco tienen mayor hacinamiento?"*
- *"Buscar variables relacionadas con actividad económica"*

El modelo consulta los datos del Censo 2022 directamente a través del servidor sin que el usuario necesite escribir código.

---

## Arquitectura

```
Cliente MCP (Claude, Cursor, Cline...)
        ↓  JSON-RPC 2.0 / stdio
censoargentino.mcp_server
        ↓  Python API
censoargentino._client
        ↓  DuckDB / HTTP
Parquet en Hugging Face (pedroorden/censoargentino)
        ↓  predicate pushdown
Datos del CPV 2022 — INDEC
```

El servidor no almacena datos localmente. Cada consulta descarga solo los bloques del Parquet que coinciden con los filtros — típicamente 2–6 segundos por query.

---

## Notas técnicas

- **Transporte:** stdio (compatible con todos los clientes MCP sin configuración de red)
- **Protocolo:** MCP 1.0, JSON-RPC 2.0
- **Sin estado:** cada consulta es independiente; el servidor no mantiene sesión entre llamadas
- **Datos:** públicos, pre-agregados por INDEC a nivel radio censal — no hay microdatos individuales
