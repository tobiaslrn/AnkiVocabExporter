import os, platform, shutil, subprocess
from pathlib import Path

src = Path(__file__).parent.resolve() / "plugin"
paths = {
    "Windows": Path(os.environ.get("APPDATA", "")) / "Anki2/addons21",
    "Linux": Path.home() / ".local/share/Anki2/addons21",  # untested
    "Darwin": Path.home() / "Library/Application Support/Anki2/addons21",  # untested
}
dst = paths.get(platform.system(), Path()) / "AnkiVocabExporter"

if dst.is_symlink() or dst.is_junction():
    dst.unlink()
elif dst.is_dir():
    confirm = (
        input(f"Directory {dst} already exists. Delete it? [y/N] ").strip().lower()
    )

    if confirm == "y":
        shutil.rmtree(dst)
    else:
        print("Aborted.")
        exit(1)

if platform.system() == "Windows":
    # symbolic links on Windows require admin privileges; use junction instead
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True)
else:
    dst.symlink_to(src, target_is_directory=True)

print(f"Linked: {dst} -> {src}")
