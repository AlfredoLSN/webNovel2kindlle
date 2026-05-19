# webnovel2kindle

![webnovel2kindle logo](logo.png)

CLI experimental para ler a pagina de uma obra na Central Novel, reconhecer volumes e capitulos, selecionar um volume e gerar um EPUB.

A imagem `logo.png` na raiz do projeto tambem e usada como logo discreta na assinatura dos EPUBs gerados.

## Stack

- Python 3.12+
- Typer para CLI
- Rich para saida no terminal
- httpx para HTTP
- BeautifulSoup para parsing HTML
- pytest para TDD

## Uso

Fluxo completo guiado:

```bash
uv run webnovel2kindle
```

A CLI vai pedir o link da obra, exibir os volumes, pedir o volume desejado, baixar os capitulos e gerar o EPUB em `dist/`.

Fluxo completo ja com link:

```bash
uv run webnovel2kindle --url https://centralnovel.com/series/shadow-slave-20230928/
```

Fluxo completo ja com link e volume:

```bash
uv run webnovel2kindle --url https://centralnovel.com/series/shadow-slave-20230928/ --volume 2
```

Para apenas ver a estrutura:

```bash
uv run webnovel2kindle scan https://centralnovel.com/series/shadow-slave-20230928/
```

Para listar todos os capitulos, use:

```bash
uv run webnovel2kindle scan https://centralnovel.com/series/shadow-slave-20230928/ --chapters
```

Tambem existe o comando explicito de exportacao:

```bash
uv run webnovel2kindle export https://centralnovel.com/series/shadow-slave-20230928/
```

Ou informe o volume diretamente:

```bash
uv run webnovel2kindle export https://centralnovel.com/series/shadow-slave-20230928/ --volume 2
```

## Testes

```bash
uv run --extra dev pytest
```
