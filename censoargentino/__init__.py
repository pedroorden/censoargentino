"""
censoargentino: cliente Python para el censo argentino 2022 (INDEC).

Uso rapido
----------
    import censoargentino as censo

    # Descubrir variables
    censo.variables()
    censo.variables(entidad="PERSONA")
    censo.variables(buscar="edad")
    censo.describe("PERSONA_P02")

    # Tabla resumida: N y % en un paso
    censo.tabla("PERSONA_P02")
    censo.tabla("HOGAR_NBI_TOT", provincia="Tucuman")

    # Comparacion geografica
    censo.comparar("HOGAR_NBI_TOT")
    censo.comparar("PERSONA_MNI", nivel="departamento", provincia="Cordoba")

    # Datos crudos (formato largo pre-agregado por radio censal)
    df = censo.query(variables="PERSONA_P02", provincia="Buenos Aires")

    # Agregar un DataFrame existente
    censo.agregar(df)
    censo.agregar(df, por="provincia")

    # Con geometria de radios censales
    gdf = censo.query(variables="PERSONA_P02", provincia="Cordoba", geometry=True)
"""

import pandas as pd

from ._analysis import agregar
from ._client import CensoClient as _CensoClient

_client = _CensoClient()


def variables(entidad: str | None = None, buscar: str | None = None) -> pd.DataFrame:
    """
    Devuelve las variables disponibles en el censo 2022.

    Parameters
    ----------
    entidad : str, opcional
        Filtrar por "PERSONA", "HOGAR" o "VIVIENDA".
    buscar : str, opcional
        Texto libre para buscar en codigo o descripcion.

    Returns
    -------
    pandas.DataFrame con columnas: codigo_variable, etiqueta_variable, entidad

    Ejemplos
    --------
    >>> censo.variables()
    >>> censo.variables(entidad="PERSONA")
    >>> censo.variables(buscar="educacion")
    """
    return _client.variables(entidad=entidad, buscar=buscar)


def describe(variable: str) -> None:
    """
    Muestra que mide una variable y sus categorias posibles.

    Parameters
    ----------
    variable : str
        Codigo de la variable, ej. "PERSONA_P02".

    Ejemplos
    --------
    >>> censo.describe("PERSONA_P02")
    >>> censo.describe("VIVIENDA_TIPOVIVG")
    >>> censo.describe("HOGAR_NBI_TOT")
    """
    return _client.describe(variable)


def provincias() -> pd.DataFrame:
    """
    Devuelve la tabla de provincias con codigo INDEC y nombre.

    Returns
    -------
    pandas.DataFrame con columnas: codigo, provincia
    """
    return _client.provincias()


def query(
    variables=None,
    provincia: str | None = None,
    departamento: str | None = None,
    geometry: bool = False,
) -> pd.DataFrame:
    """
    Consulta el censo 2022. Solo descarga los datos que pedis.

    Parameters
    ----------
    variables : str o list[str], opcional
        Codigo/s de variable del censo (ej. "PERSONA_P02").
        Usa censo.variables() para ver los disponibles.
    provincia : str, opcional
        Nombre o codigo INDEC de la provincia.
        Ejemplos: "Cordoba", "Buenos Aires", "02" (CABA).
    departamento : str, opcional
        Codigo INDEC del departamento (3 digitos, ej. "007").
    geometry : bool, default False
        Si True une el resultado con los poligonos de radios censales y
        devuelve un GeoDataFrame (requiere: pip install censoargentino[geo]).

    Returns
    -------
    pandas.DataFrame o geopandas.GeoDataFrame

    Ejemplos
    --------
    >>> censo.query(variables="PERSONA_P02", provincia="02")
    >>> censo.query(variables=["VIVIENDA_TIPOVIVG"], provincia="Mendoza")
    >>> censo.query(variables="PERSONA_EDADQUI", provincia="Salta", geometry=True)
    """
    return _client.query(
        variables=variables,
        provincia=provincia,
        departamento=departamento,
        geometry=geometry,
    )


def tabla(
    variable: str,
    provincia: str | None = None,
    departamento: str | None = None,
) -> pd.DataFrame:
    """
    Descarga y resume una variable en una tabla con N y porcentaje.

    Equivale a query() + agregar() en un solo paso.

    Parameters
    ----------
    variable : str
        Codigo de variable del censo (ej. "PERSONA_P02").
    provincia : str, opcional
        Nombre o codigo INDEC de la provincia.
    departamento : str, opcional
        Codigo INDEC del departamento (3 digitos).

    Returns
    -------
    pandas.DataFrame con columnas: categoria, N, %

    Ejemplos
    --------
    >>> censo.tabla("PERSONA_P02")
    >>> censo.tabla("HOGAR_NBI_TOT", provincia="Tucuman")
    """
    return _client.tabla(variable, provincia=provincia, departamento=departamento)


def comparar(
    variable: str,
    nivel: str = "provincia",
    provincia: str | None = None,
) -> pd.DataFrame:
    """
    Compara la distribucion de una variable entre provincias o departamentos.

    Parameters
    ----------
    variable : str
        Codigo de variable del censo (ej. "HOGAR_NBI_TOT").
    nivel : str, default "provincia"
        Nivel geografico: "provincia" o "departamento".
    provincia : str, opcional
        Requerido cuando nivel="departamento".

    Returns
    -------
    pandas.DataFrame con geografia como indice, categorias como columnas (%),
    y una columna "Total" con el N total de cada unidad geografica.

    Ejemplos
    --------
    >>> censo.comparar("HOGAR_NBI_TOT")
    >>> censo.comparar("PERSONA_MNI", nivel="departamento", provincia="Cordoba")
    """
    return _client.comparar(variable, nivel=nivel, provincia=provincia)


__all__ = ["query", "variables", "describe", "provincias", "tabla", "comparar", "agregar"]
