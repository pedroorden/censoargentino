"""
censoargentino MCP server.

Expone las funciones del paquete como tools MCP compatibles con cualquier
cliente que implemente el Model Context Protocol (Claude Desktop, Cursor,
Cline, Continue.dev, Windsurf, etc.).

Instalación:
    pip install "censoargentino[mcp]"

Uso (stdio — compatible con todos los clientes MCP):
    python -m censoargentino.mcp_server

Configuración en cualquier cliente MCP:
    {
      "mcpServers": {
        "censoargentino": {
          "command": "python",
          "args": ["-m", "censoargentino.mcp_server"]
        }
      }
    }
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "El servidor MCP requiere la dependencia opcional 'mcp'.\n"
        "Instalá con: pip install 'censoargentino[mcp]'"
    ) from exc

import json
import re
from typing import Optional

import pandas as pd

import censoargentino as censo
from censoargentino._constants import METADATA_URL

# Singleton del cliente (definido en censoargentino/__init__.py)
_client = censo._client


# ──────────────────────────────────────────────────────────────────
# Servidor
# ──────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "censoargentino",
    instructions=(
        "Servidor MCP para el Censo Nacional de Población, Hogares y Viviendas 2022 "
        "de Argentina (INDEC). Datos desagregados hasta nivel de radio censal "
        "(52.000+ unidades geográficas). "
        "Flujo recomendado: "
        "1. buscar_variables() para descubrir códigos de variables. "
        "2. describir_variable() para entender categorías y valores posibles. "
        "3. tabla() para obtener distribución de una variable. "
        "4. comparar() para rankings entre provincias o departamentos. "
        "5. consultar() para filtros específicos que los anteriores no cubren. "
        "Los recursos censo://provincias y censo://variables están siempre disponibles."
    ),
)


# ──────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────

def _to_json(df: pd.DataFrame, orient: str = "records") -> str:
    return df.to_json(orient=orient, force_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────
# Resources — datos estáticos que el modelo puede leer sin llamar tools
# ──────────────────────────────────────────────────────────────────

@mcp.resource("censo://provincias")
def resource_provincias() -> str:
    """
    Tabla de provincias argentinas con código INDEC y nombre.
    Usá estos códigos en las tools que aceptan el parámetro 'provincia'.
    """
    return _to_json(censo.provincias())


@mcp.resource("censo://variables")
def resource_variables() -> str:
    """
    Catálogo completo de variables del censo 2022.
    Contiene código, descripción y entidad (PERSONA, HOGAR, VIVIENDA).
    """
    return _to_json(censo.variables())


@mcp.tool()
def departamentos(provincia: str) -> str:
    """
    Devuelve la lista de departamentos de una provincia con código INDEC y nombre.

    Usá esta tool para descubrir los nombres exactos de departamentos antes de
    llamar a tabla() o consultar() con el parámetro 'departamento'.

    Args:
        provincia: Nombre o código INDEC de la provincia. Ej: 'Buenos Aires', '06'.
    """
    return _to_json(censo.departamentos(provincia))


# ──────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────

@mcp.tool()
def buscar_variables(buscar: str, entidad: str = "") -> str:
    """
    Busca variables del censo por nombre o tema.

    Usá esta tool primero para encontrar el código correcto de una variable
    antes de consultar datos. Ejemplos de términos útiles: 'nbi', 'internet',
    'edad', 'educacion', 'hacinamiento', 'actividad', 'vivienda', 'sexo'.

    Args:
        buscar: Texto libre para buscar en código o descripción de la variable.
        entidad: Opcional. Filtra por entidad: 'PERSONA', 'HOGAR' o 'VIVIENDA'.
    """
    df = censo.variables(
        entidad=entidad.upper() if entidad else None,
        buscar=buscar,
    )
    if df.empty:
        return (
            f"No se encontraron variables para '{buscar}'. "
            f"Probá con otro término o consultá el catálogo completo en censo://variables."
        )
    return _to_json(df)


@mcp.tool()
def describir_variable(codigo_variable: str) -> str:
    """
    Devuelve los detalles completos de una variable: qué mide, a qué entidad
    pertenece y todos sus valores posibles con sus códigos.

    Usá esta tool para entender las categorías antes de interpretar resultados
    o para saber qué valores numéricos corresponden a cada categoría.

    Args:
        codigo_variable: Código de la variable. Ej: 'PERSONA_P02', 'HOGAR_NBI_TOT'.
    """
    codigo_variable = codigo_variable.strip().upper()
    if not re.match(r"^[A-Z0-9_]+$", codigo_variable):
        return (
            f"Error: código de variable inválido '{codigo_variable}'. "
            f"Los códigos tienen el formato 'ENTIDAD_NOMBRE', ej. 'PERSONA_P02'."
        )
    con = _client._conn()
    df = con.execute(
        f"""
        SELECT codigo_variable, etiqueta_variable, entidad,
               nombre_variable, valor_categoria, etiqueta_categoria
        FROM '{METADATA_URL}'
        WHERE codigo_variable = '{codigo_variable}'
        ORDER BY CAST(valor_categoria AS INTEGER) NULLS LAST
        """
    ).df()

    if df.empty:
        return (
            f"Variable '{codigo_variable}' no encontrada. "
            f"Usá buscar_variables() para encontrar el código correcto."
        )

    row = df.iloc[0]
    result = {
        "codigo": row["codigo_variable"],
        "descripcion": row["etiqueta_variable"],
        "nombre_indec": row["nombre_variable"],
        "entidad": row["entidad"],
        "categorias": df[["valor_categoria", "etiqueta_categoria"]].to_dict(orient="records"),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def tabla(
    variable: str,
    provincia: str = "",
    departamento: str = "",
) -> str:
    """
    Devuelve una tabla con conteo (N) y porcentaje (%) para cada categoría
    de una variable. Es la función principal para obtener datos del censo.

    Si no se especifica provincia, devuelve datos nacionales agregados.
    Para nivel departamental, especificá también provincia.

    Args:
        variable: Código de la variable. Ej: 'HOGAR_NBI_TOT', 'PERSONA_P02'.
        provincia: Opcional. Nombre o código INDEC. Ej: 'Chaco' o '16'.
        departamento: Opcional. Código de 3 dígitos. Ej: '007'. Requiere provincia.
    """
    df = censo.tabla(
        variable,
        provincia=provincia if provincia else None,
        departamento=departamento if departamento else None,
    )
    return _to_json(df)


@mcp.tool()
def comparar(
    variable: str,
    nivel: str = "provincia",
    provincias: Optional[list[str]] = None,
) -> str:
    """
    Compara una variable entre unidades geográficas, devolviendo un ranking
    con porcentajes por categoría.

    Escalas disponibles:
    - nivel='provincia' sin provincias → las 24 provincias del país.
    - nivel='provincia' con provincias → subset de provincias seleccionadas.
    - nivel='departamento' sin provincias → todos los departamentos del país.
    - nivel='departamento' con una provincia → departamentos de esa provincia.
    - nivel='departamento' con varias provincias → departamentos de cada provincia.

    Args:
        variable: Código de la variable. Ej: 'HOGAR_NBI_TOT'.
        nivel: Nivel geográfico: 'provincia' o 'departamento'.
        provincias: Opcional. Lista de provincias a incluir. Ej: ['Chaco', 'Formosa'].
    """
    if nivel not in ("provincia", "departamento"):
        return f"Error: 'nivel' debe ser 'provincia' o 'departamento'. Recibido: '{nivel}'."

    if nivel == "provincia":
        df = censo.comparar(variable, nivel="provincia")
        if provincias:
            df = df[df.index.isin(provincias)]
        return _to_json(df, orient="index")

    # nivel == "departamento"
    if not provincias:
        df = censo.comparar(variable, nivel="departamento")
        return _to_json(df, orient="index")

    frames = [
        censo.comparar(variable, nivel="departamento", provincia=prov)
        for prov in provincias
    ]
    return _to_json(pd.concat(frames), orient="index")


@mcp.tool()
def consultar(
    variable: str,
    provincias: Optional[list[str]] = None,
    departamentos: Optional[list[str]] = None,
) -> str:
    """
    Consulta datos del censo con filtros específicos de provincia y departamento.

    Usá esta tool cuando tabla() o comparar() no cubren tu caso. Por ejemplo:
    - Comparar departamentos puntuales de diferentes provincias.
    - Obtener datos de una combinación específica de provincia + departamento.

    Args:
        variable: Código de la variable. Ej: 'HOGAR_NBI_TOT'.
        provincias: Opcional. Lista de provincias. Ej: ['Chaco', 'Formosa'].
        departamentos: Opcional. Lista de nombres de departamento a filtrar.
                       Ej: ['San Fernando', 'Patiño']. Requiere provincias.
    """
    if not provincias:
        # Sin provincia: tabla nacional
        return tabla(variable)

    # Con provincias: comparar a nivel departamento y filtrar si hace falta
    frames = []
    for prov in provincias:
        df_prov = censo.comparar(variable, nivel="departamento", provincia=prov)
        if departamentos:
            df_prov = df_prov[df_prov.index.isin(departamentos)]
        frames.append(df_prov)

    return _to_json(pd.concat(frames), orient="index")


# ──────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
