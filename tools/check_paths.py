# tools/check_paths.py
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SONGS_DIR = ROOT / "musicas"

def main():
    print("scan em:", SONGS_DIR)
    if not SONGS_DIR.exists():
        print("pasta 'musicas' nao encontrada")
        return

    for name in sorted(os.listdir(SONGS_DIR)):
        p = SONGS_DIR / name
        if not p.is_dir():
            continue

        # audio
        audio = None
        for cand in ("audio.mp3", "musica.mp3"):
            if (p / cand).exists():
                audio = cand
                break

        # diffs
        diffs = [d for d in ("easy", "normal", "hard") if (p / f"{d}.json").exists()]

        # assets visuais
        cover = any((p / c).exists() for c in ("capa.png", "capa.jpg", "cover.png", "cover.jpg"))
        bg = any((p / b).exists() for b in ("background.png", "background.jpg"))

        print(f"- {name}: audio={'ok' if audio else 'faltando'}, diffs={diffs or 'nenhuma'}, cover={'ok' if cover else 'faltando'}, bg={'ok' if bg else 'faltando'}")

if __name__ == "__main__":
    main()
