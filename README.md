# webnovel2kindle

![webnovel2kindle logo](logo.png)

`webnovel2kindle` e uma CLI para mapear obras da [Central Novel](https://centralnovel.com/), selecionar um volume e gerar um EPUB bem estruturado para leitura em e-readers, apps de EPUB e fluxo Kindle.

A ferramenta identifica volumes e capitulos, coleta metadados da obra, baixa a capa e monta um sumario clicavel em um EPUB limpo para leitura.

> Status do projeto: experimental, especifico para Central Novel.

## Recursos

- Fluxo guiado em uma unica execucao.
- Leitura da pagina da obra a partir da URL.
- Reconhecimento de volumes e capitulos.
- Selecao interativa de volume.
- Download dos capitulos com barra de progresso.
- Geracao de EPUB por volume.
- Capa da obra no EPUB.
- Sumario visivel no inicio do livro com links clicaveis para os capitulos.
- Indices EPUB 3 (`nav.xhtml`) e NCX (`toc.ncx`) para compatibilidade.

## Requisitos

- Python 3.12 ou superior.
- [`uv`](https://docs.astral.sh/uv/) instalado.
- Acesso a internet para baixar paginas, capas e capitulos.

Verifique se o `uv` esta instalado:

```bash
uv --version
```

Se o comando nao existir, instale o `uv` seguindo a documentacao oficial: <https://docs.astral.sh/uv/>.

## Instalacao

Clone ou baixe este projeto e entre na pasta:

```bash
cd webNovel2kindlle
```

Instale as dependencias do projeto com:

```bash
uv sync
```

Para instalar tambem as dependencias de desenvolvimento:

```bash
uv sync --extra dev
```

## Primeiro Uso

O fluxo recomendado e executar a CLI sem subcomandos:

```bash
uv run webnovel2kindle
```

A ferramenta vai pedir:

1. o link da obra na Central Novel;
2. o volume que voce deseja baixar.

Exemplo de link aceito:

```text
https://centralnovel.com/series/shadow-slave-20230928/
```

Depois disso, a CLI vai:

1. buscar os dados da obra;
2. exibir os volumes encontrados;
3. baixar os capitulos do volume escolhido;
4. baixar a capa, quando disponivel;
5. gerar o EPUB na pasta `dist/`.

## Interface Web

Para usar uma interface no navegador, execute:

```bash
uv run webnovel2kindle-ui
```

A interface local abre em `http://127.0.0.1:8765` e permite colar o link da obra,
analisar os volumes, escolher o volume desejado e gerar o EPUB.

Se preferir abrir o navegador manualmente:

```bash
uv run webnovel2kindle-ui --no-browser
```

## Uso Com URL

Voce tambem pode passar a URL diretamente:

```bash
uv run webnovel2kindle --url https://centralnovel.com/series/shadow-slave-20230928/
```

Nesse modo, a CLI ainda vai exibir os volumes e perguntar qual volume deve ser exportado.

## Uso Com URL E Volume

Para executar tudo sem perguntas:

```bash
uv run webnovel2kindle \
  --url https://centralnovel.com/series/shadow-slave-20230928/ \
  --volume 2
```

O numero do volume corresponde a ordem mostrada na tabela da CLI. Por exemplo, se `Volume Extra` aparece primeiro, ele e o volume `1`; `Volume 1` sera o volume `2`.

## Pasta De Saida

Por padrao, os EPUBs sao salvos em:

```text
dist/
```

Para escolher outra pasta:

```bash
uv run webnovel2kindle \
  --url https://centralnovel.com/series/shadow-slave-20230928/ \
  --volume 2 \
  --output-dir meus-epubs
```

## Comandos

### Fluxo completo

Executa o fluxo principal: pede link, mostra volumes, pede volume, baixa e gera EPUB.

```bash
uv run webnovel2kindle
```

### Fluxo completo com parametros

```bash
uv run webnovel2kindle --url URL_DA_OBRA --volume NUMERO_DO_VOLUME
```

### Apenas analisar a obra

Mostra os volumes e quantidade de capitulos, sem baixar nem gerar EPUB.

```bash
uv run webnovel2kindle scan URL_DA_OBRA
```

### Listar todos os capitulos

```bash
uv run webnovel2kindle scan URL_DA_OBRA --chapters
```

### Exportar EPUB explicitamente

Equivalente ao fluxo completo, mas usando o subcomando `export`.

```bash
uv run webnovel2kindle export URL_DA_OBRA --volume NUMERO_DO_VOLUME
```

## Exemplo Completo

```bash
uv run webnovel2kindle \
  --url https://centralnovel.com/series/shadow-slave-20230928/ \
  --volume 2
```

Saida esperada:

```text
Shadow Slave
12 volume(s) • 2981 capitulo(s)

Baixando capitulos  100%
Baixando capa
EPUB gerado: dist/shadow-slave-volume-1.epub
```

## Estrutura Do EPUB

Cada EPUB gerado contem:

- pagina de capa;
- sumario visivel e clicavel;
- capitulos do volume selecionado;
- metadados tecnicos no `content.opf`;
- indice EPUB 3;
- indice NCX para leitores mais antigos.

## Desenvolvimento

Instale as dependencias de desenvolvimento:

```bash
uv sync --extra dev
```

Rode os testes:

```bash
uv run --extra dev pytest
```

Rode o lint:

```bash
uv run --extra dev ruff check .
```

## Estrutura Do Projeto

```text
src/webnovel2kindle/
  cli.py                  # comandos e fluxo principal da CLI
  epub.py                 # montagem do EPUB
  models.py               # modelos de Novel, Volume, Chapter e metadados
  scraper/
    centralnovel.py       # parser especifico da Central Novel
    client.py             # cliente HTTP
  rendering/
    console.py            # exibicao no terminal

tests/
  fixtures/
  test_centralnovel_parser.py
  test_epub.py
  test_cli.py
```

## Solucao De Problemas

### `uv: command not found`

Instale o `uv` seguindo a documentacao oficial: <https://docs.astral.sh/uv/>.

### A CLI diz que o link nao e da Central Novel

Use uma URL da obra no formato:

```text
https://centralnovel.com/series/nome-da-obra/
```

Por enquanto a ferramenta e especifica para `centralnovel.com`.

### O site respondeu erro HTTP

Pode ser instabilidade, bloqueio temporario ou mudanca no site. Tente novamente depois. Se o problema persistir, rode:

```bash
uv run webnovel2kindle scan URL_DA_OBRA
```

Isso ajuda a verificar se a pagina da obra ainda pode ser lida.

### O EPUB foi gerado, mas nao aparece onde eu esperava

Verifique a pasta `dist/`:

```bash
ls dist
```

Ou defina uma pasta explicitamente com `--output-dir`.

### O volume escolhido nao e o volume esperado

O numero usado em `--volume` segue a ordem exibida pela CLI, nao necessariamente o numero editorial do volume. Primeiro rode:

```bash
uv run webnovel2kindle scan URL_DA_OBRA
```

Depois use o indice da linha desejada.
