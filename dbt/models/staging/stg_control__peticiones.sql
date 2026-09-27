-- Auditoria de las peticiones a ESIOS, con el desenlace derivado.
--
-- El `exito` se calcula aqui y no en cada consulta que lo necesite: la regla de
-- que una peticion salio bien -codigo 200 y sin error- es una sola, y repetirla en
-- tres sitios es garantizar que algun dia difieran.

select
    momento,
    indicador_id,
    ventana_inicio,
    ventana_fin,
    codigo,
    intentos,
    puntos,
    segundos,
    error,

    codigo = 200 and error is null as exito,

    -- Reintentos consumidos. Interesa aparte de `intentos` porque un valor alto
    -- aqui significa que ESIOS iba mal, no que hubiese mas trabajo que hacer.
    intentos - 1 as reintentos,

    timestamp_diff(ventana_fin, ventana_inicio, hour) as horas_pedidas

from {{ source('control', 'peticiones') }}
