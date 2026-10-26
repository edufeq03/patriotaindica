import re

BRAZIL_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
}

INSTAGRAM_REGEX = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def validate_cpf(cpf: str) -> bool:
    """Valida os dígitos verificadores de um CPF."""
    numbers = [int(digit) for digit in cpf if digit.isdigit()]
    if len(numbers) != 11:
        return False
    # CPFs com todos os dígitos iguais são inválidos
    if len(set(numbers)) == 1:
        return False
    # Primeiro dígito verificador
    sum_1 = sum(numbers[i] * (10 - i) for i in range(9))
    expected_1 = (sum_1 * 10 % 11) % 10
    if numbers[9] != expected_1:
        return False
    # Segundo dígito verificador
    sum_2 = sum(numbers[i] * (11 - i) for i in range(10))
    expected_2 = (sum_2 * 10 % 11) % 10
    return numbers[10] == expected_2


def validate_cnpj(cnpj: str) -> bool:
    """Valida os dígitos verificadores de um CNPJ."""
    numbers = [int(digit) for digit in cnpj if digit.isdigit()]
    if len(numbers) != 14:
        return False
    # CNPJs com todos os dígitos iguais são inválidos
    if len(set(numbers)) == 1:
        return False
    # Primeiro dígito
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_1 = sum(numbers[i] * weights_1[i] for i in range(12))
    rem_1 = sum_1 % 11
    expected_1 = 0 if rem_1 < 2 else 11 - rem_1
    if numbers[12] != expected_1:
        return False
    # Segundo dígito
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_2 = sum(numbers[i] * weights_2[i] for i in range(13))
    rem_2 = sum_2 % 11
    expected_2 = 0 if rem_2 < 2 else 11 - rem_2
    return numbers[13] == expected_2
