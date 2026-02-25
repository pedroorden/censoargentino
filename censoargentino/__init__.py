"""
censoargentino: cliente Python para el censo argentino 2022 (INDEC).

Uso rapido
----------
    import censoargentino as censo

    # Ver variables disponibles
    censo.variables()

    # Traer datos filtrados (sin bajar el archivo completo)
    df = censo.query(variables="PERSONA_P02", provincia="Buenos Aires")

    # Con geometria de radios censales
    gdf = censo.query(variables="PERSONA_P02", provincia="Cordoba", geometry=True)
"""

import pandas as pd

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
    >>> censo.variables()                        # todas
    >>> censo.variables(entidad="PERSONA")       # solo variables de personas
    >>> censo.variables(buscar="educacion")      # buscar por palabra clave
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
        Codigo/s de variable del censo (ej. "PERSONA_P02" o
        ["PERSONA_P02", "PERSONA_EDADQUI"]).
        Usa censo.variables() para ver los disponibles.
    provincia : str, opcional
        Nombre o codigo INDEC de la provincia.
        Ejemplos: "Cordoba", "Buenos Aires", "02" (CABA).
        Usa censo.provincias() para ver todos los nombres validos.
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
    >>> import censoargentino as censo
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


__all__ = ["query", "variables", "describe", "provincias"]
