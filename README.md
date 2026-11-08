# GeoHack CR 2026, grupo 4: prototipo de dashboard

Prototipo de referencia del dashboard que el grupo 4 del GeoHack Costa Rica 2026
construye en ArcGIS Online: **necesidades de personas migrantes nicaragüenses por
cantón de residencia en Costa Rica** (encuesta NIC de la DTM de OIM, enero 2025 a
marzo 2026), con las instituciones que pueden atenderlas y el contexto regional
de las estadísticas migratorias del SICA.

Es una maqueta funcional hecha en [Streamlit](https://streamlit.io/) por el
mentor del grupo para discutir decisiones de diseño (filtros, indicadores,
tratamiento de los cantones sin datos) antes de fijarlas en ArcGIS Dashboards.
No sustituye el producto final del grupo.

## Contenido

| Ruta | Qué es |
|---|---|
| `app.py` | Aplicación Streamlit (cuatro pestañas: mapa por cantón, instituciones, contexto SICA, datos y vacíos). |
| `scripts/preparar_datos.py` | Genera `datos/` a partir del paquete de datos del GeoHack (OIM) y del shapefile cantonal del INEC. |
| `datos/nic_limpio.csv` | Encuesta NIC por cantón y mes con las **17 necesidades** del archivo original (659 filas). |
| `datos/cantones.geojson` | 84 cantones (INEC, Unidad Geoestadística Cantonal 2024) simplificados, en WGS84, con población 2022. |
| `datos/sica.csv` | Series mensuales del SICA 2019-2026 (aprehensiones, deportaciones, entradas y salidas regulares, residencia permanente, retorno forzado) en formato largo. |
| `scripts/geocodificar_instituciones.py` | Geocodifica la base de instituciones del grupo (`Base_insticrcr.csv`, no versionada) con los enlaces de Google Maps publicados por ACNUR, hitos en OpenStreetMap (Nominatim) o centroides distritales INEC, y asigna el cantón por intersección. |
| `datos/instituciones_puntos.csv` | Las 22 sedes geocodificadas con método, confianza (12 alta, 7 media, 3 baja) y categorías de necesidad que atienden. |
| `datos/instituciones.csv` | Instituciones que pueden atender cada necesidad, a partir de la propuesta del grupo (4 de noviembre de 2026). La asignación a categorías de la encuesta es una propuesta por validar. |
| `datos/registro_preparacion.md` | Qué hizo el script y qué quedó pendiente (lo genera el propio script). |
| `environment.yml` | Ambiente conda `geohack-2026` (incluye geopandas para preparar los datos). |
| `requirements.txt` | Dependencias mínimas para ejecutar solo la aplicación (por ejemplo en Streamlit Community Cloud). |

Los datos originales del GeoHack (3.8 GB) no se versionan. El script espera tres
carpetas del paquete: `Datos_GeoHACK_OIM/`, `data_CR/GIS/Unidad Geoestadística
Cantonal 2024/` (dentro de `data_CR.zip`) y `databases_geohack/sica/` (dentro de
`databases_geohack.zip`).

## Uso

```bash
conda env create -f environment.yml
conda activate geohack-2026

# Regenerar los datos (solo si cambian los originales)
python scripts/preparar_datos.py <Datos_GeoHACK_OIM> "<Unidad Geoestadística Cantonal 2024>" <sica>

# Geocodificar la base de instituciones del grupo (requiere red: Google Maps y Nominatim)
python scripts/geocodificar_instituciones.py <Base_insticrcr.csv> "<Unidad Geoestadística Distrital 2024>"

# Ejecutar la aplicación
streamlit run app.py
```

## Decisiones de diseño que el prototipo pone a prueba

- **Cantones sin encuestas no son ceros.** Se dibujan en gris con su propio mensaje.
  Siete cantones nunca aparecen en la encuesta y muchos otros faltan en meses sueltos.
- **Tres medidas conmutables:** menciones, menciones por 10 mil habitantes y
  porcentaje de las menciones del cantón. La encuesta admite varias respuestas por
  persona y OIM no entrega el número de personas encuestadas por cantón, así que
  ninguna medida es "porcentaje de personas"; el dashboard lo advierte.
- **"Todos" como opción de año y de mes.** Con una mediana de 3 menciones por cantón y
  mes, el mapa de un solo mes no sirve para comparar cantones.
- **Las 17 necesidades del original.** Una versión limpia que circuló en el grupo
  conservó 12; aquí se reponen las cinco restantes (414 menciones).
- **Oferta frente a demanda.** Las sedes de la base del grupo se dibujan sobre el coropletas, filtradas por la
  necesidad elegida, y se cuentan por cantón para señalar cantones con necesidad alta y sin puntos de atención.
  Falta la red de la CCSS (capa oficial en https://sgis.ccss.sa.cr, fuera de servicio al 8 de noviembre de 2026).
- **SICA como contexto, no como capa.** Series por país con colores fijos y una matriz
  de cobertura que muestra el vacío principal: Nicaragua no reporta ningún indicador.

## Fuentes

- OIM, Matriz de Seguimiento de Desplazamiento (DTM) Costa Rica: encuesta a personas
  nicaragüenses en la frontera norte (NIC_2025_2026), tabla cantonal con población y
  porcentaje de migrantes (censos INEC 2011 y 2022) e índice de pobreza
  multidimensional (PEN 2020). Paquete de datos del GeoHack CR 2026.
- INEC, Unidad Geoestadística Cantonal 2024 (límites cantonales).
- SICA / OBSMI, estadísticas migratorias mensuales por país, 2019-2026.
