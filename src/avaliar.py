"""Acurácia exata, erro absoluto médio e tempo médio no conjunto de teste."""

import argparse
import csv
import sys
from pathlib import Path


CAMPOS_ANOTACAO = ("arquivo", "conjunto", "contagem_real", "valor_centavos")


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def para_float(valor: object) -> float | None:
    texto = _texto(valor)
    if not texto:
        return None
    texto = texto.replace(" ", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return float(texto)


def para_int(valor: object) -> int | None:
    numero = para_float(valor)
    if numero is None:
        return None
    return int(round(numero))


def para_bool(valor: object) -> bool:
    return _texto(valor).casefold() in {"1", "true", "sim", "verdadeiro"}


def ler_csv(caminho: str | Path) -> list[dict]:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def avaliar(
    anotacoes_csv: str | Path,
    resultados_csv: str | Path,
    conjunto: str = "teste",
) -> dict:
    anotacoes = ler_csv(anotacoes_csv)
    resultados = ler_csv(resultados_csv)
    por_arquivo = {Path(_texto(linha.get("arquivo"))).name.lower(): linha for linha in resultados}
    alvo = conjunto.casefold()
    detalhes = []
    erros_contagem = []
    tempos = []
    erros_valor = []

    for linha in anotacoes:
        if _texto(linha.get("conjunto")).casefold() != alvo:
            continue
        nome = Path(_texto(linha.get("arquivo"))).name
        real = para_int(linha.get("contagem_real"))
        valor_real = para_int(linha.get("valor_centavos"))
        previsto = por_arquivo.get(nome.lower())
        item = {
            "arquivo": nome,
            "contagem_real": real,
            "contagem_estimada": None,
            "erro_contagem": None,
            "valor_real": valor_real,
            "valor_estimado": None,
            "valor_confiavel": False,
            "tempo_s": None,
            "ausente": previsto is None,
        }
        if previsto is not None:
            estimada = para_int(previsto.get("contagem"))
            tempo = para_float(previsto.get("tempo_s"))
            valor_estimado = para_int(previsto.get("valor_centavos"))
            confiavel = para_bool(previsto.get("valor_confiavel"))
            item["contagem_estimada"] = estimada
            item["valor_estimado"] = valor_estimado
            item["valor_confiavel"] = confiavel
            item["tempo_s"] = tempo
            if real is not None and estimada is not None:
                item["erro_contagem"] = abs(estimada - real)
                erros_contagem.append(item["erro_contagem"])
            if tempo is not None:
                tempos.append(tempo)
            if confiavel and valor_real is not None and valor_estimado is not None:
                erros_valor.append(abs(valor_estimado - valor_real))
        detalhes.append(item)

    total = len(detalhes)
    acertos = sum(
        1
        for item in detalhes
        if item["contagem_real"] is not None
        and item["contagem_estimada"] == item["contagem_real"]
    )
    return {
        "conjunto": conjunto,
        "imagens": total,
        "acertos": acertos,
        "acuracia_exata_percentual": (100.0 * acertos / total) if total else None,
        "erro_absoluto_medio": (sum(erros_contagem) / len(erros_contagem)) if erros_contagem else None,
        "tempo_medio_s": (sum(tempos) / len(tempos)) if tempos else None,
        "erro_absoluto_medio_valor": (sum(erros_valor) / len(erros_valor)) if erros_valor else None,
        "imagens_valor_comparadas": len(erros_valor),
        "imagens_ausentes": sum(1 for item in detalhes if item["ausente"]),
        "detalhes": detalhes,
    }


def formatar_relatorio(metricas: dict) -> str:
    def numero(valor: float | None, casas: int) -> str:
        if valor is None:
            return "—"
        return f"{valor:.{casas}f}"

    linhas = [
        f"Avaliação — conjunto {metricas['conjunto']}",
        f"Imagens: {metricas['imagens']}",
        f"Acurácia exata da contagem: {numero(metricas['acuracia_exata_percentual'], 2)}%",
        f"Erro absoluto médio da contagem: {numero(metricas['erro_absoluto_medio'], 3)}",
        f"Tempo médio por imagem: {numero(metricas['tempo_medio_s'], 4)} s",
        f"Erro absoluto médio do valor (centavos): {numero(metricas['erro_absoluto_medio_valor'], 2)}",
        f"Imagens com valor comparado: {metricas['imagens_valor_comparadas']}",
        f"Imagens sem resultado: {metricas['imagens_ausentes']}",
        "",
        "arquivo | real | estimado | erro | valor real | valor estimado | tempo_s",
    ]
    for item in metricas["detalhes"]:
        erro = "ausente" if item["ausente"] else item["erro_contagem"]
        linhas.append(
            " | ".join(
                [
                    str(item["arquivo"]),
                    str(item["contagem_real"]),
                    str(item["contagem_estimada"]),
                    str(erro),
                    str(item["valor_real"]),
                    str(item["valor_estimado"]),
                    numero(item["tempo_s"], 4),
                ]
            )
        )
    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compara a contagem automática com as anotações do conjunto de teste."
    )
    parser.add_argument("--anotacoes", type=Path, default=Path("data/anotacoes.csv"))
    parser.add_argument("--resultados", type=Path, default=Path("data/resultados/resumo.csv"))
    parser.add_argument("--conjunto", default="teste")
    parser.add_argument("--saida", type=Path, default=Path("data/resultados/relatorio_avaliacao.txt"))
    args = parser.parse_args(argv)
    try:
        metricas = avaliar(args.anotacoes, args.resultados, args.conjunto)
    except FileNotFoundError as erro:
        print(erro)
        return 1
    relatorio = formatar_relatorio(metricas)
    print(relatorio, end="")
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(relatorio, encoding="utf-8")
    print(f"Relatório salvo em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
