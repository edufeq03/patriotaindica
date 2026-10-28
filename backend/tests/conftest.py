import os

# Define chave criptográfica forte para suíte de testes automatizados (atende validador de >= 64 caracteres sem termos de blocklist)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "f78a2e19d6c4b50381e9f2a47d0c653891ba42e5d7c0836192fab4e1d3c50782",
)
