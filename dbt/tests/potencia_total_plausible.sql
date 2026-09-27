-- La potencia total del sistema, cuando estan todas las tecnologias.
--
-- Este test existe porque el de rango por tecnologia no lo cubre: cada tecnologia
-- puede estar dentro de su rango y la suma seguir siendo imposible. Paso de
-- verdad: con solo la hidraulica y la eolica cargadas, el mart publicaba una
-- potencia total NEGATIVA -la hidraulica resta cuando bombea- y ninguna
-- comprobacion se quejaba, porque cada pieza estaba bien por separado.
--
-- Solo se aplica a las horas con cobertura completa. Mientras falten tecnologias
-- por ingerir, una suma parcial no tiene por que parecerse a nada.
--
-- El rango: la demanda peninsular se mueve entre unos 18 y 45 GW, y la generacion
-- la sigue de cerca. 5.000 y 60.000 MW dejan margen de sobra para lo raro sin
-- dejar pasar lo imposible.

select
    hora,
    geo_nombre,
    potencia_total_mw,
    tecnologias,
    tecnologias_esperadas

from {{ ref('mart_generacion_horaria') }}
where cobertura_completa
  and (potencia_total_mw < 5000 or potencia_total_mw > 60000)
