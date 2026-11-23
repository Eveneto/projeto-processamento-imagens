"""Parâmetros do pipeline.

Os valores numéricos são provisórios, calibrados para as imagens sintéticas.
Quando as fotos reais existirem, ajuste este arquivo só com o conjunto de
desenvolvimento e mantenha os mesmos valores na avaliação do conjunto de teste.
"""

from dataclasses import dataclass


METODOS_SEGMENTACAO = ("otsu", "adaptativo", "bordas")
POLARIDADES = ("auto", "moedas_escuras", "moedas_claras")

# 2ª família do Real. O ouro aparece duas vezes (10 e 25 centavos) e só se
# separa pelo diâmetro. As outras aparências têm um único diâmetro.
CATALOGO = (
    {"nome": "10 centavos", "rotulo": "10c", "centavos": 10, "mm": 20.0, "aparencia": "ouro"},
    {"nome": "5 centavos", "rotulo": "5c", "centavos": 5, "mm": 22.0, "aparencia": "cobre"},
    {"nome": "50 centavos", "rotulo": "50c", "centavos": 50, "mm": 23.0, "aparencia": "bimetalica_50"},
    {"nome": "25 centavos", "rotulo": "25c", "centavos": 25, "mm": 25.0, "aparencia": "ouro"},
    {"nome": "1 real", "rotulo": "R$1", "centavos": 100, "mm": 27.0, "aparencia": "bimetalica_1"},
)


@dataclass
class Config:
    kernel_gaussiano: int = 5
    sigma_gaussiano: float = 0.0
    usar_clahe: bool = False
    clahe_clip: float = 2.0
    # Nas fotos de desenvolvimento, Otsu perde a moeda de 10 centavos clara,
    # quase da mesma tonalidade do papel. A borda (Canny) ainda contorna a moeda.
    metodo_segmentacao: str = "bordas"
    polaridade: str = "auto"
    adaptativo_bloco: int = 51
    adaptativo_c: int = 5
    canny_limiar1: int = 50
    canny_limiar2: int = 150
    kernel_morfologia: int = 5
    abertura_iteracoes: int = 1
    fechamento_iteracoes: int = 2
    area_minima_relativa: float = 0.002
    area_maxima_relativa: float = 0.25
    # Moeda isolada nas sintéticas fica perto de 0,9. 0,70 é o piso de um
    # formato compatível com moeda. De 0,50 a 0,70 o contorno ainda é contado,
    # mas marcado como possível junção de moedas encostadas.
    circularidade_minima: float = 0.70
    circularidade_minima_juncao: float = 0.50
    somar_valores: bool = True
    mm_por_px: float | None = None
    saturacao_prata: float = 40.0
    # No desenvolvimento, o anel da moeda gasta de 5 centavos fica com matiz
    # até 17 e o da de 10 centavos fica de 18 para cima. O cobre sintético
    # continua perto de 5 e o ouro sintético perto de 19.
    hue_cobre_max: float = 17.0
    hue_ouro_max: float = 40.0
    fracao_amostra_centro: float = 0.40
    fracao_amostra_anel_interna: float = 0.72
    fracao_amostra_anel_externa: float = 0.92
    tolerancia_mm: float = 4.0
    razao_duas_classes: float = 1.15
    pixels_minimos_amostra: int = 30


def validar_config(config: Config) -> None:
    if config.metodo_segmentacao not in METODOS_SEGMENTACAO:
        raise ValueError(
            f"Método de segmentação desconhecido: {config.metodo_segmentacao}. "
            f"Use um de: {', '.join(METODOS_SEGMENTACAO)}."
        )
    if config.polaridade not in POLARIDADES:
        raise ValueError(
            f"Polaridade desconhecida: {config.polaridade}. "
            f"Use uma de: {', '.join(POLARIDADES)}."
        )
    if config.circularidade_minima_juncao > config.circularidade_minima:
        raise ValueError("A circularidade de junção precisa ser menor ou igual à mínima.")
    if not 0 < config.area_minima_relativa < config.area_maxima_relativa <= 1:
        raise ValueError("Confira os limites relativo de área.")


def parametros_usados(config: Config) -> dict:
    return {
        "metodo_segmentacao": config.metodo_segmentacao,
        "polaridade": config.polaridade,
        "kernel_gaussiano": config.kernel_gaussiano,
        "kernel_morfologia": config.kernel_morfologia,
        "circularidade_minima": config.circularidade_minima,
        "circularidade_minima_juncao": config.circularidade_minima_juncao,
        "area_minima_relativa": config.area_minima_relativa,
        "area_maxima_relativa": config.area_maxima_relativa,
        "mm_por_px": config.mm_por_px,
        "somar_valores": config.somar_valores,
        "usar_clahe": config.usar_clahe,
    }
