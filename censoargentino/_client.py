from __future__ import annotations

import os
import re
import time
import unicodedata

import pandas as pd

from ._constants import DATA_URL, METADATA_URL, PROVINCIAS, RADIOS_URL
from ._geo import resolve_provincia

# Tamaño aproximado de los archivos en Hugging Face (comprimidos con ZSTD)
_DATA_SIZE_MB = 137
_RADIOS_SIZE_MB = 58


def _log(msg: str) -> None:
    if os.environ.get("CENSO_VERBOSE", "1") == "0":
        return
    import sys
    enc = sys.stderr.encoding or "utf-8"
    safe = msg.encode(enc, errors="replace").decode(enc)
    print(f"[censo] {safe}", flush=True, file=sys.stderr)


class CensoClient:
    def __init__(self) -> None:
        self._con = None
        self._metadata_cache: pd.DataFrame | None = None
        self._variable_labels_cache: dict[str, str] = {}
        self._dept_labels_cache: dict = {}
        self._provincias_cache: pd.DataFrame | None = None

    def _conn(self):
        if self._con is None:
            import duckdb

            _log("Iniciando DuckDB e instalando extension HTTP...")
            self._con = duckdb.connect()
            self._con.execute("INSTALL httpfs; LOAD httpfs;")
            try:
                self._con.execute("SET enable_progress_bar = false;")
            except Exception:
                pass  # falla en Jupyter sin ipywidgets; no es crítico
            _log("Listo. Las consultas van directo a Hugging Face (pedroorden/censoargentino).")
        return self._con

    def _get_variable_label(self, codigo: str) -> str:
        """Devuelve la etiqueta legible de una variable."""
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
            Texto libre para buscar en el nombre o descripcion de la variable.

        Returns
        -------
        DataFrame con columnas: codigo_variable, etiqueta_variable, entidad
        """
        if self._metadata_cache is None:
            _log("Descargando catalogo de variables (archivo de metadatos, ~1 MB)...")
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
            _log(f"Catalogo cargado en {elapsed:.1f}s -> {n} variables disponibles")
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
        Muestra la descripcion completa de una variable: que mide y sus categorias posibles.

        Parameters
        ----------
        variable : str
            Codigo de la variable, ej. "PERSONA_P02".
        """
        variable = variable.strip().upper()
        if not re.match(r"^[A-Z0-9_]+$", variable):
            raise ValueError(
                f"Código de variable inválido: '{variable}'. "
                f"Los códigos tienen el formato 'ENTIDAD_NOMBRE', ej. 'PERSONA_P02'."
            )
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
            _log("Usa censo.variables() para ver todas las disponibles.")
            return

        row = df.iloc[0]
        entity_labels = {"PERSONA": "personas", "HOGAR": "hogares", "VIVIENDA": "viviendas"}
        entity_desc = entity_labels.get(row["entidad"], row["entidad"])

        print()
        print(f"  Variable    : {row['codigo_variable']}")
        print(f"  Nombre INDEC: {row['nombre_variable']}")
        print(f"  Descripcion : {row['etiqueta_variable']}")
        print(f"  Entidad     : {row['entidad']}  (aplica a {entity_desc})")
        print(f"  Referencia  : https://redatam.indec.gob.ar/redarg/CENSOS/CPV2022/Docs/Redatam_Definiciones_de_la_base_de_datos.pdf")
        print()
        print(f"  Categorias ({len(df)} valores):")
        print(f"  {'Codigo':<10}  Etiqueta")
        print(f"  {'-'*8}  {'-'*40}")
        for _, r in df.iterrows():
            print(f"  {str(r['valor_categoria']):<10}  {r['etiqueta_categoria']}")
        print()

    def provincias(self) -> pd.DataFrame:
        """Devuelve la tabla de provincias con nombre y codigo INDEC."""
        if self._provincias_cache is None:
            seen: dict[str, str] = {}
            for nombre, codigo in PROVINCIAS.items():
                if codigo not in seen:
                    seen[codigo] = nombre.title()
            rows = sorted(seen.items(), key=lambda x: x[0])
            self._provincias_cache = pd.DataFrame(rows, columns=["codigo", "provincia"])
        return self._provincias_cache

    def departamentos(self, provincia: str) -> pd.DataFrame:
        """
        Devuelve la tabla de departamentos de una provincia con nombre y codigo INDEC.

        Parameters
        ----------
        provincia : str
            Nombre o codigo INDEC de la provincia. Ej: 'Buenos Aires', '06'.

        Returns
        -------
        pandas.DataFrame con columnas: codigo, departamento
        """
        prov_code = resolve_provincia(provincia)
        labels = self._dept_labels(prov_code)  # {code: nombre}
        rows = sorted(labels.items(), key=lambda x: x[1])
        return pd.DataFrame(rows, columns=["codigo", "departamento"])

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
            Codigo/s de variable del censo (ej. "PERSONA_P02").
            Usa censo.variables() para ver todos los disponibles.
        provincia : str
            Nombre o codigo INDEC de la provincia (ej. "Cordoba" o "14").
        departamento : str
            Codigo INDEC del departamento (3 digitos, ej. "007").
        geometry : bool
            Si True devuelve un GeoDataFrame con poligonos de radios censales.
            Requiere: pip install censoargentino[geo]

        Returns
        -------
        pandas.DataFrame (o geopandas.GeoDataFrame si geometry=True)
        """
        if variables is None and provincia is None and departamento is None:
            raise ValueError(
                "Especifica al menos un filtro (variables, provincia o departamento) "
                "para no intentar descargar el dataset completo (~137 MB)."
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
            dpto_str = str(departamento).strip()
            if dpto_str.isdigit():
                dpto_code = dpto_str.zfill(3)
            else:
                if prov_code is None:
                    raise ValueError(
                        "Para filtrar por nombre de departamento, especificá también la provincia."
                    )
                dpto_code = self._resolve_departamento(dpto_str, prov_code)

        # --- Mostrar resumen de la consulta ---
        _log("=" * 55)
        _log("Consulta al Censo Nacional 2022 (INDEC)")
        _log(f"Fuente: censo-2022-largo.parquet (~{_DATA_SIZE_MB} MB en Hugging Face)")
        _log("  (DuckDB descarga solo los bloques que coinciden con los filtros)")
        _log("-" * 55)

        if variables:
            for v in variables:
                label = self._get_variable_label(v) if self._metadata_cache is not None else ""
                suffix = f'  ("{label}")' if label and label != v else ""
                _log(f"  Variable : {v}{suffix}")

        if prov_label:
            _log(f"  Provincia: {prov_label}  (codigo INDEC: {prov_code})")
        if dpto_code:
            _log(f"  Dpto.    : {dpto_code}")

        _log("-" * 55)
        _log("Estructura del resultado:")
        _log("  Cada fila = una (radio censal x categoria de variable x conteo)")
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

        _log("Descargando datos desde Hugging Face...")
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

    def tabla(
        self,
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
        >>> censo.tabla("PERSONA_MNI", provincia="14", departamento="007")
        """
        from ._analysis import agregar

        df = self.query(variables=variable, provincia=provincia, departamento=departamento)
        return agregar(df)

    def _dept_labels(self, prov_code: str | None = None) -> dict[str, str]:
        """
        Devuelve un diccionario {etiqueta_departamento_codigo: nombre_real}
        consultando la variable DPTO_NDPTO del propio dataset.
        """
        if prov_code in self._dept_labels_cache:
            return self._dept_labels_cache[prov_code]


        conditions = ["codigo_variable = 'DPTO_NDPTO'"]
        if prov_code:
            conditions.append(f"valor_provincia = '{prov_code}'")
        where = "WHERE " + " AND ".join(conditions)

        result = self._conn().execute(
            f"SELECT DISTINCT etiqueta_departamento, valor_categoria "
            f"FROM '{DATA_URL}' {where}"
        ).df()

        # Normalizar a string con zero-padding de 3 dígitos para que coincida con el agg
        keys = result["etiqueta_departamento"].astype(str).str.strip().str.zfill(3)
        labels = dict(zip(keys, result["valor_categoria"]))
        self._dept_labels_cache[prov_code] = labels
        return labels

    @staticmethod
    def _ascii(s: str) -> str:
        """Normaliza a minúsculas sin tildes para comparaciones flexibles."""
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()

    def _resolve_departamento(self, departamento: str, prov_code: str) -> str:
        """Resuelve nombre de departamento a código INDEC de 3 dígitos."""
        labels = self._dept_labels(prov_code)  # {code: nombre}
        name_to_code = {v.lower(): k for k, v in labels.items()}
        name_to_code_ascii = {self._ascii(v): k for k, v in labels.items()}

        key = departamento.strip().lower()
        key_ascii = self._ascii(departamento.strip())

        if key in name_to_code:
            return name_to_code[key]
        if key_ascii in name_to_code_ascii:
            return name_to_code_ascii[key_ascii]

        matches = [(name, code) for name, code in name_to_code.items() if key in name or key_ascii in self._ascii(name)]
        if len(matches) == 1:
            return matches[0][1]
        if len(matches) > 1:
            names = ", ".join(n.title() for n, _ in matches)
            raise ValueError(
                f"Departamento '{departamento}' es ambiguo. ¿Quisiste decir alguno de: {names}?"
            )
        raise ValueError(
            f"Departamento '{departamento}' no encontrado. "
            f"Usá censo.comparar(..., nivel='departamento', provincia=...) para ver los disponibles."
        )

    def comparar(
        self,
        variable: str,
        nivel: str = "provincia",
        provincia: str | None = None,
    ) -> pd.DataFrame:
        """
        Compara la distribucion de una variable entre provincias o departamentos.

        Devuelve una tabla pivot: geografia en filas, categorias en columnas, % como valores.
        Cuando nivel="departamento", los nombres reales de departamento se resuelven
        automaticamente a partir de la variable DPTO_NDPTO.

        Parameters
        ----------
        variable : str
            Codigo de variable del censo (ej. "HOGAR_NBI_TOT").
        nivel : str, default "provincia"
            Nivel geografico de comparacion: "provincia" o "departamento".
        provincia : str, opcional
            Requerido cuando nivel="departamento". Filtra por provincia.

        Returns
        -------
        pandas.DataFrame con geografia como indice, categorias como columnas y
        una columna "Total" con el N total de cada unidad geografica.

        Ejemplos
        --------
        >>> censo.comparar("HOGAR_NBI_TOT")
        >>> censo.comparar("PERSONA_MNI", nivel="departamento", provincia="Cordoba")
        >>> censo.comparar("VIVIENDA_TIPOVIVG")
        """
        from ._analysis import agregar

        if nivel not in ("provincia", "departamento"):
            raise ValueError(
                f"'nivel' debe ser 'provincia' o 'departamento'. Recibido: '{nivel}'"
            )

        if nivel == "departamento" and provincia is None:
            _log("Advertencia: comparando departamentos de todo el pais (puede tardar).")

        df = self.query(variables=variable, provincia=provincia)
        agg = agregar(df, por=nivel)

        geo_col = agg.columns[0]  # primera columna = etiqueta geografica

        # Resolver nombres reales de departamento
        if nivel == "departamento":
            prov_code = resolve_provincia(provincia) if provincia else None
            labels = self._dept_labels(prov_code)
            agg[geo_col] = agg[geo_col].map(
                lambda x: labels.get(str(x).strip().zfill(3), x)
            )

        # Pivot: geografia x categorias, valores = %
        pivot = agg.pivot_table(
            index=geo_col, columns="categoria", values="%", aggfunc="first"
        )
        pivot.columns.name = None
        pivot.index.name = None

        # Columna Total con N
        total_n = agg.groupby(geo_col)["N"].sum().rename("Total")
        pivot = pivot.join(total_n)

        # Ordenar por Total descendente
        pivot = pivot.sort_values("Total", ascending=False)

        return pivot

    def _attach_geometry(self, df: pd.DataFrame, prov_code: str | None):
        """Une el DataFrame con los poligonos de radios censales."""
        try:
            import geopandas as gpd
        except ImportError as e:
            raise ImportError(
                "geopandas es necesario para geometry=True. "
                "Instalalo con: pip install censoargentino[geo]"
            ) from e

        radios_conditions: list[str] = []
        if prov_code is not None:
            radios_conditions.append(f"CAST(prov AS VARCHAR) = '{prov_code}'")

        radios_where = (
            f"WHERE {' AND '.join(radios_conditions)}" if radios_conditions else ""
        )

        _log(f"Descargando poligonos de radios censales (~{_RADIOS_SIZE_MB} MB total)...")
        t0 = time.time()
        radios = self._conn().execute(
            f"SELECT cod_2022, geometry FROM '{RADIOS_URL}' {radios_where}"
        ).df()
        elapsed = time.time() - t0
        _log(f"Radios descargados en {elapsed:.1f}s -> {len(radios):,} radios censales")

        _log("Uniendo datos censales con geometrias...")
        merged = df.merge(radios, left_on="id_geo", right_on="cod_2022", how="left")
        matched = merged["geometry"].notna().sum()
        merged["geometry"] = gpd.GeoSeries.from_wkb(merged["geometry"])
        gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")

        _log(f"GeoDataFrame listo -> {matched:,}/{len(merged):,} filas con geometria")
        return gdf
