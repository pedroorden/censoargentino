S3_BASE = "https://arg-fulbright-data.s3.us-east-2.amazonaws.com/censo-argentino-2022"

METADATA_URL = f"{S3_BASE}/censo-2022-metadatos.parquet"
DATA_URL = f"{S3_BASE}/censo-2022-largo.parquet"
RADIOS_URL = f"{S3_BASE}/radios-2022.parquet"

# Códigos de provincia INDEC (2 dígitos)
PROVINCIAS: dict[str, str] = {
    "ciudad autónoma de buenos aires": "02",
    "ciudad autonoma de buenos aires": "02",
    "caba": "02",
    "buenos aires": "06",
    "catamarca": "10",
    "córdoba": "14",
    "cordoba": "14",
    "corrientes": "18",
    "chaco": "22",
    "chubut": "26",
    "entre ríos": "30",
    "entre rios": "30",
    "formosa": "34",
    "jujuy": "38",
    "la pampa": "42",
    "la rioja": "46",
    "mendoza": "50",
    "misiones": "54",
    "neuquén": "58",
    "neuquen": "58",
    "río negro": "62",
    "rio negro": "62",
    "salta": "66",
    "san juan": "70",
    "san luis": "74",
    "santa cruz": "78",
    "santa fe": "82",
    "santiago del estero": "86",
    "tucumán": "90",
    "tucuman": "90",
    "tierra del fuego": "94",
    "tierra del fuego, antártida e islas del atlántico sur": "94",
}
