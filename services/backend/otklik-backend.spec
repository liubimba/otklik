from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)

datas = [
    (str(root / "alembic"), "alembic"),
    (str(root / "alembic.ini"), "."),
]
datas += collect_data_files("patchright")
datas += collect_data_files("litellm")
datas += collect_data_files("botocore")
datas += collect_data_files("keyring")

hiddenimports = []
hiddenimports += collect_submodules("litellm")
hiddenimports += collect_submodules("botocore")
hiddenimports += collect_submodules("keyring.backends")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("aiosqlite")
hiddenimports += ["tiktoken_ext", "tiktoken_ext.openai_public"]
hiddenimports += collect_submodules("tiktoken_ext")
hiddenimports += collect_submodules("socksio")

a = Analysis(
    [str(root / "scripts" / "sidecar_entry.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="otklik-backend",
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, name="backend")
