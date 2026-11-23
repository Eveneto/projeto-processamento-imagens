# Contagem e soma de moedas

Programa em Python para contar moedas brasileiras da 2ª família do Real e estimar a soma em centavos. O método é clássico (OpenCV e NumPy), sem rede neural.

As fotos reais estão em `data/fotos/`. O experimento usa cópias em `data/desenvolvimento/` (39 fotos) e `data/teste/` (5 fotos). O ajuste fica no desenvolvimento. O teste não serve para mudar `config.py`.

## Instalação

Na raiz do projeto, com Python 3.12:

```bash
python -m pip install -r requirements.txt
```

Todos os comandos abaixo também partem dessa pasta. No PowerShell, caminhos com espaço vão entre aspas.

## Guia prático

### 1. Abrir o painel

Este é o caminho para revisar as fotos, a soma de cada cena e o total estimado. Não altera o algoritmo.

```bash
python scripts/painel.py
```

Abra `data/painel/index.html` no navegador. Os filtros de conjunto, acerto e confiança recalculam o total das fotos visíveis. Em cada cartão, “Ver original, máscara e resultado” mostra as três imagens. “Técnicas e imprecisões” explica o método.

### 2. Processar o desenvolvimento

```bash
python main.py --pasta data/desenvolvimento --saida data/resultados_desenvolvimento
```

Cada foto gera uma pasta com a original, a pré-processada, a máscara, o resultado e `etapas.png`. O resumo fica em `data/resultados_desenvolvimento/resumo.csv`.

Para medir só esse conjunto:

```bash
python -m src.avaliar --anotacoes data/anotacoes.csv --resultados data/resultados_desenvolvimento/resumo.csv --conjunto desenvolvimento --saida data/resultados_desenvolvimento/relatorio_avaliacao.txt
```

### 3. Avaliar o teste uma vez

Rode isto com o `config.py` já congelado. O resultado não volta para o ajuste.

```bash
python main.py --pasta data/teste --saida data/resultados_teste
python -m src.avaliar --anotacoes data/anotacoes.csv --resultados data/resultados_teste/resumo.csv --saida data/resultados_teste/relatorio_avaliacao.txt
```

O relatório traz acurácia exata da contagem, erro absoluto médio, tempo médio e erro do valor nas imagens em que a soma foi marcada como confiável.

### 4. Uma foto só

```bash
python main.py --imagem "data/desenvolvimento/WhatsApp Image 2026-11-23 at 09.34.07.jpeg" --saida data/resultados
```

Outras opções:

```bash
python main.py --pasta data/desenvolvimento --sem-valor
python main.py --pasta data/desenvolvimento --metodo otsu
python main.py --pasta data/desenvolvimento --metodo adaptativo
python main.py --pasta data/desenvolvimento --mm-por-px 0.2
```

`--sem-valor` só conta. `--metodo` aceita `bordas` (padrão), `otsu` e `adaptativo`. `--mm-por-px` fixa a escala quando a câmera não muda de distância. Nas fotos atuais essa escala não está informada.

### 5. Testes automáticos

```bash
python -m unittest testes.test_pipeline -v
```

O experimento de Fourier não entra na contagem:

```bash
python scripts/experimento_fourier.py
```

## Anotações e pastas

`data/anotacoes.csv` tem `arquivo`, `conjunto`, `contagem_real` e `valor_centavos`. O valor fica em branco quando a denominação da foto não dá para cravar. A separação é por fotografia inteira.

- `data/fotos/` — originais, inclusive os zips do WhatsApp (eles repetem os JPEGs)
- `data/desenvolvimento/` — ajuste
- `data/teste/` — avaliação final
- `data/sinteticas/` — imagens geradas, fora do experimento real
- `data/painel/` — dashboard

Não rode `python scripts/gerar_sinteticas.py` em cima deste conjunto. Esse script reescreve `data/anotacoes.csv` e grava PNGs dentro de `data/desenvolvimento/` e `data/teste/`.

## Limitações

O método conta moedas visíveis, sem sobreposição, em fundo claro e luz razoavelmente uniforme. Fora disso, a contagem e a soma falham de jeitos já vistos nestas fotos.

**Moedas encostadas.** O Canny funde as bordas. Se a circularidade fica entre 0,50 e 0,70, conta 1 e marca junção, sem denominação. Abaixo de 0,50, descarta o contorno e a contagem vai a 0.

**Borda que não fecha.** Foto borrada, aro fraco ou moeda cortada não viram disco. A contagem sai 0.

**Bloco grande demais.** Dedo, borda preta da mesa ou moeda cortada podem se fundir com a moeda. Se o bloco passa de 25% da imagem, ele é descartado mesmo quando a forma é redonda.

**Zero confiável.** Quando nenhuma moeda é aceita, a soma devolve 0 centavos e marca esse zero como confiável. Isso entra no erro de valor como se a cena estivesse vazia.

**Soma nas moedas gastas.** O conjunto real só tem 5 e 10 centavos velhos. A diferença de diâmetro é de 2 mm e a cor desbota, então a maior parte das somas fica incerta. Quando o programa crava um valor, ele pode errar: uma de 10 centavos foi lida como 25 (as duas são ouro e a tolerância é de 4 mm) e outra como 50 (centro ouro e anel prata). Sem `--mm-por-px`, a escala só sai de moedas de aparência única na mesma foto.

**Total do painel.** A soma total junta o valor de cada foto. A mesma moeda aparece em várias cenas, então o total não é o dinheiro de uma única mesa. Nas 44 fotos o estimado ficou em R$ 1,00, contra R$ 5,20 anotados, e a parte confiável também é R$ 1,00 vinda de duas fotos erradas.

**O que o método não promete.** Sobreposição, oclusão, fundo muito variado e luz extrema. Otsu perde a moeda de 10 centavos clara, quase da mesma tonalidade do papel; por isso o padrão é a borda.
