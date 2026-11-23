"""Escala de cinza, HSV e suavização gaussiana."""

import cv2
import numpy as np

from config import Config


def _kernel_impar(valor: int) -> int:
    valor = max(1, int(valor))
    if valor % 2 == 0:
        valor += 1
    return valor


def preprocessar(imagem_bgr: np.ndarray, config: Config) -> tuple[np.ndarray, np.ndarray]:
    """Desfoca a imagem e devolve cinza (para segmentar) e HSV (para a cor)."""
    kernel = _kernel_impar(config.kernel_gaussiano)
    suave = cv2.GaussianBlur(imagem_bgr, (kernel, kernel), config.sigma_gaussiano)
    cinza = cv2.cvtColor(suave, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(suave, cv2.COLOR_BGR2HSV)
    if config.usar_clahe:
        clahe = cv2.createCLAHE(clipLimit=config.clahe_clip, tileGridSize=(8, 8))
        cinza = clahe.apply(cinza)
    return cinza, hsv
