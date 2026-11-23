"""Abertura, fechamento e preenchimento de buracos da máscara."""

import cv2
import numpy as np

from config import Config


def elemento_estruturante(tamanho: int) -> np.ndarray:
    tamanho = max(3, int(tamanho))
    if tamanho % 2 == 0:
        tamanho += 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (tamanho, tamanho))


def preencher_buracos(mascara: np.ndarray) -> np.ndarray:
    """Preenche regiões pretas totalmente cercadas por branco.

    O canto da foto é tratado como fundo. Buracos internos (reflexo no meio
    da moeda, ou o disco deixado por uma borda) passam a fazer parte do objeto.
    """
    altura, largura = mascara.shape[:2]
    if mascara[0, 0] != 0:
        return mascara
    flood = mascara.copy()
    marcador = np.zeros((altura + 2, largura + 2), np.uint8)
    cv2.floodFill(flood, marcador, (0, 0), 255)
    buracos = cv2.bitwise_not(flood)
    return cv2.bitwise_or(mascara, buracos)


def limpar_mascara(mascara: np.ndarray, config: Config) -> np.ndarray:
    elemento = elemento_estruturante(config.kernel_morfologia)
    # No limiar adaptativo a resposta inicial é um anel. Fechar e preencher
    # vem antes da abertura, senão a abertura apaga o anel fino.
    if config.metodo_segmentacao == "adaptativo":
        fechada = cv2.morphologyEx(
            mascara, cv2.MORPH_CLOSE, elemento, iterations=config.fechamento_iteracoes
        )
        preenchida = preencher_buracos(fechada)
        return cv2.morphologyEx(
            preenchida, cv2.MORPH_OPEN, elemento, iterations=config.abertura_iteracoes
        )

    aberta = cv2.morphologyEx(
        mascara, cv2.MORPH_OPEN, elemento, iterations=config.abertura_iteracoes
    )
    fechada = cv2.morphologyEx(
        aberta, cv2.MORPH_CLOSE, elemento, iterations=config.fechamento_iteracoes
    )
    return preencher_buracos(fechada)
