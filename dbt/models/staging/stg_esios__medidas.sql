-- Deduplicacion de las medidas crudas.
--
-- `raw.medidas` es de solo anadir: la ventana revisable se vuelve a pedir a
-- proposito, asi que un mismo punto -indicador, instante, zona- puede aparecer
-- varias veces con distintos `ingerido_en`. Aqui se conserva la ultima version,
-- que es la que REE considera buena ahora.
--
-- Lo que NO se hace es borrar las anteriores en `raw`. Que REE haya revisado un
-- valor, y cuando, es un dato en si mismo: `raw` lo guarda y `staging` decide
-- cual es la verdad vigente. Separar las dos cosas es lo que permite responder
-- "que valores ha revisado REE" con una consulta.

with ordenadas as (

    select
        indicador_id,
        instante,
        valor,
        geo_id,
        geo_nombre,
        ingerido_en,

        -- Por si una revision trae el mismo `ingerido_en`: el desempate por
        -- `valor` no es arbitrario, solo hace el resultado determinista. Sin el,
        -- dos ejecuciones podrian elegir filas distintas y los tests parpadearian.
        row_number() over (
            partition by indicador_id, instante, geo_id
            order by ingerido_en desc, valor desc
        ) as version

    from {{ source('esios', 'medidas') }}

)

select
    indicador_id,
    instante,
    valor as potencia_mw,
    geo_id,
    geo_nombre,
    ingerido_en

from ordenadas
where version = 1
