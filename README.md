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

## Técnicas

A contagem não usa rede neural. O caminho padrão está em `config.py` e passa por seis etapas.

### 1. Suavização e conversão de cor

A foto entra em BGR. Um desfoque gaussiano 5×5 reduz o ruído da compressão do JPEG. Dessa imagem suavizada saem duas versões:

- cinza, usada para achar a forma
- HSV, usada para a cor

O CLAHE está desligado.

### 2. Segmentação por bordas

O padrão é o detector de Canny, com limiares 50 e 150. A borda é dilatada e fechada com uma elipse de 5×5 pixels. Os contornos externos são preenchidos e viram a máscara branca.

Otsu e o limiar adaptativo continuam disponíveis em `--metodo otsu` e `--metodo adaptativo`. O Otsu saiu do padrão porque, nas fotos de desenvolvimento, a moeda de 10 centavos clara fica quase da mesma tonalidade do papel e some no limiar global. No modo automático, Otsu e o adaptativo escolhem a polaridade (moeda escura ou clara) pela quantidade de componentes que já parecem moeda.

### 3. Morfologia

A máscara passa por abertura (1 vez), fechamento (2 vezes) e preenchimento dos buracos internos. O canto da foto é tratado como fundo: um reflexo no meio da moeda entra no objeto e a mesa em volta continua de fora.

### 4. Contornos, área e circularidade

Cada contorno externo vira candidato. A área precisa ficar entre 0,2% e 25% da imagem, o que descarta poeira e também a faixa preta da mesa quando ela ocupa um pedaço grande do quadro.

A circularidade é 4π × área / perímetro². O círculo perfeito vale 1.

- de 0,70 para cima, conta como uma moeda
- entre 0,50 e 0,70, ainda conta como um objeto e marca possível junção de moedas encostadas
- abaixo de 0,50, descarta

O centro sai dos momentos do contorno. O diâmetro em pixels sai do menor círculo que envolve o contorno.

### 5. Cor em HSV e diâmetro

O catálogo é a 2ª família do Real:

| Moeda | Diâmetro | Aparência |
| --- | --- | --- |
| 10 centavos | 20 mm | ouro |
| 5 centavos | 22 mm | cobre |
| 50 centavos | 23 mm | ouro no centro, prata no anel |
| 25 centavos | 25 mm | ouro |
| 1 real | 27 mm | prata no centro, ouro no anel |

De cada moeda o programa lê a mediana do HSV em dois anéis: o disco interno, até 40% do raio, e a borda, de 72% a 92% do raio. Saturação abaixo de 40 é prata. Matiz até 12, ou a partir de 168, é cobre. Matiz até 40 é ouro.

- cobre no centro e no anel: 5 centavos
- ouro no centro e prata no anel: 50 centavos
- prata no centro e ouro no anel: 1 real
- ouro nos dois lados: 10 ou 25 centavos, separados pelo diâmetro

Sem `--mm-por-px`, a escala em milímetros por pixel sai da mediana das moedas cuja aparência aponta um único diâmetro. Ouro, junção e cor incerta não entram nessa conta. Se não houver escala e existirem dois tamanhos de ouro com razão acima de 1,15, o corte fica no meio dos dois diâmetros em pixels. Uma única classe de ouro, sem escala, fica sem denominação. A tolerância para casar o diâmetro com o catálogo é de 4 mm. Junção também fica sem denominação.

### 6. Soma

A soma é a dos centavos atribuídos. Ela só é confiável quando toda moeda detectada tem denominação. Se alguma falha, o número é uma soma parcial e o resultado marca a soma como incerta. Se nenhuma moeda é detectada, a soma devolve 0 centavos e marca esse zero como confiável.

A transformada de Fourier, em `scripts/experimento_fourier.py`, é um experimento à parte e não altera a contagem nem a soma.

## Limitações

O método conta moedas visíveis, sem sobreposição, em fundo claro e luz razoavelmente uniforme. Fora disso, a contagem e a soma falham de jeitos já vistos nestas fotos.

**Moedas encostadas.** O Canny funde as bordas. Se a circularidade fica entre 0,50 e 0,70, conta 1 e marca junção, sem denominação. Abaixo de 0,50, descarta o contorno e a contagem vai a 0.

**Borda que não fecha.** Foto borrada, aro fraco ou moeda cortada não viram disco. A contagem sai 0.

**Bloco grande demais.** Dedo, borda preta da mesa ou moeda cortada podem se fundir com a moeda. Se o bloco passa de 25% da imagem, ele é descartado mesmo quando a forma é redonda.

**Zero confiável.** Quando nenhuma moeda é aceita, a soma devolve 0 centavos e marca esse zero como confiável. Isso entra no erro de valor como se a cena estivesse vazia.

**Soma nas moedas gastas.** O conjunto real só tem 5 e 10 centavos velhos. A diferença de diâmetro é de 2 mm e a cor desbota, então a maior parte das somas fica incerta. Quando o programa crava um valor, ele pode errar: uma de 10 centavos foi lida como 25 (as duas são ouro e a tolerância é de 4 mm) e outra como 50 (centro ouro e anel prata). Sem `--mm-por-px`, a escala só sai de moedas de aparência única na mesma foto.

**Total do painel.** A soma total junta o valor de cada foto. A mesma moeda aparece em várias cenas, então o total não é o dinheiro de uma única mesa. Nas 44 fotos o estimado ficou em R$ 1,00, contra R$ 5,20 anotados, e a parte confiável também é R$ 1,00 vinda de duas fotos erradas.

**O que o método não promete.** Sobreposição, oclusão, fundo muito variado e luz extrema. Otsu perde a moeda de 10 centavos clara, quase da mesma tonalidade do papel; por isso o padrão é a borda.
