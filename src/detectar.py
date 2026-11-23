"""Contornos, área, perímetro, centro e circularidade."""

import cv2
import numpy as np

from config import Config


def circularidade(area: float, perimetro: float) -> float:
    """4π × área / perímetro². Círculo perfeito vale 1."""
    if perimetro <= 0:
        return 0.0
    return float(4.0 * np.pi * area / (perimetro * perimetro))


def detectar(
    mascara: np.ndarray, formato: tuple[int, ...], config: Config
) -> tuple[list[dict], list[dict]]:
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    altura, largura = formato[:2]
    area_imagem = float(altura * largura)
    aceitas: list[dict] = []
    rejeitadas: list[dict] = []

    for contorno in contornos:
        area = float(cv2.contourArea(contorno))
        perimetro = float(cv2.arcLength(contorno, True))
        momentos = cv2.moments(contorno)
        if area <= 0 or perimetro <= 0 or momentos["m00"] == 0 or area_imagem <= 0:
            continue
        circ = circularidade(area, perimetro)
        centro = (float(momentos["m10"] / momentos["m00"]), float(momentos["m01"] / momentos["m00"]))
        (_, _), raio = cv2.minEnclosingCircle(contorno)
        relativo = area / area_imagem

        motivo = None
        possivel_juncao = False
        if relativo < config.area_minima_relativa:
            motivo = "area_pequena"
        elif relativo > config.area_maxima_relativa:
            motivo = "area_grande"
        elif circ >= config.circularidade_minima:
            possivel_juncao = False
        elif circ >= config.circularidade_minima_juncao:
            possivel_juncao = True
        else:
            motivo = "circularidade_baixa"

        item = {
            "contorno": contorno,
            "area": area,
            "perimetro": perimetro,
            "circularidade": circ,
            "centro": centro,
            "diametro_px": float(raio * 2.0),
            "possivel_juncao": possivel_juncao,
        }
        if motivo is None:
            aceitas.append(item)
            continue
        if relativo >= config.area_minima_relativa * 0.5:
            item["motivo"] = motivo
            rejeitadas.append(item)

    aceitas.sort(key=lambda moeda: (moeda["centro"][1], moeda["centro"][0]))
    for indice, moeda in enumerate(aceitas, start=1):
        moeda["indice"] = indice
    return aceitas, rejeitadas
