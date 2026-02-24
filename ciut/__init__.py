"""
ciut-censo: cliente Python para el censo argentino 2022 (INDEC / CIUT-REDATAM).

Uso rápido
----------
    import ciut

    # Ver variables disponibles
    ciut.variables()

    # Traer datos filtrados (sin bajar el archivo completo)
    df = ciut.query(variables="PERSONA_SEXO", provincia="Buenos Aires")

    # Con geometría de radios censales
    gdf = ciut.query(variables="PERSONA_SEXO", provincia="Córdoba", geometry=True)
"""

from ._client import CensoClient as _CensoClient

_client = _CensoClient()


def variables(entidad: str | None = None, buscar: str | None = None):
    """
    Devuelve las variables disponibles en el censo 2022.

    Parameters
    ----------
    entidad : str, opcional
        Filtrar por "PERSONA", "HOGAR" o "VIVIENDA".
    buscar : str, opcional
        Texto libre para buscar en código o descripción.

    Ejemplos
    --------
    >>> ciut.variables()                        # todas
    >>> ciut.variables(entidad="PERSONA")       # solo variables de personas
    >>> ciut.variables(buscar="educacion")      # buscar por palabra clave
    """
    return _client.variables(entidad=entidad, buscar=buscar)


def describe(variable: str) -> None:
    """
    Muestra qué mide una variable y sus categorías posibles.

    Parameters
    ----------
    variable : str
        Código de la variable, ej. "PERSONA_SEXO".

    Ejemplos
    --------
    >>> ciut.describe("PERSONA_SEXO")
    >>> ciut.describe("VIVIENDA_TIPOVIVG")
    """
    return _client.describe(variable)


def provincias():
    """
    Devuelve la tabla de provincias con código INDEC y nombre.

    Returns
    -------
    pandas.DataFrame con columnas: codigo, provincia
    """
    return _client.provincias()


def query(
    variables=None,
    provincia=None,
    departamento=None,
    geometry=False,
):
    """
    Consulta el censo 2022. Solo descarga los datos que pedís.

    Parameters
    ----------
    variables : str o list[str], opcional
        Código/s de variable del censo (ej. "PERSONA_SEXO" o
        ["PERSONA_SEXO", "PERSONA_EDAD"]).
        Usá ciut.variables() para ver los disponibles.
    provincia : str, opcional
        Nombre o código INDEC de la provincia.
        Ejemplos: "Córdoba", "Buenos Aires", "02" (CABA).
        Usá ciut.provincias() para ver todos los nombres válidos.
    departamento : str, opcional
        Código INDEC del departamento (3 dígitos, ej. "007").
    geometry : bool, default False
        Si True une el resultado con los polígonos de radios censales y
        devuelve un GeoDataFrame (requiere: pip install ciut-censo[geo]).

    Returns
    -------
    pandas.DataFrame o geopandas.GeoDataFrame

    Ejemplos
    --------
    >>> import ciut
    >>> ciut.query(variables="PERSONA_SEXO", provincia="02")
    >>> ciut.query(variables=["VIVIENDA_TIPOVIVG"], provincia="Mendoza")
    >>> ciut.query(variables="PERSONA_EDAD", provincia="Salta", geometry=True)
    """
    return _client.query(
        variables=variables,
        provincia=provincia,
        departamento=departamento,
        geometry=geometry,
    )


__all__ = ["query", "variables", "describe", "provincias"]
