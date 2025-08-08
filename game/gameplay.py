import os, json, pygame
from .leaderboard import submit_result

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG_KEYS = os.path.join(ROOT, "config", "keys_pc.json")
SONGS_DIR = os.path.join(ROOT, "musicas")

# janelas de acerto (ms)
HIT_WINDOWS = { "perfect": 50, "good": 100, "bad": 150 }

def _load_keys_and_windows():
    with open(CFG_KEYS, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    lane_keys = [pygame.key.key_code(k) for k in cfg["lanes"]]
    # permite override de hit windows via config
    hw = cfg.get("timing", {}).get("hit_window_ms", HIT_WINDOWS)
    return lane_keys, hw

def _load_beatmap(song_id: str, difficulty: str):
    bp = os.path.join(SONGS_DIR, song_id, f"{difficulty}.json")
    with open(bp, "r", encoding="utf-8") as f:
        data = json.load(f)
    # aceita esquema [{ "tempo": ms, "coluna": 1..4 }, ...]
    notes = [{"time": int(n["tempo"]), "lane": int(n["coluna"]) - 1} for n in data]
    return notes

def run_game(screen, song_id: str, difficulty: str, player_name: str = "Player"):
    pygame.mixer.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 24)

    # carrega teclas e hit windows
    lane_keys, HW = _load_keys_and_windows()

    # carrega audio
    audio = os.path.join(SONGS_DIR, song_id, "audio.mp3")
    if not os.path.exists(audio):
        audio2 = os.path.join(SONGS_DIR, song_id, "musica.mp3")
        audio = audio2 if os.path.exists(audio2) else None
    if not audio:
        raise RuntimeError(f"Audio não encontrado para {song_id}")

    pygame.mixer.music.load(audio)
    pygame.mixer.music.set_volume(0.9)

    # carrega beatmap
    notes = _load_beatmap(song_id, difficulty)
    notes.sort(key=lambda n: n["time"])

    # visual basico
    W, H = screen.get_size()
    LANE_W = 100
    LEFT_X = W//2 - (LANE_W*4)//2
    HIT_Y = H - 120
    NOTE_H = 24
    SPEED = 0.6  # pixel por ms (ajuste: depende de ar)

    # estado
    start_ms = None
    idx_next = 0
    score = 0
    combo = 0
    max_combo = 0
    total_notes = len(notes)
    hits = 0

    # Toca
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.mixer.music.stop()
                raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.mixer.music.stop()
                    return  # saiu sem salvar

                # verificar hit por lane pressionada
                if ev.key in lane_keys and start_ms is not None:
                    lane = lane_keys.index(ev.key)
                    now = pygame.time.get_ticks() - start_ms

                    # procura a nota mais proxima nessa lane ainda nao analisada
                    # tolerancia = HW["bad"]
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
                        # pontuacao simples
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

        # inicia musica e cronometro no primeiro frame
        if start_ms is None:
            pygame.mixer.music.play()
            start_ms = pygame.time.get_ticks()

        now = pygame.time.get_ticks() - start_ms

        # avanca indice da proxima nota que deve aparecer
        while idx_next < len(notes) and notes[idx_next]["time"] < now - 1000:
            idx_next += 1

        # desenho
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
            # perdeu (passou muito)
            if now - n["time"] > HW["bad"] and not n.get("judged"):
                n["judged"] = True
                combo = 0

        # HUD
        acc = (hits/total_notes) if total_notes else 0.0
        hud = f"{song_id} [{difficulty}]  Score: {score}  Combo: {combo}  Acc: {acc*100:.0f}%"
        screen.blit(font.render(hud, True, (240,240,240)), (20, 20))

        # fim da musica?
        if not pygame.mixer.music.get_busy() and now > 1000:
            running = False

        pygame.display.flip()
        clock.tick(60)

    # fim de música, calcula precisao e salva
    accuracy = (hits/total_notes) if total_notes else 0.0
    res = submit_result(
        song_id=song_id,
        difficulty=difficulty,
        player_name=player_name,
        score=score,
        accuracy=accuracy,
        max_combo=max_combo
    )
    # pequena tela de resultado (rapida)
    _results_screen(screen, res)

def _results_screen(screen, res):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 28)
    small = pygame.font.SysFont("arial", 20)
    timer = 0
    while timer < 3000:  # 3s
        screen.fill((8,8,12))
        lines = [
            f'{res["name"]} — Score {res["score"]}  Acc {res["accuracy"]*100:.0f}%  MaxCombo {res["max_combo"]}',
            f'Posição #{res["_position"]} de {res["_total"]}  |  Melhor que {res["_percentile"]}% dos jogadores',
            res["_feedback"]
        ]
        for i, t in enumerate(lines):
            screen.blit(font.render(t, True, (240,240,240)), (40, 100 + i*40))
        screen.blit(small.render("Pressione ESC para sair", True, (200,200,200)), (40, 260))
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                timer = 3000
        clock.tick(60)
        timer += clock.get_time()
