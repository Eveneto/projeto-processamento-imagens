"""Gera um painel HTML com todas as fotos anotadas.

Serve para revisar o desenvolvimento antes da execução final do teste.
O método não é alterado aqui.
"""

import csv
import html
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import cv2

from config import CATALOGO, Config
from src.avaliar import avaliar, formatar_relatorio
from src.io_imagem import carregar_imagem, salvar_imagem
from src.pipeline import processar, publicar_resultado


def _reduzir(imagem, largura: int = 420):
    altura, largura_atual = imagem.shape[:2]
    if largura_atual <= largura:
        return imagem
    nova_altura = max(1, int(altura * largura / largura_atual))
    return cv2.resize(imagem, (largura, nova_altura), interpolation=cv2.INTER_AREA)


def _ler_anotacoes(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def _achar_imagem(nome: str, conjunto: str) -> Path:
    candidato = RAIZ / "data" / conjunto / nome
    if candidato.is_file():
        return candidato
    raise FileNotFoundError(f"Não achei {nome} em data/{conjunto}")


def _numero(valor, casas: int) -> str:
    if valor is None:
        return "—"
    return f"{valor:.{casas}f}"


def gerar(saida: Path | None = None) -> Path:
    saida = saida or RAIZ / "data" / "painel"
    previews = saida / "img"
    previews.mkdir(parents=True, exist_ok=True)
    anotacoes = _ler_anotacoes(RAIZ / "data" / "anotacoes.csv")
    config = Config()
    resumo = []
    cartoes = []

    for indice, linha in enumerate(anotacoes, start=1):
        nome = linha["arquivo"]
        conjunto = linha["conjunto"]
        imagem = carregar_imagem(_achar_imagem(nome, conjunto))
        inicio = time.perf_counter()
        resultado = processar(imagem, config)
        tempo = time.perf_counter() - inicio
        publicado = publicar_resultado(resultado, nome, tempo)
        pasta = previews / f"{indice:03d}"
        salvar_imagem(pasta / "original.jpg", _reduzir(resultado["original"]))
        salvar_imagem(pasta / "mascara.jpg", _reduzir(resultado["mascara"]))
        salvar_imagem(pasta / "resultado.jpg", _reduzir(resultado["resultado"]))
        resumo.append(
            {
                "arquivo": nome,
                "contagem": publicado["contagem"],
                "valor_centavos": "" if publicado["valor_centavos"] is None else publicado["valor_centavos"],
                "valor_confiavel": "sim" if publicado["valor_confiavel"] else "nao",
                "tempo_s": publicado["tempo_s"],
                "observacoes": " | ".join(publicado["observacoes"]),
            }
        )
        cartoes.append(
            {
                "indice": indice,
                "arquivo": nome,
                "conjunto": conjunto,
                "contagem_real": linha["contagem_real"],
                "valor_real": linha.get("valor_centavos", ""),
                "contagem": publicado["contagem"],
                "valor": publicado["valor_centavos"],
                "confiavel": publicado["valor_confiavel"],
                "tempo": publicado["tempo_s"],
                "observacoes": publicado["observacoes"],
                "juncao": any(moeda["possivel_juncao"] for moeda in publicado["moedas"]),
                "moedas": [
                    {
                        "rotulo": moeda.get("rotulo") or "?",
                        "centavos": moeda.get("valor_centavos"),
                        "aparencia": moeda.get("aparencia"),
                        "centro": moeda.get("metal_centro"),
                        "anel": moeda.get("metal_anel"),
                        "circularidade": moeda.get("circularidade"),
                        "juncao": moeda.get("possivel_juncao"),
                    }
                    for moeda in publicado["moedas"]
                ],
                "rejeitados": [
                    {
                        "motivo": item["motivo"],
                        "circularidade": item["circularidade"],
                    }
                    for item in publicado["rejeitados"]
                ],
            }
        )
        print(f"{conjunto}: {nome} -> {publicado['contagem']}")

    with (saida / "resumo.csv").open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=("arquivo", "contagem", "valor_centavos", "valor_confiavel", "tempo_s", "observacoes"),
        )
        escritor.writeheader()
        escritor.writerows(resumo)

    metricas = {
        conjunto: avaliar(RAIZ / "data" / "anotacoes.csv", saida / "resumo.csv", conjunto)
        for conjunto in ("desenvolvimento", "teste")
    }
    (saida / "relatorio_desenvolvimento.txt").write_text(
        formatar_relatorio(metricas["desenvolvimento"]),
        encoding="utf-8",
    )
    pagina = saida / "index.html"
    pagina.write_text(_html(cartoes, metricas, config), encoding="utf-8")
    print(f"Painel salvo em {pagina}")
    return pagina


