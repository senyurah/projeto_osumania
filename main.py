# main.py
import os
import json
import pygame

from game.menu import run_menu
from game.gameplay import run_game
from game.options_menu import run_options
from game.data_store import get_user_settings

ROOT = os.path.abspath(os.path.dirname(__file__))

def init_pygame(width=1000, height=720):
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("projeto_osumania")
    return screen

def apply_global_volume():
    try:
        s = get_user_settings()
        vol = float(s.get("volume", 0.8) or 0.8)
        pygame.mixer.music.set_volume(vol)
    except Exception:
        pass

def main():
    screen = init_pygame()
    clock = pygame.time.Clock()

    running = True
    while running:
        # atalho: F1 abre opcoes a qualquer momento
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F1:
                # pausa qualquer audio atual do menu
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
                run_options(screen)
                apply_global_volume()
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass

        # fluxo padrao: menu -> gameplay
        try:
            song_id, difficulty = run_menu(screen)
        except SystemExit:
            running = False
            break
        except Exception as e:
            # caso nao haja musicas, ou erro no loader
            print("erro no menu:", e)
            running = False
            break

        # roda gameplay
        try:
            run_game(screen, song_id, difficulty, player_name="Player")
        except SystemExit:
            running = False
            break
        except Exception as e:
            print("erro na gameplay:", e)

        clock.tick(60)

    # encerra
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    pygame.quit()

if __name__ == "__main__":
    main()
