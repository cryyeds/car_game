import pygame
from settings import *
from car import make_car_sprite, BODY_NAMES, COLORS, PATTERNS

fonts = {}


def get_font(size):
    if size not in fonts:
        fonts[size] = pygame.font.SysFont(FONT_NAME, size, bold=True)
    return fonts[size]


def draw_text(screen, text, size, x, y, color=WHITE, center=True):
    # Text with a small shadow so it is easy to read
    font = get_font(size)
    shadow = font.render(text, True, BLACK)
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(shadow, rect.move(2, 2))
    screen.blit(image, rect)


def draw_background(screen):
    # Dark background with checkered bands at the top and bottom
    screen.fill(BG_COLOR)
    for band_y in (0, SCREEN_H - 40):
        for column in range(SCREEN_W // 20):
            for row in range(2):
                if (column + row) % 2 == 0:
                    pygame.draw.rect(screen, (60, 66, 100), (column * 20, band_y + row * 20, 20, 20))


class Menu:
    def __init__(self, title, options, first_y=250):
        self.title = title
        self.options = options
        self.selected = 0
        self.rects = []
        for i in range(len(options)):
            self.rects.append(pygame.Rect(SCREEN_W // 2 - 160, first_y + i * 70, 320, 54))

    def handle_event(self, event):
        # Returns the chosen option text, or None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.options[self.selected]
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    return self.options[i]
        return None

    def draw(self, screen):
        if self.title:
            draw_text(screen, self.title, 72, SCREEN_W // 2, 130, YELLOW)
        for i, rect in enumerate(self.rects):
            color = BUTTON_SELECTED if i == self.selected else BUTTON_COLOR
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, WHITE, rect, 3)
            draw_text(screen, self.options[i], 32, rect.centerx, rect.centery)


class CustomizeScreen:
    def __init__(self, style):
        self.style = style   # dict shared with the game
        self.rows = ["body", "color", "pattern", "stripe"]
        self.labels = ["Body", "Car Color", "Pattern", "Pattern Color"]
        self.sizes = [len(BODY_NAMES), len(COLORS), len(PATTERNS), len(COLORS)]
        self.selected = 0

    def get_value_name(self, row):
        key = self.rows[row]
        index = self.style[key]
        if key == "body":
            return BODY_NAMES[index]
        if key == "pattern":
            return PATTERNS[index]
        return COLORS[index][0]

    def handle_event(self, event):
        # Returns "back" when the player is done
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            return "back"
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.rows)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.rows)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            key = self.rows[self.selected]
            self.style[key] = (self.style[key] - 1) % self.sizes[self.selected]
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            key = self.rows[self.selected]
            self.style[key] = (self.style[key] + 1) % self.sizes[self.selected]
        return None

    def draw(self, screen):
        draw_background(screen)
        draw_text(screen, "CUSTOMIZE CAR", 56, SCREEN_W // 2, 80, YELLOW)

        # Option rows
        for row in range(len(self.rows)):
            rect = pygame.Rect(80, 190 + row * 80, 520, 60)
            color = BUTTON_SELECTED if row == self.selected else BUTTON_COLOR
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, WHITE, rect, 3)
            draw_text(screen, self.labels[row], 24, rect.x + 15, rect.y + 18, center=False)
            draw_text(screen, "< " + self.get_value_name(row) + " >", 24, rect.right - 190, rect.centery)

        # Big preview of the car
        panel = pygame.Rect(680, 170, 240, 340)
        pygame.draw.rect(screen, (40, 44, 70), panel)
        pygame.draw.rect(screen, WHITE, panel, 3)
        sprite = make_car_sprite(self.style["body"], self.style["color"],
                                 self.style["pattern"], self.style["stripe"], scale=12)
        screen.blit(sprite, sprite.get_rect(center=panel.center))

        draw_text(screen, "UP/DOWN: choose    LEFT/RIGHT: change    ENTER: done",
                  22, SCREEN_W // 2, 580)


ACTIONS = [
    ("accelerate", "Accelerate"),
    ("brake", "Brake / Reverse"),
    ("left", "Steer Left"),
    ("right", "Steer Right"),
]


class ControlsScreen:
    def __init__(self, bindings):
        self.bindings = bindings   # dict shared with the game: action -> [key1, key2]
        self.row = 0
        self.column = 0
        self.waiting = False       # True while waiting for the player to press a key

    def rebind(self, new_key):
        action = ACTIONS[self.row][0]
        old_key = self.bindings[action][self.column]
        # If another slot already uses this key, give it our old key (swap)
        for other_action, keys in self.bindings.items():
            for slot in range(len(keys)):
                if keys[slot] == new_key:
                    keys[slot] = old_key
        self.bindings[action][self.column] = new_key

    def handle_event(self, event):
        # Returns "back" when the player leaves the screen
        if event.type != pygame.KEYDOWN:
            return None
        if self.waiting:
            if event.key != pygame.K_ESCAPE:
                self.rebind(event.key)
            self.waiting = False
        elif event.key == pygame.K_ESCAPE:
            return "back"
        elif event.key == pygame.K_UP:
            self.row = (self.row - 1) % len(ACTIONS)
        elif event.key == pygame.K_DOWN:
            self.row = (self.row + 1) % len(ACTIONS)
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.column = 1 - self.column
        elif event.key == pygame.K_RETURN:
            self.waiting = True
        elif event.key == pygame.K_r:
            for action, keys in DEFAULT_CONTROLS.items():
                self.bindings[action][:] = keys
        return None

    def draw(self, screen):
        draw_background(screen)
        draw_text(screen, "CONTROLS", 56, SCREEN_W // 2, 80, YELLOW)
        draw_text(screen, "Key 1", 24, 590, 160, YELLOW)
        draw_text(screen, "Key 2", 24, 790, 160, YELLOW)

        for row, (action, label) in enumerate(ACTIONS):
            y = 190 + row * 75
            draw_text(screen, label, 28, 100, y + 15, center=False)
            for column in range(2):
                rect = pygame.Rect(490 + column * 200, y, 200, 56)
                selected = row == self.row and column == self.column
                pygame.draw.rect(screen, BUTTON_SELECTED if selected else BUTTON_COLOR, rect)
                pygame.draw.rect(screen, WHITE, rect, 3)
                if selected and self.waiting:
                    text = "press a key"
                else:
                    text = pygame.key.name(self.bindings[action][column]).upper()
                draw_text(screen, text, 26, rect.centerx, rect.centery)

        draw_text(screen, "Pause: ESC (fixed).  Menus use arrows + ENTER (fixed).", 22, SCREEN_W // 2, 520)
        draw_text(screen, "ARROWS: move    ENTER: change key    R: reset    ESC: back",
                  22, SCREEN_W // 2, 580)
