## Made By
  - Jose Gonzalez
  - William Hale
    
## Original idea

We wanted to make a racing game for our CS project that feels like a real game
but is still small enough to understand completely. I picked a top-down racer with 8 cars on the track, because then I could
focus on the code and not on 3D graphics.

## Goals

- 1 player + 7 AI cars racing at the same time
- 3 laps, with checkpoints so nobody can skip parts of the track
- Race position (1st to 8th), countdown, HUD and results screen
- Arcade-style driving that is fun, not realistic
- Menus, pause menu, a car customization screen and customizable driving keys
- Code that is simple enough that I can explain every part

## Technologies

- **Python** for everything.
- **Pygame** (I used `pygame-ce`, which works the same but installs on newer
  Python versions) for the window, drawing, keyboard/mouse input, fonts,
  sounds and the game loop.
- **Pymunk** for the physics of the cars and the walls.

### Why Pygame?

Pygame is simple and I already know the basic loop: handle events, update,
draw. It can draw pixel-art by scaling up tiny surfaces, and it can do menus
and sound without extra libraries.

### Why Pymunk?

Pygame does not have physics. I could have written my own collision code, but
car-vs-car and car-vs-wall collisions with bouncing and spinning are hard to
get right. Pymunk (a 2D physics engine) does this for me. I give each car a
body and a shape and Pymunk handles the collisions.

## File structure

`main.py` | Starts the game 
`settings.py` | Constants (screen size, laps, physics numbers, colors, default keys) 
`game.py` | The `Game` class: main loop, game states, race setup, HUD, results 
`car.py` | Pixel-art car sprites and the `Car` class (physics + lap progress) 
`ai_car.py` | `AICar`, a `Car` that steers itself using waypoints 
`track.py` | Builds the track shape, walls, waypoints, checkpoints and the track picture 
`menu.py` | `Menu` buttons, the customize screen and the controls (key binding) screen 
`sounds.py` | Makes the beep/crash sounds in code 

The only inheritance is `AICar(Car)`. A `Car` has `throttle` and `steer`
values. The player sets them from the keyboard (using the key bindings), the AI sets them from its
waypoint code. After that both use the exact same physics.

The game uses a simple `state` string in `Game`: `"menu"`, `"customize"`,
`"controls"`, `"race"`, `"paused"` and `"results"`. Events, update and draw
all check this state.

## How car movement works

Each frame, `Car.apply_forces()` does this:

1. Find the direction the car is facing (`forward`) and the sideways direction (`right`).
2. If the player holds up, push the car forward with an engine force.
3. If the player holds down: brake if still moving forward, otherwise push backwards (reverse).
4. Add drag (a force against the velocity).
5. Add tire grip (a force against sideways sliding).
6. Turn the car by changing its angular velocity.

Angle 0 means the car faces up the screen and a bigger angle turns clockwise,
which matches how Pygame rotates the sprite.

## How the physics works

Every car is a Pymunk `Body` (mass 1) with a box-shaped `Poly`. I apply forces
and let `space.step()` move the cars. A few ideas make it arcade-like:

- **Top speed comes from drag.** The engine force is constant but drag grows
  with speed. At some point they are equal and the car stops speeding up
  (around 430 pixels/second).
- **Grip.** A real car does not slide sideways much. I measure how fast the car
  moves sideways (`velocity.dot(right)`) and push against it. A low grip number
  gives drifting, a high one makes the car feel on rails. I settled on 6.
- **Steering.** The car turns faster when it is moving. When it is not moving
  it cannot turn. When reversing the steering flips, like a real car. I do not
  set the angle directly, I move the angular velocity toward the wanted
  value, so a crash can still make the car spin a bit.
- Physics runs 2 steps per frame to keep collisions stable.

## How collisions work

- The track edges are lots of short static `Segment` shapes (about 360 of them)
  following the left and right edges of the road.
- Cars are boxes with slightly rounded corners, so they bounce off walls and
  each other. Pymunk calculates the bounce, friction and spinning.
- For the effects I just look at the speed: if a car loses more than 100
  pixels/second in a single frame it must have hit something, so I spawn
  sparks (and play a crash sound for the player). This was easier than
  using Pymunk collision callbacks.
- Cars also leave dark skid marks on the track picture when they slide sideways.

## The track

In `track.py` I wrote about 18 rough points around the map. A Catmull-Rom spline
turns those into a smooth loop. From that loop I make:

- **Waypoints** (about every 180 pixels) for the AI.
- **Checkpoints** (every 3rd waypoint, so about 540 pixels apart).
- **Closely spaced points** (every 40 pixels). I move them left and right
  by half the track width to get the two edges. The edges are used to draw the road,
  kerbs and to build the walls, so what you see is what you hit.

The track picture is drawn once into one big surface. The camera just shows
the part around the player.

## How the AI works

Each AI car does this every frame (`AICar.think`):

