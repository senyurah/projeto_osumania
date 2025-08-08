from __future__ import annotations
import json, os, tempfile, shutil
from datetime import datetime
from typing import List, Dict, Any, Optional

# local dos rankings por musica e dificuldade
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "musicas")
TOP_LIMIT = 10  # mantem so top 10

def _phase_dir(song_id: str) -> str:
    return os.path.join(DATA_DIR, song_id, "leaderboard")

def _phase_path(song_id: str, difficulty: str) -> str:
    os.makedirs(_phase_dir(song_id), exist_ok=True)
    return os.path.join(_phase_dir(song_id), f"{difficulty.lower()}.json")

def _atomic_write(path: str, payload: Any):
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".tmp_lb_", dir=os.path.dirname(path))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        shutil.move(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def load_leaderboard(song_id: str, difficulty: str) -> List[Dict[str, Any]]:
    path = _phase_path(song_id, difficulty)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _ts(iso: Optional[str]) -> int:
    if not iso:
        return 0
    try:
        return int(datetime.fromisoformat(iso.rstrip("Z")).timestamp())
    except Exception:
        return 0

def save_leaderboard(song_id: str, difficulty: str, entries: List[Dict[str, Any]]):
    # ordena: score desc, accuracy desc, mais antigo antes em empate
    entries_sorted = sorted(
        entries,
        key=lambda e: (e.get("score", 0), e.get("accuracy", 0.0), -_ts(e.get("date"))),
        reverse=True,
    )[:TOP_LIMIT]
    _atomic_write(_phase_path(song_id, difficulty), entries_sorted)

def submit_result(
    song_id: str,
    difficulty: str,
    player_name: str,
    score: int,
    accuracy: float,   # 0.0..1.0
    max_combo: int,
) -> Dict[str, Any]:
    entry = {
        "name": player_name[:20],
        "score": int(score),
        "accuracy": round(float(accuracy), 4),
        "max_combo": int(max_combo),
        "date": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    lb = load_leaderboard(song_id, difficulty)
    lb.append(entry)
    save_leaderboard(song_id, difficulty, lb)

    pos, total = rank_position(lb, entry)
    pct = percentile(lb, entry)

    # campos auxiliares para tela de resultado
    entry["_position"] = pos
    entry["_total"] = total
    entry["_percentile"] = pct
    entry["_feedback"] = feedback_phrase(accuracy, pct)
    return entry

def rank_position(lb: List[Dict[str, Any]], entry: Dict[str, Any]) -> (int, int): # type: ignore
    sorted_lb = sorted(
        lb,
        key=lambda e: (e.get("score",0), e.get("accuracy",0.0), -_ts(e.get("date"))),
        reverse=True
    )
    for i, e in enumerate(sorted_lb, start=1):
        if (e["name"], e["score"], e["accuracy"], e["max_combo"], e["date"]) == \
           (entry["name"], entry["score"], entry["accuracy"], entry["max_combo"], entry["date"]):
            return i, len(sorted_lb)
    return len(sorted_lb), len(sorted_lb)

def percentile(lb: List[Dict[str, Any]], entry: Dict[str, Any]) -> int:
    if not lb: return 0
    sorted_lb = sorted(lb, key=lambda e: (e.get("score",0), e.get("accuracy",0.0), -_ts(e.get("date"))), reverse=True)
    pos = next((i for i, e in enumerate(sorted_lb, start=1)
                if (e["name"], e["score"], e["accuracy"], e["max_combo"], e["date"]) ==
                   (entry["name"], entry["score"], entry["accuracy"], entry["max_combo"], entry["date"])), len(sorted_lb))
    better_than = (len(sorted_lb) - pos) / len(sorted_lb)
    return int(round(better_than * 100))

def feedback_phrase(accuracy: float, percentile_value: int) -> str:
    acc = accuracy * 100.0
    if acc >= 95: return "Você é um SPEED DEMON!"
    if acc >= 85: return "Reflexos de ninja (quase)"
    if percentile_value >= 70: return "Você foi melhor que 68% dos jogadores!"
    if acc < 60: return "PÉSSIMO tanto pra cirurgia cerebral quanto pra jogos, mas (não) é só o começo!"
    return "Bom jogo — dá pra subir mais na tabela!"
