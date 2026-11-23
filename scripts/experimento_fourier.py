"""Compara uma imagem com a versão filtrada por um passa-baixa de Fourier."""

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.gerar_sinteticas import criar_imagem, definicoes
from src.fourier import filtrar_passa_baixa
from src.io_imagem import carregar_imagem


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Experimento complementar: passa-baixa no domínio da frequência."
    )
    parser.add_argument("--imagem", type=Path, default=None)
    parser.add_argument("--saida", type=Path, default=Path("data/resultados/fourier"))
    parser.add_argument("--fracao", type=float, default=0.12)
    return parser


def _carregar_cinza(caminho: Path | None) -> tuple[np.ndarray, str]:
    if caminho is not None:
        imagem = carregar_imagem(caminho)
        return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY), caminho.name
    definicao = definicoes()[0]
    imagem = criar_imagem(definicao["moedas"], ruido=8.0, semente=definicao["semente"])
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY), "sintetica_em_memoria"


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    cinza, nome = _carregar_cinza(args.imagem)
    espectro, filtrada = filtrar_passa_baixa(cinza, args.fracao)
    args.saida.mkdir(parents=True, exist_ok=True)
    destino = args.saida / "comparacao_fourier.png"

    fig, eixos = plt.subplots(1, 3, figsize=(12, 4))
    eixos[0].imshow(cinza, cmap="gray", vmin=0, vmax=255)
    eixos[0].set_title("Original")
    eixos[1].imshow(espectro, cmap="magma")
    eixos[1].set_title("Espectro (log)")
    eixos[2].imshow(filtrada, cmap="gray", vmin=0, vmax=255)
    eixos[2].set_title("Passa-baixa")
    for eixo in eixos:
        eixo.axis("off")
    fig.suptitle(f"Fourier — {nome}")
    fig.tight_layout()
    try:
        fig.savefig(destino, dpi=110, bbox_inches="tight")
    finally:
        plt.close(fig)
    print(f"Comparação salva em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
