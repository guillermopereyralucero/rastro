# Por que la eolica marcaba 37.483 "MW"

> Resuelto el 25-sep-2026 con dos peticiones a la API. Se deja escrito porque
> la conclusion condiciona todo el modelado posterior, y porque el proceso
> vale mas que el resultado.

## El numero que no cuadraba

La primera exploracion de la API de ESIOS pidio el indicador 551 (*Generacion
T.Real eolica*) para el 24 de septiembre con `time_trunc=hour`. El primer
punto del dia daba **37.483**, en un campo cuya unidad declarada es
"Potencia".

La potencia eolica instalada en Espana ronda los **32 GW**. Un valor de 37.483
MW seria mas generacion que capacidad fisica instalada: imposible.

Ante eso caben tres actitudes. Redondear y seguir. Poner una nota al pie y
seguir. O averiguar que se esta contando. Solo la tercera produce un modelo en
el que se pueda confiar.

## Las tres hipotesis

| # | Hipotesis | Como se descarta o confirma |
|---|---|---|
| 1 | La unidad no es MW | Comparar con la capacidad instalada conocida |
| 2 | El valor agrega varias zonas geograficas | Contar los `geo_id` distintos de la respuesta |
| 3 | `time_trunc=hour` agrega por suma, no por media | Pedir el mismo periodo sin `time_trunc` y comparar |

La tercera era la mas probable por aritmetica simple: 37.483 dividido entre 12
da 3.124, y dividido entre 6 da 6.247. Ambos son valores de eolica
perfectamente normales a medianoche. Eso sugeria una serie sub-horaria sumada.

## La comprobacion: dos peticiones

`rastro diagnostico 551 --dia 2026-09-24` pide el mismo dia dos veces, con y
sin `time_trunc`, y compara la primera hora.

```
--- sin time_trunc: 288 puntos, 1 zonas
    geo 8741 (Península): 288 puntos, min 1265.0  max 2900.0  media 2132.1
    2026-09-24 00:00Z  geo 8741  2801.0
    2026-09-24 00:05Z  geo 8741  2785.0
    2026-09-24 00:10Z  geo 8741  2738.0

--- time_trunc=hour: 24 puntos, 1 zonas
    geo 8741 (Península): 24 puntos, min 15456.0  max 33902.0  media 25585.4
    2026-09-24 00:00Z  geo 8741  32307.0

--- hora 2026-09-24 00:00Z, geo 8741
    valor con time_trunc=hour : 32307.000
    puntos sub-horarios       : 12
    su suma                   : 32307.000
    su media                  : 2692.250
    => time_trunc=hour SUMA. El valor horario no es potencia media.
```

## La conclusion

**La hipotesis 3, y de forma exacta.**

- La serie se publica **cada 5 minutos**: 288 puntos al dia, 12 por hora.
- `time_trunc=hour` **suma** esas 12 lecturas. La coincidencia es exacta, no
  aproximada: 32.307 es la suma de los doce valores de esa hora.
- La potencia eolica real a las 00:00Z del 24-sep era de **2.692 MW de
  media**, con un maximo de 2.900 MW. Plausible sin discusion frente a los
  32 GW instalados.
- Las hipotesis 1 y 2 quedan descartadas por la misma respuesta: la unidad si
  es MW en los puntos crudos, y solo hay **una** zona geografica (8741,
  Peninsula), asi que no habia doble conteo.

Sumar potencias instantaneas de intervalos de 5 minutos no produce ninguna
magnitud fisica util. No es potencia, y tampoco es energia: para obtener MWh
habria que multiplicar cada lectura por su duracion (5/60 h) antes de sumar.
`time_trunc=hour` da un numero que no es ninguna de las dos cosas.

## Que consecuencias tiene

**1 · La ingesta no usa `time_trunc`.** Se pide el dato tal y como se publica,
a 5 minutos, y la agregacion ocurre en dbt, donde el criterio esta escrito,
versionado y probado. Delegar la agregacion en un parametro de la API cuyo
criterio no esta documentado es precisamente como se llega a un 37.483 en un
dashboard.

Por eso `ClienteESIOS.valores()` no manda `time_trunc` salvo que se le pida a
proposito, y hay un test que lo fija:
`test_time_trunc_no_se_envia_salvo_que_se_pida`.

**2 · El primer test de dbt es un rango plausible por tecnologia.** Un modelo
que no sabe que la eolica no puede pasar de ~32 GW aceptara cualquier cosa que
le llegue. El test de rango es barato y habria cazado esto el primer dia.

**3 · Volumen real de la plataforma.** 288 puntos al dia por 16 indicadores son
**4.608 filas diarias**, alrededor de **1,7 millones al ano**. Cabe de sobra en
los 10 GiB gratuitos de BigQuery, y ademas justifica la particion por fecha:
las consultas del dashboard miran siempre una ventana temporal.

**4 · El streaming deja de ser un adorno.** Una serie que se actualiza cada 5
minutos justifica de verdad una arquitectura de ingesta continua. Con datos
horarios habria sido un ejercicio.

## La moraleja, que es la parte que importa

Un numero que contradice la realidad fisica no es un detalle de formato: es la
senal de que no se sabe que se esta midiendo. Descartarlo cuesta dos
peticiones. Modelar encima de el cuesta un trimestre de decisiones tomadas
sobre datos que no significan lo que parecia.
