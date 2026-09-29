# Imagen del job de ingesta.
#
# En dos etapas, y no por moda: la primera instala, la segunda solo copia lo
# instalado. Asi las herramientas de compilacion no viajan en la imagen final, que
# pesa menos y tiene menos superficie de ataque. Y pesar menos importa aqui mas de lo
# habitual, porque el tramo gratuito de Artifact Registry son 0,5 GB compartidos
# entre todos los proyectos de la cuenta.
#
# La compila Cloud Build, no un Docker local: 120 minutos de compilacion al dia
# gratis, y una cosa menos que instalar en el portatil.

FROM python:3.12-slim AS construir

WORKDIR /origen

# Solo lo que hace falta para instalar. Copiar el proyecto entero aqui invalidaria
# la cache de capas con cualquier cambio de codigo, y cada compilacion empezaria
# desde cero.
COPY pyproject.toml README.md ./
COPY src ./src

# `[bigquery]` y nada mas. El job de ingesta no dibuja grafos ni ejecuta pipelines
# de Beam, asi que traerselos seria engordar la imagen por nada.
RUN pip install --no-cache-dir --prefix=/instalado ".[bigquery]"


FROM python:3.12-slim

# Usuario sin privilegios. Un contenedor que solo hace peticiones HTTP y escribe en
# BigQuery no necesita ser root, y si algun dia algo va mal, que vaya mal con los
# menos permisos posibles.
RUN useradd --create-home --uid 1000 rastro

COPY --from=construir /instalado /usr/local

USER rastro
WORKDIR /home/rastro

# Sin buffer, para que los registros salgan en el momento y no al terminar. En un
# job que dura segundos, un log que aparece al final no sirve para ver que pasa.
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["rastro"]
CMD ["--help"]
