"""Geocodifica la base de instituciones y puntos de atención del grupo (Base_insticrcr.csv,
elaborada por Paz Ramírez Brizuela, 4 de noviembre de 2026) y produce datos/instituciones_puntos.csv.

Uso:
    python scripts/geocodificar_instituciones.py <Base_insticrcr.csv> <dir shapefile distrital INEC> [datos]

Método, por orden de preferencia:
  1. Enlace de Google Maps publicado por ACNUR en la columna url_ubicacion_o_fuente (se resuelve la
     redirección y se extraen las coordenadas): confianza alta.
  2. Hito de la dirección de referencia buscado en Nominatim (OpenStreetMap): confianza alta si el
     hito es la sede misma (municipalidad, facultad), media si la sede está a cierta distancia del hito.
  3. Centroide del distrito (INEC, Unidad Geoestadística Distrital 2024): confianza baja.
Después se asigna el cantón por intersección con los polígonos de datos/cantones.geojson y se compara
con el cantón declarado en la base.
"""
import sys, re, csv, json, time, pathlib, subprocess, unicodedata, urllib.request, urllib.parse
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

UA = 'geohack-2026-prototipo (Escuela de Geografia UCR)'

# Consultas a Nominatim por sede (la primera que devuelva resultado se usa) y confianza asignada.
HITOS = {
    'CMM-SJO': (['Centro Corporativo Internacional, San José, Costa Rica'], 'alta'),
    'CMM-CARPIO': (['SIFAIS, La Carpio, Uruca, San José, Costa Rica'], 'media'),
    'CMM-LIM': (['Parque Vargas, Limón, Costa Rica'], 'media'),
    'CMM-TAR': (['Municipalidad de Tarrazú, San Marcos, Tarrazú, Costa Rica'], 'alta'),
    'CMM-HER': (['Municipalidad de Heredia, Heredia, Costa Rica'], 'media'),
    'CEN-SJO': (['Torre Mercedes, Paseo Colón, San José, Costa Rica'], 'media'),
    'HIAS-SJO': (['Centro Colón, Paseo Colón, San José, Costa Rica', 'Edificio Centro Colón, San José, Costa Rica'], 'media'),
    'RET-SJO': (['Embajada de Italia, Los Yoses, San Pedro, Montes de Oca, Costa Rica'], 'media'),
    'CLIN-UCR': (['Facultad de Derecho, Universidad de Costa Rica'], 'alta'),
    'REDNAM': (['Musmanni, San Felipe, Alajuelita, Costa Rica'], 'media'),
    'IRCA': (['Sede Lechera, Zapote, San José, Costa Rica'], 'media'),
    'OIM-SJO': (['Rohrmoser, Pavas, San José, Costa Rica'], 'baja'),
}
# Sedes que se resuelven al centroide del distrito (sin hito localizable o sin sede física).
DISTRITO = {'CMM-SC': 'sin sede física (atención virtual)', 'FUND-MUJER': 'hito "Escuela de Betania" no localizado'}

# Categorías de necesidad de la encuesta NIC que cada sede puede atender (propuesta del prototipo, por validar).
NECESIDADES = {
    'CMM': 'Asistencia en documentación;Información sobre restricciones de movilidad',
    'SJM': 'Asistencia legal;Asistencia en documentación;DIMEX',
    'FOD': 'Falta de recursos económicos;Educación',
    'CEN': 'Apoyo psicosocial;Seguridad y protección;Asistencia legal',
    'HIAS': 'Apoyo psicosocial;Seguridad y protección;Falta de recursos económicos',
    'RET': 'Educación;Seguridad y protección',
    'CLIN': 'Asistencia legal;Apoyo psicosocial',
    'FUND': 'Falta de recursos económicos',
    'REDNAM': 'Información sobre restricciones de movilidad;Asistencia legal',
    'IRCA': 'Falta de comida;Falta de un albergue seguro',
    'OIM': 'Falta de recursos económicos;Falta de comida;Falta de un albergue seguro;Seguridad y protección',
    'ACNUR': 'Asistencia legal;Asistencia en documentación;Seguridad y protección',
}


def clave(s):
    s = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    return ' '.join(s.lower().split())


