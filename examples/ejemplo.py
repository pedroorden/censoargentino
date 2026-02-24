"""
Ejemplos de uso de ciut-censo.

Instalación:
    pip install -e ciut-censo/           # dependencias básicas
    pip install -e "ciut-censo/[geo]"    # + geopandas para geometría
"""

import ciut

# ------------------------------------------------------------------
# 1. Ver variables disponibles (trae solo el archivo de metadatos, chico)
# ------------------------------------------------------------------
print("=== Variables disponibles ===")
vars_df = ciut.variables()
print(vars_df.head(10))
print(f"\nTotal variables: {len(vars_df)}")

# ------------------------------------------------------------------
# 2. Ver provincias (lookup local, sin red)
# ------------------------------------------------------------------
print("\n=== Provincias ===")
print(ciut.provincias())

# ------------------------------------------------------------------
# 3. Consulta básica: una variable, todo el país
# ------------------------------------------------------------------
print("\n=== PERSONA_SEXO (todo el país) ===")
df_sexo = ciut.query(variables="PERSONA_SEXO")
print(df_sexo.head())

# ------------------------------------------------------------------
# 4. Consulta filtrada por provincia (solo descarga esa provincia)
# ------------------------------------------------------------------
print("\n=== PERSONA_SEXO en CABA ===")
df_caba = ciut.query(variables="PERSONA_SEXO", provincia="02")
print(df_caba)

# ------------------------------------------------------------------
# 5. Varias variables + provincia por nombre
# ------------------------------------------------------------------
print("\n=== Tipo de vivienda y condición de habitabilidad en Córdoba ===")
df_cordoba = ciut.query(
    variables=["VIVIENDA_TIPOVIVG", "VIVIENDA_CONDICION_HABITABILIDAD"],
    provincia="Córdoba",
)
print(df_cordoba.head(20))

# ------------------------------------------------------------------
# 6. Con geometría (requiere pip install ciut-censo[geo])
# ------------------------------------------------------------------
print("\n=== PERSONA_SEXO en Mendoza con polígonos de radios censales ===")
try:
    gdf = ciut.query(variables="PERSONA_SEXO", provincia="Mendoza", geometry=True)
    print(gdf.head())
    print(f"\nCRS: {gdf.crs}")
    print(f"Filas con geometría: {gdf.geometry.notna().sum()}")
except ImportError as e:
    print(f"Instalá geopandas para este ejemplo: pip install ciut-censo[geo]\n{e}")
