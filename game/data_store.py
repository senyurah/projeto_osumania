from __future__ import annotations
import json, os, tempfile, shutil
from typing import Any, Dict

# pasta base para os dados globais
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "dados")
os.makedirs(BASE_DIR, exist_ok=True)

def _path(name: str) -> str:
    return os.path.join(BASE_DIR, name)

def _atomic_write(path: str, payload: Any):
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".tmp_data_", dir=os.path.dirname(path))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        shutil.move(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def load_json(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    path = _path(name)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(name: str, payload: Dict[str, Any]):
    _atomic_write(_path(name), payload)

# configuracoes do jogo
def get_last_selected() -> Dict[str, Any]:
    return load_json("last_selected.json", {
        "song_id": None,
        "difficulty": None
    })

def set_last_selected(song_id: str, difficulty: str):
    save_json("last_selected.json", {
        "song_id": song_id,
        "difficulty": difficulty
    })

def get_user_settings() -> Dict[str, Any]:
    return load_json("settings_user.json", {
        "volume": 0.8,      # volume padrao
        "latency_ms": 0,    # compensacao de atraso
        "bg_video": False   # usar ou nao video de fundo
    })

def update_user_settings(**kwargs):
    data = get_user_settings()
    data.update({k: v for k, v in kwargs.items() if v is not None})
    save_json("settings_user.json", data)
