"""Denominação pela cor (HSV) e pelo diâmetro, e soma em centavos."""

import numpy as np

from config import CATALOGO, Config


def _metal(pixels: np.ndarray, config: Config) -> str:
    if pixels.ndim != 2 or pixels.shape[0] < config.pixels_minimos_amostra:
        return "desconhecido"
    hue = float(np.median(pixels[:, 0]))
    saturacao = float(np.median(pixels[:, 1]))
    if saturacao < config.saturacao_prata:
        return "prata"
    if hue <= config.hue_cobre_max or hue >= 180.0 - config.hue_cobre_max:
        return "cobre"
    if hue <= config.hue_ouro_max:
        return "ouro"
    return "desconhecido"


def _amostrar(hsv: np.ndarray, moeda: dict, config: Config) -> tuple[str, str]:
    altura, largura = hsv.shape[:2]
    cx, cy = moeda["centro"]
    raio = moeda["diametro_px"] / 2.0
    if raio <= 1:
        return "desconhecido", "desconhecido"
    yy, xx = np.ogrid[:altura, :largura]
    distancia = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    centro = distancia <= raio * config.fracao_amostra_centro
    anel = (distancia >= raio * config.fracao_amostra_anel_interna) & (
        distancia <= raio * config.fracao_amostra_anel_externa
    )
    return _metal(hsv[centro], config), _metal(hsv[anel], config)


def _aparencia(centro: str, anel: str) -> str:
    if centro == "ouro" and anel == "prata":
        return "bimetalica_50"
    if centro == "prata" and anel == "ouro":
        return "bimetalica_1"
    if centro == anel and centro in {"cobre", "ouro"}:
        return centro
    # Cobre e ouro não formam par bimetálico nesta família. O centro inclui o
    # algarismo e, na moeda gasta, destoa da borda. A borda é o metal.
    if centro in {"cobre", "ouro"} and anel in {"cobre", "ouro"}:
        return anel
    return "incerta"


def _item_unico(aparencia: str) -> dict | None:
    itens = [item for item in CATALOGO if item["aparencia"] == aparencia]
    if len(itens) == 1:
        return itens[0]
    return None


def _estimar_escala(moedas: list[dict]) -> float | None:
    estimativas = []
    for moeda in moedas:
        if moeda.get("possivel_juncao") or moeda.get("aparencia") in {None, "juncao", "incerta", "ouro"}:
            continue
        item = _item_unico(moeda["aparencia"])
        if item is None or moeda["diametro_px"] <= 0:
            continue
        estimativas.append(item["mm"] / moeda["diametro_px"])
    if not estimativas:
        return None
    return float(np.median(estimativas))


def _ouro_menor() -> dict:
    return min(
        (item for item in CATALOGO if item["aparencia"] == "ouro"),
        key=lambda item: item["mm"],
    )


def _marcar(
    moeda: dict,
    item: dict | None,
    rotulo_incerto: str = "?",
    confiavel: bool = True,
) -> None:
    if item is None:
        moeda["denominacao"] = None
        moeda["valor_centavos"] = None
        moeda["confiavel"] = False
        moeda["rotulo"] = rotulo_incerto
        return
    moeda["denominacao"] = item["nome"]
    moeda["valor_centavos"] = int(item["centavos"])
    moeda["confiavel"] = confiavel
    moeda["rotulo"] = item["rotulo"] if confiavel else f"{item['rotulo']}?"


def _escolher_ouro_por_mm(mm: float, config: Config) -> dict | None:
    opcoes = [item for item in CATALOGO if item["aparencia"] == "ouro"]
    melhor = min(opcoes, key=lambda item: abs(item["mm"] - mm))
    if abs(melhor["mm"] - mm) > config.tolerancia_mm:
        return None
    return melhor


