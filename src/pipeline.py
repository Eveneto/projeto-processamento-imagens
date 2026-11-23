"""Orquestra leitura já feita, pré-processamento, segmentação, contagem e soma."""

from config import Config, parametros_usados, validar_config

from .classificar import classificar, sem_classificacao
from .detectar import detectar
from .morfologia import limpar_mascara
from .preprocessar import preprocessar
from .segmentar import segmentar
from .visualizar import desenhar_resultado


def processar(imagem_bgr, config: Config | None = None) -> dict:
    if config is None:
        config = Config()
    validar_config(config)
    if imagem_bgr is None or getattr(imagem_bgr, "size", 0) == 0:
        raise ValueError("A imagem está vazia.")
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ValueError("A imagem precisa estar em BGR com 3 canais.")

    cinza, hsv = preprocessar(imagem_bgr, config)
    mascara = segmentar(cinza, config)
    mascara = limpar_mascara(mascara, config)
    moedas, rejeitados = detectar(mascara, imagem_bgr.shape, config)
    if config.somar_valores:
        info = classificar(hsv, moedas, config)
    else:
        info = sem_classificacao(moedas)

    return {
        "contagem": len(info["moedas"]),
        "valor_centavos": info["valor_centavos"],
        "valor_confiavel": info["valor_confiavel"],
        "escala_mm_por_px": info["mm_por_px"],
        "moedas": info["moedas"],
        "rejeitados": rejeitados,
        "observacoes": info["observacoes"],
        "cinza": cinza,
        "mascara": mascara,
        "resultado": desenhar_resultado(imagem_bgr, info["moedas"]),
        "original": imagem_bgr,
        "parametros": parametros_usados(config),
    }


def publicar_resultado(resultado: dict, arquivo: str, tempo_s: float) -> dict:
    def moeda_publica(moeda: dict) -> dict:
        return {
            "indice": moeda["indice"],
            "centro_x": round(float(moeda["centro"][0]), 2),
            "centro_y": round(float(moeda["centro"][1]), 2),
            "area": round(float(moeda["area"]), 1),
            "perimetro": round(float(moeda["perimetro"]), 2),
            "circularidade": round(float(moeda["circularidade"]), 4),
            "diametro_px": round(float(moeda["diametro_px"]), 2),
            "possivel_juncao": bool(moeda["possivel_juncao"]),
            "aparencia": moeda.get("aparencia"),
            "metal_centro": moeda.get("metal_centro"),
            "metal_anel": moeda.get("metal_anel"),
            "denominacao": moeda.get("denominacao"),
            "valor_centavos": moeda.get("valor_centavos"),
            "confiavel": bool(moeda.get("confiavel")),
            "rotulo": moeda.get("rotulo"),
        }

    def rejeitada_publica(item: dict) -> dict:
        return {
            "centro_x": round(float(item["centro"][0]), 2),
            "centro_y": round(float(item["centro"][1]), 2),
            "area": round(float(item["area"]), 1),
            "circularidade": round(float(item["circularidade"]), 4),
            "motivo": item["motivo"],
        }

    escala = resultado["escala_mm_por_px"]
    return {
        "arquivo": arquivo,
        "contagem": resultado["contagem"],
        "valor_centavos": resultado["valor_centavos"],
        "valor_confiavel": resultado["valor_confiavel"],
        "escala_mm_por_px": None if escala is None else round(float(escala), 6),
        "tempo_s": round(float(tempo_s), 6),
        "observacoes": list(resultado["observacoes"]),
        "moedas": [moeda_publica(moeda) for moeda in resultado["moedas"]],
        "rejeitados": [rejeitada_publica(item) for item in resultado["rejeitados"]],
        "parametros": resultado["parametros"],
    }
