"""Gera a entrega com código e documentação, sem banco local nem credenciais."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
FILES = ("app.py", "requirements.txt", ".gitignore", ".gitattributes", ".env.example", ".python-version", "vercel.json", "README.md", "iniciar.cmd", "empacotar.py")
DIRECTORIES = ("circula", "templates", "public", "tests", "docs")


def main():
    destination = ROOT / "entrega" / "circula-projeto.zip"
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, f"circula/{name}")
        for directory in DIRECTORIES:
            for path in sorted((ROOT / directory).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                    archive.write(path, "circula/" + path.relative_to(ROOT).as_posix())
    print(f"Entrega criada: {destination}")


if __name__ == "__main__":
    main()
