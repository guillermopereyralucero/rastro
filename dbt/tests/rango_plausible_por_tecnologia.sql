-- EL PRIMER TEST DEL PROYECTO, y el que justifica que exista este fichero.
--
-- Su trabajo no es comprobar formatos: es comprobar que los numeros pueden ser
-- ciertos en el mundo fisico. Cada tecnologia tiene un rango declarado en el seed
-- `tecnologias`, y una fila fuera de ese rango es un fallo.
--
-- Que habria cazado, y que no habrian cazado los tests de siempre:
--
--   * El **37.483 de eolica** que aparecio en la primera exploracion de la API.
--     Un dato unico, no nulo, con el tipo correcto y mas grande que toda la
--     potencia eolica instalada en Espana. `not_null` y `unique` lo aceptan sin
--     pestanear. Ver docs/anomalia-generacion.md.
--
--   * Una agregacion por **SUMA en lugar de media** en int_potencia_horaria. Una
--     suma de doce lecturas da doce veces la potencia real y se sale del rango
--     inmediatamente. El test no sabe nada de agregaciones, pero las cifras
--     imposibles no tienen donde esconderse.
--
-- Y lo que NO hace, que es igual de importante: exigir valores positivos. La
-- hidraulica marca **-3.600 MW** cuando el bombeo consume, y eso es correcto. Un
-- `valor >= 0` global habria marcado como roto un dato bueno, que es el error
-- contrario y cuesta lo mismo: la confianza en el test.
--
-- Los rangos son GENEROSOS a proposito. Buscan lo imposible, no lo raro. Un rango
-- ajustado se rompe el dia que hace mas viento de lo normal, y un test que falla
-- por algo que esta bien deja de leerse a la tercera vez.

with medidas as (

    select
        indicador_id,
        instante,
        potencia_mw as valor,
        'stg_esios__medidas' as modelo
    from {{ ref('stg_esios__medidas') }}

    union all

    -- Tambien se comprueba lo agregado. Si aqui se colase una suma donde debia ir
    -- una media, el rango lo cazaria aunque los datos crudos estuviesen bien.
    select
        indicador_id,
        hora as instante,
        potencia_media_mw as valor,
        'int_potencia_horaria' as modelo
    from {{ ref('int_potencia_horaria') }}

),

tecnologias as (

    select * from {{ ref('tecnologias') }}

)

select
    medidas.modelo,
    medidas.indicador_id,
    tecnologias.tecnologia,
    medidas.instante,
    medidas.valor,
    tecnologias.min_mw,
    tecnologias.max_mw,
    case
        when medidas.valor < tecnologias.min_mw then 'por debajo del minimo'
        when medidas.valor > tecnologias.max_mw then 'por encima del maximo'
        else 'sin tecnologia declarada'
    end as motivo

from medidas
left join tecnologias using (indicador_id)

where
    -- Fuera de rango.
    medidas.valor < tecnologias.min_mw
    or medidas.valor > tecnologias.max_mw
    -- O un indicador que nadie declaro. Si se ingiere algo nuevo sin anadirlo al
    -- seed, pasaria sin rango y sin vigilancia: mejor que falle y se note.
    or tecnologias.indicador_id is null
