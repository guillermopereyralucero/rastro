-- Una fila por hora y tecnologia. Es lo que necesita un grafico de areas
-- apiladas: el mart de totales agrega la tecnologia y ahi ya no hay nada que
-- apilar.
--
-- Solo tecnologias sumables, igual que el mart de totales: el indicador 552
-- "Solar" solapa con la fotovoltaica y la termica, asi que apilarlo junto a ellas
-- dibujaria el solar dos veces en el grafico. Un doble conteo en una tabla es un
-- numero mal; en un grafico apilado es una mentira que se ve bonita.

{{
    config(
        partition_by={'field': 'hora', 'data_type': 'timestamp', 'granularity': 'day'},
        cluster_by=['tecnologia']
    )
}}

with horaria as (

    select *
    from {{ ref('int_potencia_horaria') }}
    where hora_completa
      and familia = 'generacion'
      and sumable

),

totales as (

    -- Solo horas con TODAS las tecnologias. Un total parcial como denominador da
    -- porcentajes por encima de 100: paso de verdad -la eolica salio al 176 % en
    -- la hora de la primera prueba, cuando solo habia dos indicadores cargados-.
    -- Al filtrar aqui, esas horas se quedan con el porcentaje nulo y la potencia
    -- en MW intacta, que es la que si es correcta.
    select hora, geo_id, potencia_total_mw
    from {{ ref('mart_generacion_horaria') }}
    where cobertura_completa

)

select
    horaria.hora,
    horaria.geo_id,
    horaria.geo_nombre,
    horaria.indicador_id,
    horaria.tecnologia,
    horaria.renovable,

    -- Orden del apilado, de abajo arriba. Existe porque Looker Studio NO permite
    -- reordenar las series a mano: el apilado sigue el orden de clasificacion, y
    -- lo unico por lo que se puede clasificar es un campo. Asi que el orden es un
    -- dato del dominio -abajo lo estable, arriba lo variable- y vive en el seed,
    -- versionado, en lugar de en un ajuste del informe que nadie puede reproducir.
    horaria.orden_apilado,

    horaria.potencia_media_mw,
    horaria.potencia_min_mw,
    horaria.potencia_max_mw,
    horaria.energia_mwh,

    -- El peso de cada tecnologia dentro de su hora. Calculado aqui y no en el
    -- informe porque un porcentaje dentro de una hora necesita el total de ESA
    -- hora, y eso en una herramienta de cuadros de mando acaba en una tabla
    -- dinamica que nadie sabe reproducir.
    round(
        safe_divide(horaria.potencia_media_mw, totales.potencia_total_mw) * 100,
        2
    ) as porcentaje_del_mix,

    horaria.ingerido_en

from horaria
left join totales
    on horaria.hora = totales.hora
    and horaria.geo_id = totales.geo_id
