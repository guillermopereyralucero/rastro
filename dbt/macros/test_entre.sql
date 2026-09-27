{#
  Comprueba que una columna cae entre dos valores, ambos incluidos.

  Existe en lugar de usar `dbt_utils.accepted_range` porque este proyecto no tiene
  paquetes externos: son doce lineas y ahorran una dependencia que habria que
  fijar, actualizar y explicar.

  Los nulos se dejan pasar. Vigilarlos es trabajo de `not_null`, y un test que
  comprueba dos cosas a la vez no dice cual de las dos fallo.
#}
{% test entre(model, column_name, minimo, maximo) %}

select
    {{ column_name }} as valor,
    {{ minimo }} as minimo_esperado,
    {{ maximo }} as maximo_esperado

from {{ model }}
where {{ column_name }} is not null
  and ({{ column_name }} < {{ minimo }} or {{ column_name }} > {{ maximo }})

{% endtest %}
