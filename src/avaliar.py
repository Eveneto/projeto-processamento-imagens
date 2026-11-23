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


def ler_resultados(caminho: str | Path | list | tuple) -> list[dict]:
    """Lê um resumo ou vários. Arquivos seguintes completam o primeiro."""
    if isinstance(caminho, (str, Path)):
        return ler_csv(caminho)
    linhas = []
    for item in caminho:
        linhas.extend(ler_csv(item))
    return linhas


def avaliar(
    anotacoes_csv: str | Path,
    resultados_csv: str | Path | list | tuple,
    conjunto: str = "teste",
) -> dict:
    anotacoes = ler_csv(anotacoes_csv)
    resultados = ler_resultados(resultados_csv)
    por_arquivo = {Path(_texto(linha.get("arquivo"))).name.lower(): linha for linha in resultados}
    alvo = conjunto.casefold()
    detalhes = []
    erros_contagem = []
    tempos = []
    erros_valor = []

    for linha in anotacoes:
        if alvo not in {"todos", "todas", "all"} and _texto(linha.get("conjunto")).casefold() != alvo:
            continue
        nome = Path(_texto(linha.get("arquivo"))).name
        real = para_int(linha.get("contagem_real"))
        valor_real = para_int(linha.get("valor_centavos"))
        previsto = por_arquivo.get(nome.lower())
        item = {
            "arquivo": nome,
            "conjunto": _texto(linha.get("conjunto")),
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

    soma_estimada = 0
    soma_confiavel = 0
    soma_real = 0
    for item in detalhes:
        if item["valor_real"] is not None:
            soma_real += item["valor_real"]
        if item["ausente"] or item["valor_estimado"] is None:
            continue
        soma_estimada += item["valor_estimado"]
        if item["valor_confiavel"] and (item["contagem_estimada"] or 0) > 0:
            soma_confiavel += item["valor_estimado"]

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
        "soma_estimada_centavos": soma_estimada,
        "soma_confiavel_centavos": soma_confiavel,
        "soma_real_centavos": soma_real,
        "detalhes": detalhes,
    }


def formatar_relatorio(metricas: dict) -> str:
    def numero(valor: float | None, casas: int) -> str:
        if valor is None:
            return "—"
        return f"{valor:.{casas}f}"

    def reais(centavos: int) -> str:
        sinal = "-" if centavos < 0 else ""
        centavos = abs(int(centavos))
        return f"{sinal}R$ {centavos // 100},{centavos % 100:02d}"

    def celula(valor: object) -> str:
        if valor is None:
            return "—"
        return str(valor)

    todos = str(metricas["conjunto"]).casefold() in {"todos", "todas", "all"}
    cabecalho = ["arquivo"]
    if todos:
        cabecalho.append("conjunto")
    cabecalho.extend(["real", "estimado", "erro", "valor real", "valor estimado", "confiavel", "tempo_s"])
    linhas = [
        f"Avaliação — conjunto {metricas['conjunto']}",
        f"Imagens: {metricas['imagens']}",
        (
            f"Soma total estimada: {metricas['soma_estimada_centavos']} centavos "
            f"({reais(metricas['soma_estimada_centavos'])})"
        ),
        (
            f"Soma da parte confiável: {metricas['soma_confiavel_centavos']} centavos "
            f"({reais(metricas['soma_confiavel_centavos'])})"
        ),
        (
            f"Soma real anotada: {metricas['soma_real_centavos']} centavos "
            f"({reais(metricas['soma_real_centavos'])})"
        ),
        f"Acurácia exata da contagem: {numero(metricas['acuracia_exata_percentual'], 2)}%",
        f"Erro absoluto médio da contagem: {numero(metricas['erro_absoluto_medio'], 3)}",
        f"Tempo médio por imagem: {numero(metricas['tempo_medio_s'], 4)} s",
        f"Erro absoluto médio do valor (centavos): {numero(metricas['erro_absoluto_medio_valor'], 2)}",
        f"Imagens com valor comparado: {metricas['imagens_valor_comparadas']}",
        f"Imagens sem resultado: {metricas['imagens_ausentes']}",
        "",
        " | ".join(cabecalho),
    ]
    for item in metricas["detalhes"]:
        erro = "ausente" if item["ausente"] else item["erro_contagem"]
        confiavel = "—" if item["ausente"] else ("sim" if item["valor_confiavel"] else "nao")
        campos = [str(item["arquivo"])]
        if todos:
            campos.append(celula(item.get("conjunto")))
        campos.extend(
            [
                celula(item["contagem_real"]),
                celula(item["contagem_estimada"]),
                celula(erro),
                celula(item["valor_real"]),
                celula(item["valor_estimado"]),
                confiavel,
                numero(item["tempo_s"], 4),
            ]
        )
        linhas.append(" | ".join(campos))
    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compara a contagem automática com as anotações do conjunto de teste."
    )
    parser.add_argument("--anotacoes", type=Path, default=Path("data/anotacoes.csv"))
    parser.add_argument(
        "--resultados",
        type=Path,
        nargs="+",
        default=[Path("data/resultados/resumo.csv")],
        help="Um ou mais resumo.csv. Use juntos para juntar desenvolvimento e teste.",
    )
    parser.add_argument(
        "--conjunto",
        default="teste",
        help="teste, desenvolvimento ou todos.",
    )
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
