"""Segmentação por Otsu, limiar adaptativo ou bordas."""

import cv2
import numpy as np

from config import Config

from .morfologia import elemento_estruturante, preencher_buracos


def _kernel_impar(valor: int, minimo: int = 3) -> int:
    valor = max(minimo, int(valor))
    if valor % 2 == 0:
        valor += 1
    return valor


def _pontuar(mascara: np.ndarray, config: Config) -> int:
    """Conta componentes que já parecem moedas, para escolher a polaridade."""
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    altura, largura = mascara.shape[:2]
    area_imagem = float(altura * largura)
    pontos = 0
    for contorno in contornos:
        area = cv2.contourArea(contorno)
        perimetro = cv2.arcLength(contorno, True)
        if perimetro <= 0 or area_imagem <= 0:
            continue
        circularidade = 4.0 * np.pi * area / (perimetro * perimetro)
        relativo = area / area_imagem
        if (
            config.area_minima_relativa <= relativo <= config.area_maxima_relativa
            and circularidade >= config.circularidade_minima
        ):
            pontos += 1
    return pontos


def _otsu(cinza: np.ndarray, moedas_escuras: bool) -> np.ndarray:
    tipo = cv2.THRESH_BINARY_INV if moedas_escuras else cv2.THRESH_BINARY
    _, mascara = cv2.threshold(cinza, 0, 255, tipo | cv2.THRESH_OTSU)
    return mascara


def _adaptativo(cinza: np.ndarray, config: Config, moedas_escuras: bool) -> np.ndarray:
    bloco = _kernel_impar(config.adaptativo_bloco)
    tipo = cv2.THRESH_BINARY_INV if moedas_escuras else cv2.THRESH_BINARY
    return cv2.adaptiveThreshold(
        cinza,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        tipo,
        bloco,
        config.adaptativo_c,
    )


def _previa_adaptativa(mascara: np.ndarray, config: Config) -> np.ndarray:
    elemento = elemento_estruturante(config.kernel_morfologia)
    fechada = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, elemento, iterations=1)
    return preencher_buracos(fechada)


def segmentar_otsu(cinza: np.ndarray, config: Config) -> np.ndarray:
    if config.polaridade == "moedas_escuras":
        return _otsu(cinza, True)
    if config.polaridade == "moedas_claras":
        return _otsu(cinza, False)
    escura = _otsu(cinza, True)
    clara = _otsu(cinza, False)
    if _pontuar(clara, config) > _pontuar(escura, config):
        return clara
    return escura


def segmentar_adaptativo(cinza: np.ndarray, config: Config) -> np.ndarray:
    if config.polaridade == "moedas_escuras":
        return _adaptativo(cinza, config, True)
    if config.polaridade == "moedas_claras":
        return _adaptativo(cinza, config, False)
    escura = _adaptativo(cinza, config, True)
    clara = _adaptativo(cinza, config, False)
    if _pontuar(_previa_adaptativa(clara, config), config) > _pontuar(
        _previa_adaptativa(escura, config), config
    ):
        return clara
    return escura


def segmentar_bordas(cinza: np.ndarray, config: Config) -> np.ndarray:
    bordas = cv2.Canny(cinza, config.canny_limiar1, config.canny_limiar2)
    elemento = elemento_estruturante(config.kernel_morfologia)
    bordas = cv2.dilate(bordas, elemento, iterations=1)
    bordas = cv2.morphologyEx(bordas, cv2.MORPH_CLOSE, elemento, iterations=1)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mascara = np.zeros_like(cinza)
    if contornos:
        cv2.drawContours(mascara, contornos, -1, 255, thickness=cv2.FILLED)
    return mascara


def segmentar(cinza: np.ndarray, config: Config) -> np.ndarray:
    if config.metodo_segmentacao == "otsu":
        return segmentar_otsu(cinza, config)
    if config.metodo_segmentacao == "adaptativo":
        return segmentar_adaptativo(cinza, config)
    if config.metodo_segmentacao == "bordas":
        return segmentar_bordas(cinza, config)
    raise ValueError(f"Método de segmentação desconhecido: {config.metodo_segmentacao}")
