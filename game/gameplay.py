import os, json, pygame
from .leaderboard import submit_result
from .data_store import get_user_settings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG_KEYS = os.path.join(ROOT, "config", "keys_pc.json")
SONGS_DIR = os.path.join(ROOT, "musicas")  # ajuste para "songs" se for o seu caso

# janelas de acerto (ms) default - pode ser sobrescrito por config
HIT_WINDOWS = { "perfect": 50, "good": 100, "bad": 150 }

def _load_keys_and_windows():
    with open(CFG_KEYS, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    lane_keys = [pygame.key.key_code(k) for k in cfg["lanes"]]
    hw = cfg.get("timing", {}).get("hit_window_ms", HIT_WINDOWS)
    return lane_keys, hw

def _load_beatmap(song_id: str, difficulty: str):
    bp = os.path.join(SONGS_DIR, song_id, f"{difficulty}.json")
    with open(bp, "r", encoding="utf-8") as f:
        data = json.load(f)
    # formato esperado: [{ "tempo": ms, "coluna": 1..4 }, ...]
    notes = [{"time": int(n["tempo"]), "lane": int(n["coluna"]) - 1} for n in data]
    return notes

def _find_audio(song_id: str):
    a1 = os.path.join(SONGS_DIR, song_id, "audio.mp3")
    a2 = os.path.join(SONGS_DIR, song_id, "musica.mp3")
    if os.path.exists(a1): return a1
    if os.path.exists(a2): return a2
    return None

def _find_bg(song_id: str):
    for name in ("background.png", "background.jpg"):
        p = os.path.join(SONGS_DIR, song_id, name)
        if os.path.exists(p):
            return p
    return None

def run_game(screen, song_id: str, difficulty: str, player_name: str = "Player"):
    pygame.mixer.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 24)

    # carrega user settings
    us = get_user_settings()
    user_volume = float(us.get("volume", 0.9) or 0.9)      # 0.0..1.0
    latency_ms  = int(us.get("latency_ms", 0) or 0)        # pode ser negativo
    show_bg     = bool(us.get("bg_video", False))          # usar ou nao background

    # carrega teclas e hit windows
    lane_keys, HW = _load_keys_and_windows()

    # carrega audio
    audio = _find_audio(song_id)
    if not audio:
        raise RuntimeError(f"Audio nao encontrado para {song_id}")
    pygame.mixer.music.load(audio)
    pygame.mixer.music.set_volume(user_volume)

    # carrega beatmap
    notes = _load_beatmap(song_id, difficulty)
    notes.sort(key=lambda n: n["time"])

    # visual
    W, H = screen.get_size()
    LANE_W = 100
    LEFT_X = W//2 - (LANE_W*4)//2
    HIT_Y = H - 120
    NOTE_H = 24
    SPEED = 0.6  # pixel por ms (ajuste conforme ar)

    # background. se show_bg for False, nao exibe
    bg_img = None
    if show_bg:
        bg_path = _find_bg(song_id)
        if bg_path and os.path.exists(bg_path):
            bg_img = pygame.image.load(bg_path).convert()
            bg_img = pygame.transform.scale(bg_img, (W, H))

    # estado
    start_ms = None
    idx_next = 0
    score = 0
    combo = 0
    max_combo = 0
    total_notes = len(notes)
    hits = 0

    # loop
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.mixer.music.stop()
                raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.mixer.music.stop()
                    return  # sai sem salvar

                # hit por lane
                if ev.key in lane_keys and start_ms is not None:
                    lane = lane_keys.index(ev.key)
                    now = pygame.time.get_ticks() - start_ms + latency_ms  # aplica latencia

                    # procura melhor nota nesta lane
                    best_j = -1
                    best_dt = 10**9
                    for j in range(max(0, idx_next-3), min(len(notes), idx_next+20)):
                        n = notes[j]
                        if n.get("judged"): 
                            continue
                        if n["lane"] != lane:
                            continue
                        dt = abs(n["time"] - now)
                        if dt < best_dt:
                            best_dt, best_j = dt, j

                    if best_j >= 0 and best_dt <= HW["bad"]:
                        n = notes[best_j]
                        n["judged"] = True
                        if best_dt <= HW["perfect"]:
                            score += 300
                            combo += 1
                        elif best_dt <= HW["good"]:
                            score += 100
                            combo += 1
                        else:
                            score += 50
                            combo = 0
                        max_combo = max(max_combo, combo)
                        hits += 1

        # start audio e cronometro
        if start_ms is None:
            pygame.mixer.music.play()
            start_ms = pygame.time.get_ticks()

        # tempo atual com latencia
        now = pygame.time.get_ticks() - start_ms + latency_ms

        # avanca indice para otimizacao de desenho
        while idx_next < len(notes) and notes[idx_next]["time"] < now - 1000:
            idx_next += 1

        # draw
        if bg_img:
            screen.blit(bg_img, (0, 0))
            # leve escurecimento para contraste
            s = pygame.Surface((W, H), pygame.SRCALPHA); s.fill((0,0,0,140))
            screen.blit(s, (0,0))
        else:
            screen.fill((12, 12, 20))

        # lanes
        for i in range(4):
            x = LEFT_X + i*LANE_W
            pygame.draw.rect(screen, (50,50,60), (x, 0, LANE_W-4, H))
        # hit line
        pygame.draw.line(screen, (250,250,250), (LEFT_X, HIT_Y), (LEFT_X + LANE_W*4, HIT_Y), 3)

        # notas
        for n in notes:
            if n.get("judged"): 
                continue
            y = HIT_Y - (n["time"] - now) * SPEED
            x = LEFT_X + n["lane"]*LANE_W + 8
            if -NOTE_H <= y <= H+NOTE_H:
                pygame.draw.rect(screen, (80,190,255), (x, y, LANE_W-16, NOTE_H))
            # miss (passou da janela bad)
            if now - n["time"] > HW["bad"] and not n.get("judged"):
                n["judged"] = True
                combo = 0

        # HUD
        acc = (hits/total_notes) if total_notes else 0.0
        hud = f"{song_id} [{difficulty}]  Score: {score}  Combo: {combo}  Acc: {acc*100:.0f}%  Vol: {int(user_volume*100)}%  Lat: {latency_ms}ms"
        screen.blit(font.render(hud, True, (240,240,240)), (20, 20))

        # fim da musica?
        if not pygame.mixer.music.get_busy() and now > 1000:
            running = False

        pygame.display.flip()
        clock.tick(60)

    # fim: salva resultado
    accuracy = (hits/total_notes) if total_notes else 0.0
    res = submit_result(
        song_id=song_id,
        difficulty=difficulty,
        player_name=player_name,
        score=score,
        accuracy=accuracy,
        max_combo=max_combo
    )
    _results_screen(screen, res)

def _results_screen(screen, res):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 28)
    small = pygame.font.
