# Por qué existe `censoargentino`

## El censo como fuente de datos única

El Censo Nacional de Población, Hogares y Viviendas 2022 es la operación estadística más completa que produce el Estado argentino. Abarca 46 millones de personas, 16 millones de viviendas y más de 100 variables socioeconómicas desagregadas hasta el **radio censal** — la unidad geográfica mínima del sistema estadístico nacional, equivalente a unas pocas manzanas en contexto urbano.

Esta granularidad es lo que hace al censo irreemplazable. No es solo cuántos argentinos tienen acceso a internet — es en qué radios censales de qué departamentos de qué provincias esa brecha es más profunda. No es solo cuántos hogares tienen NBI — es cómo eso se distribuye dentro de una misma ciudad, entre barrios que comparten colectivos pero no oportunidades.

No existe otra fuente pública argentina que combine esa cobertura (toda la población), esa resolución geográfica (52.000+ radios censales) y esa riqueza temática (personas, hogares y viviendas coordinados en un mismo relevamiento).

---

## El problema del acceso

INDEC publica los microdatos censales en formato **REDATAM** — un sistema diseñado para la consulta estadística interactiva. Procesarlo requiere software especializado: el paquete `redatamx` de R, o la interfaz web del propio INDEC.

Este modelo de acceso tiene limitaciones estructurales que no son menores:

**No es programático.** No existe una API. No hay forma de integrar el censo en un pipeline de análisis reproducible sin primero extraer los datos a mano, variable por variable, provincia por provincia.

**No es reproducible.** Un análisis hecho en la interfaz web del INDEC no puede ser documentado de forma que otro investigador lo replique exactamente. No hay código, no hay parámetros, no hay historial.

**No es componible.** Los datos viven en un silo. Para cruzarlos con estadísticas de salud, educación o economía — algo que cualquier análisis de política pública necesita — hay que exportar, limpiar y reimportar a mano.

El resultado es paradójico: el dataset más rico del país es también uno de los más difíciles de usar para cualquier persona que no sea especialista en REDATAM.

---

## Qué existe hoy y dónde encaja `censoargentino`

El acceso a los datos del CPV 2022 no parte de cero. Hay herramientas y recursos existentes, cada uno con su perfil de usuario:

**`redatamx` (R)** es el paquete de referencia para trabajar con bases REDATAM en entorno científico. Es potente y preciso, pero está pensado para usuarios de R con conocimiento del formato REDATAM. No cubre el ecosistema Python, que es donde trabaja la mayoría de los analistas de datos en Argentina hoy.

**El portal web de INDEC** permite consultas interactivas sin instalar nada. Es útil para consultas puntuales y para usuarios no técnicos, pero no es programático: cada consulta es manual, no se puede automatizar, no deja registro reproducible y tiene límites en la cantidad de variables y geografías que se pueden combinar en una sola sesión.

**El Parquet en Hugging Face** es la capa de datos cruda que usa `censoargentino`. Técnicamente, cualquiera puede accederlo directamente con DuckDB o pandas. Pero hacerlo implica conocer la estructura del dataset, manejar el esquema en formato largo, normalizar los códigos geográficos, traducir nombres de provincias a códigos INDEC y resolver los nombres de departamentos manualmente. Son decisiones de implementación que hay que tomar cada vez.

`censoargentino` toma ese Parquet y construye sobre él una **API de alto nivel en Python**: una interfaz que resuelve esas decisiones una sola vez, de forma consistente, para que el usuario pueda concentrarse en el análisis y no en la fontanería de los datos.

---

## La solución técnica

`censoargentino` resuelve el problema en dos pasos.

**Primero, la extracción.** La base REDATAM fue procesada con `redatamx` (R) y convertida a formato **Parquet comprimido con ZSTD** en estructura larga — donde cada fila representa cuántas personas (o hogares, o viviendas) de un radio censal tienen un determinado valor para una variable. El resultado se aloja en **Hugging Face Datasets** como dataset público y libre.

**Segundo, el acceso.** `censoargentino` usa **DuckDB sobre HTTP** para consultar ese Parquet remotamente. La clave está en cómo DuckDB lee Parquet: en lugar de descargar el archivo completo (137 MB), aplica **predicate pushdown** — descarga solo los bloques que contienen los datos pedidos. Una consulta filtrada por variable y provincia transfiere típicamente menos de 5 MB y tarda entre 2 y 6 segundos.

