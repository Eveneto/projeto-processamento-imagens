"""Linha de comando: processa uma imagem ou uma pasta e salva as etapas."""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from config import Config

from src.io_imagem import carregar_imagem, listar_imagens
from src.pipeline import processar, publicar_resultado
from src.visualizar import salvar_etapas


CAMPOS_RESUMO = (
    "arquivo",
    "contagem",
    "valor_centavos",
    "valor_confiavel",
    "tempo_s",
    "observacoes",
)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Conta moedas em uma imagem e estima a soma dos valores."
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--imagem", type=Path, help="Caminho de uma imagem JPG ou PNG.")
    grupo.add_argument("--pasta", type=Path, help="Pasta com as imagens a processar.")
    parser.add_argument("--saida", type=Path, default=Path("data/resultados"))
    parser.add_argument(
        "--metodo",
        choices=("otsu", "adaptativo", "bordas"),
        default="bordas",
        help="Segmentação. O padrão é detecção de bordas; Otsu fica disponível para comparação.",
    )
    parser.add_argument(
        "--polaridade",
        choices=("auto", "moedas_escuras", "moedas_claras"),
        default="auto",
    )
    parser.add_argument(
        "--sem-valor",
        action="store_true",
        help="Só conta as moedas, sem estimar a denominação.",
    )
    parser.add_argument(
        "--mm-por-px",
        type=float,
        default=None,
        help="Escala fixa, quando a distância da câmera não muda.",
    )
    return parser


def _config_de_args(args: argparse.Namespace) -> Config:
    return Config(
        metodo_segmentacao=args.metodo,
        polaridade=args.polaridade,
        somar_valores=not args.sem_valor,
        mm_por_px=args.mm_por_px,
    )


def _titulo(arquivo: str, resultado: dict) -> str:
    contagem = resultado["contagem"]
    valor = resultado["valor_centavos"]
    if valor is None:
        return f"{arquivo} — {contagem} moedas"
    aviso = "" if resultado["valor_confiavel"] else " (soma incerta)"
    return f"{arquivo} — {contagem} moedas — R$ {valor / 100:.2f}{aviso}"


def _texto_valor(resultado: dict) -> str:
    valor = resultado["valor_centavos"]
    if valor is None:
        return "valor não calculado"
    aviso = "" if resultado["valor_confiavel"] else " (incerto)"
    return f"R$ {valor / 100:.2f}{aviso}"


def _processar_arquivo(caminho: Path, config: Config, saida: Path) -> dict | None:
    try:
        imagem = carregar_imagem(caminho)
        inicio = time.perf_counter()
        resultado = processar(imagem, config)
        tempo = time.perf_counter() - inicio
    except Exception as erro:
        print(f"{caminho.name}: erro — {erro}")
        return None

    publicado = publicar_resultado(resultado, caminho.name, tempo)
    destino = saida / caminho.stem
    salvar_etapas(
        destino,
        resultado["original"],
        resultado["cinza"],
        resultado["mascara"],
        resultado["resultado"],
        _titulo(caminho.name, resultado),
    )
    (destino / "resultado.json").write_text(
        json.dumps(publicado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"{caminho.name}: {resultado['contagem']} moeda(s), "
        f"{_texto_valor(resultado)}, {tempo * 1000:.1f} ms"
    )
    for observacao in resultado["observacoes"]:
        print(f"  - {observacao}")
    return publicado


def _gravar_resumo(caminho: Path, linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_RESUMO)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(
                {
                    "arquivo": linha["arquivo"],
                    "contagem": linha["contagem"],
                    "valor_centavos": "" if linha["valor_centavos"] is None else linha["valor_centavos"],
                    "valor_confiavel": "sim" if linha["valor_confiavel"] else "nao",
                    "tempo_s": linha["tempo_s"],
                    "observacoes": " | ".join(linha["observacoes"]),
                }
            )


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    config = _config_de_args(args)
    if args.imagem is not None:
        imagens = [args.imagem]
    else:
        try:
            imagens = listar_imagens(args.pasta)
        except FileNotFoundError as erro:
            print(erro)
            return 1
    if not imagens:
        print("Nenhuma imagem encontrada.")
        return 1

    publicados = []
    falhas = 0
    for caminho in imagens:
        publicado = _processar_arquivo(caminho, config, args.saida)
        if publicado is None:
            falhas += 1
        else:
            publicados.append(publicado)

    if publicados:
        _gravar_resumo(args.saida / "resumo.csv", publicados)
        print(f"Resumo salvo em {args.saida / 'resumo.csv'}")
    return 1 if falhas or not publicados else 0


if __name__ == "__main__":
    raise SystemExit(main())