CENAS = {
    "WhatsApp Image 2026-11-23 at 09.34.09.jpeg": "Duas moedas de 10 centavos quase encostadas.",
    "WhatsApp Image 2026-11-23 at 09.34.04.jpeg": "Uma de 5 e uma de 10 centavos encostadas.",
    "WhatsApp Image 2026-11-23 at 09.34.09 (1).jpeg": "Repetição das duas de 10 centavos encostadas.",
    "WhatsApp Image 2026-11-23 at 09.34.08 (2).jpeg": "Duas de 10 centavos; uma fica cortada na borda do quadro.",
    "WhatsApp Image 2026-11-23 at 09.18.41 (2).jpeg": "Foto borrada de uma moeda. O valor real ficou em branco.",
    "WhatsApp Image 2026-11-23 at 09.18.50.jpeg": "Uma moeda de 5 centavos com dedos na borda do quadro.",
    "WhatsApp Image 2026-11-23 at 09.18.44 (1).jpeg": "Uma moeda de 10 centavos cuja borda não fecha.",
    "WhatsApp Image 2026-11-23 at 09.18.54 (3).jpeg": "Uma moeda de 10 centavos cuja borda não fecha.",
    "WhatsApp Image 2026-11-23 at 09.34.09 (2).jpeg": "Uma de 5 e uma de 10 centavos encostadas, no conjunto de teste.",
    "WhatsApp Image 2026-11-23 at 09.18.52 (3).jpeg": "Uma moeda de 5 centavos no conjunto de teste. O arco da borda não fecha.",
    "WhatsApp Image 2026-11-23 at 09.34.08 (3).jpeg": "Duas moedas de 10 centavos. A contagem acertou e a soma, não.",
    "WhatsApp Image 2026-11-23 at 09.34.08 (1).jpeg": "Duas de 10 e uma de 5 centavos, no teste. A contagem acertou e a soma, não.",
}


def _virgula(numero: float, casas: int = 2) -> str:
    return f"{numero:.{casas}f}".replace(".", ",")


def _valor_anotado(texto: str) -> int | None:
    texto = (texto or "").strip()
    if not texto:
        return None
    return int(texto)


