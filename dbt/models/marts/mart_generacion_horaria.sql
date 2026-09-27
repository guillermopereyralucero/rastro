-- Lo que lee el dashboard: una fila por hora, con la generacion por familia y el
-- porcentaje renovable.
--
-- Materializado como tabla y no como vista. El resto de la cadena son vistas,
-- porque no ocupan nada y se recalculan al consultarlas; aqui no, porque el
-- dashboard consulta esto muchas veces al dia y cada consulta recalcularia la
-- cadena entera. Una tabla se lee una vez.
--
-- Solo horas completas. Una hora a medio cargar daria un porcentaje renovable
-- falso, y un dashboard que dice 40 % cuando es 60 % es peor que un dashboard
-- vacio: el vacio se nota.

-- Particionada por dia, y SIN agrupamiento. Agrupar necesita una columna con
-- selectividad: aqui hay una fila por hora y zona, y la zona es siempre la
-- Peninsula, asi que no hay nada por lo que agrupar que ahorre lectura. Poner
-- `cluster_by` igualmente seria ruido que aparenta optimizacion.
{{
    config(
        partition_by={'field': 'hora', 'data_type': 'timestamp', 'granularity': 'day'}
    )
}}

with horaria as (

    select *
    from {{ ref('int_potencia_horaria') }}
    where hora_completa
      and familia = 'generacion'
      -- `sumable` excluye los agregados que solapan con sus componentes. Sin
      -- este filtro el solar se contaba dos veces -por el indicador 552 y por
      -- 1294 mas 1295- y la generacion total daba 52 GW en un sistema cuyo pico
      -- de demanda ronda los 45.
      and sumable

),

-- Cuantas tecnologias de generacion existen segun el seed. Sin este numero, el
-- mart no puede saber si le falta alguna, y un porcentaje renovable calculado
-- sobre la mitad de las tecnologias es un numero inventado con pinta de dato.
--
-- Esto no es teorico: con solo la hidraulica y la eolica cargadas, este modelo
-- publicaba 100 % renovable y una potencia total NEGATIVA -porque la hidraulica
-- resta cuando bombea-, y el test de rango 0-100 lo aceptaba, porque 100 esta
-- entre 0 y 100. El test no estaba mal: faltaba esta comprobacion.
esperadas as (

    select count(*) as tecnologias_esperadas
    from {{ ref('tecnologias') }}
    where familia = 'generacion'
      and sumable

),

agregada as (

    select
        hora,
        geo_id,
        geo_nombre,

        sum(potencia_media_mw) as potencia_total_mw,
        sum(energia_mwh) as energia_total_mwh,

        sum(if(renovable, potencia_media_mw, 0)) as potencia_renovable_mw,
        sum(if(not renovable, potencia_media_mw, 0)) as potencia_no_renovable_mw,

        count(distinct indicador_id) as tecnologias,
        max(ingerido_en) as ingerido_en

    from horaria
    group by hora, geo_id, geo_nombre

)

select
    agregada.hora,
    agregada.geo_id,
    agregada.geo_nombre,

    agregada.potencia_total_mw,
    agregada.energia_total_mwh,
    agregada.potencia_renovable_mw,
    agregada.potencia_no_renovable_mw,

    agregada.tecnologias,
    esperadas.tecnologias_esperadas,
    agregada.tecnologias = esperadas.tecnologias_esperadas as cobertura_completa,

    -- El porcentaje solo se publica si estan TODAS las tecnologias. Si falta
    -- alguna sale nulo, y un hueco en el dashboard se ve; un 100 % falso no.
    --
    -- `safe_divide` y no una division: si en una hora no hubiese generacion, una
    -- division normal reventaria el modelo entero por una fila.
    if(
        agregada.tecnologias = esperadas.tecnologias_esperadas,
        round(
            safe_divide(agregada.potencia_renovable_mw, agregada.potencia_total_mw) * 100,
            2
        ),
        null
    ) as porcentaje_renovable,

    agregada.ingerido_en

from agregada
cross join esperadas
