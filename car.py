import pygame
import pymunk
from pymunk import Vec2d
from settings import *

# Car shapes as tiny pixel maps (9 wide, 15 tall, front of the car at the top)
# . = empty, B = body, W = window, K = tire, H = headlight, T = taillight
BODIES = {
    "Racer": [
        "..HBBBH..",
        "..BBBBB..",
        "..BBBBB..",
        "KBBBBBBBK",
        "KBBWWWBBK",
        ".BBWWWBB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".BBWWWBB.",
        "KBBBBBBBK",
        "KBBBBBBBK",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".TBBBBBT.",
    ],
    "Hatch": [
        ".HBBBBBH.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        "KBBBBBBBK",
        "KBBWWWBBK",
        ".BWWWWWB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".BWWWWWB.",
        "KBBBBBBBK",
        "KBBBBBBBK",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".TTBBBTT.",
    ],
    "Wedge": [
        "...HBH...",
        "..BBBBB..",
        "..BBBBB..",
        "KBBBBBBBK",
        "KBBWWWBBK",
        ".BBWWWBB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        ".BBBBBBB.",
        "KBBBBBBBK",
        "KBBBBBBBK",
        "BBBBBBBBB",
        "BBBBBBBBB",
        "BTBBBBBTB",
    ],
}
BODY_NAMES = list(BODIES.keys())

COLORS = [
    ("Red", (220, 50, 50)),
    ("Blue", (50, 100, 230)),
    ("Green", (50, 190, 80)),
    ("Yellow", (240, 210, 50)),
    ("Orange", (240, 140, 40)),
    ("Purple", (150, 70, 210)),
    ("Pink", (240, 120, 180)),
    ("White", (235, 235, 235)),
    ("Black", (50, 50, 55)),
    ("Cyan", (60, 210, 220)),
]

PATTERNS = ["None", "Center Stripe", "Twin Stripes", "Checkers", "Spots", "Side Stripes"]

WINDOW_COLOR = (130, 200, 255)
TIRE_COLOR = (25, 25, 28)
HEADLIGHT_COLOR = (255, 245, 160)
TAILLIGHT_COLOR = (255, 40, 40)


def pattern_hits(pattern, x, y):
    # Does this body pixel get the pattern color?
    if pattern == 1:
        return x == 4
    if pattern == 2:
        return x in (3, 5)
    if pattern == 3:
        return 6 <= y <= 8 and (x + y) % 2 == 0
    if pattern == 4:
        return x % 3 == 1 and y % 3 == 1
    if pattern == 5:
        return x in (2, 6)
    return False


def make_car_sprite(body, color, pattern, stripe, scale=SPRITE_SCALE):
    # Build the car pixel by pixel then scale it up
    pixels = BODIES[BODY_NAMES[body]]
    body_color = COLORS[color][1]
    stripe_color = COLORS[stripe][1]
    dark_color = tuple(int(c * 0.75) for c in body_color)

    small = pygame.Surface((len(pixels[0]), len(pixels)), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, letter in enumerate(row):
            if letter == "B":
                if pattern_hits(pattern, x, y):
                    pixel_color = stripe_color
                elif x in (1, 7):
                    pixel_color = dark_color
                else:
                    pixel_color = body_color
            elif letter == "W":
                pixel_color = WINDOW_COLOR
            elif letter == "K":
                pixel_color = TIRE_COLOR
            elif letter == "H":
                pixel_color = HEADLIGHT_COLOR
            elif letter == "T":
                pixel_color = TAILLIGHT_COLOR
            else:
                continue
            small.set_at((x, y), pixel_color)
    return pygame.transform.scale(small, (small.get_width() * scale, small.get_height() * scale))


class Car:
    def __init__(self, space, position, angle, sprite, name):
        self.name = name
        self.sprite = sprite

        # Pymunk body and shape
        self.body = pymunk.Body(CAR_MASS, pymunk.moment_for_box(CAR_MASS, (CAR_W, CAR_H)))
        self.body.position = position
        self.body.angle = angle
        self.shape = pymunk.Poly.create_box(self.body, (CAR_W, CAR_H), 3)
        self.shape.elasticity = 0.3
        self.shape.friction = 0.4
        space.add(self.body, self.shape)

        # Controls
        self.throttle = 0.0   # -1 = brake/reverse, 1 = accelerate
        self.steer = 0.0      # -1 = left, 1 = right
        self.side_speed = 0.0
        self.last_speed = 0.0

        # Race progress
        self.passed = 0            # total checkpoints passed
        self.next_checkpoint = 0
        self.laps_done = 0
        self.score = 0             # bigger score = further ahead
        self.finish_time = None

    def get_forward(self):
        # Angle 0 points up the screen, positive angle turns clockwise
        return Vec2d(0, -1).rotated(self.body.angle)

    def apply_forces(self):
        forward = self.get_forward()
        right = forward.perpendicular()
        velocity = self.body.velocity
        forward_speed = velocity.dot(forward)
        self.side_speed = velocity.dot(right)

        # Engine, brake or reverse
        force = Vec2d(0, 0)
        if self.throttle > 0:
            force += forward * (ENGINE_ACCEL * self.throttle)
        elif self.throttle < 0:
            if forward_speed > 30:
                force -= forward * BRAKE_ACCEL
            else:
                force += forward * (REVERSE_ACCEL * self.throttle)

        # Drag slows the car and gives it a top speed
        force -= velocity * DRAG
        if self.throttle == 0:
            force -= velocity * COAST_DRAG

        # Tire grip: push back against sideways sliding
        force -= right * (self.side_speed * GRIP)

        self.body.apply_force_at_world_point(force * CAR_MASS, self.body.position)

        # Steering: turn faster when moving, and flip when reversing
        direction = 1 if forward_speed >= 0 else -1
        grip_factor = min(abs(forward_speed) / 100, 1)
        steer_rate = STEER_RATE - 1.0 * min(abs(forward_speed) / 450, 1)
        target_turn = self.steer * steer_rate * grip_factor * direction
        self.body.angular_velocity += (target_turn - self.body.angular_velocity) * 0.35

    def update_progress(self, checkpoints, total_laps, race_time):
        # Check next checkpoint: close enough and past its line
        position, direction = checkpoints[self.next_checkpoint]
        offset = self.body.position - position
        if offset.length < GATE_RADIUS and offset.dot(direction) >= 0:
            self.passed += 1
            self.next_checkpoint = self.passed % len(checkpoints)
            position, direction = checkpoints[self.next_checkpoint]

        # Update lap (the first crossing of the start line is not a lap)
        self.laps_done = max(0, (self.passed - 1) // len(checkpoints))
        if self.finish_time is None and self.laps_done >= total_laps:
            self.finish_time = race_time

        # Score used for race positions
        self.score = self.passed * 10000 - self.body.position.get_distance(position)