def _causa(cartao: dict, config: Config) -> str:
    real = int(cartao["contagem_real"])
    estimado = int(cartao["contagem"])
    valor_real = _valor_anotado(cartao["valor_real"])
    partes = []
    cena = CENAS.get(cartao["arquivo"])
    if cena:
        partes.append(cena)
    if real != estimado and cartao["juncao"]:
        partes.append(
            "O Canny funde as bordas que se tocam num contorno só. "
            f"A circularidade { _virgula(config.circularidade_minima_juncao) }–"
            f"{ _virgula(config.circularidade_minima) } ainda entra na contagem, "
            "como uma moeda, e recebe a marca de junção. A junção não ganha denominação."
        )
    elif real != estimado and estimado == 0:
        partes.append("Nenhum contorno foi aceito.")
        grandes = [item for item in cartao["rejeitados"] if item["motivo"] == "area_grande"]
        pouco_circulares = [
            item for item in cartao["rejeitados"] if item["motivo"] == "circularidade_baixa"
        ]
        if grandes:
            partes.append(
                "A máscara formou um bloco com mais de "
                f"{_virgula(config.area_maxima_relativa * 100, 0)}% da imagem "
                f"(circularidade {_virgula(grandes[0]['circularidade'])}). "
                "A moeda se fundiu com a borda da mesa ou com a outra moeda, e o bloco inteiro foi descartado."
            )
        if pouco_circulares:
            partes.append(
                "O que restou teve circularidade "
                f"{_virgula(pouco_circulares[0]['circularidade'])}, abaixo de "
                f"{_virgula(config.circularidade_minima_juncao)}. "
                "Abaixo desse piso o contorno é descartado e nem recebe a marca de junção. "
                "É o caso do arco de Canny que não fecha o disco."
            )
        if not cartao["rejeitados"]:
            partes.append(
                "O Canny não chegou a fechar um contorno. Borrão, moeda cortada ou borda fraca "
                "não viram disco."
            )
        partes.append(
            "Com zero detecções, a soma devolve 0 centavos e marca esse zero como confiável."
        )
    elif real != estimado:
        partes.append(f"A contagem estimada foi {estimado} e a real é {real}.")

    errou_valor = (
        cartao["confiavel"]
        and valor_real is not None
        and cartao["valor"] is not None
        and int(cartao["valor"]) != valor_real
        and estimado > 0
    )
    if errou_valor:
        rotulos = ", ".join(
            f"{moeda['rotulo']} (centro {moeda['centro']}, anel {moeda['anel']})"
            for moeda in cartao["moedas"]
        )
        if any(moeda["rotulo"] == "50c" for moeda in cartao["moedas"]):
            detalhe = (
                "Uma moeda de 10 centavos gasta teve o centro lido como ouro e o anel como prata. "
                "No catálogo essa combinação é a de 50 centavos."
            )
        elif any(moeda["rotulo"] == "25c" for moeda in cartao["moedas"]):
            detalhe = (
                "Uma moeda de 10 centavos foi lida como 25. As duas são ouro e só o diâmetro as separa. "
                f"A tolerância é de {_virgula(config.tolerancia_mm, 0)} mm, e a escala veio de outra moeda da mesma foto."
            )
        else:
            detalhe = "A cor HSV ou o diâmetro apontou uma denominação diferente da moeda real."
        partes.append(
            f"A soma foi marcada como confiável e deu {cartao['valor']} centavos, "
            f"contra {valor_real} centavos. Atribuição: {rotulos}. {detalhe}"
        )
    return " ".join(partes)


