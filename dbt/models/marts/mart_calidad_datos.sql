-- Salud de la plataforma, por dia.
--
-- Este modelo es el que convierte el cuadro de mando en algo de ingeniero de
-- datos. Cualquiera puede graficar generacion renovable; lo que casi nadie ensena
-- es **si los datos que esta graficando son fiables**, y eso es exactamente la
-- pregunta de la que vive Rastro.
--
-- Cuatro cosas que mide:
--
--   1. **Cobertura**: cuantas horas del dia estan completas y cuantas a medias.
--   2. **Revisiones**: cuantos puntos ha cambiado REE despues de publicarlos. Esto
--      solo se puede saber porque `raw` es de solo anadir; si se sobreescribiera,
--      la pregunta no tendria respuesta.
--   3. **Frescura**: cuanto hace del ultimo dato.
--   4. **Peticiones**: cuantas se hicieron a ESIOS y cuantas fallaron, que es la
--      cuenta que hay que poder dar a quien cede la cuota.

{{
    config(
        partition_by={'field': 'dia', 'data_type': 'date', 'granularity': 'day'}
    )
}}

with horas as (

    select
        date(hora) as dia,
        count(*) as filas_horarias,
        countif(hora_completa) as horas_completas,
        countif(not hora_completa) as horas_parciales,
        count(distinct indicador_id) as indicadores,
        min(lecturas) as lecturas_min,
        max(ingerido_en) as ultimo_dato

    from {{ ref('int_potencia_horaria') }}
    group by dia

),

-- Un punto revisado es uno que aparece mas de una vez en `raw` con distintos
-- `ingerido_en`. Se cuenta sobre la fuente y no sobre staging, porque staging ya
-- se quedo solo con la ultima version: ahi la revision ya no existe.
revisiones as (

    select
        date(instante) as dia,
        countif(veces > 1) as puntos_revisados,
        count(*) as puntos_totales

    from (
        select
            instante,
            count(*) as veces
        from {{ source('esios', 'medidas') }}
        group by instante, indicador_id, geo_id
    )
    group by dia

),

peticiones as (

    select
        date(momento) as dia,
        count(*) as peticiones,
        countif(codigo = 200 and error is null) as peticiones_ok,
        countif(codigo != 200 or error is not null) as peticiones_fallidas,
        sum(intentos) as intentos_http,
        sum(puntos) as puntos_obtenidos,
        round(avg(segundos), 3) as segundos_medios

    from {{ ref('stg_control__peticiones') }}
    group by dia

)

select
    horas.dia,

    -- Cobertura
    horas.indicadores,
    horas.horas_completas,
    horas.horas_parciales,
    round(
        safe_divide(horas.horas_completas, horas.filas_horarias) * 100, 2
    ) as porcentaje_horas_completas,

    -- Revisiones de REE
    coalesce(revisiones.puntos_revisados, 0) as puntos_revisados,
    coalesce(revisiones.puntos_totales, 0) as puntos_totales,
    round(
        safe_divide(revisiones.puntos_revisados, revisiones.puntos_totales) * 100, 3
    ) as porcentaje_revisado,

    -- Peticiones a ESIOS
    coalesce(peticiones.peticiones, 0) as peticiones,
    coalesce(peticiones.peticiones_ok, 0) as peticiones_ok,
    coalesce(peticiones.peticiones_fallidas, 0) as peticiones_fallidas,
    coalesce(peticiones.intentos_http, 0) as intentos_http,
    peticiones.segundos_medios,

    -- Frescura. En minutos porque en horas se pierde el detalle que importa: la
    -- serie se publica cada cinco minutos.
    horas.ultimo_dato,
    timestamp_diff(current_timestamp(), horas.ultimo_dato, minute) as minutos_desde_el_ultimo_dato

from horas
left join revisiones using (dia)
left join peticiones using (dia)
