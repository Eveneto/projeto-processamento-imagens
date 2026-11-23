"""Gera fotos sintéticas para exercitar o pipeline antes das fotos reais.

As cores são simplificadas (cobre, ouro e prata sobre fundo claro). Elas não
substituem as fotografias do projeto; só permitem testar a contagem e a soma.
"""

import csv
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from config import CATALOGO

MM_POR_PX_SINTETICO = 0.2
FRACA_NUCLEO = 0.55
FUNDO = (240, 240, 240)

# Anel e núcleo em BGR. Núcleo None desenha uma moeda de cor única.
CORES = {
    "cobre": ((30, 50, 160), None),
    "ouro": ((30, 140, 200), None),
    "bimetalica_50": ((170, 170, 175), (30, 140, 200)),
    "bimetalica_1": ((30, 140, 200), (170, 170, 175)),
}


def moeda_por_centavos(centavos: int) -> dict:
    for item in CATALOGO:
        if item["centavos"] == centavos:
            return item
    raise ValueError(f"Denominação desconhecida: {centavos} centavos.")


def raio_px(mm: float, mm_por_px: float = MM_POR_PX_SINTETICO) -> int:
    diametro = mm / mm_por_px
    return max(1, int(diametro / 2.0 + 0.5))


def criar_imagem(
    moedas: list[dict],
    largura: int = 900,
    altura: int = 700,
    ruido: float = 4.0,
    semente: int = 0,
) -> np.ndarray:
    imagem = np.full((altura, largura, 3), FUNDO, np.uint8)
    for moeda in moedas:
        item = moeda_por_centavos(int(moeda["centavos"]))
        raio = raio_px(item["mm"])
        x, y = int(moeda["centro"][0]), int(moeda["centro"][1])
        if x - raio < 1 or y - raio < 1 or x + raio >= largura - 1 or y + raio >= altura - 1:
            raise ValueError(f"A moeda de {item['nome']} em {(x, y)} não cabe na imagem.")
        _desenhar(imagem, (x, y), raio, item["aparencia"])
    if ruido > 0:
        gerador = np.random.default_rng(semente)
        ruido_img = gerador.normal(0, ruido, imagem.shape)
        imagem = np.clip(imagem.astype(np.float32) + ruido_img, 0, 255).astype(np.uint8)
    return imagem


def _desenhar(imagem: np.ndarray, centro: tuple[int, int], raio: int, aparencia: str) -> None:
    anel, nucleo = CORES[aparencia]
    cv2.circle(imagem, centro, raio, anel, thickness=-1)
    if nucleo is not None:
        cv2.circle(imagem, centro, max(1, int(raio * FRACA_NUCLEO)), nucleo, thickness=-1)


def definicoes() -> list[dict]:
    return [
        {
            "arquivo": "sintetica_mista_01.png",
            "conjunto": "desenvolvimento",
            "semente": 1,
            "ruido": 4.0,
            "moedas": [
                {"centavos": 10, "centro": (140, 140)},
                {"centavos": 5, "centro": (360, 150)},
                {"centavos": 25, "centro": (640, 170)},
                {"centavos": 50, "centro": (200, 480)},
                {"centavos": 100, "centro": (520, 500)},
            ],
        },
        {
            "arquivo": "sintetica_ouro_02.png",
            "conjunto": "desenvolvimento",
            "semente": 2,
            "ruido": 4.0,
            "moedas": [
                {"centavos": 10, "centro": (180, 300)},
                {"centavos": 10, "centro": (420, 280)},
                {"centavos": 25, "centro": (700, 360)},
            ],
        },
        {
            "arquivo": "sintetica_mista_03.png",
            "conjunto": "teste",
            "semente": 3,
            "ruido": 4.0,
            "moedas": [
                {"centavos": 100, "centro": (160, 180)},
                {"centavos": 25, "centro": (430, 160)},
                {"centavos": 10, "centro": (700, 200)},
                {"centavos": 5, "centro": (250, 520)},
                {"centavos": 50, "centro": (560, 500)},
            ],
        },
        {
            "arquivo": "sintetica_encostadas_04.png",
            "conjunto": "teste",
            "semente": 4,
            "ruido": 4.0,
            "moedas": [
                {"centavos": 5, "centro": (250, 250)},
                {"centavos": 10, "centro": (349, 250)},
            ],
        },
        {
            "arquivo": "sintetica_sem_moedas_05.png",
            "conjunto": "teste",
            "semente": 5,
            "ruido": 0.0,
            "moedas": [],
        },
    ]


def gerar(raiz: Path | None = None) -> Path:
    raiz = raiz or RAIZ
    data = raiz / "data"
    linhas = []
    for definicao in definicoes():
        pasta = data / definicao["conjunto"]
        pasta.mkdir(parents=True, exist_ok=True)
        imagem = criar_imagem(
            definicao["moedas"],
            ruido=definicao["ruido"],
            semente=definicao["semente"],
        )
        destino = pasta / definicao["arquivo"]
        ok, buffer = cv2.imencode(".png", imagem)
        if not ok:
            raise RuntimeError(f"Não foi possível codificar {destino}")
        destino.write_bytes(buffer.tobytes())
        contagem = len(definicao["moedas"])
        valor = sum(int(moeda["centavos"]) for moeda in definicao["moedas"])
        linhas.append(
            {
                "arquivo": definicao["arquivo"],
                "conjunto": definicao["conjunto"],
                "contagem_real": contagem,
                "valor_centavos": valor,
            }
        )
        print(f"{destino.relative_to(raiz)} — {contagem} moedas, {valor} centavos")

    csv_path = data / "anotacoes.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=("arquivo", "conjunto", "contagem_real", "valor_centavos"),
        )
        escritor.writeheader()
        escritor.writerows(linhas)
    print(f"Anotações salvas em {csv_path.relative_to(raiz)}")
    return csv_path


if __name__ == "__main__":
    gerar()