def _bloco_tecnico(cartoes: list[dict], metricas: dict, config: Config) -> str:
    catalogo = "".join(
        "<tr><td>{nome}</td><td>{mm}</td><td>{aparencia}</td><td>{centavos}</td></tr>".format(
            nome=html.escape(item["nome"]),
            mm=_virgula(item["mm"], 0),
            aparencia=html.escape(item["aparencia"]),
            centavos=item["centavos"],
        )
        for item in CATALOGO
    )
    itens = []
    for cartao in cartoes:
        real = int(cartao["contagem_real"])
        estimado = int(cartao["contagem"])
        valor_real = _valor_anotado(cartao["valor_real"])
        errou_contagem = real != estimado
        errou_valor = (
            cartao["confiavel"]
            and valor_real is not None
            and cartao["valor"] is not None
            and int(cartao["valor"]) != valor_real
        )
        if not errou_contagem and not errou_valor:
            continue
        causa = _causa(cartao, config)
        tipo = []
        if errou_contagem:
            tipo.append(f"contagem {estimado} em vez de {real}")
        if errou_valor and estimado > 0:
            tipo.append(f"soma {cartao['valor']} em vez de {valor_real}")
        elif errou_valor:
            tipo.append(f"soma 0 confiável em vez de {valor_real}")
        itens.append(
            "<li><a href='#foto-{indice}'>{arquivo}</a> "
            "<span class='conjunto'>({conjunto})</span> — {tipo}. {causa}</li>".format(
                indice=cartao["indice"],
                arquivo=html.escape(cartao["arquivo"]),
                conjunto=html.escape(cartao["conjunto"]),
                tipo=html.escape("; ".join(tipo)),
                causa=html.escape(causa),
            )
        )
    dev = metricas["desenvolvimento"]
    return """
<section class="tecnica">
<h2 class="secao">Como a moeda é identificada</h2>
<ol>
<li>A foto entra em BGR. Um desfoque gaussiano de {kernel}×{kernel} reduz ruído da compressão. Dessa imagem saem o cinza, usado na forma, e o HSV, usado na cor. O CLAHE está desligado.</li>
<li>A segmentação padrão é a borda de Canny, com limiares {canny1} e {canny2}. A borda é dilatada e fechada com uma elipse de {morfologia}×{morfologia} pixels. Os contornos externos são preenchidos e viram a máscara branca. Otsu e o limiar adaptativo continuam no código para comparação. Otsu saiu do padrão porque, no desenvolvimento, a moeda de 10 centavos clara fica quase da mesma tonalidade do papel e some no limiar global.</li>
<li>A máscara passa por abertura ({abertura} vez), fechamento ({fechamento} vezes) e preenchimento dos buracos internos. O canto da foto é tratado como fundo, então um reflexo no meio da moeda entra no objeto e a mesa em volta continua de fora.</li>
<li>Cada contorno externo vira candidato. A área precisa ficar entre {area_min} e {area_max} da imagem, o que descarta poeira e também a faixa preta da mesa quando ela ocupa um pedaço grande do quadro. A circularidade é 4π × área / perímetro²: o círculo perfeito vale 1. De {circ_ok} para cima, conta como uma moeda. Entre {circ_juncao} e {circ_ok}, ainda conta como um objeto e marca possível junção. Abaixo de {circ_juncao}, descarta.</li>
</ol>
<h2 class="secao">Como o valor é somado</h2>
<p>O catálogo é a 2ª família do Real. A cor separa cobre, ouro e as duas bimetálicas. O ouro aparece duas vezes, e só o diâmetro separa 10 de 25 centavos.</p>
<table>
<thead><tr><th>Moeda</th><th>Diâmetro (mm)</th><th>Aparência</th><th>Centavos</th></tr></thead>
<tbody>{catalogo}</tbody>
</table>
<p>De cada moeda o programa lê a mediana do HSV em dois anéis: o disco interno, até {centro} do raio, e a borda, de {anel_int} a {anel_ext} do raio. Saturação abaixo de {prata} é prata. Matiz até {cobre} ou a partir de {cobre_alto} é cobre. Matiz até {ouro} é ouro. Centro e anel iguais em cobre viram 5 centavos. Ouro no centro e prata no anel viram 50 centavos. Prata no centro e ouro no anel viram R$ 1. Ouro nos dois lados pode ser 10 ou 25 centavos.</p>
<p>A escala em milímetros por pixel sai da mediana das moedas cuja aparência aponta um único diâmetro. Ouro, junção e cor incerta não entram nessa conta. Não há escala fixa informada à mão. Se não houver escala e existirem dois tamanhos de ouro com razão acima de {razao}, o corte fica no meio dos dois diâmetros em pixels. Uma única classe de ouro, sem escala, fica sem denominação. Junção também fica sem denominação.</p>
<p>A soma é a dos centavos atribuídos. Ela só é confiável quando toda moeda detectada tem denominação. Se alguma falha, o número mostrado é uma soma parcial e o painel marca “incerto”. Se nenhuma moeda é detectada, a soma devolve 0 e marca esse 0 como confiável.</p>
<h2 class="secao">Onde o método erra nesta revisão</h2>
<p>No desenvolvimento a contagem fecha em {acertos} de {imagens} fotos. O erro absoluto médio é {mae} moeda. As falhas de contagem se concentram em três mecanismos: moedas que se tocam, borda que não fecha e objeto cortado ou atrapalhado no quadro. A soma é o ponto fraco. As fotos só têm 5 e 10 centavos velhos: 2 mm de diferença e a cor gasta. Na maior parte das fotos o valor sai incerto. Quando a moeda some na detecção, o 0 confiável entra na conta do erro de valor e puxa a média para cima.</p>
<ul class="falhas">{falhas}</ul>
</section>
""".format(
        kernel=config.kernel_gaussiano,
        canny1=config.canny_limiar1,
        canny2=config.canny_limiar2,
        morfologia=config.kernel_morfologia,
        abertura=config.abertura_iteracoes,
        fechamento=config.fechamento_iteracoes,
        area_min=_virgula(config.area_minima_relativa * 100, 1) + "%",
        area_max=_virgula(config.area_maxima_relativa * 100, 0) + "%",
        circ_ok=_virgula(config.circularidade_minima),
        circ_juncao=_virgula(config.circularidade_minima_juncao),
        catalogo=catalogo,
        centro=_virgula(config.fracao_amostra_centro * 100, 0) + "%",
        anel_int=_virgula(config.fracao_amostra_anel_interna * 100, 0) + "%",
        anel_ext=_virgula(config.fracao_amostra_anel_externa * 100, 0) + "%",
        prata=_virgula(config.saturacao_prata, 0),
        cobre=_virgula(config.hue_cobre_max, 0),
        cobre_alto=_virgula(180 - config.hue_cobre_max, 0),
        ouro=_virgula(config.hue_ouro_max, 0),
        razao=_virgula(config.razao_duas_classes),
        acertos=dev["acertos"],
        imagens=dev["imagens"],
        mae=_virgula(dev["erro_absoluto_medio"], 3),
        falhas="".join(itens),
    )


