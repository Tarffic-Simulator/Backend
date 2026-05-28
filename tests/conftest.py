import os


os.environ["SECRET_KEY"] = "12345678901234567890123456789012"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENGINE_API_URL"] = "http://localhost:8000"