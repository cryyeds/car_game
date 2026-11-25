import math
import random
import pygame
import pymunk
from pymunk import Vec2d
from settings import *
from track import Track
from car import Car, make_car_sprite, COLORS, BODIES, PATTERNS
from ai_car import AICar
from menu import Menu, CustomizeScreen, ControlsScreen, draw_background, draw_text
from sounds import load_sounds


def ordinal(number):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(number, str(number) + "th")


def format_time(seconds):
    return "%d:%05.2f" % (seconds // 60, seconds % 60)


def standing_key(car):
    # Finished cars first (fastest time first), then by race progress
    if car.finish_time is not None:
        return (0, car.finish_time)
    return (1, -car.score)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Pixel Racer")
        self.clock = pygame.time.Clock()
        self.sounds = load_sounds()
        self.track = Track()

        # Player's car
        self.style = {"body": 0, "color": 0, "pattern": 1, "stripe": 7}

        self.main_menu = Menu("PIXEL RACER", ["Play", "Customize Car", "Controls", "Quit"])
        self.pause_menu = Menu("PAUSED", ["Resume", "Restart Race", "Main Menu"], first_y=300)
        self.results_menu = Menu(None, ["Restart Race", "Main Menu"], first_y=520)
        self.customize_screen = CustomizeScreen(self.style)

        # Driving keys (the player can change these on the Controls screen)
        self.controls = {action: list(keys) for action, keys in DEFAULT_CONTROLS.items()}
        self.controls_screen = ControlsScreen(self.controls)

        self.state = "menu"
        self.running = True

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    # Starting a race

    def start_race(self):
        # New physics world with the track walls
        self.space = pymunk.Space()
        self.track.add_walls(self.space)
        self.track_image = self.track.image.copy()   # copy so skid marks can be drawn on it

        start_position, start_direction = self.track.checkpoints[0]
        side = start_direction.perpendicular()
        start_angle = math.atan2(start_direction.x, -start_direction.y)

        # Grid slots: 2 columns, 4 rows, behind the start line
        slots = []
        for i in range(NUM_AI + 1):
            row = i // 2
            column = i % 2
            back = 70 + row * 75 + column * 35
            sideways = -35 if column == 0 else 35
            slots.append(start_position - start_direction * back + side * sideways)
        player_slot = 5

        # Player car
        sprite = make_car_sprite(self.style["body"], self.style["color"],
                                 self.style["pattern"], self.style["stripe"])
        self.player = Car(self.space, slots[player_slot], start_angle, sprite, "You")
        self.cars = [self.player]

        # 7 AI cars with random looks, lanes and skill
        free_slots = [s for i, s in enumerate(slots) if i != player_slot]
        ai_colors = [i for i in range(len(COLORS)) if i != self.style["color"]]
        random.shuffle(ai_colors)
        for i in range(NUM_AI):
            ai_sprite = make_car_sprite(random.randrange(len(BODIES)), ai_colors[i],
                                        random.randrange(len(PATTERNS)), random.randrange(len(COLORS)))
            ai_car = AICar(self.space, free_slots[i], start_angle, ai_sprite, "Bot " + str(i + 1),
                           self.track, random.uniform(-40, 40), random.uniform(0.85, 0.98))
            self.cars.append(ai_car)

        self.countdown = COUNTDOWN_SECONDS
        self.last_number = 0
        self.racing = False
        self.race_time = 0.0
        self.go_flash = 0.0
        self.finish_delay = 2.5
        self.sparks = []
        self.standings = list(self.cars)
        self.camera = Vec2d(0, 0)
        self.state = "race"

    # Events

    def handle_event(self, event):
        if self.state == "menu":
            choice = self.main_menu.handle_event(event)
            if choice == "Play":
                self.start_race()
            elif choice == "Customize Car":
                self.state = "customize"
            elif choice == "Controls":
                self.state = "controls"
            elif choice == "Quit":
                self.running = False

        elif self.state == "customize":
            if self.customize_screen.handle_event(event) == "back":
                self.state = "menu"

        elif self.state == "controls":
            if self.controls_screen.handle_event(event) == "back":
                self.state = "menu"

        elif self.state == "race":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.pause_menu.selected = 0
                self.state = "paused"

        elif self.state == "paused":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "race"
            choice = self.pause_menu.handle_event(event)
            if choice == "Resume":
                self.state = "race"
            elif choice == "Restart Race":
                self.start_race()
            elif choice == "Main Menu":
                self.state = "menu"

        elif self.state == "results":
            choice = self.results_menu.handle_event(event)
            if choice == "Restart Race":
                self.start_race()
            elif choice == "Main Menu":
                self.state = "menu"

    # Update

    def get_player_input(self):
        keys = pygame.key.get_pressed()

        def is_down(action):
            return any(keys[key] for key in self.controls[action])

        throttle = is_down("accelerate") - is_down("brake")
        steer = is_down("right") - is_down("left")
        return throttle, steer

    def update_countdown(self, dt):
        self.countdown -= dt
        number = math.ceil(self.countdown)
        if number != self.last_number and number > 0:
            self.play_sound("beep")
        self.last_number = number
        if self.countdown <= 0:
            self.racing = True
            self.go_flash = 1.0
            self.play_sound("go")

    def update_race(self, dt):
        if not self.racing:
            self.update_countdown(dt)
        else:
            self.race_time += dt
            self.go_flash -= dt

        # Set the controls for every car
        for car in self.cars:
            car.throttle = 0
            car.steer = 0
        if self.racing:
            if self.player.finish_time is None:
                self.player.throttle, self.player.steer = self.get_player_input()
            for car in self.cars[1:]:
                car.think(dt)

        # Physics
        step_time = dt / PHYSICS_STEPS
        for _ in range(PHYSICS_STEPS):
            for car in self.cars:
                car.apply_forces()
            self.space.step(step_time)

        # Laps, positions, effects
        for car in self.cars:
            was_finished = car.finish_time is not None
            car.update_progress(self.track.checkpoints, TOTAL_LAPS, self.race_time)
            if car is self.player and car.finish_time is not None and not was_finished:
                self.play_sound("finish")
            self.update_car_effects(car)
        self.standings = sorted(self.cars, key=standing_key)
        self.update_sparks(dt)

        # Show results shortly after the player finishes
        if self.player.finish_time is not None:
            self.finish_delay -= dt
            if self.finish_delay <= 0:
                self.results_menu.selected = 0
                self.state = "results"

    def update_car_effects(self, car):
        # Crash: big speed drop in one frame
        speed = car.body.velocity.length
        if car.last_speed - speed > 100:
            for _ in range(6):
                self.sparks.append([car.body.position.x, car.body.position.y,
                                    random.uniform(-150, 150), random.uniform(-150, 150), 0.4])
            if car is self.player:
                self.play_sound("crash")
        car.last_speed = speed

        # Skid marks when sliding sideways
        if abs(car.side_speed) > 90:
            forward = car.get_forward()
            right = forward.perpendicular()
            for wheel_side in (-9, 9):
                mark = car.body.position - forward * 14 + right * wheel_side
                pygame.draw.circle(self.track_image, SKID_COLOR, (int(mark.x), int(mark.y)), 2)

    def update_sparks(self, dt):
        for spark in self.sparks:
            spark[0] += spark[2] * dt
            spark[1] += spark[3] * dt
            spark[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]

    # Drawing
    def draw(self):
        if self.state == "menu":
            draw_background(self.screen)
            self.main_menu.draw(self.screen)
        elif self.state == "customize":
            self.customize_screen.draw(self.screen)
        elif self.state == "controls":
            self.controls_screen.draw(self.screen)
        elif self.state in ("race", "paused"):
            self.draw_race()
            if self.state == "paused":
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                self.screen.blit(overlay, (0, 0))
                self.pause_menu.draw(self.screen)
        elif self.state == "results":
            self.draw_results()

    def draw_race(self):
        # Camera follows the player and stays inside the map
        position = self.player.body.position
        self.camera = Vec2d(max(0, min(WORLD_W - SCREEN_W, position.x - SCREEN_W / 2)),
                            max(0, min(WORLD_H - SCREEN_H, position.y - SCREEN_H / 2)))
        self.screen.blit(self.track_image, (0, 0),
                         pygame.Rect(int(self.camera.x), int(self.camera.y), SCREEN_W, SCREEN_H))

        # Draw cars (player last so it is on top)
        for car in reversed(self.cars):
            self.draw_car(car)

        # Sparks
        for x, y, _, _, _ in self.sparks:
            pygame.draw.rect(self.screen, YELLOW, (int(x - self.camera.x), int(y - self.camera.y), 4, 4))

        self.draw_hud()

    def draw_car(self, car):
        image = pygame.transform.rotate(car.sprite, -math.degrees(car.body.angle))
        screen_position = car.body.position - self.camera
        rect = image.get_rect(center=(int(screen_position.x), int(screen_position.y)))
        if not self.screen.get_rect().inflate(100, 100).colliderect(rect):
            return
        shadow = pygame.mask.from_surface(image).to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0))
        self.screen.blit(shadow, rect.move(4, 4))
        self.screen.blit(image, rect)
        if car is self.player:
            draw_text(self.screen, "YOU", 18, rect.centerx, rect.top - 12, YELLOW)

    def draw_hud(self):
        place = self.standings.index(self.player) + 1
        lap = min(self.player.laps_done + 1, TOTAL_LAPS)

        panel = pygame.Surface((230, 100), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        self.screen.blit(panel, (10, 10))
        draw_text(self.screen, "LAP %d/%d" % (lap, TOTAL_LAPS), 32, 25, 20, WHITE, center=False)
        draw_text(self.screen, "POS %d/%d" % (place, len(self.cars)), 32, 25, 60, YELLOW, center=False)

        time_panel = pygame.Surface((150, 40), pygame.SRCALPHA)
        time_panel.fill((0, 0, 0, 140))
        self.screen.blit(time_panel, (SCREEN_W - 160, 10))
        draw_text(self.screen, format_time(self.race_time), 28, SCREEN_W - 85, 30)

        speed = int(self.player.body.velocity.length * 0.4)
        draw_text(self.screen, "%d km/h" % speed, 26, 25, SCREEN_H - 40, center=False)

        # Countdown, GO and finish messages
        if not self.racing:
            draw_text(self.screen, str(math.ceil(self.countdown)), 140, SCREEN_W // 2, 250, YELLOW)
        elif self.go_flash > 0:
            draw_text(self.screen, "GO!", 140, SCREEN_W // 2, 250, (90, 255, 110))
        if self.player.finish_time is not None:
            draw_text(self.screen, "FINISHED! You placed " + ordinal(place), 48, SCREEN_W // 2, 200, YELLOW)

    def draw_results(self):
        draw_background(self.screen)
        place = self.standings.index(self.player) + 1
        draw_text(self.screen, "RACE RESULTS", 52, SCREEN_W // 2, 60, YELLOW)
        draw_text(self.screen, "You finished " + ordinal(place), 30, SCREEN_W // 2, 110)

        for i, car in enumerate(self.standings):
            y = 150 + i * 40
            if car is self.player:
                pygame.draw.rect(self.screen, BUTTON_SELECTED, (250, y - 2, 500, 36))
            if car.finish_time is not None:
                result = format_time(car.finish_time)
            else:
                result = "Racing"
            draw_text(self.screen, ordinal(i + 1), 26, 270, y + 6, center=False)
            draw_text(self.screen, car.name, 26, 380, y + 6, center=False)
            draw_text(self.screen, result, 26, 600, y + 6, center=False)
        self.results_menu.draw(self.screen)

    # Main loop
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.handle_event(event)
            if self.state == "race":
                self.update_race(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()