def _fotos_json(cartoes: list[dict], config: Config) -> str:
    fotos = []
    for cartao in cartoes:
        real = int(cartao["contagem_real"])
        estimado = int(cartao["contagem"])
        textos = list(cartao["observacoes"])
        causa = _causa(cartao, config)
        if causa:
            textos.append(causa)
        if not textos:
            textos = ["Contagem e soma sem observação extra."]
        valor_real = _valor_anotado(cartao["valor_real"])
        fotos.append(
            {
                "indice": cartao["indice"],
                "arquivo": cartao["arquivo"],
                "conjunto": cartao["conjunto"],
                "contagemReal": real,
                "contagem": estimado,
                "valorReal": valor_real,
                "valor": None if cartao["valor"] is None else int(cartao["valor"]),
                "confiavel": bool(cartao["confiavel"]),
                "tempo": cartao["tempo"],
                "juncao": bool(cartao["juncao"]),
                "acertou": real == estimado,
                "descricao": " ".join(textos),
                "moedas": cartao["moedas"],
            }
        )
    return json.dumps(fotos, ensure_ascii=False).replace("<", "\\u003c")


def _html(cartoes: list[dict], metricas: dict, config: Config) -> str:
    blocos = []
    for conjunto in ("desenvolvimento", "teste"):
        dados = metricas[conjunto]
        acuracia = _numero(dados["acuracia_exata_percentual"], 1)
        erro = _numero(dados["erro_absoluto_medio"], 3)
        tempo = _numero(dados["tempo_medio_s"], 3)
        blocos.append(
            "<article class='metrica'>"
            f"<p>Acurácia no {html.escape(conjunto)}</p>"
            f"<strong>{html.escape(acuracia)}%</strong>"
            f"<span>{dados['acertos']} de {dados['imagens']} fotos</span>"
            "</article>"
            "<article class='metrica'>"
            f"<p>Erro absoluto médio no {html.escape(conjunto)}</p>"
            f"<strong>{html.escape(erro)}</strong>"
            "<span>média de |estimado − real|</span>"
            "</article>"
            "<article class='metrica'>"
            f"<p>Tempo médio no {html.escape(conjunto)}</p>"
            f"<strong>{html.escape(tempo)} s</strong>"
            "<span>por imagem</span>"
            "</article>"
        )
    pagina = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Painel — contagem de moedas</title>
