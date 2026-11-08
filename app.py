"""Prototipo de dashboard: necesidades de personas migrantes por cantón (Costa Rica).

GeoHack CR 2026, grupo 4. Maqueta funcional de referencia para el dashboard que el
grupo construye en ArcGIS Online. Ejecutar con:  streamlit run app.py
"""
import json
import pathlib

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATOS = pathlib.Path(__file__).parent / 'datos'

# Paleta (referencia dataviz): un solo tono para magnitud, gris para "sin datos",
# orden categórico fijo por país para las series SICA.
SEQ = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5',
       '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
AZUL, NARANJA, AQUA, SIN_DATOS, GRID, INK2, MUTED = '#2a78d6', '#eb6834', '#1baf7a', '#e1e0d9', '#e1e0d9', '#52514e', '#898781'
PAISES = {'Costa Rica': '#2a78d6', 'Panamá': '#eb6834', 'Guatemala': '#1baf7a', 'Honduras': '#eda100',
          'El Salvador': '#e87ba4', 'Rep. Dominicana': '#008300', 'Belize': '#6250d6', 'Nicaragua': '#e34948'}
MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
NO_NECESIDAD = {'Ninguna necesidad', 'Prefiere no responder'}
TODAS = 'Todas'
MEDIDAS = {
    'Menciones (número)': 'menciones',
    'Menciones por 10 mil habitantes del cantón': 'tasa',
    'Porcentaje de las menciones del cantón': 'pct',
}
LAYOUT = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
              font=dict(family='system-ui, sans-serif', color=INK2, size=12),
              margin=dict(l=10, r=10, t=40, b=10), hoverlabel=dict(font_size=12))
EJES = dict(gridcolor=GRID, zerolinecolor='#c3c2b7', linecolor='#c3c2b7', tickfont=dict(color=INK2))


@st.cache_data
def cargar():
    nic = pd.read_csv(DATOS / 'nic_limpio.csv')
    gj = json.loads((DATOS / 'cantones.geojson').read_text(encoding='utf-8'))
    cantones = pd.DataFrame([f['properties'] for f in gj['features']])
    sica = pd.read_csv(DATOS / 'sica.csv')
    inst = pd.read_csv(DATOS / 'instituciones.csv')
    puntos = pd.read_csv(DATOS / 'instituciones_puntos.csv')
    salud = pd.read_csv(DATOS / 'ccss_healthsites.csv')
    notas = (DATOS / 'registro_preparacion.md').read_text(encoding='utf-8')
    return nic, gj, cantones, sica, inst, puntos, salud, notas


nic, gj, cantones, sica, inst, puntos, salud, notas = cargar()
NECESIDADES = [c for c in nic.columns if c not in
               ('anio', 'mes', 'canton_original', 'clave', 'nota', 'promedio_grupo_sin_encuestado')]
nic['total'] = nic[NECESIDADES].sum(axis=1)
nic['todas'] = nic[[c for c in NECESIDADES if c not in NO_NECESIDAD]].sum(axis=1)
nic['periodo'] = pd.to_datetime(dict(year=nic['anio'], month=nic['mes'], day=1))

st.set_page_config(page_title='Necesidades por cantón', page_icon='🗺️', layout='wide')
st.title('Necesidades de personas migrantes nicaragüenses por cantón')
st.caption('Prototipo de referencia (GeoHack CR 2026, grupo 4). Fuente: OIM, DTM, encuesta a personas '
           'nicaragüenses en la frontera norte (NIC, enero 2025 a marzo 2026), por cantón de residencia en '
           'Costa Rica. Población: INEC, censo 2022. Límites: INEC, Unidad Geoestadística Cantonal 2024.')

tab_mapa, tab_inst, tab_sica, tab_datos = st.tabs(
    ['Mapa por cantón', 'Instituciones que atienden', 'Contexto regional (SICA)', 'Datos y vacíos'])