def coord_google(url):
    final = subprocess.run(['curl', '-s', '-o', '/dev/null', '-L', '-m', '30', '-A', 'Mozilla/5.0',
                            '-w', '%{url_effective}', url], capture_output=True, text=True).stdout
    final = urllib.parse.unquote(final)
    for pat in (r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', r'/search/(-?\d+\.\d+),[+\s]*(-?\d+\.\d+)', r'@(-?\d+\.\d+),(-?\d+\.\d+)'):
        m = re.search(pat, final)
        if m:
            return float(m.group(1)), float(m.group(2)), final
    return None


def nominatim(q):
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'json', 'limit': 1, 'countrycodes': 'cr'})
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    time.sleep(1.1)
    return (float(d[0]['lat']), float(d[0]['lon']), d[0]['display_name']) if d else None


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    base = pd.read_csv(sys.argv[1], encoding='utf-8-sig', dtype=str).fillna('')
    distritos = gpd.read_file(next(pathlib.Path(sys.argv[2]).glob('*.shp')), encoding='utf-8').to_crs(4326)
    salida = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else pathlib.Path(__file__).resolve().parent.parent / 'datos'
    cantones = gpd.read_file(salida / 'cantones.geojson')

    filas = []
    for _, r in base.iterrows():
        i = r['id']; lat = lon = None; metodo = detalle = ''; conf = ''
        if 'goo.gl' in r['url_ubicacion_o_fuente']:
            g = coord_google(r['url_ubicacion_o_fuente'])
            if g:
                lat, lon, detalle = g; metodo = 'Enlace de Google Maps publicado por ACNUR'; conf = 'alta'
                detalle = re.sub(r'/data=.*', '', detalle)
        if lat is None and i in HITOS:
            for q in HITOS[i][0]:
                n = nominatim(q)
                if n:
                    lat, lon, detalle = n; metodo = f'Nominatim (OSM), hito: {q}'; conf = HITOS[i][1]
                    break
        if lat is None:
            en_canton = distritos[distritos['NOMB_UGEC'].map(clave) == clave(r['canton'])]
            d = en_canton[en_canton['NOMB_UGED'].map(clave) == clave(r['distrito'])]
            if not len(d):  # nombre de distrito no coincide (ej. "Ciudad Quesada" vs "Quesada"): distrito primero (cabecera)
                d = en_canton[en_canton['COD_UGED'].astype(str).str.endswith('01')]
            if len(d):
                c = d.geometry.iloc[0].representative_point(); lat, lon = c.y, c.x
                metodo = 'Centroide del distrito (INEC 2024)'; conf = 'baja'
                detalle = DISTRITO.get(i, 'sin hito localizable')
        filas.append({'id': i, 'institucion_sede': r['institucion_sede'], 'tipo_actor': r['tipo_actor'],
                      'provincia': r['provincia'], 'canton': r['canton'], 'distrito': r['distrito'],
                      'lat': round(lat, 6) if lat else None, 'lon': round(lon, 6) if lon else None,
                      'metodo': metodo, 'confianza': conf, 'detalle_geocodificacion': detalle,
                      'necesidades': NECESIDADES[i.split('-')[0]],
                      'servicios': r['servicios_relevantes'], 'telefono': r['telefono_contacto'],
                      'direccion_referencia': r['direccion_referencia'], 'url': r['url_ubicacion_o_fuente'],
                      'observaciones_base': r['observaciones_calidad']})
        print(f"{i:11s} {conf:5s} {lat},{lon}  {metodo[:60]}")

    pts = pd.DataFrame(filas)
    g = gpd.GeoDataFrame(pts, geometry=[Point(x, y) if pd.notna(x) else None for x, y in zip(pts['lon'], pts['lat'])], crs=4326)
    j = gpd.sjoin(g, cantones[['clave', 'canton', 'geometry']].rename(columns={'canton': 'canton_sig'}), how='left', predicate='within')
    pts['clave_canton'] = j['clave'].values
    pts['canton_sig'] = j['canton_sig'].values
    pts['coincide_canton'] = [clave(a) == clave(b) if isinstance(b, str) else False for a, b in zip(pts['canton'], pts['canton_sig'])]
    pts.to_csv(salida / 'instituciones_puntos.csv', index=False)
    print('\nCantón declarado vs cantón del polígono:', pts['coincide_canton'].value_counts().to_dict())
    print(pts.loc[~pts['coincide_canton'], ['id', 'canton', 'canton_sig']].to_string(index=False))
    print('Confianza:', pts['confianza'].value_counts().to_dict())
    print(f'Salida: {salida / "instituciones_puntos.csv"}')


if __name__ == '__main__':
    main()