1. Target = the current waypoint, shifted sideways a bit (each car has its own
   random lane offset so they don't all drive in a line).
2. If the car is closer than 110 pixels to the target, switch to the next waypoint.
3. Work out the angle to the target. The difference between that angle and the
   car's angle decides the steering (`steer = angle_difference * 2.5`, limited to -1..1).
4. Throttle is full but goes down in sharp turns. Every AI has a `skill`
   number (0.85 to 0.98) that limits its throttle so some cars are slower.
5. If the car is almost not moving for 1.2 seconds, it reverses for 0.8
   seconds (this fixes getting stuck on a wall or another car).

There is no machine learning or path finding, just "aim at the next point".

## Checkpoints and laps

Each checkpoint has a position and a direction along the track. A car passes its
*next* checkpoint when it is closer than 110 pixels *and* it is in front of the
checkpoint's line (`offset.dot(direction) >= 0`). Because cars must pass the
checkpoints in order, they cannot skip a part of the track.

Checkpoint 0 is the start/finish line. The cars start behind it, so the first
time they cross it does not count as a lap. After that, each time a car passes
checkpoint 0 again, one lap is finished:

`laps_done = (checkpoints_passed - 1) // number_of_checkpoints`

When `laps_done` reaches 3 the car gets its `finish_time`.

## Race position calculation

Every car has a `score`:

`score = checkpoints_passed * 10000 - distance_to_next_checkpoint`

More checkpoints means further ahead. If two cars have passed the same number,
the one that is closer to the next checkpoint is ahead. Cars that finished are
sorted first by finish time, and then everybody else by score. I sort the 8 cars
every frame and the player's place is the index in that list plus one.

## Customization system

The car pictures are tiny text maps in `car.py`, 9x15 characters
(`B` = body, `W` = window, `K` = tire, and so on). `make_car_sprite()` goes
through the characters and draws each pixel on a small surface, then scales
it up 3x so it looks like pixel-art. Because the colors are looked up when
building, recoloring is just changing one value.

The player can change four things: **body shape** (3 options), **car color**
(10), **pattern** (6: none, center stripe, twin stripes, checkers, spots, side
stripes) and **pattern color**. A pattern is a small function that says
whether a body pixel gets the pattern color. The settings are stored in
the `style` dictionary in `Game` and the customize screen shows a big live
preview. AI cars use the same function with random options (and never the same
color as the player). The choice is kept while the game is open but it is not
saved to a file.

## Customizable controls

The driving keys are stored in a dictionary in `Game`, for example
`{"accelerate": [K_UP, K_w], ...}`. Every action has two keys, which is why
the arrows and WASD both work by default. The defaults are in `settings.py`.

Each frame `get_player_input()` checks if any key of an action is held down:
`throttle = accelerate - brake` and `steer = right - left`, so the rest of the
car code did not need to change.

The Controls screen (`ControlsScreen` in `menu.py`) shows a grid of 4 actions
x 2 keys. You select a box, press Enter, and the next key you press becomes the
new binding (Esc cancels). If that key was already used by another action, the
two keys are swapped so no key ends up doing two things and no action loses
all its keys. R resets everything to the defaults. The dictionary is shared
with the screen, so changes work in the next race right away. I kept Esc
(pause) and the menu keys fixed, so you can never lock yourself out of the
menus. The bindings are not saved to a file.

## Problems and how we solved them

- *Pygame would not install* The normal `pygame` failed to install on our
  Python 3.14. I switched to `pygame-ce`, which has the same `import pygame`.
- *Rotation direction* Our first idea of "angle" did not match Pygame's rotation.
  I decided that angle 0 is up and bigger angle = clockwise, then used
  `Vec2d(0, -1).rotated(angle)` for the forward direction and `-degrees(angle)` for
  drawing the sprite.
- *Cars sliding like on ice.* At first the cars kept moving in their old
  direction when they turned. Adding the sideways grip force fixed this.
- *Knowing which car is ahead.* Just using distance on the track was
  confusing at the start line, so I used the checkpoint counting score above.
- *Pause menu remembered the old button.* After pressing "Restart Race"
  and pausing again the cursor was still on the old option. I now reset the
  selected button when the pause/results menu opens.
- *AI getting stuck.* Cars sometimes touched a wall or each other and stopped,
  so I added the small reverse timer.
- *Two actions on one key.* When rebinding, a key could end up used twice. I
  fixed it by swapping keys when there is a conflict.

## Testing and debugging

I tested in two ways:

- Playing the game and watching how the cars behave.
- Running the game without a window (headless) with a script that drove the player car
  with the AI code. All 8 cars finished 3 laps in about 60 seconds, lap
  checkpoints and positions updated correctly, and the results screen appeared.
  We also checked that accelerating, steering right (angle goes up), braking and reversing
  all work, and we pressed through every menu (main, customize, controls, pause,
  results, restart).
- We also tested the key rebinding with a script: rebinding a key, swapping on a
  conflict, reading the new keys in `get_player_input()`, and the reset.
- We drew screenshots of the track and the menus to check how they look.
  Looking at the track picture helped me see that the shape was not
  too tight for the walls.

## What we learned

- How a game loop works with several states (menu, race, pause, results).
- That a physics engine is great for collisions but I still have to design the
  "feel" myself with forces, drag and grip.
- Simple AI (aim at the next point) can already look like racing.
- How to split a project into small files so that every file has one job.

## Future improvements

- More tracks and a track selection menu
- Save the car style, key bindings and best lap times to a file
- Smarter AI (look ahead for corners, avoid other cars, difficulty levels)
- Pickups or boosts, and engine sounds
- A minimap and a "wrong way" warning
- Let the race keep going until all cars finish
