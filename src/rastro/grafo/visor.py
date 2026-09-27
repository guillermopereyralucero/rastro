"""Genera el visor: un fichero HTML que se abre con doble clic.

Los datos van **embebidos** en el HTML, no en un JSON al lado. No es por comodidad:
un fichero abierto desde el disco usa el protocolo `file:`, y ahi el navegador
bloquea `fetch` de un fichero vecino. Embebiendolos, el visor se puede mandar por
correo, meter en un adjunto de un ticket o abrir en una maquina sin red, y funciona.

Sin dependencias y sin CDN. Una herramienta de diagnostico que necesita internet para
dibujar un grafo no sirve cuando mas falta hace.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from .disposicion import disponer
from .modelos import Grafo

MARCA = "/*DATOS*/"


def construir(grafo: Grafo) -> str:
    """Devuelve el HTML completo del visor, con los datos dentro."""
    plantilla = (
        resources.files("rastro.grafo")
        .joinpath("plantillas", "visor.html")
        .read_text(encoding="utf-8")
    )

    disposicion = disponer(grafo)
    datos = grafo.a_json()
    datos["disposicion"] = disposicion.a_json()
    datos["ancho"] = disposicion.ancho
    datos["alto"] = disposicion.alto
    datos["niveles"] = disposicion.niveles

    # `</script>` dentro de una cadena JSON cerraria la etiqueta antes de tiempo y
    # rompería la pagina. Un nombre de tabla no deberia contener eso nunca, pero el
    # grafo se construye a partir de SQL ajeno y "nunca" no es una garantia: si un dia
    # alguien crea una vista con un nombre creativo, el visor tiene que seguir
    # abriendose. Se escapa la barra, que en JSON es equivalente.
    crudo = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    crudo = crudo.replace("</", "<\\/")

    if MARCA not in plantilla:
        raise RuntimeError(f"la plantilla del visor no tiene la marca {MARCA}")

    return plantilla.replace(MARCA, crudo)


def escribir(grafo: Grafo, ruta: str | Path) -> Path:
    """Escribe el visor y devuelve donde quedo."""
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        f.write(construir(grafo))
    return destino
