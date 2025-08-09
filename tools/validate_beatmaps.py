# tools/validate_beatmaps.py
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "musicas"
DIFFS = ("easy", "normal", "hard")

def validate_entry(entry, idx, song_id, diff):
    errors = []
    if not isinstance(entry, dict):
        errors.append(f"[{song_id}/{diff}] item #{idx}: nao eh objeto JSON")
        return errors

    if "tempo" not in entry:
        errors.append(f"[{song_id}/{diff}] item #{idx}: falta chave 'tempo'")
    if "coluna" not in entry:
        errors.append(f"[{song_id}/{diff}] item #{idx}: falta chave 'coluna'")

    tempo = entry.get("tempo")
    coluna = entry.get("coluna")

    if tempo is not None:
        if not isinstance(tempo, (int, float)):
            errors.append(f"[{song_id}/{diff}] item #{idx}: tempo deve ser numero (ms). valor={tempo!r}")
        elif tempo < 0:
            errors.append(f"[{song_id}/{diff}] item #{idx}: tempo deve ser >= 0. valor={tempo}")
    if coluna is not None:
        if not isinstance(coluna, int):
            errors.append(f"[{song_id}/{diff}] item #{idx}: coluna deve ser inteiro 1..4. valor={coluna!r}")
        elif not (1 <= coluna <= 4):
            errors.append(f"[{song_id}/{diff}] item #{idx}: coluna fora do intervalo 1..4. valor={coluna}")

    return errors

def validate_file(path: Path, song_id: str, diff: str):
    errors = []
    if not path.exists():
        return errors  # sem arquivo = sem validacao para este diff

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"[{song_id}/{diff}] JSON invalido em {path.name}: linha {e.lineno}, col {e.colno} - {e.msg}")
        return errors
    except Exception as e:
        errors.append(f"[{song_id}/{diff}] erro lendo {path.name}: {e}")
        return errors

    if not isinstance(data, list):
        errors.append(f"[{song_id}/{diff}] raiz do JSON deve ser lista []")
        return errors

    # validar itens
    last_t = -1
    for i, entry in enumerate(data):
        errs = validate_entry(entry, i, song_id, diff)
        errors.extend(errs)
        # checar ordem de tempo quando possivel
        t = entry.get("tempo")
        if isinstance(t, (int, float)):
            if t < last_t:
                errors.append(f"[{song_id}/{diff}] item #{i}: tempo fora de ordem (anterior={last_t}, atual={t})")
            last_t = max(last_t, t if t is not None else last_t)

    return errors

def validate_song(song_dir: Path):
    song_id = song_dir.name
    errors = []
    for diff in DIFFS:
        path = song_dir / f"{diff}.json"
        errors.extend(validate_file(path, song_id, diff))
    return errors

def main():
    base = MUSIC_DIR
    if len(sys.argv) > 1:
        # validar so uma musica: tools/validate_beatmaps.py <song_id>
        base = base / sys.argv[1]
        if not base.exists():
            print(f"pasta nao encontrada: {base}")
            sys.exit(2)
        song_dirs = [base]
    else:
        if not MUSIC_DIR.exists():
            print("pasta 'musicas' nao encontrada")
            sys.exit(2)
        song_dirs = [p for p in MUSIC_DIR.iterdir() if p.is_dir()]

    all_errors = []
    for sdir in sorted(song_dirs, key=lambda p: p.name):
        errs = validate_song(sdir)
        if errs:
            for e in errs:
                print(e)
            all_errors.extend(errs)
        else:
            print(f"[ok] {sdir.name} (easy/normal/hard validos ou ausentes)")

    if all_errors:
        print(f"\nfalhas: {len(all_errors)} problema(s) encontrado(s)")
        sys.exit(1)
    else:
        print("\nvalidacao concluida sem erros.")
        sys.exit(0)

if __name__ == "__main__":
    main()
