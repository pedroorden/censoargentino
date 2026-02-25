from __future__ import annotations

import pandas as pd

# Mapeo de nivel geografico a columnas del DataFrame crudo
_GEO = {
    "provincia":    ("etiqueta_provincia",    "valor_provincia"),
    "departamento": ("etiqueta_departamento", "valor_departamento"),
}


def agregar(df: pd.DataFrame, por: str | None = None) -> pd.DataFrame:
    """
    Agrega el resultado de censo.query() calculando N y porcentaje.

    Funcion pura: no hace llamadas de red, opera sobre un DataFrame existente.

    Parameters
    ----------
    df : pandas.DataFrame
        Output de censo.query().
    por : str, opcional
        Nivel de agregacion geografica: "provincia" o "departamento".
        Si None, devuelve totales nacionales.

    Returns
    -------
    pandas.DataFrame con columnas: [geografia,] categoria, N, %

    Ejemplos
    --------
    >>> df = censo.query(variables="PERSONA_P02")
    >>> censo.agregar(df)                      # totales nacionales
    >>> censo.agregar(df, por="provincia")     # por provincia
    """
    if df.empty:
        return pd.DataFrame(columns=["categoria", "N", "%"])

    if por is not None and por not in _GEO:
        raise ValueError(
            f"'por' debe ser 'provincia', 'departamento' o None. Recibido: '{por}'"
        )

    base_group = ["valor_categoria", "etiqueta_categoria"]

    if por is not None:
        label_col, sort_col = _GEO[por]
        group_cols = [label_col, sort_col] + base_group
    else:
        label_col = None
        sort_col = None
        group_cols = base_group

    agg = (
        df.groupby(group_cols, sort=False)["conteo"]
        .sum()
        .reset_index()
        .rename(columns={"conteo": "N", "etiqueta_categoria": "categoria"})
    )

    # Ordenar numericamente por codigo de categoria (evita que "10" < "2")
    agg["_ord"] = pd.to_numeric(agg["valor_categoria"], errors="coerce")
    sort_by = ([sort_col] if sort_col else []) + ["_ord"]
    agg = agg.sort_values(sort_by).drop(columns=["_ord", "valor_categoria"])
    if sort_col and sort_col in agg.columns:
        agg = agg.drop(columns=[sort_col])

    # Calcular % dentro de cada grupo geografico
    if por is not None:
        totales = agg.groupby(label_col)["N"].transform("sum")
        agg["%"] = (agg["N"] / totales * 100).round(1)
        cols = [label_col, "categoria", "N", "%"]
    else:
        agg["%"] = (agg["N"] / agg["N"].sum() * 100).round(1)
        cols = ["categoria", "N", "%"]

    return agg[cols].reset_index(drop=True)
