// Generado por build.py. No editar a mano.
// Fuente: decisiones.yaml
window.FLOWCRACK = {
  "formato": 2,
  "generado": "2026-09-27 16:15",
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
      "superada_por": [],
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
    }
  ]
};
