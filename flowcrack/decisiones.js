// Generado por build.py. No editar a mano.
// Fuente: decisiones.yaml
window.FLOWCRACK = {
  "formato": 2,
  "generado": "2026-09-27 19:10",
  "proyecto": {
    "nombre": "Rastro",
    "perfil": "investigacion",
    "seguimiento": "../docs/seguimiento.md",
    "publico": true
  },
  "vocabulario": {
    "carriles": [
      {
        "id": "pregunta",
        "nombre": "Pregunta",
        "descripcion": "Que se quiere averiguar y por que importa"
      },
      {
        "id": "metodo",
        "nombre": "Metodo",
        "descripcion": "Como se va a averiguar"
      },
      {
        "id": "fuentes",
        "nombre": "Fuentes",
        "descripcion": "Con que material se trabaja y de donde sale"
      },
      {
        "id": "analisis",
        "nombre": "Analisis",
        "descripcion": "Que se hace con el material"
      },
      {
        "id": "difusion",
        "nombre": "Difusion",
        "descripcion": "Donde y como se publica"
      },
      {
        "id": "etica",
        "nombre": "Etica y permisos",
        "descripcion": "Consentimientos, licencias, comites"
      }
    ],
    "hitos": [
      {
        "id": "pregunta-central",
        "pregunta": "Cual es la pregunta que se responde?"
      },
      {
        "id": "evaluacion",
        "pregunta": "Como se sabe que Rastro responde bien?"
      },
      {
        "id": "corpus",
        "pregunta": "Con que material se trabaja?"
      },
      {
        "id": "metodo",
        "pregunta": "Que metodo se emplea?"
      },
      {
        "id": "permisos",
        "pregunta": "Que permisos o consentimientos hacen falta?",
        "irreversible": true
      },
      {
        "id": "donde-se-publica",
        "pregunta": "Donde se publica y bajo que licencia?"
      },
      {
        "id": "alcance-temporal",
        "pregunta": "Que periodo o ambito cubre, y cual queda fuera?"
      }
    ],
    "impacto": {
      "pregunta": "Si manana lo cambiamos, que hay que rehacer?",
      "valores": {
        "mayor": "Revertirla obliga a rehacer trabajo ya hecho en otras areas",
        "menor": "Revertirla afecta a trabajo no empezado, o queda en un solo carril",
        "parche": "Revertirla no cambia nada de lo ya construido"
      }
    },
    "tipos": {
      "pregunta": "Habia alternativas entre las que elegir?",
      "valores": {
        "decision": "Habia alternativas y se eligio una",
        "hallazgo": "No se eligio nada, se descubrio un hecho que cambio lo que sabiamos",
        "medicion": "Un hallazgo con cifra, obtenido midiendo",
        "hito-externo": "Ocurre fuera del proyecto y no lo controlas"
      }
    },
    "irreversible": {
      "criterio": "Solo si al deshacerla se pierde algo que no se recupera: usuarios, dinero gastado, datos, una ventana temporal. \"Seria incomodo\" no cuenta: eso es impacto mayor.\n"
    }
  },
  "carriles": [
    {
      "id": "pregunta",
      "nombre": "Pregunta",
      "descripcion": "Que se quiere averiguar y por que importa"
    },
    {
      "id": "metodo",
      "nombre": "Metodo",
      "descripcion": "Como se va a averiguar"
    },
    {
      "id": "fuentes",
      "nombre": "Fuentes",
      "descripcion": "Con que material se trabaja y de donde sale"
    },
    {
      "id": "analisis",
      "nombre": "Analisis",
      "descripcion": "Que se hace con el material"
    },
    {
      "id": "difusion",
      "nombre": "Difusion",
      "descripcion": "Donde y como se publica"
    },
    {
      "id": "etica",
      "nombre": "Etica y permisos",
      "descripcion": "Consentimientos, licencias, comites"
    }
  ],
  "preguntas_abiertas": [
    {
      "id": "evaluacion",
      "pregunta": "Como se sabe que Rastro responde bien?",
      "irreversible": false
    }
  ],
  "decisiones": [
    {
      "id": "r001",
      "fecha": "2026-09-25",
      "orden": 1,
      "carril": "etica",
      "titulo": "ESIOS es privado, BigQuery es publico: nada publico llama a la API",
      "tipo": "decision",
      "detalle": "Regla operativa: ESIOS -> (privado) -> BigQuery -> (publico) -> todo lo demas. El unico componente que habla con la API es el job de ingesta, que corre con el token, en el proyecto de Guillermo y sin exponerse.",
      "porque": "El correo del token trae una condicion explicita de REE: si el proyecto da acceso publico, los datos que devuelve la API deben servirse desde un servidor propio y no desde los sistemas de REE. No es una recomendacion, es lo que permite que el repo sea publico.",
      "consecuencia": "Ni el dashboard, ni el visor de Rastro, ni la capa de lenguaje natural pueden consultar ESIOS. Todos leen BigQuery.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": true,
      "hito": "permisos",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Ingesta privada a BigQuery y todo lo publico leyendo de ahi",
          "elegida": true,
          "motivo": "Cumple la condicion de REE y ademas es la arquitectura correcta"
        },
        {
          "opcion": "Que el dashboard consulte ESIOS en directo",
          "elegida": false,
          "motivo": "Incumple la condicion del token y haria el proyecto impublicable"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r002",
      "fecha": "2026-09-25",
      "orden": 2,
      "carril": "etica",
      "titulo": "Ingesta incremental con marca de agua, impuesta por REE",
      "tipo": "decision",
      "detalle": "Marca de agua por indicador en una tabla de control. Los periodos cerrados no se vuelven a pedir nunca; solo se refresca la ventana de las ultimas horas. El catalogo se valida en local antes de salir a la red. Reintentos con espera exponencial y tope de peticiones por ejecucion.",
      "porque": "La segunda condicion de REE prohibe peticiones masivas, redundantes o innecesarias, y la tercera prohibe pedir indicadores inexistentes. Lo que en otro proyecto seria una buena practica opcional, aqui es requisito.",
      "consecuencia": "La ingesta incremental deja de ser un extra y pasa a ser el nucleo del diseno, que es justo lo que se espera de un senior y casi ningun portfolio hace.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Marca de agua por indicador y validacion local del catalogo",
          "elegida": true,
          "motivo": "Cumple las dos condiciones y es lo que se pediria en produccion"
        },
        {
          "opcion": "Recarga completa en cada ejecucion",
          "elegida": false,
          "motivo": "Peticiones redundantes: prohibido por las condiciones del token"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r003",
      "fecha": "2026-09-25",
      "orden": 3,
      "carril": "difusion",
      "titulo": "El proyecto se llama Rastro",
      "tipo": "decision",
      "detalle": "",
      "porque": "Corto, dice lo que hace (seguir el rastro de un dato) y es distintivo en un ecosistema lleno de nombres en ingles. Cambiarlo hoy es gratis; en cuanto exista repo publico, paquete pip, comando y articulo, ya no.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Rastro",
          "elegida": true,
          "motivo": "Corto, descriptivo y distintivo"
        },
        {
          "opcion": "Lineo",
          "elegida": false,
          "motivo": "Mas literal pero se pierde entre los nombres genericos del sector"
        },
        {
          "opcion": "Trazo",
          "elegida": false,
          "motivo": "Encaja con el visor, pero mas abstracto sobre que hace"
        },
        {
          "opcion": "Downstream",
          "elegida": false,
          "motivo": "Termino generico del sector, invisible junto a dbt y OpenLineage"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r004",
      "fecha": "2026-09-25",
      "orden": 4,
      "carril": "difusion",
      "titulo": "Repo publico desde el primer commit, con el registro de decisiones dentro",
      "tipo": "decision",
      "detalle": "El repositorio git publico es la subcarpeta `rastro/`. La carpeta de trabajo `AI-Rastro/` no es un repo y nunca se inicializa como tal, porque contiene `notas/` con el token y contexto de una busqueda de empleo.",
      "porque": "El historial visible es parte del escaparate: se ve como se construyo, no solo el resultado. Y un registro de decisiones razonado dentro de un repo publico es exactamente lo que diferencia a este proyecto de los cien portfolios que un recruiter tecnico ya ha visto.",
      "consecuencia": "Tambien se ven los tropiezos. Se asume a cambio de que el proceso sea auditable.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": true,
      "hito": "donde-se-publica",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Publico desde el commit 1 con FlowCrack dentro",
          "elegida": true,
          "motivo": "El historial y el razonamiento son parte de lo que se ensena"
        },
        {
          "opcion": "Publico pero con el registro de decisiones en notas/",
          "elegida": false,
          "motivo": "Se pierde el argumento mas diferenciador por miedo a los errores"
        },
        {
          "opcion": "Privado hasta tener algo presentable",
          "elegida": false,
          "motivo": "Sin historial visible el repo vale lo mismo que un zip"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r005",
      "fecha": "2026-09-25",
      "orden": 5,
      "carril": "etica",
      "titulo": "La herramienta previa del trabajo se usa como fuente de requisitos, nunca de codigo",
      "tipo": "decision",
      "detalle": "De ella se toman ideas de diseno ya validadas contra 26 proyectos reales: bloque de metricas con reconciliacion, auditoria por objeto con motivo de exclusion, parseo de SQL en dos pasadas con respaldo por regex, y el visor de un solo fichero. No se copia codigo, ni identificadores de proyecto, ni nombres de tabla, ni la paleta corporativa del cliente.",
      "porque": "La idea de una herramienta de linaje no es de nadie (existen dbt docs, OpenLineage y Dataplex), pero una implementacion hecha para un cliente si lo es. Leerla para saber que preguntas importan y que falla no cruza esa linea; copiarla si.",
      "consecuencia": "En entrevista se puede decir sin ambiguedad: en el trabajo resolvi un problema parecido y lo adoptaron 48 personas; aqui esta mi propia version, publica y disenada desde cero.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": true,
      "hito": "permisos",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Fuente de requisitos, no de codigo",
          "elegida": true,
          "motivo": "Aprovecha la experiencia real sin tocar obra hecha para un cliente"
        },
        {
          "opcion": "No abrirla siquiera",
          "elegida": false,
          "motivo": "Renuncia a saber que preguntas importan y que falla, sin ganar nada: el riesgo esta en copiar, no en leer\n"
        },
        {
          "opcion": "Adaptar el codigo",
          "elegida": false,
          "motivo": "Es obra hecha para un cliente y lleva dentro sus ids y sus tablas"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r006",
      "fecha": "2026-09-25",
      "orden": 6,
      "carril": "metodo",
      "titulo": "En el portatil no hay gcloud, terraform, bq, docker, dbt ni jq",
      "tipo": "hallazgo",
      "detalle": "Comprobado el 25-sep: solo estan Python 3.12.3 y git 2.38.1. El plan por semanas daba por instalado el tooling de nube.",
      "porque": "Se comprobo antes de asumirlo, siguiendo la regla de verificar antes de afirmar. Cambia el orden del plan: la semana 1 no puede empezar por Terraform.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [
        "r007",
        "r008"
      ],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r007",
      "fecha": "2026-09-25",
      "orden": 7,
      "carril": "metodo",
      "titulo": "Rastro se escribe en Python puro, no en bash con bq CLI y jq",
      "tipo": "decision",
      "detalle": "Cliente `google-cloud-bigquery` en lugar del CLI `bq`, y `json` de la libreria estandar en lugar de `jq`. Empaquetado con pyproject, instalable con pip, con su comando de consola.",
      "porque": "Rastro es una herramienta pensada para que otros la adopten, y eso decide el lenguaje: en bash exige instalar el SDK de gcloud entero, se comporta distinto en Windows, no hay forma razonable de testearlo y no se distribuye por pip. En Python se instala con una orden, corre igual en los tres sistemas y los tests son triviales.",
      "consecuencia": "El CI puede ejecutar la suite de tests sin nube y sin credenciales.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Python puro con google-cloud-bigquery",
          "elegida": true,
          "motivo": "Instalable con pip, multiplataforma y testeable"
        },
        {
          "opcion": "Bash con bq CLI y jq",
          "elegida": false,
          "motivo": "Exige el SDK de gcloud completo, falla en Windows y no hay manera seria de testearlo ni de distribuirlo\n"
        },
        {
          "opcion": "Python llamando al CLI bq por debajo",
          "elegida": false,
          "motivo": "Arrastra la dependencia del SDK sin ganar nada sobre el cliente"
        }
      ],
      "causada_por": [
        "r006"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r008",
      "fecha": "2026-09-25",
      "orden": 8,
      "carril": "metodo",
      "titulo": "Se arranca por el cliente de ingesta en local, sin nube",
      "tipo": "decision",
      "detalle": "Semana 1 reordenada: repo, registro de decisiones, cliente ESIOS con marca de agua y tests, todo en local. Terraform y BigQuery entran cuando el proyecto de GCP este completo y el tooling instalado.",
      "porque": "El cliente de ingesta y sus tests corren contra la API sin necesitar nube, asi que es lo unico del plan que avanza hoy. Ademas es donde vive la anomalia de datos que hay que resolver antes de modelar nada.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Ingesta en local primero",
          "elegida": true,
          "motivo": "Avanza hoy sin instalar nada y desbloquea el modelado"
        },
        {
          "opcion": "Instalar gcloud y Terraform y seguir la semana 1 tal cual",
          "elegida": false,
          "motivo": "La sesion se va en instalar y autenticar, sin nada que ensenar"
        },
        {
          "opcion": "Empezar por el nucleo de Rastro",
          "elegida": false,
          "motivo": "Sin plataforma propia que analizar, el grafo es de juguete"
        }
      ],
      "causada_por": [
        "r006"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r009",
      "fecha": "2026-09-25",
      "orden": 9,
      "carril": "fuentes",
      "titulo": "El proyecto de GCP se llama Rastro y esta a medias",
      "tipo": "hito-externo",
      "detalle": "Existe el proyecto pero falta confirmar facturacion activada y la alerta de presupuesto a 1 EUR. Falta tambien el id real del proyecto, que no es el nombre visible.",
      "porque": "Sin facturacion activada no hay capa gratuita, y sin alerta de presupuesto no hay red de seguridad para un objetivo de coste de 0 EUR.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r010",
      "fecha": "2026-09-25",
      "orden": 10,
      "carril": "pregunta",
      "titulo": "La pregunta que responde Rastro: que se rompe si toco esta tabla",
      "tipo": "decision",
      "detalle": "Cuatro preguntas concretas sobre el grafo de dependencias de BigQuery y dbt. De donde sale esta tabla (linaje aguas arriba, a traves de vistas anidadas). Que se rompe si la borro o le cambio una columna (radio de impacto aguas abajo). Que tablas no consulta nadie desde hace 90 dias (dinero en almacenamiento). Hay dependencias rotas o ciclos.",
      "porque": "Es la pregunta que nadie sabe responder en una plataforma de datos que ha crecido, y por eso nadie se atreve a borrar nada. Ademas se puede responder con consultas a INFORMATION_SCHEMA, que en BigQuery no se facturan: la herramienta cuesta cero euros ejecutarla.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "pregunta-central",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Una herramienta de linaje e impacto",
          "elegida": true,
          "motivo": "El 95% de los portfolios de datos son ingesta mas dashboard; una herramienta que otros adoptan es otra categoria\n"
        },
        {
          "opcion": "Un pipeline con dashboard",
          "elegida": false,
          "motivo": "Un recruiter tecnico ya ha visto cien iguales"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r011",
      "fecha": "2026-09-25",
      "orden": 11,
      "carril": "fuentes",
      "titulo": "El corpus son 16 indicadores de ESIOS a 5 minutos",
      "tipo": "decision",
      "detalle": "Generacion en tiempo real por tecnologia (hidraulica, carbon, fuel-gas, nuclear, ciclo combinado, eolica, solar, solar termica, fotovoltaica, termica renovable, cogeneracion, intercambios y resto) mas demanda real, nacional y suma de generacion. Una sola zona geografica, la Peninsula (geo_id 8741). 288 puntos al dia por indicador.",
      "porque": "Son las series que cuentan la historia completa de un dia electrico espanol, y ademas es un sector que interesa a Guillermo: un proyecto sobre generacion renovable es conversacion con las empresas a las que quiere entrar.",
      "consecuencia": "4.608 filas al dia, unos 1,7 millones al ano. Cabe de sobra en los 10 GiB gratuitos de BigQuery y justifica particionar por fecha.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "corpus",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "16 indicadores de generacion y demanda peninsular",
          "elegida": true,
          "motivo": "Cuentan un dia electrico completo sin inflar el volumen"
        },
        {
          "opcion": "Los 1.983 indicadores del catalogo",
          "elegida": false,
          "motivo": "Peticiones masivas, prohibidas por las condiciones del token"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r012",
      "fecha": "2026-09-25",
      "orden": 12,
      "carril": "analisis",
      "titulo": "time_trunc=hour de ESIOS suma las lecturas de 5 minutos, no las promedia",
      "tipo": "medicion",
      "detalle": "Comprobado con dos peticiones sobre el indicador 551 del 24-sep. Sin time_trunc la API devuelve 288 puntos al dia, uno cada 5 minutos. Con time_trunc=hour devuelve 24, y el valor de las 00:00Z es 32.307, que es la suma exacta de las doce lecturas de esa hora. La potencia eolica real de esa hora era 2.692 MW de media, plausible frente a los 32 GW instalados. Una sola zona geografica, asi que no habia doble conteo.",
      "porque": "El valor de 37.483 en unidad \"Potencia\" superaba la potencia eolica instalada en Espana. Un numero que contradice la realidad fisica no es un detalle de formato: es la senal de que no se sabe que se esta midiendo.",
      "consecuencia": "Sumar potencias instantaneas no produce ninguna magnitud util: no es potencia, y tampoco energia, porque para MWh habria que multiplicar cada lectura por su duracion antes de sumar. Escrito en docs/anomalia-generacion.md.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [
        "r013",
        "r014"
      ],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r013",
      "fecha": "2026-09-25",
      "orden": 13,
      "carril": "analisis",
      "titulo": "La ingesta pide el dato crudo a 5 minutos y agrega en dbt",
      "tipo": "decision",
      "detalle": "`ClienteESIOS.valores()` no manda `time_trunc` salvo que se le pida a proposito, y hay un test que lo fija.",
      "porque": "Delegar la agregacion en un parametro de la API cuyo criterio no esta documentado es exactamente como se llega a un 37.483 en un dashboard. En dbt el criterio esta escrito, versionado y probado.",
      "consecuencia": "Se ingiere 12 veces mas volumen, que sigue siendo trivial (1,7 M filas al ano), y a cambio la agregacion es auditable. Ademas una serie que cambia cada 5 minutos justifica de verdad el streaming.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Ingerir crudo a 5 minutos y agregar en dbt",
          "elegida": true,
          "motivo": "El criterio de agregacion queda escrito, versionado y probado"
        },
        {
          "opcion": "Dejar que ESIOS agregue con time_trunc",
          "elegida": false,
          "motivo": "Suma lecturas instantaneas y produce una magnitud sin sentido"
        },
        {
          "opcion": "Agregar en el cliente de ingesta",
          "elegida": false,
          "motivo": "Esconde el criterio en codigo Python en vez de en el modelo"
        }
      ],
      "causada_por": [
        "r012"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r014",
      "fecha": "2026-09-25",
      "orden": 14,
      "carril": "analisis",
      "titulo": "El primer test de dbt es un rango plausible por tecnologia",
      "tipo": "decision",
      "detalle": "",
      "porque": "Un modelo que no sabe que la eolica no puede pasar de unos 32 GW aceptara cualquier cosa que le llegue. El test de rango es barato y habria cazado la anomalia el primer dia, sin necesidad de que alguien mirase el numero con desconfianza.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Rango plausible por tecnologia como primer test",
          "elegida": true,
          "motivo": "Barato, y captura la clase de error que de verdad pasa"
        },
        {
          "opcion": "Empezar por tests de unicidad y no nulos",
          "elegida": false,
          "motivo": "Son los que trae todo el mundo y no habrian detectado nada: el dato era unico, no nulo y estaba mal\n"
        }
      ],
      "causada_por": [
        "r012"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r015",
      "fecha": "2026-09-25",
      "orden": 15,
      "carril": "metodo",
      "titulo": "El nucleo del paquete se instala sin dependencias",
      "tipo": "decision",
      "detalle": "La ingesta usa `urllib` de la libreria estandar. `google-cloud-bigquery` queda como extra opcional, en `pip install rastro[bigquery]`.",
      "porque": "Para una herramienta pensada para que otros la adopten, cada dependencia que no esta es una excusa menos para no instalarla. Quien solo quiera mirar un grafo no deberia tener que traerse medio SDK de Google.",
      "consecuencia": "La suite de tests corre en CI sin token, sin nube y sin credenciales, porque el transporte HTTP se inyecta.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Nucleo sin dependencias, con urllib",
          "elegida": true,
          "motivo": "Se instala en cualquier sitio y no arrastra nada"
        },
        {
          "opcion": "Usar requests",
          "elegida": false,
          "motivo": "Mas comodo de escribir, pero es una dependencia por un GET"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r016",
      "fecha": "2026-09-26",
      "orden": 1,
      "carril": "difusion",
      "titulo": "El repositorio ya es publico en github.com/guillermopereyralucero/rastro",
      "tipo": "hito-externo",
      "detalle": "Publicado con dos commits y 28 ficheros, con temas (bigquery, dbt, data-lineage, data-engineering, gcp, terraform, esios, open-data) y CI corriendo. Antes de publicar se verifico que el token de ESIOS no aparece en el historial completo, no solo en el arbol de trabajo.",
      "porque": "La decision r004 ya lo habia fijado: publico desde el primer commit, porque el historial visible es parte del escaparate.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": true,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [
        "r004"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r017",
      "fecha": "2026-09-26",
      "orden": 2,
      "carril": "fuentes",
      "titulo": "El proyecto de GCP es rastro-509715, region europe-southwest1",
      "tipo": "decision",
      "detalle": "Madrid. La capa gratuita de BigQuery se aplica igual en cualquier region, asi que la eleccion se hace por otra cosa.",
      "porque": "Son datos del sistema electrico espanol: la residencia del dato y la latencia quedan donde corresponde, y ademas es un detalle que se explica bien en una entrevista.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "europe-southwest1 (Madrid)",
          "elegida": true,
          "motivo": "Residencia coherente con el origen del dato, sin coste extra"
        },
        {
          "opcion": "Multirregion EU",
          "elegida": false,
          "motivo": "Mas margen si algun servicio no llega a Madrid, pero el dato espanol acabaria replicado por media Europa sin necesidad\n"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r018",
      "fecha": "2026-09-26",
      "orden": 3,
      "carril": "metodo",
      "titulo": "La alerta de presupuesto se declara en Terraform, no en la consola",
      "tipo": "decision",
      "detalle": "Techo de 1 EUR con avisos al 50, 90 y 100 por ciento, mas uno sobre el gasto previsto del mes. Recurso `google_billing_budget`.",
      "porque": "Una alerta creada a mano no esta en ningun sitio: nadie sabe que existe, nadie la revisa y si el proyecto se recrea desaparece. En Terraform esta versionada y se revisa en el pull request. Ademas es coherente con el resto del proyecto, donde nada se crea por consola.",
      "consecuencia": "Un presupuesto en GCP no corta el servicio, solo avisa. Asi que no es un limite sino un detector de humo: con objetivo de coste 0 EUR, cualquier cargo es por definicion algo no previsto.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Presupuesto en Terraform",
          "elegida": true,
          "motivo": "Versionado, revisable y se recrea solo"
        },
        {
          "opcion": "Crearlo a mano en la consola",
          "elegida": false,
          "motivo": "Mas rapido una vez, invisible para siempre"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r019",
      "fecha": "2026-09-26",
      "orden": 4,
      "carril": "analisis",
      "titulo": "Cuatro datasets (raw, staging, marts, control), no uno",
      "tipo": "decision",
      "detalle": "",
      "porque": "El grafo que Rastro va a dibujar necesita capas distinguibles: con todo en el mismo dataset el linaje seria una mancha y no ensenaria nada. La herramienta y la plataforma se disenan a la vez a proposito, no una despues de la otra.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Cuatro datasets por capa",
          "elegida": true,
          "motivo": "El linaje solo se ve si hay capas que distinguir"
        },
        {
          "opcion": "Un dataset unico",
          "elegida": false,
          "motivo": "Mas simple de montar y deja la capa 2 sin nada que mostrar"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r020",
      "fecha": "2026-09-26",
      "orden": 5,
      "carril": "analisis",
      "titulo": "Particion por dia y agrupamiento por indicador desde el primer dia",
      "tipo": "decision",
      "detalle": "La tabla `raw.medidas` va particionada por DAY sobre `instante` y agrupada por `indicador_id`.",
      "porque": "Particionar \"cuando haga falta\" no funciona: cuando hace falta ya hay consultas escritas contra la tabla sin particionar y cambiarlo cuesta reescribirlas. La particion por dia se aplica siempre porque todas las consultas del dashboard miran una ventana temporal, y con 16 valores distintos el agrupamiento por indicador es muy efectivo.",
      "consecuencia": "Queda pendiente medir la consulta tipica antes y despues para poner la cifra en el README. Sin la cifra, la decision es una opinion.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Particion y agrupamiento desde el inicio",
          "elegida": true,
          "motivo": "Es gratis hacerlo ahora y caro hacerlo despues"
        },
        {
          "opcion": "Tabla plana y optimizar cuando duela",
          "elegida": false,
          "motivo": "Cuando duele ya hay consultas que dependen de la forma vieja"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r021",
      "fecha": "2026-09-26",
      "orden": 6,
      "carril": "etica",
      "titulo": "El token vive en Secret Manager y su valor no pasa por Terraform",
      "tipo": "decision",
      "detalle": "Terraform crea el secreto vacio y da acceso de lectura a la cuenta de servicio de la ingesta. El valor se mete aparte con `gcloud secrets versions add`.",
      "porque": "El estado de Terraform se guarda en claro: cualquier valor que entre por una variable acaba legible ahi. Separar la creacion del secreto de su contenido es lo que evita que el token termine en un fichero de estado.",
      "consecuencia": "La cuenta de servicio de la ingesta tiene `dataEditor` solo sobre raw y control, y `jobUser` en el proyecto. Nada de `roles/editor`, que permite borrar el proyecto entero.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Secret Manager, con el valor fuera de Terraform",
          "elegida": true,
          "motivo": "El token no llega nunca al estado de Terraform"
        },
        {
          "opcion": "Variable de entorno en el servicio",
          "elegida": false,
          "motivo": "Queda visible en la configuracion del servicio"
        },
        {
          "opcion": "Variable de Terraform",
          "elegida": false,
          "motivo": "El estado se guarda en claro"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r022",
      "fecha": "2026-09-26",
      "orden": 7,
      "carril": "fuentes",
      "titulo": "La serie arranca cuando la plataforma esta lista, sin carga historica",
      "tipo": "decision",
      "detalle": "Sin `--desde`, el inicio historico se pone una ventana revisable por detras: lo justo para que la primera ejecucion traiga algo. La carga historica existe pero hay que pedirla a proposito con `--desde AAAA-MM-DD`.",
      "porque": "Decision de Guillermo el 26-sep. Evita arrastrar historia antes de que la plataforma este montada y probada, y mantiene el numero de peticiones al minimo mientras se valida el circuito completo.",
      "consecuencia": "El dashboard tendra poca historia las primeras semanas. La carga historica sigue disponible en una sola opcion: un ano son unos 53 tramos por indicador, unas 850 peticiones en total, que el planificador reparte por turnos entre varias ejecuciones. REE lo permite explicitamente si se hace una vez y por tramos.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": "alcance-temporal",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Arrancar ahora, carga historica bajo demanda",
          "elegida": true,
          "motivo": "Menos peticiones mientras se valida el circuito completo"
        },
        {
          "opcion": "Cargar un ano de historia desde el principio",
          "elegida": false,
          "motivo": "El dashboard seria interesante antes, pero son 850 peticiones sobre una plataforma aun sin probar\n"
        },
        {
          "opcion": "Arrancar ahora y no permitir carga historica",
          "elegida": false,
          "motivo": "Cierra una puerta que no cuesta nada dejar abierta"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r023",
      "fecha": "2026-09-26",
      "orden": 8,
      "carril": "metodo",
      "titulo": "Entorno virtual en el proyecto, sin tocar el PATH del sistema",
      "tipo": "decision",
      "detalle": "`.venv` dentro de `rastro/`, con el paquete instalado en modo editable. gcloud y terraform si quedan en el PATH de usuario porque sus propios instaladores lo hacen.",
      "porque": "pip instala `pytest`, `ruff`, `dbt` y el comando `rastro` en un directorio que no estaba en el PATH. Anadirlo habria funcionado, pero el PATH de usuario de esta maquina ya tiene mas de cuarenta entradas con duplicados, asi que meter una mas es empeorar algo que ya esta al limite. El entorno virtual es ademas lo que cualquiera espera al clonar un proyecto Python.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "parche",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Entorno virtual en el proyecto",
          "elegida": true,
          "motivo": "Reproducible al clonar y no toca nada del sistema"
        },
        {
          "opcion": "Anadir el directorio de scripts al PATH de usuario",
          "elegida": false,
          "motivo": "Funciona, pero engorda un PATH que ya esta saturado"
        },
        {
          "opcion": "Instalar las herramientas globalmente",
          "elegida": false,
          "motivo": "Mezcla las dependencias de este proyecto con las de los demas"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r024",
      "fecha": "2026-09-27",
      "orden": 24,
      "carril": "metodo",
      "titulo": "El plan escrito de F4 rompe el objetivo de 0 EUR: la suscripcion BigQuery de Pub/Sub no tiene capa gratuita",
      "tipo": "medicion",
      "detalle": "Verificado en las paginas oficiales de precios de 2026, componente a componente. La suscripcion BigQuery de Pub/Sub -que es el ultimo paso del plan escrito de F4- NO tiene capa gratuita: la propia pagina de precios lo dice con una frase literal, \"The first 10 GiB of BigQuery subscription throughput is not free\". Cuesta 50 USD/TiB desde el primer byte. Ademas el throughput facturable de Pub/Sub cuenta publicacion MAS suscripcion, asi que los 10 GiB gratis del SKU normal equivalen a unos 5 GiB de payload real, unos 170 MB al dia. Y dos costes mas que hay que tener fichados: Dataflow no tiene capa gratuita y el worker de streaming por defecto sale a unos 0,37 USD/hora -tres horas son 1,10 USD, un mes encendido son unos 270-, y Cloud Composer no tiene capa gratuita NI se puede apagar por horas: la cuota de entorno pequeno son 0,35 USD/hora, es decir unos 255 USD al mes de tarifa fija antes de ejecutar un solo DAG.",
      "porque": "Salio al investigar, para otro proyecto, si un proyecto de datos podia sostenerse en la capa gratuita de GCP. El objetivo de coste de Rastro es 0 EUR con alerta de presupuesto a 1 EUR, y el camino escrito en F4 activaria esa alerta en cuanto suba el volumen.",
      "consecuencia": "El camino gratuito es el largo: suscripcion push normal, consumidor propio, y escritura con la Storage Write API por gRPC, cuyos primeros 2 TiB al mes son gratis. Y tiene un beneficio que no es menor: ese camino largo es el que obliga a poner la idempotencia, el manejo de esquemas que cambian y la cola de mensajes muertos en codigo propio, que es exactamente lo que este proyecto quiere mostrar. La ruta corta ahorra codigo y borra la evidencia. Para Dataflow, la regla operativa es ventana de 2-4 horas con captura del grafo de ejecucion, el retraso del sistema, el watermark y las metricas de eventos tardios, y despues drain y borrar - con un Cloud Scheduler que lo drene, no con la memoria-. Composer queda fuera del proyecto: la misma orquestacion se demuestra con Argo Workflows mas Airflow 3 en local con docker compose, sin coste.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": "ia",
      "ref": "seguimiento.md#f4-streaming",
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [
        "r033"
      ],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r025",
      "fecha": "2026-09-27",
      "orden": 25,
      "carril": "fuentes",
      "titulo": "Si F4 necesita una fuente en streaming de verdad, Wikidata via EventStreams es la unica con replay y licencia CC0",
      "tipo": "hallazgo",
      "detalle": "El stream recentchange de Wikimedia EventStreams es Server-Sent Events sobre HTTP -conexion abierta, no consulta periodica-, con unos 1,38 millones de eventos al dia en todos los proyectos y unos 500.000 solo en Wikidata. Y trae algo que ninguna otra fuente gratuita tiene: el parametro `since` permite consumo historico con entre 7 y 31 dias de retencion.",
      "porque": "Ese replay es lo que convierte la idempotencia, el reproceso, el backfill y los datos que llegan tarde en algo DEMOSTRABLE y reproducible por cualquiera que clone el repo, en vez de una afirmacion en el README. Y el filtro a wikidatawiki resuelve de una linea el problema de licencia: el contenido de los wikis es CC BY-SA 4.0, es decir share-alike, que obliga a propagar la licencia a cualquier obra derivada, mientras que Wikidata publica TODO bajo CC0, sin atribucion obligatoria y sin share-alike. Eso permite publicar el dataset derivado en el repo, usarlo en un articulo y en material de curso sin pedir permiso ni contaminar la licencia.",
      "consecuencia": "NO sustituye a ESIOS, que es la fuente con sentido para la pregunta de Rastro. Queda anotada como la opcion si F4 necesita volumen de streaming real que ESIOS no da. Dos avisos operativos documentados: la capa HTTP de Wikimedia corta la conexion a los 15 minutos, asi que hay que reconectar con `since` para no perder eventos, y el User-Agent es obligatorio. El coste total verificado de esa arquitectura, con la conexion viviendo en una VM e2-micro Always Free en us-central1 y no en un servicio de Cloud Run -que con conexion de larga duracion serian unos 44 USD/mes-, esta entre 0,00 y 0,07 USD al mes.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": "ia",
      "ref": "seguimiento.md#f4-streaming",
      "alternativas": [],
      "causada_por": [
        "r024"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r026",
      "fecha": "2026-09-27",
      "orden": 26,
      "carril": "difusion",
      "titulo": "El argumento de venta de Rastro estaba en la lista de precios de Google",
      "tipo": "hallazgo",
      "detalle": "Dataplex se llama Knowledge Catalog desde el 10-abr-2026. Su procesado estandar tiene 100 DCU-horas al mes gratis, pero el nivel PREMIUM -que es exactamente donde viven el LINAJE DE DATOS, la calidad y el perfilado- NO tiene capa gratuita y factura desde el primer segundo a 0,089 USD por DCU-hora, con minimo de un minuto.",
      "porque": "No se eligio nada, se leyo la pagina de precios. Y es el argumento que faltaba: el linaje de BigQuery en Google Cloud es un producto de PAGO sin nivel gratuito, y Rastro hace la parte de BigQuery y dbt gratis y en abierto. Eso no es una frase de marketing: es un precio de lista de la alternativa, citable y verificable.",
      "consecuencia": "Entra en el README: explica en una linea por que este proyecto existe. El linaje de BigQuery en Google Cloud es un producto de pago sin nivel gratuito, y Rastro hace la parte de BigQuery y dbt en abierto. Aviso operativo si se prueba Dataplex para comparar: ventana corta y medida, contando DCU-horas, igual que con Dataflow.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": "ia",
      "ref": "seguimiento.md#f4-streaming",
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r027",
      "fecha": "2026-09-27",
      "orden": 27,
      "carril": "metodo",
      "titulo": "La plataforma esta aplicada en GCP, 25 recursos y sin cambios pendientes",
      "tipo": "hito-externo",
      "detalle": "`terraform apply` completo contra rastro-509715. Cuatro datasets, la tabla `raw.medidas` particionada por dia sobre `instante` y agrupada por `indicador_id` -verificado leyendo la tabla, no el plan-, las dos tablas de control, la cuenta de servicio `rastro-ingesta` con dataEditor solo sobre raw y control, el secreto y el presupuesto de 1 EUR con cuatro umbrales. `terraform plan` devuelve sin cambios. El token ya esta en Secret Manager y se comprobo por hash que coincide con el local, sin imprimirlo.",
      "porque": "La facturacion quedo activada y vinculada, que era lo unico que bloqueaba las fases 2, 3 y 4.",
      "consecuencia": "Queda desbloqueado cerrar el circuito de la ingesta contra BigQuery y empezar dbt. La marca de agua en JSON local pasa a ser solo el modo de desarrollo.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r028",
      "fecha": "2026-09-27",
      "orden": 28,
      "carril": "metodo",
      "titulo": "Con credenciales de usuario, el provider de Google necesita billing_project y user_project_override",
      "tipo": "hallazgo",
      "detalle": "El presupuesto fallaba con un 403 SERVICE_DISABLED contra el proyecto 764086051850, que no es el nuestro sino el del cliente de gcloud. `billingbudgets` es una API que no cuelga de ningun proyecto, asi que Google necesita que se le diga cual paga la cuota, y con Application Default Credentials el provider no lo manda solo. Se arregla con `billing_project` y `user_project_override = true`, que hacen que envie la cabecera X-Goog-User-Project.",
      "porque": "Salio al aplicar. El mensaje de error despista mucho: acusa a un numero de proyecto desconocido de tener una API deshabilitada, cuando en el proyecto propio si estaba habilitada.",
      "consecuencia": "Al activar la atribucion de cuota aparecio un segundo problema encadenado: leer el proyecto pasa a necesitar `cloudresourcemanager.googleapis.com`, y esa lectura ocurre en el `plan`, antes de que Terraform pueda habilitarla. Es el huevo y la gallina clasico de Terraform contra GCP: la primera vez se habilita a mano, y se declara igualmente para que quede registrada. Tarda un par de minutos en propagarse, asi que el primer reintento puede fallar sin que nada este mal. Los dos tropiezos estan escritos en docs/puesta-en-marcha.md porque le van a pasar a cualquiera que clone.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [
        "r027"
      ],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r029",
      "fecha": "2026-09-27",
      "orden": 29,
      "carril": "analisis",
      "titulo": "La hidraulica marca -3.600 MW: el test de rango no puede exigir valores positivos",
      "tipo": "medicion",
      "detalle": "Primera ingesta real a BigQuery, 1.146 medidas de dos dias. El indicador 546 (Generacion T.Real hidraulica) va de -3.600 a 6.593 MW; el 551 (eolica), de 1.368 a 7.478 MW, siempre positivo. Una sola zona geografica en los dos casos, la Peninsula.",
      "porque": "Salio al mirar los datos ya cargados en lugar de darlos por buenos. La hipotesis es que el indicador recoge la hidraulica NETA de bombeo: el bombeo consume energia para subir agua, y Espana tiene del orden de 6 GW de potencia de bombeo, asi que -3.600 MW es plausible. Queda como hipotesis, no como hecho: hay que confirmarlo contra la documentacion de ESIOS antes de escribirlo en el README.",
      "consecuencia": "El test de rango plausible por tecnologia no puede ser uno solo. Un `valor >= 0` aplicado a todo habria marcado como roto un dato correcto, que es el error contrario al del 37.483 y igual de malo: alli se acepto un numero imposible, aqui se rechazaria uno real. El rango tiene que ser por tecnologia, y para la hidraulica con suelo negativo.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [
        "r012"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r030",
      "fecha": "2026-09-27",
      "orden": 30,
      "carril": "metodo",
      "titulo": "Trabajos de carga y `raw` de solo anadir: la revision de REE se conserva",
      "tipo": "decision",
      "detalle": "La escritura en `raw.medidas` usa trabajos de carga de BigQuery, no inserciones en streaming. Y no borra ni actualiza: cuando la ventana revisable trae otra vez las mismas medidas, se anaden con un `ingerido_en` posterior. La deduplicacion es cosa de `staging`, que se queda con la ultima version de cada punto.",
      "porque": "Los trabajos de carga son gratuitos y las inserciones en streaming de la API antigua se facturan por volumen, asi que a 4.608 filas al dia la eleccion es obvia. Y sobre la duplicacion: borrar la version anterior perderia informacion real, porque el hecho de que REE haya revisado un valor y cuando lo hizo es un dato en si mismo, no ruido.",
      "consecuencia": "`staging` tiene que deduplicar por (indicador_id, instante, geo_id) quedandose con el maximo `ingerido_en`. A cambio se puede responder a \"que valores ha revisado REE\" con una consulta, que en una plataforma de datos de generacion electrica es exactamente lo que interesa poder auditar. La Storage Write API queda para la fase de streaming, donde si hace falta latencia baja: sus primeros 2 TiB al mes son gratis.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Trabajos de carga, y raw de solo anadir",
          "elegida": true,
          "motivo": "Gratis, y conserva la evidencia de las revisiones de REE"
        },
        {
          "opcion": "Inserciones en streaming",
          "elegida": false,
          "motivo": "Se facturan por volumen sin que aqui haga falta baja latencia"
        },
        {
          "opcion": "Borrar la ventana y reinsertarla",
          "elegida": false,
          "motivo": "Deja raw limpio y borra el hecho de que hubo una revision"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r031",
      "fecha": "2026-09-27",
      "orden": 31,
      "carril": "metodo",
      "titulo": "Dataflow en streaming cuesta unos 0,25 USD/hora y no depende del volumen",
      "tipo": "medicion",
      "detalle": "Precios verificados en el ejemplo trabajado que publica Google para us-central1: 0,069 USD por vCPU de streaming y hora, 0,003557 USD por GB de memoria y hora, y 0,089 USD por unidad de computo de Streaming Engine y hora. Con la configuracion minima realista -un trabajador n1-standard-2 con Streaming Engine- sale a unos 0,25 USD/hora: 0,76 USD una ventana de tres horas, 6,09 USD un dia, 185 USD un mes encendido. Sin Streaming Engine el valor por defecto son 4 vCPU y 400 GB de disco, y sube a unos 0,33 USD/hora mas disco.",
      "porque": "Guillermo pregunto cuanto costaria de verdad. La cifra importa menos que la forma de la factura: Dataflow en streaming cobra por estar encendido, no por trabajo hecho. El volumen mensual entero de Rastro son 13,2 MB, asi que un mes de Dataflow saldria a unos 14 USD por megabyte movido.",
      "consecuencia": "Se confirma la regla de r024: Dataflow entra en ventanas medidas de 2 a 4 horas y sale, con el drenado programado por Cloud Scheduler. Y aparece una alternativa mejor para lo que hay que demostrar: Apache Beam con DirectRunner y `TestStream` corre el MISMO codigo de pipeline en local y en CI, gratis, y permite dirigir el watermark y los datos que llegan tarde de forma determinista. Unos tests asi son mejor prueba de entender semantica de streaming que una captura de un trabajo de Dataflow.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [
        "r024"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r032",
      "fecha": "2026-09-27",
      "orden": 32,
      "carril": "metodo",
      "titulo": "El coste cero deja de ser objetivo y pasa a ser requisito del proyecto",
      "tipo": "decision",
      "detalle": "Techo declarado por Guillermo el 27-sep: 0 EUR, y como maximo 1 o 2 EUR al mes. Deja de ser una preferencia de diseno y pasa a condicionar que herramientas entran. Queda escrito en docs/coste.md, componente a componente, marcando con interrogacion lo que no se ha podido verificar en la pagina oficial de precios en lugar de rellenarlo con una estimacion.",
      "porque": "Situacion economica personal. Una cifra inventada en un documento de coste no es un error tecnico: le cuesta dinero a alguien.",
      "consecuencia": "Dataflow sale del plan (r033). Antes de la primera compilacion de la imagen del job hace falta una politica de limpieza en Artifact Registry, que es el riesgo mas alto que queda.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Cero euros como requisito, con alerta al primer centimo",
          "elegida": true,
          "motivo": "Es la restriccion real, y ademas es material de entrevista"
        },
        {
          "opcion": "Aceptar unos pocos euros al mes de margen",
          "elegida": false,
          "motivo": "No hay margen que aceptar"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r033",
      "fecha": "2026-09-27",
      "orden": 33,
      "carril": "metodo",
      "titulo": "Dataflow sale del proyecto; el grafo de ejecucion se hace con Beam en local",
      "tipo": "decision",
      "detalle": "La ventana medida de 2-4 horas que fijaba r024 se cancela. En su lugar, `apache_beam.runners.render.RenderRunner`, que escribe el grafo de la pipeline en SVG en local y ademas levanta un servidor para explorarlo, y `TestStream` con DirectRunner para la semantica de streaming.",
      "porque": "Se pregunto si el grafo de ejecucion se podia obtener gratis, y se puede. RenderRunner da el grafo como fichero SVG, que es mejor que una captura de pantalla: se versiona en el repositorio y lo regenera cualquiera que clone. Y `TestStream` permite dirigir el watermark y los eventos tardios de forma determinista, asi que la semantica de streaming se demuestra con tests que pasan siempre igual, no con una captura de un panel.",
      "consecuencia": "Se ahorran los 0,76 USD de la ventana de demostracion, que con techo de 1-2 EUR al mes no son despreciables. Lo que se pierde es el comportamiento de autoescalado de un servicio gestionado y las metricas de retraso del sistema de Dataflow, que es la parte menos importante y la mas difícil de explicar desde una captura. La interfaz web de un runner distribuido de verdad -Flink o Spark- daria casi lo mismo gratis, pero en esta maquina no hay Java ni Docker y Flink ya no trae scripts para Windows, asi que necesitaria WSL: queda anotado como opcional, no como plan.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Beam con RenderRunner y TestStream, en local y en CI",
          "elegida": true,
          "motivo": "Gratis, reproducible al clonar y mejor evidencia que una captura"
        },
        {
          "opcion": "Una ventana de Dataflow de 3 horas",
          "elegida": false,
          "motivo": "0,76 USD y solo anade autoescalado, que es lo que menos aporta"
        },
        {
          "opcion": "Flink o Spark en local con su interfaz web",
          "elegida": false,
          "motivo": "Da casi lo mismo gratis, pero exige Java o Docker y WSL en Windows"
        }
      ],
      "causada_por": [
        "r031",
        "r032"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [
        "r024"
      ],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r034",
      "fecha": "2026-09-27",
      "orden": 34,
      "carril": "metodo",
      "titulo": "Varios topes gratuitos se cuentan por cuenta de facturacion, no por proyecto",
      "tipo": "hallazgo",
      "detalle": "Verificado el 27-sep: los 0,5 GB de Artifact Registry y los 3 trabajos de Cloud Scheduler son el total de la cuenta de facturacion, sumando todos sus proyectos. La cuenta tenia cinco proyectos; Guillermo quito los dos de pruebas de dbt ese mismo dia y quedan tres: rastro-509715, app-fincrack y jobcrack-gmail. Ninguno usa todavia Scheduler ni Artifact Registry.",
      "porque": "Salio al auditar el coste. Y destapo un fallo en lo aplicado el dia anterior: el presupuesto solo filtraba por el proyecto de Rastro, asi que un cargo originado en app-fincrack o jobcrack-gmail no habria avisado a nadie. Lo que se paga es la cuenta, no el proyecto.",
      "consecuencia": "Se anade un segundo presupuesto sobre la cuenta completa, y los dos bajan su primer umbral al 1 % -un centimo en el de Rastro, dos en el de la cuenta-. Con objetivo de coste cero lo que hay que saber no es que el gasto se acerca al techo sino que ha habido gasto. Y queda pendiente, antes de construir ninguna imagen, una politica de limpieza en Artifact Registry: cada compilacion deja la imagen anterior sin etiqueta pero ocupando, y con tres o cuatro se agota el medio giga.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [
        "r032"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r035",
      "fecha": "2026-09-27",
      "orden": 35,
      "carril": "analisis",
      "titulo": "Medido: 51 bytes por fila, unos 86 MB al ano",
      "tipo": "medicion",
      "detalle": "Primera carga real en BigQuery: 1.146 filas ocupan 0,057 MB. A 4.608 filas al dia son unos 0,23 MB diarios, 7 MB al mes y 86 MB al ano. El tope gratuito de BigQuery son 10 GiB, asi que a este ritmo tardaria mas de un siglo en agotarse.",
      "porque": "Se midio en lugar de estimarlo, ahora que ya hay datos de verdad cargados.",
      "consecuencia": "El almacenamiento queda descartado como riesgo de coste. El riesgo esta en Artifact Registry y en los topes compartidos, no en los datos.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r036",
      "fecha": "2026-09-27",
      "orden": 36,
      "carril": "analisis",
      "titulo": "El indicador 552 (Solar) solapa con 1294 y 1295: sumarlos inflaba la generacion a 52 GW",
      "tipo": "medicion",
      "detalle": "Al construir el primer mart con los 16 indicadores, la generacion total daba entre 50 y 52 GW. El pico de demanda peninsular espanol ronda los 45 GW, asi que era imposible. La causa es que el indicador 552 \"Generacion T.Real solar\" solapa con 1294 (solar termica) y 1295 (solar fotovoltaica), y los tres estaban en la suma. Excluyendo el 552 la generacion baja a 31-36 GW contra una demanda de 26-29, razon 1,15-1,28, que es lo que cabe esperar con exportacion y bombeo.",
      "porque": "Salio al comparar el total contra la demanda, no al mirar cada indicador. Y esa es la parte importante: cada tecnologia estaba dentro de su rango, la hora estaba completa, la cobertura estaba completa y ninguna comprobacion por pieza se quejaba. Un total imposible formado por partes correctas solo se ve contrastandolo contra una medida independiente.",
      "consecuencia": "El seed `tecnologias` gana una columna `sumable`, y 552 va a `false`. Se conserva en el modelo en lugar de borrarlo del seed porque un agregado publicado por la fuente es la mejor referencia contra la que contrastar la suma de las partes. Y se anade el test de reconciliacion contra la demanda, con severidad de aviso: no es una especificacion -la generacion nunca iguala la demanda- sino la alarma que detecta esta clase de error.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [
        "r012"
      ],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r037",
      "fecha": "2026-09-27",
      "orden": 37,
      "carril": "analisis",
      "titulo": "Sin explicar: el indicador 10004 marca 46.976 MW de demanda donde el 1293 marca 28.167",
      "tipo": "hallazgo",
      "detalle": "Los dos dicen ser demanda. El 1293 \"Demanda real\" da 28.167 MW a mediodia del 27-sep, que cuadra con la realidad conocida del sistema peninsular en septiembre. El 10004 \"Demanda real suma de generacion\" da 46.976 a la misma hora. No es doble conteo del solar, porque son indicadores independientes de la suma que hace el mart.",
      "porque": "Aparecio al buscar una medida independiente contra la que reconciliar la generacion. Queda anotado como pregunta abierta en lugar de elegir uno de los dos a ojo.",
      "consecuencia": "La reconciliacion se hace contra el 1293, que es el que cuadra con la realidad. El 10004 se sigue ingiriendo pero no se usa para nada hasta saber que mide. Esta escrito en el propio test para que quien lo lea sepa que hay algo sin cerrar y no lo tome por verificado.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r038",
      "fecha": "2026-09-27",
      "orden": 38,
      "carril": "metodo",
      "titulo": "Vistas en staging e intermediate, tabla en marts, y sin paquetes de dbt",
      "tipo": "decision",
      "detalle": "36 comprobaciones en verde contra BigQuery. Staging e intermediate como vistas; el mart como tabla particionada por dia y SIN agrupamiento. Los tests genericos `entre` y `combinacion_unica` son propios, sin `dbt_utils`.",
      "porque": "Las vistas no ocupan almacenamiento y se recalculan al consultarlas, que con 1 TiB de consultas gratis al mes es lo mas barato. El mart es tabla porque el dashboard lo consulta muchas veces al dia y una vista recalcularia la cadena entera cada vez. Y hay un beneficio lateral que no es casual: las vistas anidadas son justo lo que hace interesante el linaje que Rastro tiene que dibujar, asi que la plataforma y la herramienta se refuerzan.\nSin agrupamiento en el mart porque agrupar necesita una columna con selectividad, y ahi hay una fila por hora y una sola zona geografica. Poner `cluster_by` seria ruido que aparenta optimizacion.\nY sin `dbt_utils` porque el test de rango tiene que comparar cada fila contra el rango de SU tecnologia, que vive en una tabla: `accepted_range` no hace eso, y quince lineas propias evitan una dependencia que habria que fijar, actualizar y explicar.",
      "consecuencia": null,
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Vistas hasta marts, tabla en marts, tests propios",
          "elegida": true,
          "motivo": "Coste minimo, y las vistas anidadas alimentan la capa 2"
        },
        {
          "opcion": "Tablas en toda la cadena",
          "elegida": false,
          "motivo": "Ocupa y hay que reconstruir, sin ganar nada a este volumen"
        },
        {
          "opcion": "Traer dbt_utils",
          "elegida": false,
          "motivo": "No resuelve el test que importa y anade una dependencia"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r039",
      "fecha": "2026-09-27",
      "orden": 39,
      "carril": "analisis",
      "titulo": "El porcentaje renovable sale nulo si falta alguna tecnologia",
      "tipo": "decision",
      "detalle": "",
      "porque": "Con solo la hidraulica y la eolica cargadas, el mart publicaba 100 % renovable y una potencia total NEGATIVA -la hidraulica resta cuando bombea-, y el test de rango 0-100 lo aceptaba porque 100 esta entre 0 y 100. El test no estaba mal: faltaba comprobar la cobertura.",
      "consecuencia": "El mart cuenta las tecnologias presentes, las compara con las declaradas en el seed y solo publica el porcentaje si coinciden. Un hueco en el dashboard se ve; un 100 % falso no. Y `porcentaje_renovable` NO lleva `not_null` a proposito: el nulo es el comportamiento correcto, y exigir que no lo sea obligaria a publicar un numero que no se sostiene.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Nulo cuando la cobertura esta incompleta",
          "elegida": true,
          "motivo": "Un hueco visible es mejor que un numero falso"
        },
        {
          "opcion": "Publicar el porcentaje parcial",
          "elegida": false,
          "motivo": "Es exactamente el 100 % falso que se acaba de detectar"
        },
        {
          "opcion": "No publicar la fila entera",
          "elegida": false,
          "motivo": "Se perderia la potencia por tecnologia, que si es correcta"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r040",
      "fecha": "2026-09-27",
      "orden": 40,
      "carril": "analisis",
      "titulo": "El grafo cruza dos fuentes, y el motivo de cada arista es una senal de confianza",
      "tipo": "decision",
      "detalle": "`dbt.desde_manifiesto` lee lo que dbt gestiona y `bigquery.desde_information_schema` lee lo que HAY en la base de datos. Cuando las dos ven la misma dependencia no se guardan dos aristas: se guarda una con los motivos acumulados -`vista+dbt`- y una propiedad `confirmada`. En la plataforma real salen 10 nodos, 11 aristas y 3 confirmadas por las dos.",
      "porque": "La primera version guardaba una arista por motivo y daba 14 donde hay 11. Al deduplicar aparecio algo mejor que un numero limpio: quien vio cada dependencia dice cuanto fiarse. Solo dbt puede ser un manifiesto viejo de antes del ultimo despliegue; solo el SQL puede ser una vista creada a mano o un error del analizador; las dos a la vez es lo mas fiable que hay.",
      "consecuencia": "Es la diferencia con `dbt docs`, que solo puede dibujar el grafo de dbt. Y requiere que los nodos de las dos fuentes tengan el MISMO identificador, asi que el de dbt se construye como `database.schema.name` en minusculas y no con su clave interna: eso es lo que hace que se fusionen sin tabla de equivalencias.",
      "estado": "vigente",
      "impacto": "mayor",
      "irreversible": false,
      "hito": "metodo",
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Una arista por dependencia, con los motivos acumulados",
          "elegida": true,
          "motivo": "El motivo pasa a decir cuanto fiarse de la arista"
        },
        {
          "opcion": "Una arista por cada fuente que la ve",
          "elegida": false,
          "motivo": "Infla el grafo y duplica las lineas del visor sin anadir nada"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r041",
      "fecha": "2026-09-27",
      "orden": 41,
      "carril": "metodo",
      "titulo": "Analisis de SQL en dos pasadas, con sqlglot opcional",
      "tipo": "decision",
      "detalle": "`sqlglot` primero, que entiende SQL de verdad y sabe que una expresion comun no es una tabla. Expresiones regulares despues, SIEMPRE, no solo cuando el analizador falla. Y si `sqlglot` no esta instalado, se usa solo la segunda pasada y el resultado lo declara con `aproximada`.",
      "porque": "Los analizadores fallan: dialectos con extensiones, SQL generado, procedimientos largos con `EXECUTE IMMEDIATE` dentro. Quedarse sin respuesta cuando el analizador se atraganta es peor que dar una respuesta aproximada y decir que lo es. Y el respaldo se suma siempre porque encuentra cosas que sqlglot no marca como tabla -un procedimiento en un `CALL`-: en un grafo de dependencias, sobrar una arista dudosa cuesta menos que faltar una real.",
      "consecuencia": "Una herramienta de diagnostico que no arranca porque falta una dependencia no diagnostica nada, asi que `sqlglot` va en el extra `grafo` y no en el nucleo.\nLas referencias que aparecen en COMENTARIOS se devuelven aparte, con un patron mas permisivo -sin exigir palabra clave delante-, porque ahi el resultado es una pista y no una arista: casi siempre es una dependencia que alguien quito hace meses sin borrarla, y eso explica por que una tabla parece huerfana.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Analizador con respaldo por regex, y el analizador opcional",
          "elegida": true,
          "motivo": "Siempre da una respuesta, y dice cuando es aproximada"
        },
        {
          "opcion": "Solo sqlglot",
          "elegida": false,
          "motivo": "Deja huecos silenciosos cuando falla, que es lo peor que puede pasar"
        },
        {
          "opcion": "Solo expresiones regulares",
          "elegida": false,
          "motivo": "Confunde expresiones comunes y alias con tablas"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r042",
      "fecha": "2026-09-27",
      "orden": 42,
      "carril": "analisis",
      "titulo": "Las huerfanas son la pregunta, no la respuesta",
      "tipo": "decision",
      "detalle": "",
      "porque": "En la plataforma real la lista da tres: la marca de agua y dos marts. Ninguna es basura. Los marts son puntos finales legitimos -los lee el cuadro de mando, que esta fuera del grafo- y la marca de agua la lee el codigo de ingesta, no una consulta. Una herramienta que las presentase como candidatas a borrar seria peligrosa.",
      "consecuencia": "La orden imprime la advertencia junto al resultado, no en la documentacion: lo que se lee es la salida del comando, no el manual. Y las externas se excluyen por defecto, porque un nodo descubierto solo porque una vista lo mencionaba no se puede declarar huerfano sin haberlo mirado. Cerrar la pregunta necesita cruzar esto con el uso real -quien consulto la tabla en 90 dias-, que es lo siguiente de F5.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Listarlas con la advertencia en la propia salida del comando",
          "elegida": true,
          "motivo": "Lo que se lee es la salida, no el manual"
        },
        {
          "opcion": "Llamarlas \"candidatas a borrar\"",
          "elegida": false,
          "motivo": "Alguien borraria un mart que si se usa, desde fuera del grafo"
        },
        {
          "opcion": "No ofrecer la consulta hasta poder cruzarla con el uso real",
          "elegida": false,
          "motivo": "La lista ya sirve para revisar, aunque no cierre la decision"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r043",
      "fecha": "2026-09-27",
      "orden": 43,
      "carril": "metodo",
      "titulo": "Los heredocs de Git Bash corrompen escapes: aparecio un byte 0x08 en una regex",
      "tipo": "hallazgo",
      "detalle": "Un `\\\\b` escrito dentro de un heredoc acabo como un byte de retroceso real (0x08) en el fichero fuente, y la expresion regular dejo de encontrar nada sin dar ningun error. Se detecto porque un test fallaba y el patron en memoria salia con `\\\\x08`.",
      "porque": "Es la tercera vez que los heredocs largos causan un problema en este proyecto, despues del YAML de FlowCrack y de unos `\\\\n` convertidos en saltos de linea de verdad dentro de cli.py. RETOMAR ya avisaba de que fallan; ahora hay tres casos concretos.",
      "consecuencia": "Regla operativa: cualquier fichero con escapes -expresiones regulares, cadenas con `\\\\n`, YAML largo- se escribe con la herramienta de escritura o con un script en el scratchpad, nunca con un heredoc. Y despues de generar codigo asi, comprobar que no hay bytes de control: un `grep` no lo ve, pero rompe en silencio.",
      "estado": "vigente",
      "impacto": "parche",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    },
    {
      "id": "r044",
      "fecha": "2026-09-27",
      "orden": 44,
      "carril": "difusion",
      "titulo": "El cuadro de mando lleva una pagina de calidad del dato",
      "tipo": "decision",
      "detalle": "Cuatro paginas especificadas en docs/dashboard.md: estado actual, el dia, renovables y calidad. La cuarta mide frescura, horas incompletas, revisiones de REE y peticiones a la API.",
      "porque": "Las tres primeras paginas las hace cualquiera con un tutorial. La cuarta demuestra que se entiende que un dato bonito puede estar mal, que es la pregunta de la que vive todo el proyecto. La metrica de puntos revisados solo se puede calcular porque `raw` es de solo anadir: si sobreescribiera, no existiria.",
      "consecuencia": "Hacen falta dos marts nuevos: `mart_generacion_por_tecnologia` para el apilado y `mart_calidad_datos` para esa pagina. Y dos avisos que no son cosmeticos: el anillo del mix tiene que filtrar valores positivos porque la hidraulica es negativa cuando bombea -y decirlo en el informe en lugar de esconderlo-, y los campos de porcentaje ya vienen en escala 0-100, asi que el tipo Porcentaje de Looker Studio los multiplicaria otra vez.",
      "estado": "vigente",
      "impacto": "menor",
      "irreversible": false,
      "hito": null,
      "publico": null,
      "decidido_por": null,
      "ref": null,
      "alternativas": [
        {
          "opcion": "Cuatro paginas, con una dedicada a la calidad del dato",
          "elegida": true,
          "motivo": "Es la unica que no sale de un tutorial, y la que explica el proyecto"
        },
        {
          "opcion": "Tres paginas de generacion, sin calidad",
          "elegida": false,
          "motivo": "Mas bonito y indistinguible de cualquier otro portfolio"
        },
        {
          "opcion": "Las metricas de calidad repartidas por las otras paginas",
          "elegida": false,
          "motivo": "Se diluyen; juntas cuentan una historia sobre como se construyo"
        }
      ],
      "causada_por": [],
      "abre": [],
      "cierra": [],
      "supera_a": [],
      "superada_por": [],
      "mata_riesgo": null,
      "espera_hasta": null,
      "commit": null,
      "fecha_commit": null,
      "version": null,
      "desfase_fechas": null
    }
  ]
};
