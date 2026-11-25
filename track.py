import random
import pygame
import pymunk
from pymunk import Vec2d
from settings import *

# Rough shape of the track the game smooths these points into a loop
# The first point is the start/finish line and cars drive in this order
CONTROL_POINTS = [
    (1500, 1720), (2000, 1700), (2450, 1620), (2700, 1350), (2600, 1050),
    (2300, 900), (2350, 600), (2150, 330), (1750, 250), (1450, 480),
    (1100, 330), (700, 250), (350, 450), (300, 900), (550, 1150),
    (350, 1450), (500, 1700), (1000, 1700),
]


def smooth_loop(points, steps=20):
    # Catmull-Rom spline: a smooth curve that passes through every point
    def spline(a, b, c, d, t):
        return 0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                      + (-a + 3 * b - 3 * c + d) * t ** 3)

    result = []
    count = len(points)
    for i in range(count):
        p0 = points[i - 1]
        p1 = points[i]
        p2 = points[(i + 1) % count]
        p3 = points[(i + 2) % count]
        for step in range(steps):
            t = step / steps
            x = spline(p0[0], p1[0], p2[0], p3[0], t)
            y = spline(p0[1], p1[1], p2[1], p3[1], t)
            result.append(Vec2d(x, y))
    return result


def resample(points, count):
    # Pick evenly spaced points around a closed loop
    n = len(points)
    lengths = [points[i].get_distance(points[(i + 1) % n]) for i in range(n)]
    total = sum(lengths)
    result = []
    segment = 0
    walked = 0
    for k in range(count):
        target = total * k / count
        while walked + lengths[segment] < target:
            walked += lengths[segment]
            segment += 1
        t = (target - walked) / lengths[segment]
        result.append(points[segment].interpolate_to(points[(segment + 1) % n], t))
    return result


def get_normals(points):
    # Normal = direction pointing to the right side of the track
    normals = []
    n = len(points)
    for i in range(n):
        tangent = (points[(i + 1) % n] - points[i - 1]).normalized()
        normals.append(tangent.perpendicular())
    return normals


def offset_points(points, normals, distance):
    return [p + normal * distance for p, normal in zip(points, normals)]


class Track:
    def __init__(self):
        smooth = smooth_loop(CONTROL_POINTS)
        self.length = sum(smooth[i].get_distance(smooth[(i + 1) % len(smooth)])
                          for i in range(len(smooth)))

        # AI waypoints
        waypoint_count = 3 * round(self.length / 540)
        self.waypoints = resample(smooth, waypoint_count)
        self.waypoint_normals = get_normals(self.waypoints)

        # Checkpoints for every 3rd waypoint stored as (position, direction)
        self.checkpoints = []
        for i in range(0, waypoint_count, 3):
            direction = (self.waypoints[(i + 1) % waypoint_count] - self.waypoints[i - 1]).normalized()
            self.checkpoints.append((self.waypoints[i], direction))

        # Closely spaced points for walls and drawing
        self.center = resample(smooth, round(self.length / 40))
        normals = get_normals(self.center)
        half = TRACK_WIDTH / 2
        self.right_edge = offset_points(self.center, normals, half)
        self.left_edge = offset_points(self.center, normals, -half)
        self.right_kerb = offset_points(self.center, normals, half + 12)
        self.left_kerb = offset_points(self.center, normals, -half - 12)

        self.image = self.draw_image(normals)

    def add_walls(self, space):
        # Static walls along both edges of the track
        for edge in (self.right_edge, self.left_edge):
            for i in range(len(edge)):
                wall = pymunk.Segment(space.static_body, edge[i], edge[(i + 1) % len(edge)], 4)
                wall.elasticity = 0.3
                wall.friction = 0.5
                space.add(wall)

    def draw_image(self, normals):
        image = pygame.Surface((WORLD_W, WORLD_H))
        image.fill(GRASS)

        # Grass texture
        rng = random.Random(1)
        for _ in range(5000):
            image.fill(GRASS_DARK, (rng.randint(0, WORLD_W), rng.randint(0, WORLD_H), 4, 4))

        n = len(self.center)
        for i in range(n):
            j = (i + 1) % n
            # Red and white blocks
            kerb_color = KERB_RED if i % 2 == 0 else KERB_WHITE
            pygame.draw.polygon(image, kerb_color,
                                [self.right_edge[i], self.right_edge[j], self.right_kerb[j], self.right_kerb[i]])
            pygame.draw.polygon(image, kerb_color,
                                [self.left_edge[i], self.left_edge[j], self.left_kerb[j], self.left_kerb[i]])
            # Road
            pygame.draw.polygon(image, ASPHALT,
                                [self.right_edge[i], self.right_edge[j], self.left_edge[j], self.left_edge[i]])
            # Dashed center line
            if i % 2 == 0:
                pygame.draw.line(image, (200, 200, 200), self.center[i], self.center[j], 3)

        self.draw_start_line(image)
        return image

    def draw_start_line(self, image):
        # Start line
        position, direction = self.checkpoints[0]
        side = direction.perpendicular()
        size = TRACK_WIDTH / 10
        for column in range(10):
            for row in range(2):
                color = WHITE if (column + row) % 2 == 0 else BLACK
                start = position + side * (-TRACK_WIDTH / 2 + column * size) + direction * (row * size - size)
                corners = [start, start + side * size, start + side * size + direction * size, start + direction * size]
                pygame.draw.polygon(image, color, corners)
