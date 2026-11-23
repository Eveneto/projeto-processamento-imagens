"""Desenho dos contornos e painel com as etapas."""

from pathlib import Path

import cv2
import numpy as np

from .io_imagem import salvar_imagem


def desenhar_resultado(imagem_bgr: np.ndarray, moedas: list[dict]) -> np.ndarray:
    saida = imagem_bgr.copy()
    fonte = cv2.FONT_HERSHEY_SIMPLEX
    for moeda in moedas:
        cor = (0, 140, 255) if moeda.get("possivel_juncao") else (0, 170, 0)
        cv2.drawContours(saida, [moeda["contorno"]], -1, cor, 2)
        texto = _texto(moeda)
        x, y = moeda["centro"]
        origem = (max(0, int(x) - 24), max(16, int(y) - 8))
        cv2.putText(saida, texto, origem, fonte, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(saida, texto, origem, fonte, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return saida


def _texto(moeda: dict) -> str:
    rotulo = moeda.get("rotulo")
    indice = moeda.get("indice", "?")
    if rotulo:
        return f"{indice}:{rotulo}"
    return str(indice)


def salvar_etapas(
    diretorio: str | Path,
    original: np.ndarray,
    cinza: np.ndarray,
    mascara: np.ndarray,
    resultado: np.ndarray,
    titulo: str,
) -> None:
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    salvar_imagem(diretorio / "original.png", original)
    salvar_imagem(diretorio / "preprocessada.png", cinza)
    salvar_imagem(diretorio / "mascara.png", mascara)
    salvar_imagem(diretorio / "resultado.png", resultado)
    _salvar_painel(diretorio / "etapas.png", original, cinza, mascara, resultado, titulo)


def _rgb(imagem_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)


def _salvar_painel(
    caminho: Path,
    original: np.ndarray,
    cinza: np.ndarray,
    mascara: np.ndarray,
    resultado: np.ndarray,
    titulo: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, eixos = plt.subplots(2, 2, figsize=(10, 8))
    paineis = (
        (eixos[0, 0], _rgb(original), None, "Original"),
        (eixos[0, 1], cinza, "gray", "Pré-processada"),
        (eixos[1, 0], mascara, "gray", "Máscara"),
        (eixos[1, 1], _rgb(resultado), None, "Resultado"),
    )
    for eixo, imagem, cmap, nome in paineis:
        if cmap is None:
            eixo.imshow(imagem)
        else:
            eixo.imshow(imagem, cmap=cmap, vmin=0, vmax=255)
        eixo.set_title(nome)
        eixo.axis("off")
    fig.suptitle(titulo)
    fig.tight_layout()
    try:
        fig.savefig(caminho, dpi=110, bbox_inches="tight")
    finally:
        plt.close(fig)
