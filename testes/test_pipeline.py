"""Testes do pipeline com imagens sintéticas, sem fotos reais."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np

from config import Config
from main import main
from scripts.gerar_sinteticas import criar_imagem, definicoes
from src.avaliar import avaliar
from src.fourier import filtrar_passa_baixa
from src.io_imagem import carregar_imagem, salvar_imagem
from src.pipeline import processar
from src.visualizar import salvar_etapas


def _mista() -> np.ndarray:
    definicao = next(item for item in definicoes() if item["arquivo"] == "sintetica_mista_01.png")
    return criar_imagem(definicao["moedas"], ruido=definicao["ruido"], semente=definicao["semente"])


class TestePipeline(unittest.TestCase):
    def test_mista_conta_e_soma(self):
        resultado = processar(_mista())
        self.assertEqual(resultado["contagem"], 5)
        self.assertEqual(resultado["valor_centavos"], 190)
        self.assertTrue(resultado["valor_confiavel"])
        self.assertEqual(
            sorted(moeda["valor_centavos"] for moeda in resultado["moedas"]),
            [5, 10, 25, 50, 100],
        )

    def test_ouro_se_separa_pelo_diametro_relativo(self):
        definicao = next(item for item in definicoes() if item["arquivo"] == "sintetica_ouro_02.png")
        imagem = criar_imagem(definicao["moedas"], ruido=definicao["ruido"], semente=definicao["semente"])
        resultado = processar(imagem)
        self.assertEqual(resultado["contagem"], 3)
        self.assertEqual(resultado["valor_centavos"], 45)
        self.assertTrue(resultado["valor_confiavel"])

    def test_ouro_sem_escala_fica_incerto(self):
        imagem = criar_imagem(
            [
                {"centavos": 10, "centro": (180, 250)},
                {"centavos": 10, "centro": (400, 250)},
                {"centavos": 10, "centro": (620, 300)},
            ],
            semente=7,
        )
        resultado = processar(imagem)
        self.assertEqual(resultado["contagem"], 3)
        self.assertFalse(resultado["valor_confiavel"])
        self.assertEqual(resultado["valor_centavos"], 0)

    def test_escala_informada_classifica_moedas_iguais(self):
        imagem = criar_imagem(
            [
                {"centavos": 10, "centro": (180, 250)},
                {"centavos": 10, "centro": (400, 250)},
                {"centavos": 10, "centro": (620, 300)},
            ],
            semente=8,
        )
        resultado = processar(imagem, Config(mm_por_px=0.2))
        self.assertEqual(resultado["contagem"], 3)
        self.assertEqual(resultado["valor_centavos"], 30)
        self.assertTrue(resultado["valor_confiavel"])

    def test_imagem_sem_moedas(self):
        imagem = criar_imagem([], ruido=0.0)
        resultado = processar(imagem)
        self.assertEqual(resultado["contagem"], 0)
        self.assertEqual(resultado["valor_centavos"], 0)
        self.assertTrue(resultado["valor_confiavel"])

    def test_moedas_encostadas_sao_registradas(self):
        definicao = next(item for item in definicoes() if item["arquivo"] == "sintetica_encostadas_04.png")
        imagem = criar_imagem(definicao["moedas"], ruido=definicao["ruido"], semente=definicao["semente"])
        resultado = processar(imagem)
        self.assertGreaterEqual(resultado["contagem"], 1)
        self.assertLessEqual(resultado["contagem"], 2)
        if resultado["contagem"] < 2:
            juncoes = [moeda for moeda in resultado["moedas"] if moeda["possivel_juncao"]]
            self.assertTrue(juncoes or resultado["observacoes"])
            self.assertFalse(resultado["valor_confiavel"])

    def test_metodos_alternativos_contam_a_mista(self):
        imagem = _mista()
        for metodo in ("adaptativo", "bordas"):
            with self.subTest(metodo=metodo):
                resultado = processar(imagem, Config(metodo_segmentacao=metodo))
                self.assertEqual(resultado["contagem"], 5)
                self.assertEqual(resultado["valor_centavos"], 190)

    def test_sem_soma_so_conta(self):
        resultado = processar(_mista(), Config(somar_valores=False))
        self.assertEqual(resultado["contagem"], 5)
        self.assertIsNone(resultado["valor_centavos"])

    def test_leitura_e_gravacao(self):
        imagem = criar_imagem(
            [{"centavos": 10, "centro": (120, 120)}],
            largura=300,
            altura=300,
            ruido=0.0,
        )
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "moeda.png"
            salvar_imagem(caminho, imagem)
            lida = carregar_imagem(caminho)
            self.assertTrue(np.array_equal(lida, imagem))
            with self.assertRaises(FileNotFoundError):
                carregar_imagem(Path(tmp) / "nao_existe.png")

    def test_cli_salva_etapas(self):
        imagem = criar_imagem(
            [{"centavos": 5, "centro": (160, 160)}, {"centavos": 100, "centro": (360, 200)}],
            largura=520,
            altura=400,
            ruido=3.0,
            semente=9,
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            caminho = tmp / "amostra.png"
            salvar_imagem(caminho, imagem)
            saida = tmp / "saida"
            codigo = main(["--imagem", str(caminho), "--saida", str(saida)])
            self.assertEqual(codigo, 0)
            pasta = saida / "amostra"
            self.assertTrue((pasta / "etapas.png").is_file())
            self.assertTrue((pasta / "resultado.png").is_file())
            self.assertTrue((pasta / "mascara.png").is_file())
            self.assertTrue((saida / "resumo.csv").is_file())
            salvar_etapas(pasta, imagem, imagem[:, :, 0], imagem[:, :, 0], imagem, "titulo")


class TesteAvaliacao(unittest.TestCase):
    def test_metricas_ignoram_desenvolvimento(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            anotacoes = tmp / "anotacoes.csv"
            resultados = tmp / "resumo.csv"
            _escrever(
                anotacoes,
                ["arquivo", "conjunto", "contagem_real", "valor_centavos"],
                [
                    ["a.png", "teste", "3", "30"],
                    ["b.png", "teste", "2", "40"],
                    ["c.png", "desenvolvimento", "9", "100"],
                    ["d.png", "teste", "1", "10"],
                ],
            )
            _escrever(
                resultados,
                ["arquivo", "contagem", "valor_centavos", "valor_confiavel", "tempo_s", "observacoes"],
                [
                    ["a.png", "3", "30", "sim", "0,10", ""],
                    ["b.png", "4", "10", "sim", "0.30", ""],
                    ["c.png", "0", "0", "sim", "1.00", ""],
                ],
            )
            metricas = avaliar(anotacoes, resultados, "teste")

        self.assertEqual(metricas["imagens"], 3)
        self.assertEqual(metricas["acertos"], 1)
        self.assertAlmostEqual(metricas["acuracia_exata_percentual"], 100.0 / 3)
        self.assertAlmostEqual(metricas["erro_absoluto_medio"], 1.0)
        self.assertAlmostEqual(metricas["tempo_medio_s"], 0.2)
        self.assertAlmostEqual(metricas["erro_absoluto_medio_valor"], 15.0)
        self.assertEqual(metricas["imagens_ausentes"], 1)


class TesteFourier(unittest.TestCase):
    def test_passa_baixa_reduz_variancia(self):
        gerador = np.random.default_rng(0)
        cinza = gerador.integers(0, 256, size=(80, 96), dtype=np.uint8)
        espectro, filtrada = filtrar_passa_baixa(cinza, 0.08)
        self.assertEqual(espectro.shape, cinza.shape)
        self.assertEqual(filtrada.shape, cinza.shape)
        self.assertEqual(filtrada.dtype, np.uint8)
        self.assertLess(float(filtrada.astype(np.float32).var()), float(cinza.astype(np.float32).var()))


def _escrever(caminho: Path, campos: list[str], linhas: list[list[str]]) -> None:
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(campos)
        escritor.writerows(linhas)


if __name__ == "__main__":
    unittest.main()