def _ouro_relativo(diametro: float, corte: float) -> dict:
    opcoes = sorted(
        (item for item in CATALOGO if item["aparencia"] == "ouro"),
        key=lambda item: item["mm"],
    )
    if diametro < corte:
        return opcoes[0]
    return opcoes[1]


def _observacoes(moedas: list[dict], valor_confiavel: bool, somar: bool) -> list[str]:
    textos = []
    if any(moeda.get("possivel_juncao") for moeda in moedas):
        textos.append(
            "Há contorno com circularidade baixa: moedas encostadas podem ter sido contadas como um único objeto."
        )
    if somar and moedas and not valor_confiavel:
        if any(moeda.get("valor_centavos") is None for moeda in moedas):
            textos.append("A soma não é confiável: alguma moeda não teve a denominação definida.")
        if any(
            moeda.get("valor_centavos") is not None and not moeda.get("confiavel") for moeda in moedas
        ):
            textos.append(
                "Ouro sem escala na foto foi contado como 10 centavos. "
                "A soma inclui esse valor, mas 25 centavos tem a mesma cor e a soma fica incerta."
            )
    return textos


def sem_classificacao(moedas: list[dict]) -> dict:
    for moeda in moedas:
        moeda["aparencia"] = None
        moeda["metal_centro"] = None
        moeda["metal_anel"] = None
        moeda["denominacao"] = None
        moeda["valor_centavos"] = None
        moeda["confiavel"] = False
        moeda["rotulo"] = None
    return {
        "moedas": moedas,
        "valor_centavos": None,
        "valor_confiavel": False,
        "mm_por_px": None,
        "observacoes": _observacoes(moedas, True, False),
    }


def classificar(hsv: np.ndarray, moedas: list[dict], config: Config) -> dict:
    if not moedas:
        return {
            "moedas": moedas,
            "valor_centavos": 0,
            "valor_confiavel": True,
            "mm_por_px": config.mm_por_px,
            "observacoes": [],
        }

    for moeda in moedas:
        metal_centro, metal_anel = _amostrar(hsv, moeda, config)
        moeda["metal_centro"] = metal_centro
        moeda["metal_anel"] = metal_anel
        if moeda.get("possivel_juncao"):
            moeda["aparencia"] = "juncao"
        else:
            moeda["aparencia"] = _aparencia(metal_centro, metal_anel)

    escala = config.mm_por_px if config.mm_por_px else _estimar_escala(moedas)
    ouros = [moeda for moeda in moedas if moeda["aparencia"] == "ouro"]
    corte = None
    if escala is None and len(ouros) >= 2:
        diametros = [moeda["diametro_px"] for moeda in ouros]
        menor = min(diametros)
        maior = max(diametros)
        if menor > 0 and maior / menor > config.razao_duas_classes:
            corte = (menor + maior) / 2.0

    for moeda in moedas:
        aparencia = moeda["aparencia"]
        if aparencia == "juncao":
            _marcar(moeda, None, "juncao?")
            continue
        item = _item_unico(aparencia)
        if item is not None:
            _marcar(moeda, item)
            continue
        if aparencia == "ouro":
            if escala is not None:
                _marcar(moeda, _escolher_ouro_por_mm(moeda["diametro_px"] * escala, config))
            elif corte is not None:
                _marcar(moeda, _ouro_relativo(moeda["diametro_px"], corte))
            else:
                # Sem outra moeda para dar a escala, 10 e 25 centavos ficam
                # indistinguíveis. A soma usa 10 centavos e permanece incerta.
                _marcar(moeda, _ouro_menor(), confiavel=False)
            continue
        _marcar(moeda, None)

    total = sum(moeda["valor_centavos"] or 0 for moeda in moedas)
    confiavel = all(moeda["confiavel"] for moeda in moedas)
    return {
        "moedas": moedas,
        "valor_centavos": total,
        "valor_confiavel": confiavel,
        "mm_por_px": escala,
        "observacoes": _observacoes(moedas, confiavel, True),
    }
