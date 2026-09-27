-- Reconciliacion: la generacion tiene que parecerse a la demanda.
--
-- **Severidad `warn` a proposito.** No es una especificacion, es una alarma de
-- humo: la generacion nunca es igual a la demanda -hay exportaciones,
-- importaciones, bombeo y perdidas- asi que un margen razonable es lo unico que
-- se puede exigir. Que avise sin bloquear es la clasificacion honesta de algo que
-- todavia no se entiende del todo.
--
-- Por que existe: es lo que detecto el doble conteo del solar. Cada tecnologia
-- estaba dentro de su rango, la hora estaba completa, la cobertura estaba
-- completa, y aun asi el total era imposible. Ninguna comprobacion por pieza
-- puede ver eso; solo compararlo contra otra medida independiente.
--
-- Queda una discrepancia SIN EXPLICAR, y por eso este test avisa en lugar de
-- callar: el indicador 10004 -"demanda real suma de generacion"- marcaba 46.976
-- MW cuando el 1293 -"demanda real"- marcaba 28.167 a la misma hora. Los dos
-- dicen ser demanda. Hasta saber que mide cada uno, la reconciliacion se hace
-- contra el 1293, que es el que cuadra con la realidad conocida del sistema.

{{ config(severity='warn') }}

with generacion as (

    select hora, potencia_total_mw
    from {{ ref('mart_generacion_horaria') }}
    where cobertura_completa

),

demanda as (

    select hora, potencia_media_mw as demanda_mw
    from {{ ref('int_potencia_horaria') }}
    where indicador_id = 1293
      and hora_completa

)

select
    generacion.hora,
    round(generacion.potencia_total_mw, 0) as generacion_mw,
    round(demanda.demanda_mw, 0) as demanda_mw,
    round(generacion.potencia_total_mw / demanda.demanda_mw, 3) as razon

from generacion
inner join demanda using (hora)

-- Entre el 70 % y el 160 % de la demanda. El margen alto cubre exportacion y
-- bombeo; el bajo, importacion. Un doble conteo se va por encima del 160 %.
where generacion.potencia_total_mw / demanda.demanda_mw not between 0.70 and 1.60
