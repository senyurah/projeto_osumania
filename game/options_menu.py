# game/options_menu.py
import pygame
from .data_store import get_user_settings, update_user_settings

def run_options(screen) -> None:
    clock = pygame.time.Clock()
    font  = pygame.font.SysFont("arial", 28)
    small = pygame.font.SysFont("arial", 20)

    s = get_user_settings()
    volume_pct = int(round((s.get("volume", 0.8) or 0.0) * 100))
    bg_video   = bool(s.get("bg_video", False))
    latency_ms = int(s.get("latency_ms", 0))

    idx = 0
    items = ["Volume", "Background durante a musica", "Latencia (ms)", "Salvar", "Voltar"]

    def apply_volume():
        try:
            pygame.mixer.music.set_volume(volume_pct/100.0)
        except Exception:
            pass

    def render():
        screen.fill((14,14,22))
        W, H = screen.get_size()

        title = font.render("Opcoes", True, (240,240,240))
        screen.blit(title, (W//2 - title.get_width()//2, 50))

        opts = [
            f"Volume: {volume_pct}%",
            f"Background: {'Ativo' if bg_video else 'Inativo'}",
            f"Latencia: {latency_ms} ms",
            "Salvar alteracoes",
            "Voltar"
        ]
        for i, text in enumerate(opts):
            color = (120,200,255) if i == idx else (220,220,220)
            t = font.render(text, True, color)
            screen.blit(t, (W//2 - t.get_width()//2, 150 + i*50))

        help_text = {
            0: "Ajusta o volume geral da musica (0-100%).",
            1: "Liga/desliga background na gameplay (imagem/video).",
            2: "Compensa atraso entre audio/visual e sua tecla.",
            3: "Grava em dados/settings_user.json.",
            4: "Volta ao menu anterior."
        }[idx]
        h = small.render(help_text, True, (220,220,220))
        screen.blit(h, (W//2 - h.get_width()//2, H - 80))

        pygame.display.flip()

    running = True
    while running:
        render()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return
                if ev.key in (pygame.K_UP, pygame.K_w):
                    idx = (idx - 1) % len(items)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    idx = (idx + 1) % len(items)
                elif ev.key in (pygame.K_LEFT, pygame.K_a):
                    if idx == 0:
                        volume_pct = max(0, volume_pct - 5); apply_volume()
                    elif idx == 1:
                        bg_video = not bg_video
                    elif idx == 2:
                        latency_ms -= 5
                elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                    if idx == 0:
                        volume_pct = min(100, volume_pct + 5); apply_volume()
                    elif idx == 1:
                        bg_video = not bg_video
                    elif idx == 2:
                        latency_ms += 5
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if idx == 3:
                        update_user_settings(
                            volume=round(volume_pct/100.0, 2),
                            bg_video=bool(bg_video),
                            latency_ms=int(latency_ms)
                        )
                        apply_volume()
                    elif idx == 4:
                        return
        clock.tick(60)
