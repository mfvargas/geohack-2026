"""Prepara las tablas que usa el dashboard (datos/) a partir del paquete de datos
del GeoHack CR 2026 (OIM) y del shapefile cantonal del INEC.

Uso:
    python scripts/preparar_datos.py <dir Datos_GeoHACK_OIM> <dir shapefile INEC> <dir sica> [datos] [healthsites.geojson]

    <dir Datos_GeoHACK_OIM>  carpeta con NIC_2025_2026.xlsx y
                             Población_migrantes_por_canton__con_indicadores.xlsx
    <dir shapefile INEC>     carpeta "Unidad Geoestadística Cantonal 2024" (de data_CR.zip)
    <dir sica>               carpeta databases_geohack/sica (de databases_geohack.zip)
    [datos]                  carpeta de salida (por defecto datos/ junto al repositorio)
    [healthsites.geojson]    GeoJSON "Costa Rica healthsites" de HDX (healthsites.io, derivado de OpenStreetMap);
                             si se da, produce datos/ccss_healthsites.csv con la red pública de salud

Salidas:
    datos/nic_limpio.csv      encuesta NIC (flujo mixto nicaragüense) por cantón y mes,
                              con las 17 necesidades del archivo original
    datos/cantones.geojson    84 cantones INEC 2024 (WGS84, simplificados) con población 2022
    datos/sica.csv            series mensuales SICA 2019-2026 en formato largo
    datos/ccss_healthsites.csv  establecimientos públicos de salud (CCSS y cooperativas contratadas) según OSM
    datos/registro_preparacion.md  qué se hizo y qué quedó pendiente
"""
import re
import sys, unicodedata, pathlib
import pandas as pd
import geopandas as gpd

MESES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
         'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}

# Nombres cortos para las 17 necesidades del archivo NIC (en el orden original).
NECESIDADES = {
    'Falta de recursos económicos': 'Falta de recursos económicos',
    'Falta de un albergue seguro': 'Falta de un albergue seguro',
    'Falta de comida': 'Falta de comida',
    'Asistencia médica': 'Asistencia médica',
    'Asistencia en documentación': 'Asistencia en documentación',
    'Asistencia legal': 'Asistencia legal',
    'Educación': 'Educación',
    'Artículos no alimentarios (ropa, cuidado personal)': 'Artículos no alimentarios',
    'Ninguna necesidad': 'Ninguna necesidad',
    'Otra necesidad': 'Otra necesidad',
    'Prefiere no responder': 'Prefiere no responder',
    'DIMEX': 'DIMEX',
    'Apoyo psicosocial': 'Apoyo psicosocial',
    'Saneamiento e higiene (baños, duchas, limpieza personal)': 'Saneamiento e higiene',
    'Seguridad y proteción': 'Seguridad y protección',
    'Información sobre restricciones a la movilidad, restricciones fronterizas': 'Información sobre restricciones de movilidad',
    'Artículos de higiene femenina y pañales': 'Artículos de higiene femenina y pañales',
}

# Equivalencias de nombre entre fuentes (clave normalizada -> clave del shapefile INEC).
EQUIVALENCIAS = {'leon cortes': 'leon cortes castro', 'vasquez de coronado': 'vazquez de coronado'}