<style>
body { font-family: Georgia, serif; margin: 0; background: #f4f1ea; color: #1d1a16; }
main { max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }
h1 { font-size: 2rem; margin-bottom: 0.2rem; }
.aviso, .nota { background: #fff; border-left: 4px solid #8a5a12; padding: 12px 16px; }
.metricas, .somas, .grade { display: grid; gap: 12px; }
.metricas, .somas { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin: 16px 0; }
.metrica, .soma { background: #fff; padding: 16px; }
.metrica p, .metrica span, .soma span, .meta, figcaption { margin: 0; color: #5c564c; }
.metrica strong, .soma strong { display: block; font-size: 1.7rem; margin: 6px 0; }
.soma.destaque { background: #1d1a16; color: #f4f1ea; }
.soma.destaque span { color: #d9d0c1; }
.filtros { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.filtros input { flex: 1 1 220px; padding: 8px 10px; border: 1px solid #d9d0c1; font: inherit; }
.filtros button { border: 1px solid #d9d0c1; background: #fff; padding: 8px 12px; font: inherit; cursor: pointer; }
.filtros button.ativo { background: #1d1a16; color: #f4f1ea; }
.grade { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.cartao { background: #fff; padding: 12px; border-top: 4px solid #1d6b3a; }
.cartao.erro { border-top-color: #9d2c2c; }
.cartao h2 { font-size: 1rem; margin: 8px 0; word-break: break-word; }
.cartao img.capa { width: 100%; height: 180px; object-fit: cover; background: #111; }
.etiquetas { display: flex; flex-wrap: wrap; gap: 6px; }
.etiquetas span, .moedas span { background: #f4f1ea; padding: 2px 8px; font-size: 0.85rem; }
.valores { display: flex; justify-content: space-between; gap: 12px; margin: 8px 0; }
.valores div { flex: 1; }
.valores span, .valores strong { display: block; }
.valores strong { font-size: 1.05rem; }
.descricao { line-height: 1.4; }
.cartao button { margin-top: 8px; border: 0; background: transparent; color: #8a5a12; font: inherit; cursor: pointer; padding: 0; }
.detalhe { display: none; margin-top: 8px; }
.cartao.aberto .detalhe { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.detalhe img { width: 100%; height: auto; background: #111; }
table { width: 100%; border-collapse: collapse; background: #fff; font-family: Consolas, monospace; font-size: 13px; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e4dfd4; }
h2.secao { font-size: 1.45rem; margin: 1.4rem 0 0.4rem; }
.tecnica { background: #fff; padding: 4px 20px 20px; margin-top: 20px; line-height: 1.45; }
.tecnica ol, .tecnica ul { padding-left: 1.2rem; }
.tecnica a { color: #8a5a12; }
</style>
</head>
<body>
<main>
<h1>Fotos, soma de cada cena e total estimado</h1>
<p class="aviso">O método permanece o de bordas. Os filtros abaixo mudam as fotos e recalculam o total. A mesma moeda aparece em várias fotos, então o total soma as cenas e não é o dinheiro de uma única mesa.</p>
<section class="somas" id="somas"></section>
<div class="filtros">
<input id="busca" type="search" placeholder="Buscar foto ou descrição">
<button type="button" data-grupo="conjunto" data-valor="todas" class="ativo">Todas</button>
<button type="button" data-grupo="conjunto" data-valor="desenvolvimento">Desenvolvimento</button>
<button type="button" data-grupo="conjunto" data-valor="teste">Teste</button>
<button type="button" data-grupo="resultado" data-valor="todas" class="ativo">Contagens</button>
<button type="button" data-grupo="resultado" data-valor="acertos">Acertos</button>
<button type="button" data-grupo="resultado" data-valor="erros">Erros</button>
<button type="button" data-grupo="valor" data-valor="todas" class="ativo">Somas</button>
<button type="button" data-grupo="valor" data-valor="confiavel">Soma confiável</button>
<button type="button" data-grupo="valor" data-valor="incerto">Soma incerta</button>
</div>
<section class="grade" id="grade"></section>
<section class="metricas">__METRICAS__</section>
<details class="tecnica">
<summary>Técnicas e imprecisões</summary>
__TECNICA__
</details>
</main>
<script>
const FOTOS = __DADOS__;
const estado = { conjunto: "todas", resultado: "todas", valor: "todas", busca: "" };

function escapar(texto) {
  return String(texto)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function reais(centavos) {
  if (centavos === null || centavos === undefined) return "—";
  const abs = Math.abs(centavos);
  const reaisInteiros = Math.floor(abs / 100);
  const cents = String(abs % 100).padStart(2, "0");
  return (centavos < 0 ? "-" : "") + "R$ " + reaisInteiros + "," + cents;
}

function visiveis() {
  const busca = estado.busca.trim().toLowerCase();
  return FOTOS.filter(function (foto) {
    if (estado.conjunto !== "todas" && foto.conjunto !== estado.conjunto) return false;
    if (estado.resultado === "acertos" && !foto.acertou) return false;
    if (estado.resultado === "erros" && foto.acertou) return false;
    const denominou = foto.confiavel && foto.contagem > 0;
    if (estado.valor === "confiavel" && !denominou) return false;
    if (estado.valor === "incerto" && denominou) return false;
    if (!busca) return true;
    return (foto.arquivo + " " + foto.descricao).toLowerCase().indexOf(busca) >= 0;
  });
}

function somar(lista, campo, soConfiavel) {
  return lista.reduce(function (total, foto) {
    if (soConfiavel && !foto.confiavel) return total;
    const valor = foto[campo];
    return total + (valor === null || valor === undefined ? 0 : valor);
  }, 0);
}

function desenharSomas(lista) {
  const estimada = somar(lista, "valor", false);
  const confiavel = lista.reduce(function (total, foto) {
    return total + (foto.confiavel && foto.contagem > 0 ? foto.valor : 0);
  }, 0);
  const real = somar(lista, "valorReal", false);
  const nConf = lista.filter(function (foto) { return foto.confiavel && foto.contagem > 0; }).length;
  const nReal = lista.filter(function (foto) { return foto.valorReal !== null; }).length;
  document.getElementById("somas").innerHTML =
    "<article class='soma destaque'><p>Soma total estimada</p><strong>" + reais(estimada) +
    "</strong><span>" + estimada + " centavos nas " + lista.length + " fotos visíveis</span></article>" +
    "<article class='soma'><p>Parte confiável</p><strong>" + reais(confiavel) +
    "</strong><span>" + nConf + " fotos em que toda moeda teve denominação</span></article>" +
    "<article class='soma'><p>Soma real anotada</p><strong>" + reais(real) +
    "</strong><span>" + nReal + " fotos com valor anotado</span></article>";
}

function cartao(foto) {
  const pasta = String(foto.indice).padStart(3, "0");
  const moedas = foto.moedas.length
    ? foto.moedas.map(function (moeda) {
        const cents = moeda.centavos === null ? "sem valor" : moeda.centavos + " centavos";
        return "<span>" + escapar(moeda.rotulo) + " · " + cents + "</span>";
      }).join("")
    : "<span>nenhuma moeda aceita</span>";
  const somaFoto = foto.confiavel ? reais(foto.valor) : reais(foto.valor) + " (incerta)";
  return "<article class='cartao " + (foto.acertou ? "acerto" : "erro") + "' id='foto-" + foto.indice + "'>" +
    "<img class='capa' src='img/" + pasta + "/resultado.jpg' alt='Resultado de " + escapar(foto.arquivo) + "'>" +
    "<div class='etiquetas'><span>" + escapar(foto.conjunto) + "</span><span>" +
    (foto.acertou ? "contagem certa" : "contagem errada") + "</span></div>" +
    "<h2>" + escapar(foto.arquivo.replace("WhatsApp Image 2026-11-23 at ", "")) + "</h2>" +
    "<p class='meta'>Contagem estimada " + foto.contagem + " · real " + foto.contagemReal +
    " · " + foto.tempo.toFixed(3) + "&nbsp;s</p>" +
    "<div class='valores'><div><span>Soma das moedas</span><strong>" + somaFoto +
    "</strong></div><div><span>Soma real</span><strong>" + reais(foto.valorReal) + "</strong></div></div>" +
    "<p class='descricao'>" + escapar(foto.descricao) + "</p>" +
    "<div class='moedas etiquetas'>" + moedas + "</div>" +
    "<button type='button' data-indice='" + foto.indice + "'>Ver original, máscara e resultado</button>" +
    "<div class='detalhe'>" +
    "<figure><img src='img/" + pasta + "/original.jpg' alt='Original'><figcaption>Original</figcaption></figure>" +
    "<figure><img src='img/" + pasta + "/mascara.jpg' alt='Máscara'><figcaption>Máscara</figcaption></figure>" +
    "<figure><img src='img/" + pasta + "/resultado.jpg' alt='Resultado'><figcaption>Resultado</figcaption></figure>" +
    "</div></article>";
}

function desenhar() {
  const lista = visiveis();
  desenharSomas(lista);
  document.getElementById("grade").innerHTML = lista.map(cartao).join("");
}

document.getElementById("busca").addEventListener("input", function (evento) {
  estado.busca = evento.target.value;
  desenhar();
});
document.querySelector(".filtros").addEventListener("click", function (evento) {
  const botao = evento.target.closest("button");
  if (!botao) return;
  estado[botao.dataset.grupo] = botao.dataset.valor;
  document.querySelectorAll("button[data-grupo='" + botao.dataset.grupo + "']").forEach(function (item) {
    item.classList.toggle("ativo", item === botao);
  });
  desenhar();
});
document.getElementById("grade").addEventListener("click", function (evento) {
  const botao = evento.target.closest("button");
  if (!botao) return;
  botao.parentElement.classList.toggle("aberto");
});
desenhar();
</script>
</body>
</html>
"""
    return (
        pagina.replace("__METRICAS__", "".join(blocos))
        .replace("__TECNICA__", _bloco_tecnico(cartoes, metricas, config))
        .replace("__DADOS__", _fotos_json(cartoes, config))
    )


if __name__ == "__main__":
    gerar()
