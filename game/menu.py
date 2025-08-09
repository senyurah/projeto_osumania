import os, json, pygame
from .data_store import get_last_selected, set_last_selected, get_user_settings
from .leaderboard import load_leaderboard
from .options_menu import run_options  # novo: abre menu de opcoes

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SONGS_DIR = os.path.join(ROOT, "musicas")  # ajuste para "songs" se for o seu caso
CFG_KEYS = os.path.join(ROOT, "config", "keys_pc.json")

TEMPO_PREVIEW = 30.0

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
    items = []
    for name in sorted(os.listdir(SONGS_DIR)):
        p = os.path.join(SONGS_DIR, name)
        if not os.path.isdir(p):
            continue

        # audio
        audio = None
        for cand in ("audio.mp3", "musica.mp3"):
            ap = os.path.join(p, cand)
            if os.path.exists(ap):
                audio = ap; break
        if not audio:
            continue

        # cover
        cover = None
        for c in ("capa.png", "capa.jpg", "cover.png", "cover.jpg"):
            cp = os.path.join(p, c)
            if os.path.exists(cp):
                cover = cp; break

        # bg
        bg = None
        for b in ("background.png", "background.jpg"):
            bp = os.path.join(p, b)
            if os.path.exists(bp):
                bg = bp; break

        # diffs
        diffs = []
        for d in ("easy", "normal", "hard", "expert", "master"):
            if os.path.exists(os.path.join(p, f"{d}.json")):
                diffs.append(d)
        if not diffs:
            continue

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
        raise RuntimeError("nenhuma musica encontrada em /musicas")

    # lista combinada: [configuracoes] + songs
    CONFIG_ITEM = {"id": "__config__", "title": "[Configuracoes]"}
    items = [CONFIG_ITEM] + songs

    last = get_last_selected()
    # index inicial: se havia ultima musica, posiciona nela (shift +1 por causa do config)
    sel_song_idx = 0
    if last.get("song_id"):
        for i, it in enumerate(items):
            if it["id"] == last["song_id"]:
                sel_song_idx = i
                break

    sel_diff_idx = 0
    phase = "select_song"  # ou "select_diff"

    current_preview = None

    def apply_volume_from_settings():
        try:
            us = get_user_settings()
            vol = float(us.get("volume", 0.6) or 0.6)
            pygame.mixer.music.set_volume(vol)
        except Exception:
            pass

    def play_preview(song):
        nonlocal current_preview
        if song["id"] == "__config__":
            # nao toca preview
            if current_preview is not None:
                pygame.mixer.music.stop()
                current_preview = None
            return
        if current_preview == song["id"]:
            return
        pygame.mixer.music.stop()
        pygame.mixer.music.load(song["audio"])
        apply_volume_from_settings()
        pygame.mixer.music.play(start=TEMPO_PREVIEW)
        current_preview = song["id"]

    running = True
    while running:
        screen.fill((10, 10, 18))
        W, H = screen.get_size()

        # eventos
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.mixer.music.stop()
                raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if phase == "select_song":
                    if ev.key == keys["up"]:
                        sel_song_idx = (sel_song_idx - 1) % len(items)
                    elif ev.key == keys["down"]:
                        sel_song_idx = (sel_song_idx + 1) % len(items)
                    elif ev.key == keys["confirm"]:
                        if items[sel_song_idx]["id"] == "__config__":
                            # abre menu de opcoes e retorna aqui
                            pygame.mixer.music.stop()
                            run_options(screen)
                            # apos sair das opcoes, reaplica volume no preview
                            apply_volume_from_settings()
                            current_preview = None
                        else:
                            phase = "select_diff"
                            sel_diff_idx = 0
                elif phase == "select_diff":
                    song = items[sel_song_idx]
                    diffs = song["diffs"]
                    if ev.key == keys["left"]:
                        sel_diff_idx = (sel_diff_idx - 1) % len(diffs)
                    elif ev.key == keys["right"]:
                        sel_diff_idx = (sel_diff_idx + 1) % len(diffs)
                    elif ev.key == keys["confirm"]:
                        song_id = song["id"]
                        diff = diffs[sel_diff_idx]
                        pygame.mixer.music.stop()
                        set_last_selected(song_id, diff)
                        return song_id, diff
                    elif ev.key == keys["back"]:
                        phase = "select_song"

        # preview automatico quando navegando
        item = items[sel_song_idx]
        if phase == "select_song":
            # bg e preview apenas se for musica
            if item["id"] != "__config__":
                play_preview(item)
            else:
                # parado em config: sem audio
                if current_preview is not None:
                    pygame.mixer.music.stop()
                    current_preview = None

        # background (se item for musica e tiver bg)
        if item.get("bg") and item["id"] != "__config__" and os.path.exists(item["bg"]):
            bg_img = pygame.image.load(item["bg"]).convert()
            bg_img = pygame.transform.scale(bg_img, (W, H))
            screen.blit(bg_img, (0, 0))
            s = pygame.Surface((W, H), pygame.SRCALPHA); s.fill((0,0,0,140))
            screen.blit(s, (0,0))
        else:
            # fundo simples
            screen.fill((12,12,20))

        # coluna direita: primeiro configuracoes, depois musicas
        x_list, y_list = W - 360, 100
        title = font.render("Menu", True, (240,240,240))
        screen.blit(title, (x_list, 50))

        # desenha lista
        for i, it in enumerate(items):
            label = it["title"] if it["id"] == "__config__" else it["title"]
            color = (120,200,255) if i == sel_song_idx else (220,220,220)
            line = font.render(label, True, color)
            screen.blit(line, (x_list, y_list + 36*i))

        # coluna esquerda: leaderboard ou dica
        if item["id"] == "__config__":
            tip = "enter abre configuracoes"
            screen.blit(small.render(tip, True, (230,230,230)), (40, 100))
        else:
            diff_for_lb = (item["diffs"][sel_diff_idx] if phase == "select_diff"
                           else (get_last_selected().get("difficulty") or item["diffs"][0]))
            lb = load_leaderboard(item["id"], diff_for_lb)[:10]
            lb_title = font.render(f"Leaderboard — {diff_for_lb.title()}", True, (240,240,240))
            screen.blit(lb_title, (40, 50))
            for i, e in enumerate(lb):
                row = f'{i+1:>2}. {e.get("name","---")[:14]:<14}  {e.get("score",0):>7}  {round(e.get("accuracy",0)*100):>3}%'
                screen.blit(small.render(row, True, (230,230,230)), (40, 100 + i*24))

        # centro: capa e dificuldades se musica
        if item["id"] != "__config__":
            if item.get("cover") and os.path.exists(item["cover"]):
                cover = pygame.image.load(item["cover"]).convert_alpha()
                cover = pygame.transform.smoothscale(cover, (220, 220))
                screen.blit(cover, (W//2 - 110, H//2 - 140))

            name_txt = font.render(item["title"], True, (255,255,255))
            screen.blit(name_txt, (W//2 - name_txt.get_width()//2, H//2 + 100))

            if phase == "select_diff":
                diffs = item["diffs"]
                base_y = H//2 + 140
                for i, d in enumerate(diffs):
                    color = (120,200,255) if i == sel_diff_idx else (210,210,210)
                    t = font.render(d.title(), True, color)
                    screen.blit(t, (W//2 - (len(diffs)*90)//2 + i*90 - t.get_width()//2, base_y))

        pygame.display.flip()
        clock.tick(60)
