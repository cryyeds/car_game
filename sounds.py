import array
import math
import random
import pygame

SAMPLE_RATE = 22050


def make_tone(frequency, seconds, volume=0.3):
    # Simple beep made from a sine wave that fades out
    samples = array.array("h")
    total = int(SAMPLE_RATE * seconds)
    for i in range(total):
        fade = 1 - i / total
        value = math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)
        samples.append(int(32767 * volume * fade * value))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def make_crash(seconds=0.25, volume=0.4):
    # Crash = random noise that fades out quickly
    samples = array.array("h")
    total = int(SAMPLE_RATE * seconds)
    for i in range(total):
        fade = (1 - i / total) ** 2
        samples.append(int(32767 * volume * fade * random.uniform(-1, 1)))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def load_sounds():
    # Sounds are generated in code, so no audio files are needed
    try:
        pygame.mixer.init(SAMPLE_RATE, -16, 1, 512, allowedchanges=0)
        return {
            "beep": make_tone(440, 0.2),
            "go": make_tone(880, 0.5),
            "crash": make_crash(),
            "finish": make_tone(660, 0.8),
        }
    except pygame.error:
        return {}
