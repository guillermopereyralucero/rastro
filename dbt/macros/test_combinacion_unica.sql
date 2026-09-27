{#
  Comprueba que la combinacion de varias columnas no se repite: la clave primaria
  cuando no hay una sola columna que la forme.

  `coalesce` sobre las columnas que admiten nulo es deliberado: en SQL dos nulos no
  son iguales, asi que sin el, dos filas con `geo_id` nulo y todo lo demas igual
  pasarian el test siendo duplicados de verdad.
#}
{% test combinacion_unica(model, columnas) %}

with contadas as (

    select
        {% for columna in columnas %}
        {{ columna }},
        {% endfor %}
        count(*) as veces

    from {{ model }}
    group by
        {% for columna in columnas %}
        {{ loop.index }}{{ "," if not loop.last }}
        {% endfor %}

)

select * from contadas where veces > 1

{% endtest %}
