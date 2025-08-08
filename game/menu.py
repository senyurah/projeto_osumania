import os, json, pygame
from .data_store import get_last_selected, set_last_selected
from .leaderboard import load_leaderboard

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SONGS_DIR = os.path.join(ROOT, "musicas")
CFG_KEYS = os.path.join(ROOT, "config", "keys_pc.json")

TEMPO_PREVIEW = 30.0  # segundos
VOLUME = 0.6

def _load_keys():
    with open(CFG_KEYS, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    keys = {
        "up": pygame.key.key_code(cfg["menu"]["up"]),
        "down": pygame.key.key_code(cfg["menu"]["down"]),
        "left": pygame.key.key_code(cfg["menu"]["left"]),
        "right": pygame.key.key_code(cfg["menu"]["right"]),
        "confirm": pygame.key.key_code(cfg["menu"]["confirm"]),
        "back": pygame.key.key_code(cfg["menu"]["back"]),
    }
    return keys

def _scan_songs():
    """
    Espera estrutura:
      musicas/<song_id>/
        - audio.mp3
        - capa.png
        - background.jpg/png
        - easy.json / normal.json / hard.json
        - leaderboard/<diff>.json
    """
    items = []
    for name in sorted(os.listdir(SONGS_DIR)):
        p = os.path.join(SONGS_DIR, name)
        if not os.path.isdir(p): 
            continue
        audio = os.path.join(p, "audio.mp3")
        if not os.path.exists(audio):
            # aceita 'musica.mp3' como fallback
            audio2 = os.path.join(p, "musica.mp3")
            audio = audio2 if os.path.exists(audio2) else None
        if not audio:
            continue

        cover = None
        for c in ("capa.png", "capa.jpg", "cover.png", "cover.jpg"):
            cp = os.path.join(p, c)
            if os.path.exists(cp):
                cover = cp; break
        bg = None
        for b in ("background.png", "background.jpg"):
            bp = os.path.join(p, b)
            if os.path.exists(bp):
                bg = bp; break

        diffs = []
        for d in ("easy", "normal", "hard", "expert", "master"):
            if os.path.exists(os.path.join(p, f"{d}.json")):
                diffs.append(d)

        if diffs:
            items.append({
                "id": name,
                "title": name.replace("_", " ").title(),
                "audio": audio,
                "cover": cover,
                "bg": bg,
                "diffs": diffs
            })
    return items

def run_menu(screen) -> tuple[str, str]:
    pygame.mixer.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 28)
    small = pygame.font.SysFont("arial", 20)

    keys = _load_keys()
    songs = _scan_songs()
    if not songs:
        raise RuntimeError("Nenhuma musica encontrada em /musicas.")

    last = get_last_selected()
    sel_song_idx = next((i for i,s in enumerate(songs) if s["id"] == last.get("song_id")), 0)
    sel_diff_idx = 0
    phase = "select_song"  # select_song → select_diff

    current_preview = None

    def play_preview(song):
        nonlocal current_preview
        if current_preview == song["id"]:
            return
        pygame.mixer.music.stop()
        pygame.mixer.music.load(song["audio"])
        pygame.mixer.music.set_volume(VOLUME)
        pygame.mixer.music.play(start=TEMPO_PREVIEW)
        current_preview = song["id"]

    running = True
    while running:
        screen.fill((10, 10, 18))
        W, H = screen.get_size()

        # Entrada
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.mixer.music.stop()
                raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if phase == "select_song":
                    if ev.key == keys["up"]:
                        sel_song_idx = (sel_song_idx - 1) % len(songs)
                    elif ev.key == keys["down"]:
                        sel_song_idx = (sel_song_idx + 1) % len(songs)
                    elif ev.key == keys["confirm"]:
                        phase = "select_diff"
                elif phase == "select_diff":
                    diffs = songs[sel_song_idx]["diffs"]
                    if ev.key == keys["left"]:
                        sel_diff_idx = (sel_diff_idx - 1) % len(diffs)
                    elif ev.key == keys["right"]:
                        sel_diff_idx = (sel_diff_idx + 1) % len(diffs)
                    elif ev.key == keys["confirm"]:
                        # Confirma e sai pro gameplay
                        song_id = songs[sel_song_idx]["id"]
                        diff = diffs[sel_diff_idx]
                        pygame.mixer.music.stop()
                        set_last_selected(song_id, diff)
                        return song_id, diff
                    elif ev.key == keys["back"]:
                        phase = "select_song"

        # Preview automático ao navegar por músicas
        song = songs[sel_song_idx]
        if phase == "select_song":
            play_preview(song)

        # Background (blur básico: só escurece)
        if song["bg"] and os.path.exists(song["bg"]):
            bg_img = pygame.image.load(song["bg"]).convert()
            bg_img = pygame.transform.scale(bg_img, (W, H))
            screen.blit(bg_img, (0, 0))
            s = pygame.Surface((W, H), pygame.SRCALPHA); s.fill((0,0,0,140))
            screen.blit(s, (0,0))

        # Coluna direita (lista de musicas)
        x_list, y_list = W - 360, 100
        title = font.render("Músicas", True, (240,240,240))
        screen.blit(title, (x_list, 50))
        for i, s in enumerate(songs):
            color = (120,200,255) if i == sel_song_idx else (220,220,220)
            line = font.render(s["title"], True, color)
            screen.blit(line, (x_list, y_list + 36*i))

        # Coluna esquerda: leaderboard da fase corrente (usa diff padrão ou última)
        diff_for_lb = (song["diffs"][sel_diff_idx] if phase == "select_diff"
                       else (get_last_selected().get("difficulty") or song["diffs"][0]))
        lb = load_leaderboard(song["id"], diff_for_lb)[:10]
        lb_title = font.render(f"Leaderboard — {diff_for_lb.title()}", True, (240,240,240))
        screen.blit(lb_title, (40, 50))
        for i, e in enumerate(lb):
            row = f'{i+1:>2}. {e.get("name","---")[:14]:<14}  {e.get("score",0):>7}  {round(e.get("accuracy",0)*100):>3}%'
            screen.blit(small.render(row, True, (230,230,230)), (40, 100 + i*24))

        # Centro: capa e dificuldades
        if song["cover"] and os.path.exists(song["cover"]):
            cover = pygame.image.load(song["cover"]).convert_alpha()
            cover = pygame.transform.smoothscale(cover, (220, 220))
            screen.blit(cover, (W//2 - 110, H//2 - 140))

        name_txt = font.render(song["title"], True, (255,255,255))
        screen.blit(name_txt, (W//2 - name_txt.get_width()//2, H//2 + 100))

        # Seletor de dificuldade (aparece após Enter)
        if phase == "select_diff":
            diffs = song["diffs"]
            base_y = H//2 + 140
            for i, d in enumerate(diffs):
                color = (120,200,255) if i == sel_diff_idx else (210,210,210)
                t = font.render(d.title(), True, color)
                screen.blit(t, (W//2 - (len(diffs)*90)//2 + i*90 - t.get_width()//2, base_y))

        pygame.display.flip()
        clock.tick(60)
