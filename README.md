# webnovel2kindle

CLI experimental para ler a pagina de uma obra na Central Novel, reconhecer volumes e capitulos, e exibir a estrutura encontrada.

## Stack

- Python 3.12+
- Typer para CLI
- Rich para saida no terminal
- httpx para HTTP
- BeautifulSoup para parsing HTML
- pytest para TDD

## Uso

```bash
uv run webnovel2kindle scan
```

Ou passando a URL diretamente:

```bash
uv run webnovel2kindle scan https://centralnovel.com/series/shadow-slave-20230928/
```

Para listar todos os capitulos, use:

```bash
uv run webnovel2kindle scan https://centralnovel.com/series/shadow-slave-20230928/ --chapters
```

## Testes

```bash
uv run --extra dev pytest
```
