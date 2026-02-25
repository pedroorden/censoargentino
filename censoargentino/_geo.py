from ._constants import PROVINCIAS


def resolve_provincia(provincia: str) -> str:
    """
    Acepta nombre de provincia (case-insensitive) o código INDEC de 2 dígitos.
    Devuelve el código INDEC de 2 dígitos como string.

    Ejemplos:
        resolve_provincia("Buenos Aires")  → "06"
        resolve_provincia("caba")          → "02"
        resolve_provincia("02")            → "02"
    """
    key = provincia.strip().lower()

    # Si ya es un código numérico de 2 dígitos
    if key.isdigit():
        code = key.zfill(2)
        if code in PROVINCIAS.values():
            return code
        raise ValueError(
            f"Código de provincia '{provincia}' no encontrado. "
            f"Usá ciut.provincias() para ver los disponibles."
        )

    if key not in PROVINCIAS:
        # Intento de coincidencia parcial
        matches = [name for name in PROVINCIAS if key in name]
        if len(matches) == 1:
            return PROVINCIAS[matches[0]]
        elif len(matches) > 1:
            raise ValueError(
                f"Provincia '{provincia}' es ambigua. ¿Quisiste decir alguna de: "
                f"{', '.join(matches)}?"
            )
        raise ValueError(
            f"Provincia '{provincia}' no encontrada. "
            f"Usá ciut.provincias() para ver los disponibles."
        )

    return PROVINCIAS[key]