```
INDEC (REDATAM)
      ↓
  redatamx (R) → extracción de variables
      ↓
  Parquet en formato largo → Hugging Face Datasets
      ↓
  DuckDB vía HTTP → censoargentino
      ↓
  pandas DataFrame → análisis en Python
```

Esto transforma el acceso al censo de algo que requería infraestructura especializada en algo que se puede hacer desde un notebook en Google Colab, con una sola línea de código.

---

## Datos agregados, no individuos

`censoargentino` no trabaja con microdatos individuales. Los datos que distribuye el paquete son los que INDEC publica oficialmente: información **pre-agregada a nivel radio censal**.

Esto significa que la unidad mínima de análisis no es una persona, un hogar o una vivienda — es el radio censal completo. Cada fila del dataset responde a: *"en el radio censal X, hay N personas con la característica Y"*. No existe ningún registro que corresponda a un individuo identificable.

La consecuencia práctica es que trabajar con `censoargentino` no implica ningún riesgo de re-identificación ni requiere consideraciones especiales de privacidad. Los mismos datos que expone el paquete son los que cualquier ciudadano puede consultar en el portal público del INDEC o descargar desde Hugging Face. El paquete no agrega acceso a nada que no sea ya público — solo lo hace más cómodo de usar.

Esta agregación previa también define los límites del análisis: se pueden describir territorios, comparar unidades geográficas y detectar patrones estructurales, pero no es posible hacer análisis de casos individuales ni construir trayectorias personales. Para ese tipo de análisis existen otras fuentes (EPH, registros administrativos, encuestas panel) con sus propios protocolos de acceso.

---

## Por qué Python

Python es el idioma de la ciencia de datos. Es el entorno donde funcionan Jupyter, pandas, matplotlib, seaborn, scikit-learn, statsmodels — toda la cadena de análisis que usan investigadores académicos, periodistas de datos, estudiantes de ciencias sociales y equipos de gobierno que trabajan con estadísticas.

Tener el censo disponible como librería Python significa que puede integrarse directamente en esa cadena:

**Los análisis son reproducibles.** Un notebook que usa `censoargentino` puede ser compartido, ejecutado y verificado por cualquier persona con acceso a Python. No hay pasos manuales ocultos, no hay capturas de pantalla en lugar de código.

**Los datos son componibles.** El DataFrame que devuelve `censo.query()` es un DataFrame de pandas estándar — puede cruzarse con datos de salud, educación, criminalidad o economía con las mismas herramientas que ya se usan para todo lo demás.

**Los análisis pueden automatizarse.** El mismo código que corre en un notebook puede integrarse en un pipeline de ETL, un dashboard de Streamlit, un informe automatizado en Quarto o una API que sirve datos procesados. La consulta al censo se vuelve un paso más dentro de un flujo mayor.

**El código es auditable.** Un análisis que calcula un índice de vulnerabilidad por departamento puede ser versionado con git, revisado por pares y reproducido años después. Eso no es posible con una consulta hecha en una interfaz web sin registro.

---

## Un mapa sobre la sociedad argentina

El censo 2022 no es una colección de preguntas sueltas. Es un relevamiento coordinado que, tomado en conjunto, permite construir una imagen detallada de cómo vive la Argentina y cómo se distribuyen sus desigualdades en el territorio.

Con las variables disponibles en `censoargentino` es posible caracterizar cualquier radio censal del país en términos de su estructura demográfica, su nivel educativo, sus condiciones de habitabilidad, su acceso a servicios básicos y tecnología, y su composición por condición de actividad económica. Y hacerlo simultáneamente para los 52.000+ radios que cubren el país entero.

El resultado no es la respuesta a una pregunta específica — es la infraestructura para responder cualquier pregunta que tenga al territorio como variable. Las brechas digitales entre el AMBA y el NOA. Los patrones de hacinamiento dentro de una misma ciudad. La relación entre nivel educativo y condición de actividad por departamento. La distribución del envejecimiento poblacional en la Patagonia. La concentración del trabajo informal según tipo de vivienda.

Cada una de esas preguntas existe como posibilidad dentro del mismo dataset. `censoargentino` es la llave de acceso a ese mapa.

---

## Para quién es

