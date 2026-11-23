# Roteiro de apresentação

Cerca de 10 a 12 minutos. O terminal fica na raiz do projeto. Os três comandos ao vivo levam menos de um segundo cada. O relatório e o painel já estão gerados: abra os dois antes de começar, para não depender da hora.

Antes de entrar:

- `data/relatorio.txt`
- `data/painel/index.html`
- `config.py` e `src/classificar.py` no editor, sem rolar ainda

Não rode a pasta inteira na hora. São 44 fotos e o público perde o fio. Também não rode `scripts/gerar_sinteticas.py`: ele reescreve as anotações.

## 1. O problema (cerca de 1 minuto)

Fala:

O trabalho conta moedas da 2ª família do Real e soma o valor em centavos. São 5, 10, 25 e 50 centavos, e 1 real. As fotos são de celular, com fundo claro, moedas gastas de 5 e 10 centavos, algumas encostadas e outras cortadas.

O conjunto tem 44 fotos: 39 de desenvolvimento e 5 de teste. O ajuste foi feito só no desenvolvimento. O teste foi medido uma vez, com o `config.py` já congelado.

Tela: mostre `data/anotacoes.csv`, as colunas `arquivo`, `conjunto`, `contagem_real` e `valor_centavos`. Aponte que a divisão é por fotografia inteira, não por moeda sorteada.

## 2. Por que este caminho, e não outro (cerca de 2 minutos)

Fala:

O enunciado pede um método clássico, OpenCV e NumPy, sem rede neural. Com dezenas de fotos não há conjunto para treinar um modelo, e a rede não era o objetivo. A moeda é um disco de cor e diâmetro conhecidos. Forma e cor resolvem o que o catálogo pede.

Três alternativas foram descartadas no desenvolvimento, não no teste:

- Otsu. A moeda de 10 centavos clara fica quase do mesmo cinza do papel e some no limiar global. O CLAHE não corrigiu isso.
- Limiar adaptativo. Recupera essa moeda clara, mas nas moedas quase encostadas o contorno em 8 cai abaixo de 0,50 de circularidade e a contagem vai a zero.
- Escala fixa em milímetros por pixel. A distância da câmera muda de foto para foto. A escala sai das moedas da própria imagem.

O padrão ficou a borda de Canny. Nas moedas quase encostadas o 8 ainda entra na contagem e recebe a marca de junção, em vez de desaparecer.

Tela: abra `config.py` e mostre `metodo_segmentacao = "bordas"`, os limiares 50 e 150, e o comentário do `hue_cobre_max = 17`. Diga que esses números foram medidos no desenvolvimento.

## 3. Demonstração que acerta (cerca de 2 minutos)

Fala, antes de dar enter:

Esta foto tem cinco moedas, três de 10 e duas de 5. O valor anotado é 40 centavos. O programa precisa contar cinco e somar R$ 0,40.

Tela, rode:

```powershell
python main.py --imagem "data/desenvolvimento/WhatsApp Image 2026-11-23 at 09.34.08.jpeg" --saida data/resultados
```

O que deve aparecer:

```text
5 moeda(s), R$ 0.40
```

Sem a frase “soma incerta”. O tempo fica na casa de um quarto de segundo.

Abra `data/resultados/WhatsApp Image 2026-11-23 at 09.34.08/etapas.png`.

Fala, apontando o painel da esquerda para a direita:

A original entra em BGR. O desfoque gaussiano 5×5 tira a borda falsa do JPEG. Da imagem suave saem o cinza, para a forma, e o HSV, para a cor. O Canny desenha a borda, a elipse fecha o aro e o preenchimento vira a máscara. Cada contorno vira candidato. A área precisa ficar entre 0,2% e 25% da foto, senão entra poeira ou a faixa preta da mesa. A circularidade é 4π vezes área sobre perímetro ao quadrado. De 0,70 para cima, é moeda. O centro sai dos momentos e o diâmetro, do menor círculo que envolve o contorno.

A soma deu certo aqui porque as de 5 centavos são cobre. O cobre tem um diâmetro só no catálogo, 22 mm, e isso vira a escala da foto. As de ouro, com essa escala, caem em 20 mm, que é 10 centavos, e não em 25.

## 4. Por que a borda, na prática (cerca de 1 minuto e meio)

Fala:

A mesma moeda de 10 centavos, clara, no papel. Primeiro o método padrão. Depois o Otsu, que seria o caminho óbvio para separar objeto e fundo.

Tela, um comando de cada vez:

```powershell
python main.py --imagem "data/desenvolvimento/WhatsApp Image 2026-11-23 at 09.18.53.jpeg" --saida data/resultados
python main.py --imagem "data/desenvolvimento/WhatsApp Image 2026-11-23 at 09.18.53.jpeg" --metodo otsu --saida data/resultados
```

O que deve aparecer:

```text
1 moeda(s), R$ 0.10 (incerto)
0 moeda(s), R$ 0.00
```

Fala:

O Canny acha a moeda. O Otsu devolve zero, porque o cinza dela se mistura ao papel. O “(incerto)” não é falha de contagem. A moeda é ouro, e ouro no catálogo é 10 ou 25 centavos. Sozinha na foto, não há outra moeda para dar a escala. O programa soma 10 centavos e avisa que 25 tem a mesma cor. Cravar 10 como certeza seria esconder essa ambiguidade.

Se sobrar tempo, abra a máscara dos dois resultados. A do Otsu não tem disco.

## 5. Por que a cor é HSV e o diâmetro, e não um classificador (cerca de 2 minutos)

Tela: `src/classificar.py`, a função `_metal` e, em seguida, `_aparencia`.

Fala:

