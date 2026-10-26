FORMULA_INJECTION_PREFIXES = ("=", "+", "-", "@")
WHITESPACE_INJECTION_PREFIXES = ("\t", "\r", "\n")


def sanitize_csv_cell(value: str) -> str:
    """
    SEGURANÇA (M13): Proteção contra Injeção de Fórmulas em CSV (CSV/Formula Injection).
    Planilhas (Excel, LibreOffice, Google Sheets) podem interpretar células que iniciam
    com =, +, -, @, tabulação ou quebra de linha como comandos DDE ou fórmulas maliciosas.
    Esta função neutraliza a célula prefixando com aspa simples (') se detectar o padrão.
    """
    if not value:
        return ""

    if value.startswith(WHITESPACE_INJECTION_PREFIXES) or value.strip().startswith(FORMULA_INJECTION_PREFIXES):
        return f"'{value}"

    return value.strip()