def clave(s):
    """Clave de cantón: minúsculas, sin tildes ni espacios sobrantes."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    s = ' '.join(s.lower().split())
    return EQUIVALENCIAS.get(s, s)


def mes_num(v):
    if isinstance(v, (int, float)):
        return int(v)
    return MESES[str(v).strip().lower()[:3]]


def preparar_nic(d_oim, notas):
    nic = pd.read_excel(d_oim / 'NIC_2025_2026.xlsx')
    faltan = [c for c in NECESIDADES if c not in nic.columns]
    if faltan:
        sys.exit(f'Columnas no encontradas en NIC_2025_2026.xlsx: {faltan}')
    out = pd.DataFrame({
        'anio': nic['año'].astype(int),
        'mes': nic['mes'].map(mes_num),
        'canton_original': nic['Canton'],
    })
    out['clave'] = nic['Canton'].map(clave)
    sin_canton = out['clave'].isna() | out['clave'].isin(['no sabe', '(en blanco)'])
    out.loc[sin_canton, 'clave'] = None
    out['nota'] = None
    out.loc[sin_canton, 'nota'] = 'Cantón no identificado o vacío en el original'
    for col, corto in NECESIDADES.items():
        out[corto] = nic[col].fillna(0).astype(int)
    out['promedio_grupo_sin_encuestado'] = nic['Promedio_grupo_sin_encuestado']
    notas.append(f'- NIC: {len(out)} filas cantón-mes, {sin_canton.sum()} sin cantón identificable '
                 f'(se conservan con nota, no entran al mapa). Se conservan las 17 necesidades del original; '
                 f'la columna Promedio_grupo_sin_encuestado se conserva sin usar (significado por confirmar con OIM).')
    return out


def preparar_cantones(d_shp, d_oim, notas):
    shp = next(d_shp.glob('*.shp'))
    g = gpd.read_file(shp, encoding='utf-8')
    g = g.rename(columns={'NOMB_UGEP': 'provincia', 'NOMB_UGEC': 'canton', 'CODIGO_UGE': 'codigo'})
    g['clave'] = g['canton'].map(clave)
    # Simplificar en la proyección métrica (CRTM05) y pasar a WGS84.
    g['geometry'] = g.geometry.simplify(150, preserve_topology=True)
    g = g.to_crs(4326)
    pob = pd.read_excel(d_oim / 'Población_migrantes_por_canton__con_indicadores.xlsx')
    pob = pob[pob['Name_2'].notna() & (pob['Name_2'] != 'NA')]
    pob = pd.DataFrame({
        'clave': pob['Name_2'].map(clave),
        'poblacion_2022': pob['Poblacion_censo_2022'].astype(int),
        'pct_migrantes_2011': pob['Porcentaje_Migrantes_censo_2011'],
        'ipm_2020': pob['Índice de pobreza multidimensional cantonal_2020 PEN'],
    })
    g = g.merge(pob, on='clave', how='left')
    sin_pob = sorted(g.loc[g['poblacion_2022'].isna(), 'canton'])
    no_shp = sorted(set(pob['clave']) - set(g['clave']))
    notas.append(f'- Cantones: {len(g)} polígonos INEC 2024 simplificados (150 m). Sin población en la tabla '
                 f'de OIM: {sin_pob} (cantones creados después del censo 2011; sus tasas quedan sin dato). '
                 f'Cantones de la tabla de OIM sin polígono: {no_shp or "ninguno"}.')
    cols = ['codigo', 'provincia', 'canton', 'clave', 'poblacion_2022', 'pct_migrantes_2011', 'ipm_2020', 'geometry']
    return g[cols]


def preparar_sica(d_sica, notas):
    partes = []
    for f in sorted(d_sica.glob('SICA_*.xlsx')):
        indicador = f.stem.replace('SICA_', '').replace('_', ' ').replace('pernamente', 'permanente')
        df = pd.read_excel(f)
        df = df.rename(columns={'Apertura': 'apertura', 'Período': 'periodo'})
        largo = df.melt(id_vars=['apertura', 'periodo'], var_name='pais', value_name='valor')
        largo = largo.dropna(subset=['valor'])
        largo.insert(0, 'indicador', indicador)
        partes.append(largo)
    sica = pd.concat(partes, ignore_index=True)
    sica['valor'] = pd.to_numeric(sica['valor'], errors='coerce')
    sica = sica.dropna(subset=['valor'])
    sica['valor'] = sica['valor'].astype(int)
    cobertura = sica.groupby('indicador')['pais'].unique().apply(sorted).to_dict()
    notas.append('- SICA: series mensuales 2019-01 a 2026-06 en formato largo. Países con algún dato por indicador: '
                 + '; '.join(f'{k}: {", ".join(v)}' for k, v in cobertura.items())
                 + '. Nicaragua no reporta ningún indicador y Belice casi ninguno: es un vacío regional de datos.')
    return sica


RED_PUBLICA = re.compile(r'ccss|caja costarricense|seguro social|coopesana|coopesalud|coopesiba|coopesain|asemeco|'
                         r'ministerio de salud|unibe', re.I)
EXCLUIR = {'pharmacy', 'dentist', 'laboratory', 'optometrist', 'physiotherapist', 'alternative', 'veterinary'}


def preparar_healthsites(ruta, cantones, notas):
    """Extrae de Healthsites (OSM) los establecimientos de la red pública de salud y les asigna cantón."""
    g = gpd.read_file(ruta)
    g = g[g.geometry.notna()].copy()
    g['geometry'] = g.geometry.representative_point()
    g = g.to_crs(4326)
    for c in ('name', 'operator', 'operator_type', 'amenity', 'healthcare'):
        g[c] = g[c].fillna('') if c in g.columns else ''
    nombre = g['name'].str.lower()
    es_ebais = nombre.str.contains(r'ebais|e\.b\.a\.i\.s|equipo b[aá]sico', regex=True)
    publico = (g['operator'].str.contains(RED_PUBLICA) | g['operator_type'].str.lower().isin(['public', 'government']) | es_ebais)
    excluido = g['amenity'].isin(EXCLUIR) | g['healthcare'].isin(EXCLUIR)
    sel = g[publico & ~excluido].copy()
    sel['tipo'] = 'Clínica o área de salud'
    sel.loc[(sel['amenity'] == 'hospital') | (sel['healthcare'] == 'hospital') | nombre.loc[sel.index].str.contains('hospital'), 'tipo'] = 'Hospital'
    sel.loc[es_ebais.loc[sel.index], 'tipo'] = 'EBAIS'
    j = gpd.sjoin(sel, cantones[['clave', 'canton', 'geometry']], how='left', predicate='within')
    j = j[~j.index.duplicated()]
    out = pd.DataFrame({
        'osm_id': j['osm_id'].astype(str), 'nombre': j['name'], 'tipo': j['tipo'], 'operador': j['operator'],
        'operator_type': j['operator_type'], 'amenity': j['amenity'],
        'lat': j.geometry.y.round(6), 'lon': j.geometry.x.round(6),
        'clave_canton': j['clave'], 'canton': j['canton'], 'editado_osm': j['changeset_timestamp'].astype(str).str[:10],
    })
    sin_canton = out['clave_canton'].isna().sum()
    notas.append(f'- Healthsites (OSM, HDX, descargado el 8 de noviembre de 2026): {len(g)} entidades de salud en Costa Rica; '
                 f'{len(out)} clasificadas como red pública (operador CCSS, Ministerio de Salud o cooperativas contratadas por la CCSS, '
                 f'operator_type public/government, o nombre con EBAIS), sin farmacias, dentistas ni laboratorios. '
                 f'Por tipo: {out["tipo"].value_counts().to_dict()}. {sin_canton} fuera de los polígonos cantonales. '
                 f'Es un respaldo de la capa oficial de la CCSS (fuera de servicio al 8 de noviembre): cobertura y clasificación '
                 f'dependen de lo que la comunidad OSM ha mapeado.')
    return out


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    d_oim, d_shp, d_sica = (pathlib.Path(p) for p in sys.argv[1:4])
    salida = pathlib.Path(sys.argv[4]) if len(sys.argv) > 4 else pathlib.Path(__file__).resolve().parent.parent / 'datos'
    salida.mkdir(parents=True, exist_ok=True)
    notas = []

    nic = preparar_nic(d_oim, notas)
    cantones = preparar_cantones(d_shp, d_oim, notas)
    sin_poligono = sorted(set(nic['clave'].dropna()) - set(cantones['clave']))
    notas.append(f'- Claves de cantón de NIC sin polígono INEC: {sin_poligono or "ninguna"}.')
    sica = preparar_sica(d_sica, notas)
    salud = preparar_healthsites(pathlib.Path(sys.argv[5]), cantones, notas) if len(sys.argv) > 5 else None

    nic.to_csv(salida / 'nic_limpio.csv', index=False)
    cantones.to_file(salida / 'cantones.geojson', driver='GeoJSON', coordinate_precision=5)
    sica.to_csv(salida / 'sica.csv', index=False)
    if salud is not None:
        salud.to_csv(salida / 'ccss_healthsites.csv', index=False)
    (salida / 'registro_preparacion.md').write_text(
        '# Registro de preparación de datos\n\nGenerado por `scripts/preparar_datos.py`.\n\n' + '\n'.join(notas) + '\n',
        encoding='utf-8')
    print('\n'.join(notas))
    print(f'\nSalida en {salida}')


if __name__ == '__main__':
    main()
