# Registro de preparación de datos

Generado por `scripts/preparar_datos.py`.

- NIC: 659 filas cantón-mes, 23 sin cantón identificable (se conservan con nota, no entran al mapa). Se conservan las 17 necesidades del original; la columna Promedio_grupo_sin_encuestado se conserva sin usar (significado por confirmar con OIM).
- Cantones: 84 polígonos INEC 2024 simplificados (150 m). Sin población en la tabla de OIM: ['Monteverde', 'Puerto Jiménez'] (cantones creados después del censo 2011; sus tasas quedan sin dato). Cantones de la tabla de OIM sin polígono: ninguno.
- Claves de cantón de NIC sin polígono INEC: ninguna.
- SICA: series mensuales 2019-01 a 2026-06 en formato largo. Países con algún dato por indicador: aprehensiones: Costa Rica, Guatemala, Honduras, Panamá, Rep. Dominicana; deportaciones: Costa Rica, Guatemala, Panamá, Rep. Dominicana; entradas regulares: Belize, Costa Rica, El Salvador, Guatemala, Honduras, Panamá, Rep. Dominicana; residencia permanente: Costa Rica, El Salvador, Guatemala, Honduras, Panamá, Rep. Dominicana; retorno forzado: Belize, El Salvador, Guatemala, Honduras, Rep. Dominicana; salidas regulares: Belize, Costa Rica, El Salvador, Guatemala, Honduras, Panamá, Rep. Dominicana. Nicaragua no reporta ningún indicador y Belice casi ninguno: es un vacío regional de datos.