# ---------------------------------------------------------------- Mapa por cantón
with tab_mapa:
    c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
    necesidad = c1.selectbox('Necesidad', [TODAS] + NECESIDADES, index=0,
                             help='"Todas" suma las menciones de las 15 necesidades; no incluye "Ninguna necesidad" ni "Prefiere no responder".')
    anio = c2.selectbox('Año', ['Todos', 2025, 2026])
    meses_disp = sorted(nic.loc[nic['anio'] == anio, 'mes'].unique()) if anio != 'Todos' else list(range(1, 13))
    mes = c3.selectbox('Mes', ['Todos'] + [MESES[m - 1] for m in meses_disp])
    medida = c4.selectbox('Medida', list(MEDIDAS))

    sel = nic[nic['clave'].notna()]
    if anio != 'Todos':
        sel = sel[sel['anio'] == anio]
    if mes != 'Todos':
        sel = sel[sel['mes'] == MESES.index(mes) + 1]
    col = 'todas' if necesidad == TODAS else necesidad
    agg = sel.groupby('clave').agg(menciones=(col, 'sum'), total=('total', 'sum'), meses=('mes', 'size')).reset_index()
    df = cantones.merge(agg, on='clave', how='left')
    df['con_datos'] = df['menciones'].notna()
    df['tasa'] = df['menciones'] / df['poblacion_2022'] * 10_000
    df['pct'] = df['menciones'] / df['total'].where(df['total'] > 0) * 100
    df['valor'] = df[MEDIDAS[medida]]
    pts = puntos if necesidad == TODAS else puntos[puntos['necesidades'].str.contains(necesidad, regex=False)]
    oferta = pts.groupby('clave_canton').size().rename('puntos')
    df = df.merge(oferta, left_on='clave', right_index=True, how='left')
    df['puntos'] = df['puntos'].fillna(0).astype(int)
    aplica_salud = necesidad in (TODAS, 'Asistencia médica')
    df = df.merge(salud.groupby('clave_canton').size().rename('salud'), left_on='clave', right_index=True, how='left')
    df['salud'] = df['salud'].fillna(0).astype(int) if aplica_salud else 0
    df['oferta'] = df['puntos'] + df['salud']

    periodo_txt = ('enero 2025 a marzo 2026' if anio == 'Todos' else
                   f'{anio}' if mes == 'Todos' else f'{mes} {anio}')
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Menciones de la necesidad' if necesidad != TODAS else 'Menciones de alguna necesidad', f"{int(df['menciones'].sum()):,}".replace(',', ' '))
    k2.metric('Respuestas totales (incluye "ninguna")', f"{int(df['total'].sum()):,}".replace(',', ' '))
    k3.metric('Cantones con encuestas', f"{int(df['con_datos'].sum())} de 84")
    k4.metric('Cantones sin encuestas', int((~df['con_datos']).sum()))

    if mes != 'Todos' and df['total'].sum() < 400:
        st.warning('Pocas respuestas en este mes: la mayoría de los cantones tiene menos de 5 menciones. '
                   'Para comparar cantones conviene usar "Todos" los meses o un año completo.')
    if MEDIDAS[medida] == 'pct':
        st.info('Porcentaje de las menciones: la encuesta admite varias respuestas por persona y OIM no '
                'entrega el número de personas encuestadas por cantón, así que este porcentaje es sobre '
                'menciones, no sobre personas.')

    con = df[df['con_datos']]
    sin = df[~df['con_datos']]
    etiqueta = {'menciones': 'Menciones', 'tasa': 'Por 10 mil hab.', 'pct': '% de menciones'}[MEDIDAS[medida]]
    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=gj, featureidkey='properties.clave', locations=sin['clave'], z=[0] * len(sin),
        colorscale=[[0, SIN_DATOS], [1, SIN_DATOS]], showscale=False, marker_line_color='#ffffff',
        marker_line_width=0.8, customdata=sin[['canton', 'provincia']].values,
        hovertemplate='<b>%{customdata[0]}</b> (%{customdata[1]})<br>Sin encuestas en el periodo<extra></extra>',
        name='Sin encuestas'))
    fig.add_trace(go.Choroplethmap(
        geojson=gj, featureidkey='properties.clave', locations=con['clave'], z=con['valor'],
        colorscale=SEQ, zmin=0, marker_line_color='#ffffff', marker_line_width=0.8,
        colorbar=dict(title=etiqueta, thickness=12, len=0.6, outlinewidth=0),
        customdata=con[['canton', 'provincia', 'menciones', 'total', 'poblacion_2022', 'tasa', 'pct', 'puntos', 'salud']].fillna(-1).values,
        hovertemplate=('<b>%{customdata[0]}</b> (%{customdata[1]})<br>'
                       'Menciones: %{customdata[2]:,.0f} de %{customdata[3]:,.0f} en total<br>'
                       'Por 10 mil hab.: %{customdata[5]:.1f}<br>% de menciones: %{customdata[6]:.1f}<br>'
                       'Sedes de la base del grupo: %{customdata[7]:.0f}<br>Establecimientos públicos de salud (OSM): %{customdata[8]:.0f}<extra></extra>'),
        name=etiqueta))
    t1, t2 = st.columns(2)
    mostrar_puntos = t1.toggle('Sedes de la base de instituciones del grupo (22)', value=True)
    mostrar_salud = t2.toggle(f'Establecimientos públicos de salud según OpenStreetMap ({len(salud)})', value=aplica_salud,
                              disabled=not aplica_salud, help='Se activa con "Asistencia médica" o "Todas".')
    if mostrar_salud and aplica_salud:
        fig.add_trace(go.Scattermap(
            lat=salud['lat'], lon=salud['lon'], mode='markers', name='Salud pública (OSM)',
            marker=dict(size=6, color=AQUA, opacity=0.75),
            customdata=salud[['nombre', 'tipo', 'operador', 'canton']].fillna('').values,
            hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>Cantón: %{customdata[3]}<extra></extra>'))
    if mostrar_puntos and len(pts):
        fig.add_trace(go.Scattermap(
            lat=pts['lat'], lon=pts['lon'], mode='markers', name='Puntos de atención',
            marker=dict(size=11, color=NARANJA, opacity=0.95),
            customdata=pts[['institucion_sede', 'servicios', 'confianza', 'metodo', 'canton']].values,
            hovertemplate=('<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Cantón: %{customdata[4]}<br>'
                           'Ubicación: confianza %{customdata[2]} (%{customdata[3]})<extra></extra>')))
    fig.update_layout(map=dict(style='carto-positron', center=dict(lat=9.75, lon=-84.45), zoom=6.5),
                      height=560, title=dict(text=f'{"Todas las necesidades" if necesidad == TODAS else necesidad}, {periodo_txt}', x=0.01, font=dict(size=15, color='#0b0b0b')),
                      **LAYOUT)
    st.plotly_chart(fig, width='stretch')
    st.caption('Gris: cantones donde OIM no registró encuestas en el periodo (no es un cero). Naranja: sedes de la base de '
               'instituciones del grupo que atienden la necesidad seleccionada. Verde: EBAIS, clínicas y hospitales públicos '
               'según OpenStreetMap (Healthsites, septiembre 2026), respaldo de la capa oficial de la CCSS. '
               'Monteverde y Puerto Jiménez no tienen población en la tabla de OIM, por lo que no tienen tasa.')

    st.markdown('**Necesidad alta sin puntos de atención en el cantón**')
    brecha = con.dropna(subset=['valor']).sort_values('valor', ascending=False)
    brecha = brecha[brecha['valor'] > 0].head(15)
    sin_oferta = brecha[brecha['oferta'] == 0]
    if aplica_salud:
        st.caption(f'De los 15 cantones con mayor valor de la medida elegida, {len(sin_oferta)} no tienen sedes de la base del grupo ni '
                   f'establecimientos públicos de salud mapeados en OpenStreetMap. Casi todo cantón tiene al menos un EBAIS, así que para '
                   f'salud la pregunta útil es cuántos hay por cada 10 mil habitantes, no si hay o no.')
    else:
        st.caption(f'De los 15 cantones con mayor valor de la medida elegida, {len(sin_oferta)} no tienen ninguna sede de la base del grupo '
                   f'que atienda esta necesidad. Para necesidades distintas de salud la oferta solo incluye las 22 sedes de la base.')
    brecha = brecha.assign(salud_10mil=brecha['salud'] / brecha['poblacion_2022'] * 10_000)
    cols_b = ['canton', 'provincia', 'menciones', 'tasa', 'pct', 'puntos'] + (['salud', 'salud_10mil'] if aplica_salud else [])
    st.dataframe(brecha[cols_b].rename(columns={
        'canton': 'Cantón', 'provincia': 'Provincia', 'menciones': 'Menciones', 'tasa': 'Por 10 mil hab.',
        'pct': '% de menciones', 'puntos': 'Sedes (base del grupo)', 'salud': 'Establec. salud pública (OSM)',
        'salud_10mil': 'Establec. salud por 10 mil hab.'}), hide_index=True, width='stretch',
        column_config={'Por 10 mil hab.': st.column_config.NumberColumn(format='%.1f'),
                       '% de menciones': st.column_config.NumberColumn(format='%.1f'),
                       'Establec. salud por 10 mil hab.': st.column_config.NumberColumn(format='%.2f')})

    g1, g2 = st.columns(2)
    top = con.dropna(subset=['valor']).nlargest(15, 'valor').sort_values('valor')
    fb = go.Figure(go.Bar(x=top['valor'], y=top['canton'], orientation='h', marker_color=AZUL,
                          marker_cornerradius=4, customdata=top[['menciones', 'total']].values,
                          hovertemplate='<b>%{y}</b><br>' + etiqueta + ': %{x:,.1f}<br>Menciones: %{customdata[0]:,.0f}<extra></extra>'))
    fb.update_layout(title=dict(text=f'Cantones con mayor valor ({etiqueta.lower()})', x=0.01, font=dict(size=14, color='#0b0b0b')),
                     height=460, xaxis=dict(title=etiqueta, **EJES), yaxis=dict(**EJES), bargap=0.3, **LAYOUT)
    g1.plotly_chart(fb, width='stretch')

    serie = nic[nic['clave'].notna()].groupby('periodo').agg(valor=(col, 'sum'), total=('total', 'sum')).reset_index()
    fl = go.Figure(go.Scatter(x=serie['periodo'], y=serie['valor'], mode='lines+markers', line=dict(color=AZUL, width=2),
                              marker=dict(size=8, color=AZUL, line=dict(color='#fcfcfb', width=2)), customdata=serie[['total']].values,
                              text=[f'{MESES[d.month - 1]} {d.year}' for d in serie['periodo']], hovertemplate='%{text}<br>Menciones: %{y:,.0f} de %{customdata[0]:,.0f}<extra></extra>'))
    fl.update_layout(title=dict(text=f'Menciones por mes en todo el país: {"todas las necesidades" if necesidad == TODAS else necesidad}', x=0.01, font=dict(size=14, color='#0b0b0b')),
                     height=460, xaxis=dict(**EJES, tickmode='array', tickvals=serie['periodo'], ticktext=[f'{MESES[d.month - 1]}<br>{d.year}' for d in serie['periodo']]), yaxis=dict(title='Menciones', rangemode='tozero', **EJES),
                     hovermode='x unified', **LAYOUT)
    g2.plotly_chart(fl, width='stretch')

    with st.expander('Ver la tabla del mapa'):
        tabla = df[['provincia', 'canton', 'poblacion_2022', 'menciones', 'total', 'tasa', 'pct', 'puntos', 'salud', 'con_datos']].rename(columns={
            'provincia': 'Provincia', 'canton': 'Cantón', 'poblacion_2022': 'Población 2022', 'menciones': 'Menciones',
            'total': 'Menciones totales', 'tasa': 'Por 10 mil hab.', 'pct': '% de menciones', 'puntos': 'Sedes (base del grupo)', 'salud': 'Establec. salud pública (OSM)', 'con_datos': 'Con encuestas'})
        st.dataframe(tabla.sort_values('Menciones', ascending=False), hide_index=True, width='stretch',
                     column_config={'Por 10 mil hab.': st.column_config.NumberColumn(format='%.1f'),
                                    '% de menciones': st.column_config.NumberColumn(format='%.1f')})
        st.download_button('Descargar CSV', tabla.to_csv(index=False).encode('utf-8'), 'necesidades_canton.csv', 'text/csv')

# ---------------------------------------------------------------- Instituciones
with tab_inst:
    st.subheader('¿Quién puede atender cada necesidad?')
    st.caption('Tabla elaborada por el grupo (Paz, 4 de noviembre de 2026) a partir de la propuesta. La asignación de '
               'cada institución a las categorías de necesidad de la encuesta NIC es una propuesta del prototipo '
               'que el grupo debe validar. Falta georreferenciar los puntos de atención (archivo Base_insticrcr).')
    nec_inst = st.selectbox('Necesidad', ['Todas'] + [n for n in NECESIDADES if n not in NO_NECESIDAD], key='nec_inst')
    filas = (inst if nec_inst == 'Todas' else inst[inst['necesidades'].str.contains(nec_inst, regex=False)]).copy()
    filas['necesidades'] = filas['necesidades'].str.replace(';', ', ')
    st.dataframe(filas.rename(columns={'institucion': 'Institución', 'tipo': 'Tipo', 'necesidades': 'Necesidades que atiende',
                                       'que_atiende': 'Servicios', 'cobertura': 'Cobertura'}),
                 hide_index=True, width='stretch', height=min(60 + 38 * len(filas), 900))
    st.markdown('**Sedes geocodificadas (base de instituciones del grupo, 22 sedes)**')
    st.caption('Coordenadas obtenidas de los enlaces de Google Maps publicados por ACNUR (confianza alta), de hitos de la '
               'dirección buscados en OpenStreetMap (alta o media) o del centroide del distrito (baja). Una sede, el Servicio '
               'Jesuita de San José, cae en Montes de Oca según el polígono del INEC aunque la base dice San José.')
    pts_tab = puntos if nec_inst == 'Todas' else puntos[puntos['necesidades'].str.contains(nec_inst, regex=False)]
    st.dataframe(pts_tab[['institucion_sede', 'tipo_actor', 'canton_sig', 'distrito', 'lat', 'lon', 'confianza', 'metodo', 'servicios']].rename(columns={
        'institucion_sede': 'Sede', 'tipo_actor': 'Tipo', 'canton_sig': 'Cantón (polígono INEC)', 'distrito': 'Distrito',
        'lat': 'Latitud', 'lon': 'Longitud', 'confianza': 'Confianza', 'metodo': 'Método', 'servicios': 'Servicios'}),
        hide_index=True, width='stretch', column_config={'Latitud': st.column_config.NumberColumn(format='%.5f'),
                                                          'Longitud': st.column_config.NumberColumn(format='%.5f')})
    st.download_button('Descargar instituciones_puntos.csv', puntos.to_csv(index=False).encode('utf-8'),
                       'instituciones_puntos.csv', 'text/csv')
    st.markdown(f'**Red pública de salud según OpenStreetMap ({len(salud)} establecimientos)**')
    st.caption('Respaldo de la capa oficial de la CCSS (fuera de servicio al 8 de noviembre de 2026). Fuente: Healthsites.io vía HDX, '
               'derivado de OpenStreetMap, con ediciones hasta septiembre de 2026. Se incluyen establecimientos con operador CCSS, '
               'Ministerio de Salud o cooperativas contratadas por la CCSS, o con "EBAIS" en el nombre; se excluyen farmacias, '
               'dentistas y laboratorios. La cobertura depende de lo que la comunidad ha mapeado.')
    resumen_salud = salud.pivot_table(index='canton', columns='tipo', values='osm_id', aggfunc='count', fill_value=0)
    resumen_salud['Total'] = resumen_salud.sum(axis=1)
    resumen_salud = resumen_salud.merge(cantones.set_index('canton')['poblacion_2022'], left_index=True, right_index=True, how='left')
    resumen_salud['Por 10 mil hab.'] = (resumen_salud['Total'] / resumen_salud['poblacion_2022'] * 10_000).round(2)
    st.dataframe(resumen_salud.drop(columns='poblacion_2022').sort_values('Total', ascending=False), width='stretch', height=320)
    st.download_button('Descargar ccss_healthsites.csv', salud.to_csv(index=False).encode('utf-8'), 'ccss_healthsites.csv', 'text/csv')
    st.markdown('**Instituciones por necesidad (tabla de la propuesta)**')
    conteo = inst['necesidades'].str.split(';').explode().value_counts().reindex([n for n in NECESIDADES if n not in NO_NECESIDAD]).fillna(0)
    sin_inst = [n for n, v in conteo.items() if v == 0]
    if sin_inst:
        st.warning('Necesidades sin ninguna institución asignada todavía: ' + ', '.join(sin_inst) + '.')

# ---------------------------------------------------------------- SICA
with tab_sica:
    st.subheader('Contexto regional: estadísticas migratorias del SICA')
    st.caption('Fuente: SICA (OBSMI), series mensuales por país, enero 2019 a junio 2026, incluidas en el paquete de '
               'datos del GeoHack. Permiten ubicar el flujo observado en Costa Rica dentro de la dinámica regional.')
    s1, s2, s3 = st.columns([1.2, 1.5, 2.5])
    indicador = s1.selectbox('Indicador', sorted(sica['indicador'].unique()), index=2)
    sub = sica[sica['indicador'] == indicador]
    aperturas = sorted(sub['apertura'].unique())
    pref = next((a for a in aperturas if a in ('Total | Ambos sexos', 'Ambos sexos', 'Total')), aperturas[0])
    apertura = s2.selectbox('Desagregación', aperturas, index=aperturas.index(pref))
    sub = sub[sub['apertura'] == apertura]
    disponibles = [p for p in PAISES if p in set(sub['pais'])]
    por_defecto = [p for p in ('Costa Rica', 'Panamá', 'Guatemala') if p in disponibles][:3]
    paises = s3.multiselect('Países (máximo 8; los colores son fijos por país)', disponibles, default=por_defecto)
    sub = sub[sub['pais'].isin(paises)].copy()
    sub['fecha'] = pd.to_datetime(sub['periodo'])
    fs = go.Figure()
    for p in PAISES:
        if p not in paises:
            continue
        d = sub[sub['pais'] == p].sort_values('fecha')
        fs.add_trace(go.Scatter(x=d['fecha'], y=d['valor'], mode='lines', name=p, line=dict(color=PAISES[p], width=2),
                                hovertemplate='%{y:,.0f}'))
        if len(d):
            fs.add_annotation(x=d['fecha'].iloc[-1], y=d['valor'].iloc[-1], text=p, showarrow=False, xanchor='left',
                              xshift=6, font=dict(color=INK2, size=11))
    fs.update_layout(title=dict(text=f'{indicador.capitalize()} por mes ({apertura})', x=0.01, font=dict(size=14, color='#0b0b0b')),
                     height=480, xaxis=dict(**EJES), yaxis=dict(title='Personas', rangemode='tozero', **EJES),
                     hovermode='x unified', legend=dict(orientation='h', y=-0.15), **LAYOUT)
    st.plotly_chart(fs, width='stretch')

    st.markdown('**Cobertura de los datos del SICA por país e indicador** (número de meses con dato, de 90 posibles)')
    cob = (sica.groupby(['indicador', 'pais'])['periodo'].nunique().unstack('pais')
           .reindex(columns=list(PAISES)).fillna(0).astype(int))
    st.dataframe(cob, width='stretch')
    st.info('Nicaragua no reporta ningún indicador al SICA y Costa Rica no reporta retorno forzado. '
            'Para el flujo nicaragüense, el único dato regional disponible es lo que registran Costa Rica y los '
            'demás países receptores: un vacío de información que conviene señalar en el eje 2.')

# ---------------------------------------------------------------- Datos y vacíos
with tab_datos:
    st.subheader('Qué datos hay detrás del mapa y qué les falta')
    st.markdown('''
- **Unidad de registro.** Cada fila de la encuesta NIC es un cantón de residencia en un mes, con el número de
  menciones de cada necesidad. La pregunta admite varias respuestas: en 326 de 659 filas aparece "ninguna necesidad"
  junto con otras necesidades. **No se conoce el número de personas encuestadas por cantón**, así que no es posible
  calcular el porcentaje de personas con una necesidad; el dashboard usa menciones, tasas por población cantonal
  y porcentaje de menciones, y lo dice en cada caso. Es la primera pregunta que conviene hacerle a OIM.
- **Cifras pequeñas.** La mediana es de 3 menciones por cantón y mes; 437 de 659 filas tienen 5 o menos. Por eso
  el mapa mensual se ve casi vacío y los valores de un solo mes no sirven para comparar cantones.
- **Cantones sin encuestas no son cantones sin necesidad.** Siete cantones (Alvarado, Barva, Flores, Jiménez,
  Montes de Oro, Osa y Turrubares) nunca aparecen en la encuesta; otros aparecen solo algunos meses. En el mapa van
  en gris, nunca como cero.
- **Diecisiete necesidades.** El archivo original trae 17 categorías. La versión limpia que circuló en el grupo
  conservó 12; aquí se reponen las cinco restantes (saneamiento e higiene, información sobre restricciones de
  movilidad, otra necesidad, artículos de higiene femenina y pañales, artículos no alimentarios), que suman
  414 menciones.
- **Denominador de las tasas.** Las tasas por 10 mil habitantes usan la población total del cantón (censo 2022),
  no la población migrante ni la encuestada: sirven para quitar el efecto del tamaño del cantón, no para medir
  prevalencia. Monteverde y Puerto Jiménez no tienen población en la tabla de OIM.
- **Oferta de servicios incompleta.** Los puntos de atención provienen de la base de 22 sedes que elaboró el grupo
  (ONG, organismos internacionales y centros municipales para migrantes), más la red pública de salud según
  OpenStreetMap (Healthsites, septiembre 2026) como respaldo de la capa oficial de la CCSS, cuyo servidor ArcGIS
  respondía con error y tenía el certificado TLS vencido el 7 y 8 de noviembre. Para necesidades distintas de salud,
  "sin puntos de atención" significa sin sedes de la base del grupo, no sin servicios públicos.
- **Columna sin explicar.** `Promedio_grupo_sin_encuestado` viene en el original sin diccionario; se conserva
  y no se usa. Preguntar a OIM si es un factor de ponderación.
''')
    with st.expander('Registro de preparación de datos (generado por scripts/preparar_datos.py)'):
        st.markdown(notas)
    with st.expander('Tabla completa de la encuesta NIC (659 filas cantón-mes)'):
        st.dataframe(nic.drop(columns=['periodo']), hide_index=True, width='stretch')
        st.download_button('Descargar nic_limpio.csv', nic.drop(columns=['periodo', 'total']).to_csv(index=False).encode('utf-8'),
                           'nic_limpio.csv', 'text/csv')
