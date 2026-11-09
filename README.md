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
| `datos/ccss_healthsites.csv` | Red pública de salud (EBAIS, clínicas, hospitales con operador CCSS, Ministerio de Salud o cooperativas contratadas) extraída de Healthsites (OpenStreetMap vía HDX, septiembre 2026), con cantón asignado. Respaldo de la capa oficial de la CCSS. |
| `datos/missing_migrants_cr.csv` | 23 incidentes del Missing Migrants Project (OIM) ocurridos en Costa Rica, 2016-2026, con coordenadas, causa, origen y cantón (los de frontera o mar, asignados al más cercano). |
| `datos/missing_migrants_nicaragua.csv` | Personas de origen nicaragüense muertas o desaparecidas, por año y país del incidente (misma fuente). |
| `datos/transito_necesidades.csv` | Primera necesidad declarada en las encuestas de tránsito (DTM, CRC005) por mes y sitio, 2021-2026, con las 131 filas mal entrecomilladas del CSV original corregidas. |
| `datos/fms_encuestados.csv` | Personas encuestadas por país y mes en las encuestas de tránsito (FMS, Americas Data Browser), 2025. |
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
python scripts/preparar_datos.py <Datos_GeoHACK_OIM> "<Unidad Geoestadística Cantonal 2024>" <sica> datos <costa-rica.geojson de Healthsites> <20260928_FMS_AllMonths.xlsx>

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
  La red pública de salud entra desde OpenStreetMap (Healthsites) mientras la capa oficial de la CCSS
  (https://sgis.ccss.sa.cr) siga fuera de servicio, como lo estaba el 8 de noviembre de 2026.
- **Archivos "USO" del catálogo.** Las bases exigen al menos una fuente OIM (la encuesta NIC) y el SICA como
  contexto; el catálogo marca además 10 archivos como "USO". La pestaña de datos dice qué se hace con cada uno:
  Missing Migrants entra como capa de incidentes en Costa Rica (12 de 23 por falta de acceso a atención médica) y
  como resumen de personas nicaragüenses por país; FMS sirve de denominador de la tabla de necesidades en tránsito
  (coincide con ella mes a mes en 2025, con diferencias de 0 a 32); MMP_All no se usa por ser la misma fuente agregada.
- **SICA como contexto, no como capa.** Series por país con colores fijos y una matriz
  de cobertura que muestra el vacío principal: Nicaragua no reporta ningún indicador.

## Fuentes

- OIM, Matriz de Seguimiento de Desplazamiento (DTM) Costa Rica: encuesta a personas
  nicaragüenses en la frontera norte (NIC_2025_2026), tabla cantonal con población y
  porcentaje de migrantes (censos INEC 2011 y 2022) e índice de pobreza
  multidimensional (PEN 2020). Paquete de datos del GeoHack CR 2026.
- INEC, Unidad Geoestadística Cantonal 2024 (límites cantonales).
- SICA / OBSMI, estadísticas migratorias mensuales por país, 2019-2026.
- OIM, Missing Migrants Project, archivo global del paquete (Missing_Migrants_Global_Figures_allData, 2014-2026).
- OIM, DTM, Americas Data Browser: personas encuestadas en las encuestas de tránsito (FMS, 2025) y tabla de
  principales necesidades en tránsito del paquete (CRC005, 2021-2026).
- Healthsites.io vía HDX (https://data.humdata.org/dataset/costa-rica-healthsites), establecimientos de salud de
  Costa Rica derivados de OpenStreetMap (ODbL), descargado el 8 de noviembre de 2026.
- Base de instituciones y puntos de atención del grupo 4 (Paz Ramírez Brizuela, 4 de noviembre de 2026), con
  enlaces de ubicación publicados por ACNUR.
