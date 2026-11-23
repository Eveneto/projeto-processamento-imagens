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

O relatório traz acurácia exata da contagem, erro absoluto médio, tempo médio, erro do valor nas imagens em que a soma foi marcada como confiável e a soma total daquele conjunto.

Para um relatório com todas as fotos, desenvolvimento e teste juntos, e a soma total estimada:

```bash
python -m src.avaliar --anotacoes data/anotacoes.csv --resultados data/resultados_desenvolvimento/resumo.csv data/resultados_teste/resumo.csv --conjunto todos --saida data/relatorio.txt
```

`python scripts/painel.py` também regrava `data/relatorio.txt`. A soma total junta cada cena. A mesma moeda aparece em várias fotos, então esse total não é o dinheiro de uma única mesa.

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

De cada moeda o programa lê a mediana do HSV em dois anéis: o disco interno, até 40% do raio, e a borda, de 72% a 92% do raio. Saturação abaixo de 40 é prata. Matiz até 17, ou a partir de 163, é cobre. Matiz até 40 é ouro. O corte 17 foi medido nas fotos de desenvolvimento: o anel da moeda gasta de 5 centavos fica até 17, e o da de 10 centavos fica de 18 para cima. O cobre das imagens sintéticas continua perto de 5 e o ouro sintético perto de 19.

- cobre no centro e no anel: 5 centavos
- um lado cobre e o outro ouro: vale o anel, porque o centro traz o algarismo e, na moeda gasta, destoa da borda
- ouro no centro e prata no anel: 50 centavos
- prata no centro e ouro no anel: 1 real
- ouro nos dois lados: 10 ou 25 centavos, separados pelo diâmetro

Sem `--mm-por-px`, a escala em milímetros por pixel sai da mediana das moedas cuja aparência aponta um único diâmetro. Ouro, junção e cor incerta não entram nessa conta. Se não houver escala e existirem dois tamanhos de ouro com razão acima de 1,15, o corte fica no meio dos dois diâmetros em pixels. Uma única classe de ouro, sem escala, entra como 10 centavos e a soma fica incerta, porque 25 centavos tem a mesma cor. A tolerância para casar o diâmetro com o catálogo é de 4 mm. Junção fica sem denominação.

### 6. Soma

A soma é a dos centavos atribuídos. Ela só é confiável quando toda moeda detectada tem denominação definida com escala. Ouro sem escala entra no total, com a soma marcada como incerta. Se alguma moeda fica sem valor, o número é uma soma parcial. Se nenhuma moeda é detectada, a soma devolve 0 centavos e marca esse zero como confiável.

A transformada de Fourier, em `scripts/experimento_fourier.py`, é um experimento à parte e não altera a contagem nem a soma.

## Por que esse caminho

O enunciado pede um método clássico, com OpenCV e NumPy, sem rede neural. A contagem precisa funcionar com poucas fotos, fundo claro e moedas da 2ª família, então a forma e a cor bastam: não há um conjunto grande o suficiente para treinar um modelo, e a rede não era o objetivo do trabalho.

A segmentação foi escolhida só com as fotos de desenvolvimento. Otsu e o limiar adaptativo foram comparados com a borda de Canny. O Otsu perde a moeda de 10 centavos clara, porque o cinza dela fica perto do papel. O CLAHE não corrigiu esses casos. O adaptativo e o Canny recuperaram essas moedas sem contar a faixa preta da mesa como moeda. O Canny ficou como padrão porque, nas moedas quase encostadas, o contorno em 8 ainda entra na contagem e recebe a marca de junção. No adaptativo, esse mesmo 8 caía abaixo de 0,50 de circularidade e era descartado, com contagem 0.

A circularidade em duas faixas existe para não tratar todo desvio de círculo do mesmo jeito. Uma moeda isolada nas imagens sintéticas fica perto de 0,90. O piso de 0,70 aceita a moeda real, que não é um círculo perfeito por causa do relevo e da luz. Entre 0,50 e 0,70 o objeto ainda é contado, mas a soma não confia nele: é o sinal de que duas moedas podem ter virado um contorno só. Abaixo de 0,50 o formato já não parece moeda.

A cor em HSV separa cobre, ouro e as duas bimetálicas porque o catálogo da 2ª família repete o ouro em duas moedas, 10 e 25 centavos, e só o diâmetro as distingue. Nas fotos reais o cobre gasto não chega no matiz 12 das sintéticas: no desenvolvimento o anel da de 5 centavos fica até 17 e o da de 10 fica de 18 para cima, então o corte do cobre subiu para 17. Quando o centro e o anel discordam entre cobre e ouro, a borda decide, porque o algarismo no meio muda a cor. A escala não foi fixada à mão: a distância da câmera muda de foto para foto. Ela sai das moedas de aparência única que aparecem na mesma imagem. Sem essa âncora, o ouro de um tamanho só entra como 10 centavos e a soma fica incerta. O desfoque gaussiano entra antes disso para o JPEG do celular não virar borda falsa.

Essa escolha não foi reaberta depois de ver o conjunto de teste.

## Limitações

O método conta moedas visíveis, sem sobreposição, em fundo claro e luz razoavelmente uniforme. Fora disso, a contagem e a soma falham de jeitos já vistos nestas fotos.

**Moedas encostadas.** O Canny funde as bordas. Se a circularidade fica entre 0,50 e 0,70, conta 1 e marca junção, sem denominação. Abaixo de 0,50, descarta o contorno e a contagem vai a 0.

**Borda que não fecha.** Foto borrada, aro fraco ou moeda cortada não viram disco. A contagem sai 0.

**Bloco grande demais.** Dedo, borda preta da mesa ou moeda cortada podem se fundir com a moeda. Se o bloco passa de 25% da imagem, ele é descartado mesmo quando a forma é redonda.

**Zero confiável.** Quando nenhuma moeda é aceita, a soma devolve 0 centavos e marca esse zero como confiável. Isso entra no erro de valor como se a cena estivesse vazia.

**Soma nas moedas gastas.** O cobre com matiz até 17 vira 5 centavos e, quando há outra moeda na foto, dá a escala para o ouro. Foto só com ouro de um tamanho soma 10 centavos por moeda e fica incerta: 10 e 25 centavos têm a mesma cor. No desenvolvimento, 26 das 38 fotos com valor anotado fecham a soma; 14 dessas somas são confiáveis e batem com a anotação. Ainda falham a moeda antiga de prata uniforme (fora da 2ª família), o par encostado, a de 5 centavos cujo anel passou de 17 e foi lida como 10, e a foto em que uma das duas moedas ficou com o anel quase sem saturação.

**Total do painel.** A soma total junta o valor de cada foto. A mesma moeda aparece em várias cenas, então o total não é o dinheiro de uma única mesa. Nas 44 fotos o estimado ficou em R$ 4,00, contra R$ 5,20 anotados. A parte confiável soma R$ 2,55.

**O que o método não promete.** Sobreposição, oclusão, fundo muito variado e luz extrema. Otsu perde a moeda de 10 centavos clara, quase da mesma tonalidade do papel; por isso o padrão é a borda.
