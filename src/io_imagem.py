"""Leitura e gravação de imagens.

Usa o buffer do arquivo em vez de cv2.imread/imwrite para aceitar caminhos
com acentos no Windows.
"""

from pathlib import Path

import cv2
import numpy as np

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def carregar_imagem(caminho: str | Path) -> np.ndarray:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    dados = np.fromfile(caminho, dtype=np.uint8)
    imagem = cv2.imdecode(dados, cv2.IMREAD_COLOR)
    if imagem is None or imagem.size == 0:
        raise FileNotFoundError(f"Não foi possível ler a imagem: {caminho}")
    return imagem


def salvar_imagem(caminho: str | Path, imagem: np.ndarray) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    extensao = caminho.suffix if caminho.suffix else ".png"
    ok, buffer = cv2.imencode(extensao, imagem)
    if not ok:
        raise RuntimeError(f"Não foi possível codificar a imagem: {caminho}")
    caminho.write_bytes(buffer.tobytes())


def listar_imagens(pasta: str | Path) -> list[Path]:
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta}")
    arquivos = [item for item in pasta.iterdir() if item.suffix.lower() in EXTENSOES]
    return sorted(arquivos, key=lambda item: item.name.lower())