A 2ª família repete o ouro: 10 centavos tem 20 mm e 25 centavos tem 25 mm. Cor sozinha não separa as duas. Por isso a cor só diz a aparência, e o diâmetro escolhe dentro do ouro.

A amostra não é a moeda inteira. É a mediana do HSV em dois anéis: o disco interno, até 40% do raio, e a borda, de 72% a 92%. A mediana ignora um reflexo pontual. Saturação abaixo de 40 é prata. Ouro no centro e prata no anel é 50 centavos. Prata no centro e ouro no anel é 1 real.

O corte do cobre não ficou no 12 das imagens sintéticas. Nas fotos gastas do desenvolvimento, o anel da de 5 centavos fica com matiz até 17 e o da de 10 fica de 18 para cima. Se o centro e o anel discordam entre cobre e ouro, vale o anel. O centro tem o algarismo, e na moeda gasta ele destoa do metal.

Não usei o diâmetro em pixels direto, porque a câmera muda de distância. A escala, em milímetros por pixel, é a mediana das moedas de aparência única daquela foto. Ouro não entra nessa conta, senão a escala dependeria da resposta que ainda estamos procurando.

## 6. O caso que o método assume como limite (cerca de 1 minuto e meio)

Fala:

O enunciado não exige separar moedas sobrepostas. Encostar já é um limite, e eu mostro em vez de esconder.

Tela:

```powershell
python main.py --imagem "data/desenvolvimento/WhatsApp Image 2026-11-23 at 09.34.09.jpeg" --saida data/resultados
```

O que deve aparecer:

```text
1 moeda(s), R$ 0.00 (incerto)
Há contorno com circularidade baixa: moedas encostadas podem ter sido contadas como um único objeto.
```

Fala:

São duas de 10 centavos, quase encostadas. O Canny funde as bordas num 8. A circularidade fica entre 0,50 e 0,70: ainda conta como um objeto, marca junção e não dá valor. Abaixo de 0,50 o formato nem entra. A faixa de 0,70 para cima aceita a moeda real, que não é um círculo perfeito. Tratar todo desvio do mesmo jeito ou jogaria a moeda isolada fora, ou contaria o 8 como duas sem ter como separá-las.

Abra o `etapas.png` dessa foto e aponte o contorno único.

## 7. O número do trabalho (cerca de 2 minutos)

Tela: `data/relatorio.txt`, as primeiras linhas. Não rode a avaliação de novo.

Fala:

São 44 fotos. A contagem fecha em 77,27%, com erro absoluto médio de 0,273 moeda e cerca de 0,07 segundo por foto. A soma total estimada é R$ 4,00. A anotada é R$ 5,20. A parte confiável, só onde toda moeda da foto teve denominação com escala, é R$ 2,55.

Esse total soma cenas. A mesma moeda aparece em várias fotos, então não é o dinheiro de uma mesa só.

Separe os dois conjuntos, porque misturar infla o número com as fotos que serviram para ajustar:

- Desenvolvimento: 31 de 39 contagens exatas, 79,49%, erro 0,256. Das 38 fotos com valor anotado, 26 fecham a soma.
- Teste, medido uma vez: 3 de 5, 60%, erro 0,400, tempo médio 0,097 segundo. O erro de valor nas somas confiáveis é 15 centavos. Uma foto de teste soma 15 em vez de 25, outra soma 65 em vez de 35. Eu não voltei no `config.py` por causa disso.

Tela, se perguntarem onde está o teste: `data/resultados_teste/relatorio_avaliacao.txt`.

Role o `data/relatorio.txt` só até duas linhas:

- `09.34.08`, desenvolvimento, 5 e 5, 40 e 40, confiável sim. É a foto que acabou de rodar.
- `09.34.09`, desenvolvimento, 2 e 1, valor 0, confiável não. É o par encostado.

## 8. Fecho (cerca de 40 segundos)

Fala:

O método conta discos visíveis, sem sobreposição, em fundo claro. Acerta a cena em que há cobre para ancorar a escala. Declara incerteza quando o ouro está sozinho. Falha quando as moedas se tocam, quando a borda não fecha, quando um dedo ou a mesa engole a moeda, e nas duas moedas antigas de prata uniforme, que estão fora da 2ª família. A escolha da borda, do corte de cor e da escala foi fechada no desenvolvimento e não foi reaberta depois do teste.

## Se perguntarem

Por que não YOLO ou uma rede? O enunciado pede o método clássico, e 44 fotos não treinam um detector. A rede também não explica o erro: aqui o erro tem nome, junção, borda aberta ou ouro sem escala.

Por que a soma às vezes diz 10 centavos e “incerto”? Porque 10 e 25 são os dois ouros. Sem escala na foto, 10 é a menor das duas, e a soma não se apresenta como certeza.

Por que uma soma confiável pode estar errada? Em `09.34.07` são três de 5 centavos. Uma teve o anel acima de 17, entrou como ouro e, com a escala das outras, virou 10. A soma deu 20 em vez de 15. O piso 17 separa a maior parte das fotos; essa ficou do lado de lá.

Por que zero confiável quando não acha moeda? A cena vazia tem soma zero de verdade. Quando a moeda existe e a borda não fecha, esse zero entra no erro de valor. Está escrito no relatório como limitação, não como acerto.

O que é o Fourier? Um experimento à parte, em `scripts/experimento_fourier.py`. Não entra na contagem nem na soma. Só abra se sobrar tempo.

## Ordem dos arquivos na tela

1. `data/anotacoes.csv`
2. `config.py`
3. Terminal, foto das cinco moedas
4. `etapas.png` dessa foto
5. Terminal, Canny e depois Otsu na de 10 centavos clara
6. `src/classificar.py`
7. Terminal, moedas encostadas
8. `data/relatorio.txt`