`censoargentino` está pensado para cualquier persona que trabaje con datos en Argentina y necesite contexto poblacional o territorial:

**Investigadores y académicos** — sociólogos, demógrafos, economistas y geógrafos que necesitan datos desagregados para análisis regionales, modelos estadísticos o publicaciones científicas. El censo es la única fuente con cobertura total y resolución hasta radio censal.

**Periodistas de datos** — que quieran contextualizar coberturas con datos censales sin depender de solicitudes de acceso a la información, esperar respuestas institucionales o navegar interfaces diseñadas para otro tipo de usuario. Con `censoargentino`, una pregunta como "¿cuántos hogares sin internet hay en el NOA?" se responde en segundos.

**Estudiantes** — de ciencias sociales, estadística, economía o ciencia de datos que quieran trabajar con datos reales en sus proyectos, tesis o trabajos prácticos. El paquete funciona en Google Colab sin instalar nada fuera de `pip install censoargentino`.

**Equipos de gobierno y organismos públicos** — funcionarios que necesitan datos territoriales para planificar políticas, evaluar intervenciones o producir informes. La desagregación hasta radio censal permite diagnósticos mucho más precisos que los cuadros agregados de los boletines del INDEC.

**Desarrolladores de software cívico** — que quieran integrar datos censales en aplicaciones, visualizaciones o herramientas de consulta pública. `censoargentino` es una capa de acceso, no una visualización: los datos salen como DataFrames listos para cualquier pipeline posterior.

---

## Por qué como librería, y no solo como dataset

Publicar `censoargentino` como librería pip-instalable — y no solo dejar el Parquet en Hugging Face — es una decisión de diseño con consecuencias concretas.

Un dataset descargable es **pasivo**: existe para ser consumido tal como está. Una librería es **activa**: define una interfaz, tiene una API que puede evolucionar, gestiona su propia complejidad interna y puede instalarse en cualquier entorno con `pip install` sin decisiones de infraestructura.

La librería abstrae complejidades que no deberían ser problema del usuario final:

- ¿Cuál es la URL exacta del Parquet en Hugging Face? → Encapsulada en `_constants.py`.
- ¿Cómo se traduce el nombre "Córdoba" al código INDEC `"14"`? → Manejado por `_geo.py`.
- ¿Cómo se obtienen los nombres reales de departamentos si el dataset solo guarda códigos numéricos? → Resuelto automáticamente por `comparar()` usando la variable `DPTO_NDPTO`.
- ¿Cómo se configura DuckDB para acceso HTTP anónimo? → Manejado en `_client.py`.

El usuario escribe `censo.tabla("HOGAR_NBI_TOT", provincia="Chaco")` y obtiene una tabla con N y porcentaje. El resto es implementación que puede cambiar, mejorar o repararse sin que el código del usuario cambie.

Además, una librería puede ser **versionada y mantenida** de forma sistemática. Cuando INDEC publique una segunda entrega de datos censales (localidades, aglomerados), bastará con actualizar las URLs en `_constants.py` y publicar una nueva versión en PyPI. El código existente de los usuarios sigue funcionando sin modificaciones.

---

## Estado actual

`censoargentino` cubre la **1ª entrega definitiva del CPV 2022**, publicada por INDEC en diciembre de 2024. Incluye variables de **PERSONA** (sexo, edad, nivel educativo, condición de actividad), **HOGAR** (NBI, privación material, acceso a tecnología, hacinamiento) y **VIVIENDA** (tipo, habitabilidad, área urbano/rural), desagregadas hasta radio censal en todo el país.

La 2ª entrega con datos de localidades y aglomerados está prometida por INDEC sin fecha confirmada. Cuando se publique, se incorporará al dataset y al paquete.

---

## Referencias

- [PyPI — censoargentino](https://pypi.org/project/censoargentino/)
- [GitHub — pedroorden/censoargentino](https://github.com/pedroorden/censoargentino)
- [Dataset — Hugging Face](https://huggingface.co/datasets/pedroorden/censoargentino)
- [Base REDATAM — INDEC](https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos-6)
- [Definiciones de variables (PDF)](https://redatam.indec.gob.ar/redarg/CENSOS/CPV2022/Docs/Redatam_Definiciones_de_la_base_de_datos.pdf)
- [redatamx — herramienta de extracción](https://ideasybits.github.io/redatamx4r/index.html)
