import pygame

# Default keys for driving (each action has 2 keys)
DEFAULT_CONTROLS = {
    "accelerate": [pygame.K_UP, pygame.K_w],
    "brake": [pygame.K_DOWN, pygame.K_s],
    "left": [pygame.K_LEFT, pygame.K_a],
    "right": [pygame.K_RIGHT, pygame.K_d],
}

# Window
SCREEN_W = 1000
SCREEN_H = 700
FPS = 60

# Size of the whole map
WORLD_W = 3000
WORLD_H = 2000

# Race rules
TOTAL_LAPS = 3
NUM_AI = 7
COUNTDOWN_SECONDS = 3.0

# Track
TRACK_WIDTH = 170
GATE_RADIUS = 110        # how close a car must be to pass a checkpoint
WAYPOINT_RADIUS = 110    # how close an AI car must be to switch waypoint

# Car size and sprite scale
CAR_W = 24
CAR_H = 42
CAR_MASS = 1
SPRITE_SCALE = 3

# Car physics
ENGINE_ACCEL = 650
BRAKE_ACCEL = 1100
REVERSE_ACCEL = 350
DRAG = 1.5          # air/rolling drag, sets the top speed
COAST_DRAG = 1.0    # extra slowing when no pedal is pressed
GRIP = 6            # how fast sideways sliding is removed
STEER_RATE = 3.0    # radians per second at low speed
PHYSICS_STEPS = 2   # physics steps per frame to keep collisions stable

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 220, 60)
GRAY = (90, 90, 100)
BG_COLOR = (22, 26, 46)
BUTTON_COLOR = (50, 58, 96)
BUTTON_SELECTED = (230, 90, 60)
GRASS = (58, 130, 62)
GRASS_DARK = (50, 118, 56)
ASPHALT = (70, 72, 80)
KERB_RED = (210, 50, 50)
KERB_WHITE = (235, 235, 235)
SKID_COLOR = (45, 46, 52)

FONT_NAME = "consolas,couriernew,monospace"
