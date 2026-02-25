"""
Ejemplos de uso de censoargentino.

Instalacion:
    pip install censoargentino           # dependencias basicas
    pip install "censoargentino[geo]"    # + geopandas para geometria
"""

import censoargentino as censo

# ------------------------------------------------------------------
# 1. Ver variables disponibles (trae solo el archivo de metadatos, chico)
# ------------------------------------------------------------------
print("=== Variables disponibles ===")
vars_df = censo.variables()
print(vars_df.head(10))
print(f"\nTotal variables: {len(vars_df)}")

# ------------------------------------------------------------------
# 2. Ver provincias (lookup local, sin red)
# ------------------------------------------------------------------
print("\n=== Provincias ===")
print(censo.provincias())

# ------------------------------------------------------------------
# 3. Entender una variable
# ------------------------------------------------------------------
censo.describe("PERSONA_P02")     # Sexo
censo.describe("PERSONA_EDADQUI") # Edad quinquenal

# ------------------------------------------------------------------
# 4. Consulta basica: una variable, todo el pais
# ------------------------------------------------------------------
print("\n=== PERSONA_P02 - Sexo (todo el pais) ===")
df_sexo = censo.query(variables="PERSONA_P02")
print(df_sexo.head())

# ------------------------------------------------------------------
# 5. Consulta filtrada por provincia (solo descarga esa provincia)
# ------------------------------------------------------------------
print("\n=== PERSONA_P02 en CABA ===")
df_caba = censo.query(variables="PERSONA_P02", provincia="02")
print(df_caba)

# ------------------------------------------------------------------
# 6. Varias variables + provincia por nombre
# ------------------------------------------------------------------
print("\n=== Tipo de vivienda en Cordoba ===")
df_cordoba = censo.query(
    variables=["VIVIENDA_TIPOVIVG", "VIVIENDA_URP"],
    provincia="Cordoba",
)
print(df_cordoba.head(20))

# ------------------------------------------------------------------
# 7. Con geometria (requiere pip install censoargentino[geo])
# ------------------------------------------------------------------
print("\n=== PERSONA_P02 en Mendoza con poligonos de radios censales ===")
try:
    gdf = censo.query(variables="PERSONA_P02", provincia="Mendoza", geometry=True)
    print(gdf.head())
    print(f"\nCRS: {gdf.crs}")
    print(f"Filas con geometria: {gdf.geometry.notna().sum()}")
except ImportError as e:
    print(f"Instala geopandas para este ejemplo: pip install censoargentino[geo]\n{e}")
