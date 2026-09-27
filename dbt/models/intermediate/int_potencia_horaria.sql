-- Agregacion horaria. Este modelo es la leccion del 37.483 escrita en SQL.
--
-- El error que hay que no cometer: `time_trunc=hour` de la API de ESIOS SUMA las
-- doce lecturas de cinco minutos de cada hora. Eso da 32.307 para una eolica que
-- estaba generando 2.692 MW, y no es ni potencia ni energia.
--
-- Lo correcto, y por que:
--
--   * **Potencia media (MW)** = media de las lecturas. Una lectura es potencia
--     instantanea, y la media de potencias es una potencia.
--
--   * **Energia (MWh)** = suma de (potencia x duracion). Con lecturas cada cinco
--     minutos: sum(P * 5/60) = (5/60) * sum(P) = (5/60) * 12 * avg(P) = avg(P).
--     O sea que en una hora completa la energia en MWh coincide numericamente con
--     la potencia media en MW. No es una casualidad simpatica: es la razon de que
--     confundir las dos magnitudes pase desapercibido, y de que la comprobacion
--     tenga que ser el rango fisico y no el parecido entre dos numeros.
--
--   * Cuando faltan lecturas, la **media** de las presentes sigue siendo una
--     estimacion razonable de la potencia, pero la **energia** ya no: por eso se
--     cuenta `lecturas` y se marca `hora_completa`. Un dato incompleto que no se
--     sabe incompleto es peor que no tenerlo.

with medidas as (

    select * from {{ ref('stg_esios__medidas') }}

),

tecnologias as (

    select * from {{ ref('tecnologias') }}

)

select
    timestamp_trunc(medidas.instante, hour) as hora,
    medidas.indicador_id,
    tecnologias.tecnologia,
    tecnologias.familia,
    tecnologias.renovable,
    tecnologias.sumable,
    medidas.geo_id,
    medidas.geo_nombre,

    -- Potencia media de la hora. Lo que ESIOS deberia haber devuelto.
    avg(medidas.potencia_mw) as potencia_media_mw,
    min(medidas.potencia_mw) as potencia_min_mw,
    max(medidas.potencia_mw) as potencia_max_mw,

    -- Energia de la hora. Se escribe con la duracion explicita en lugar de
    -- aprovechar que coincide con la media: asi el codigo dice lo que hace y
    -- sigue siendo correcto si algun dia la serie cambia de cadencia.
    sum(medidas.potencia_mw * (5.0 / 60.0)) as energia_mwh,

    count(*) as lecturas,
    count(*) = 12 as hora_completa,
    max(medidas.ingerido_en) as ingerido_en

from medidas
left join tecnologias using (indicador_id)

group by
    hora,
    medidas.indicador_id,
    tecnologias.tecnologia,
    tecnologias.familia,
    tecnologias.renovable,
    tecnologias.sumable,
    medidas.geo_id,
    medidas.geo_nombre
