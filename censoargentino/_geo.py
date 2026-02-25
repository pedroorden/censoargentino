from ._constants import PROVINCIAS


def resolve_provincia(provincia: str) -> str:
    """
    Acepta nombre de provincia (case-insensitive) o codigo INDEC de 2 digitos.
    Devuelve el codigo INDEC de 2 digitos como string.

    Ejemplos:
        resolve_provincia("Buenos Aires")  -> "06"
        resolve_provincia("caba")          -> "02"
        resolve_provincia("02")            -> "02"
    """
    key = provincia.strip().lower()

    # Si ya es un codigo numerico de 2 digitos
    if key.isdigit():
        code = key.zfill(2)
        if code in PROVINCIAS.values():
            return code
        raise ValueError(
            f"Codigo de provincia '{provincia}' no encontrado. "
            f"Usa censo.provincias() para ver los disponibles."
        )

    if key not in PROVINCIAS:
        # Intento de coincidencia parcial
        matches = [name for name in PROVINCIAS if key in name]
        if len(matches) == 1:
            return PROVINCIAS[matches[0]]
        elif len(matches) > 1:
            raise ValueError(
                f"Provincia '{provincia}' es ambigua. Quisiste decir alguna de: "
                f"{', '.join(matches)}?"
            )
        raise ValueError(
            f"Provincia '{provincia}' no encontrada. "
            f"Usa censo.provincias() para ver los disponibles."
        )

    return PROVINCIAS[key]
