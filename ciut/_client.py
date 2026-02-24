from __future__ import annotations

import time

import pandas as pd

from ._constants import DATA_URL, METADATA_URL, PROVINCIAS, RADIOS_URL
from ._geo import resolve_provincia

# Tamaño aproximado del archivo completo en S3 (para contexto al usuario)
_DATA_SIZE_GB = 2.1
_RADIOS_SIZE_MB = 180


def _log(msg: str) -> None:
    print(f"[ciut] {msg}", flush=True)


class CensoClient:
    def __init__(self) -> None:
        self._con = None
        self._metadata_cache: pd.DataFrame | None = None
        self._variable_labels_cache: dict[str, str] = {}

    def _conn(self):
        if self._con is None:
            import duckdb

            _log("Iniciando DuckDB e instalando extensión HTTP...")
            self._con = duckdb.connect()
            self._con.execute("INSTALL httpfs; LOAD httpfs;")
            _log("Listo. Las consultas se hacen directo al bucket S3 de INDEC/CIUT.")
        return self._con

    def _get_variable_label(self, codigo: str) -> str:
        """Devuelve la etiqueta legible de una variable, ej. 'PERSONA_P02' -> 'Sexo registrado al nacer'."""
        if not self._variable_labels_cache:
            df = self.variables()
            self._variable_labels_cache = dict(
                zip(df["codigo_variable"], df["etiqueta_variable"])
            )
        return self._variable_labels_cache.get(codigo, codigo)

    def variables(self, entidad: str | None = None, buscar: str | None = None) -> pd.DataFrame:
        """
        Devuelve las variables disponibles en el censo 2022.

        Parameters
        ----------
        entidad : str, opcional
            Filtrar por entidad: "PERSONA", "HOGAR" o "VIVIENDA".
        buscar : str, opcional
            Texto libre para buscar en el nombre o descripción de la variable.

        Returns
        -------
        DataFrame con columnas: codigo_variable, etiqueta_variable, entidad
        """
        if self._metadata_cache is None:
            _log("Descargando catálogo de variables (archivo de metadatos, ~1 MB)...")
            t0 = time.time()
            self._metadata_cache = self._conn().execute(
                f"""
                SELECT DISTINCT codigo_variable, etiqueta_variable, entidad
                FROM '{METADATA_URL}'
                ORDER BY entidad, codigo_variable
                """
            ).df()
            elapsed = time.time() - t0
            n = len(self._metadata_cache)
            _log(f"Catálogo cargado en {elapsed:.1f}s -> {n} variables disponibles")
            _log("  Entidades: PERSONA (personas), HOGAR (hogares), VIVIENDA (viviendas)")

        df = self._metadata_cache
        if entidad is not None:
            df = df[df["entidad"].str.upper() == entidad.upper()]
        if buscar is not None:
            mask = (
                df["codigo_variable"].str.contains(buscar, case=False, na=False)
                | df["etiqueta_variable"].str.contains(buscar, case=False, na=False)
            )
            df = df[mask]
        return df.reset_index(drop=True)

    def describe(self, variable: str) -> None:
        """
        Muestra la descripción completa de una variable: qué mide y sus categorías posibles.

        Parameters
        ----------
        variable : str
            Código de la variable, ej. "PERSONA_SEXO".
        """
        _log(f"Consultando metadatos de '{variable}'...")
        df = self._conn().execute(
            f"""
            SELECT
                codigo_variable,
                etiqueta_variable,
                entidad,
                nombre_variable,
                valor_categoria,
                etiqueta_categoria
            FROM '{METADATA_URL}'
            WHERE codigo_variable = '{variable}'
            ORDER BY CAST(valor_categoria AS INTEGER) NULLS LAST
            """
        ).df()

        if df.empty:
            _log(f"Variable '{variable}' no encontrada.")
            _log("Usá ciut.variables() para ver todas las disponibles.")
            return

        row = df.iloc[0]
        entity_labels = {"PERSONA": "personas", "HOGAR": "hogares", "VIVIENDA": "viviendas"}
        entity_desc = entity_labels.get(row["entidad"], row["entidad"])

        print()
        print(f"  Variable   : {row['codigo_variable']}")
        print(f"  Nombre INDEC: {row['nombre_variable']}")
        print(f"  Descripción: {row['etiqueta_variable']}")
        print(f"  Entidad    : {row['entidad']}  (aplica a {entity_desc})")
        print(f"  Referencia : https://redatam.indec.gob.ar/redarg/CENSOS/CPV2022/Docs/Redatam_Definiciones_de_la_base_de_datos.pdf")
        print()
        print(f"  Categorías ({len(df)} valores):")
        print(f"  {'Código':<10}  Etiqueta")
        print(f"  {'-'*8}  {'-'*40}")
        for _, r in df.iterrows():
            print(f"  {str(r['valor_categoria']):<10}  {r['etiqueta_categoria']}")
        print()

    def provincias(self) -> pd.DataFrame:
        """Devuelve la tabla de provincias con nombre y código INDEC."""
        seen: dict[str, str] = {}
        for nombre, codigo in PROVINCIAS.items():
            if codigo not in seen:
                seen[codigo] = nombre.title()
        rows = sorted(seen.items(), key=lambda x: x[0])
        return pd.DataFrame(rows, columns=["codigo", "provincia"])

    def query(
        self,
        variables: str | list[str] | None = None,
        provincia: str | None = None,
        departamento: str | None = None,
        geometry: bool = False,
    ) -> pd.DataFrame:
        """
        Consulta datos del censo con filtros opcionales.

        Parameters
        ----------
        variables : str o lista de str
            Código/s de variable del censo (ej. "PERSONA_SEXO").
            Usá ciut.variables() para ver todos los disponibles.
        provincia : str
            Nombre o código INDEC de la provincia (ej. "Córdoba" o "14").
        departamento : str
            Código INDEC del departamento (3 dígitos, ej. "007").
        geometry : bool
            Si True devuelve un GeoDataFrame con polígonos de radios censales.
            Requiere: pip install ciut-censo[geo]

        Returns
        -------
        pandas.DataFrame (o geopandas.GeoDataFrame si geometry=True)
        """
        if variables is None and provincia is None and departamento is None:
            raise ValueError(
                "Especificá al menos un filtro (variables, provincia o departamento) "
                "para no intentar descargar el dataset completo (~2 GB)."
            )

        if isinstance(variables, str):
            variables = [variables]

        # --- Resolver provincia ---
        prov_code: str | None = None
        prov_label: str | None = None
        if provincia is not None:
            prov_code = resolve_provincia(provincia)
            prov_label = self.provincias().set_index("codigo").loc[prov_code, "provincia"]

        dpto_code: str | None = None
        if departamento is not None:
            dpto_code = str(departamento).zfill(3)

        # --- Mostrar resumen de la consulta ---
        _log("=" * 55)
        _log("Consulta al Censo Nacional 2022 (INDEC)")
        _log(f"Fuente: censo-2022-largo.parquet (~{_DATA_SIZE_GB} GB total en S3)")
        _log("  (DuckDB descarga solo los bloques que coinciden con los filtros)")
        _log("-" * 55)

        if variables:
            for v in variables:
                label = self._get_variable_label(v) if self._metadata_cache is not None else ""
                suffix = f'  ("{label}")' if label and label != v else ""
                _log(f"  Variable : {v}{suffix}")

        if prov_label:
            _log(f"  Provincia: {prov_label}  (código INDEC: {prov_code})")
        if dpto_code:
            _log(f"  Dpto.    : {dpto_code}")

        # Explicar qué es el formato largo
        _log("-" * 55)
        _log("Estructura del resultado:")
        _log("  Cada fila = una (radio censal × categoría de variable × conteo)")
        _log("  Columnas clave: id_geo | codigo_variable | valor_categoria")
        _log("                  etiqueta_categoria | conteo")
        _log("=" * 55)

        # --- Construir y ejecutar query ---
        conditions: list[str] = []
        if variables:
            var_list = ", ".join(f"'{v}'" for v in variables)
            conditions.append(f"codigo_variable IN ({var_list})")
        if prov_code:
            conditions.append(f"valor_provincia = '{prov_code}'")
        if dpto_code:
            conditions.append(f"valor_departamento = '{dpto_code}'")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        _log("Descargando datos desde S3...")
        t0 = time.time()
        df = self._conn().execute(f"SELECT * FROM '{DATA_URL}' {where}").df()
        elapsed = time.time() - t0

        mem_mb = df.memory_usage(deep=True).sum() / 1024**2
        _log(
            f"Descarga completa en {elapsed:.1f}s -> "
            f"{len(df):,} filas | {df.shape[1]} columnas | {mem_mb:.1f} MB en memoria"
        )

        if not geometry:
            return df

        return self._attach_geometry(df, prov_code)

    def _attach_geometry(self, df: pd.DataFrame, prov_code: str | None):
        """Une el DataFrame con los polígonos de radios censales."""
        try:
            import geopandas as gpd
        except ImportError as e:
            raise ImportError(
                "geopandas es necesario para geometry=True. "
                "Instalalo con: pip install ciut-censo[geo]"
            ) from e

        radios_conditions: list[str] = []
        if prov_code is not None:
            radios_conditions.append(f"CAST(prov AS VARCHAR) = '{prov_code}'")

        radios_where = (
            f"WHERE {' AND '.join(radios_conditions)}" if radios_conditions else ""
        )

        _log(f"Descargando polígonos de radios censales (~{_RADIOS_SIZE_MB} MB total)...")
        t0 = time.time()
        radios = self._conn().execute(
            f"SELECT cod_2022, geometry FROM '{RADIOS_URL}' {radios_where}"
        ).df()
        elapsed = time.time() - t0
        _log(f"Radios descargados en {elapsed:.1f}s -> {len(radios):,} radios censales")

        _log("Uniendo datos censales con geometrías...")
        merged = df.merge(radios, left_on="id_geo", right_on="cod_2022", how="left")
        matched = merged["geometry"].notna().sum()
        merged["geometry"] = gpd.GeoSeries.from_wkb(merged["geometry"])
        gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")

        _log(f"GeoDataFrame listo -> {matched:,}/{len(merged):,} filas con geometria")
        return gdf
