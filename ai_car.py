import math
from car import Car
from settings import *


class AICar(Car):
    def __init__(self, space, position, angle, sprite, name, track, lane_offset, skill):
        super().__init__(space, position, angle, sprite, name)
        self.track = track
        self.lane_offset = lane_offset   # sideways shift so cars dont all use the same line
        self.skill = skill               # 0 to 1, scales the throttle
        self.waypoint_index = 0
        self.stuck_timer = 0.0
        self.reverse_timer = 0.0

    def get_target(self):
        i = self.waypoint_index
        return self.track.waypoints[i] + self.track.waypoint_normals[i] * self.lane_offset

    def think(self, dt):
        # Check next waypoint
        target = self.get_target()
        to_target = target - self.body.position
        if to_target.length < WAYPOINT_RADIUS:
            self.waypoint_index = (self.waypoint_index + 1) % len(self.track.waypoints)
            target = self.get_target()
            to_target = target - self.body.position

        # Steer toward the waypoint (angle 0 = up, so use atan2(x, -y))
        wanted_angle = math.atan2(to_target.x, -to_target.y)
        angle_diff = (wanted_angle - self.body.angle + math.pi) % (2 * math.pi) - math.pi
        self.steer = max(-1, min(1, angle_diff * 2.5))

        # Accelerate but ease off in sharp turns
        self.throttle = self.skill * (1 - 0.5 * min(abs(angle_diff), 1))

        # If stuck against a wall reverse for a moment
        if self.reverse_timer > 0:
            self.reverse_timer -= dt
            self.throttle = -1
            self.steer = -self.steer
        elif self.body.velocity.length < 25:
            self.stuck_timer += dt
            if self.stuck_timer > 1.2:
                self.reverse_timer = 0.8
                self.stuck_timer = 0
        else:
            self.stuck_timer = 0
