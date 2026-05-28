from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path('/Users/catking/Desktop/Github/catking01/profile-dino-contrib')
SPRITE_PATH = ROOT / '100-offline-sprite.png'
OUT_LIGHT = ROOT / 'dino-runner.gif'
OUT_DARK = ROOT / 'dino-runner-dark.gif'

W, H = 800, 200
FPS = 20
DURATION_S = 60
FRAMES = FPS * DURATION_S
DT = 1.0 / FPS

GROUND_LINE_Y = 176
GROUND_SURFACE_Y = 175
DINO_X = 80
SCALE = 1
SPEED = 175.0
GRAVITY = 1800.0
JUMP_V0 = 760.0
JUMP_TRIGGER = 230
DUCK_TRIGGER = 170


@dataclass
class Obstacle:
  kind: str
  x: float
  y_bottom: int
  w: int
  h: int


class DinoState:
  def __init__(self) -> None:
    self.y = 0.0
    self.vy = 0.0
    self.jumping = False
    self.ducking = False

  def start_jump(self) -> None:
    if not self.jumping:
      self.jumping = True
      self.vy = JUMP_V0
      self.ducking = False

  def update(self, dt: float) -> None:
    if self.jumping:
      self.y += self.vy * dt
      self.vy -= GRAVITY * dt
      if self.y <= 0:
        self.y = 0
        self.vy = 0
        self.jumping = False


def crop(sheet: Image.Image, x: int, y: int, w: int, h: int) -> Image.Image:
  return sheet.crop((x, y, x + w, y + h)).convert('RGBA')


def tint_rgba(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
  r, g, b = rgb
  pix = img.load()
  out = img.copy()
  out_px = out.load()
  for yy in range(out.height):
    for xx in range(out.width):
      _, _, _, a = pix[xx, yy]
      if a:
        out_px[xx, yy] = (r, g, b, a)
  return out


def build_assets(theme: str) -> dict[str, list[Image.Image] | Image.Image]:
  sheet = Image.open(SPRITE_PATH).convert('RGBA')

  assets = {
    'cloud': crop(sheet, 86, 2, 46, 14),
    'horizon': crop(sheet, 2, 54, 600, 12),
    'cactus_small': [crop(sheet, 228, 2, 17, 35)],
    'cactus_large': [crop(sheet, 332, 2, 25, 50)],
    'bird': [crop(sheet, 134, 2, 46, 40), crop(sheet, 180, 2, 46, 40)],
    'dino_run': [crop(sheet, 936, 2, 44, 47), crop(sheet, 980, 2, 44, 47)],
    'dino_jump': [crop(sheet, 848, 2, 44, 47)],
    'dino_duck': [crop(sheet, 1112, 2, 59, 25), crop(sheet, 1171, 2, 59, 25)],
    'digits': [crop(sheet, 655 + i * 10, 2, 10, 13) for i in range(12)],
  }

  if theme == 'dark':
    for key, val in list(assets.items()):
      if isinstance(val, list):
        assets[key] = [tint_rgba(v, (139, 148, 158)) for v in val]
      else:
        assets[key] = tint_rgba(val, (139, 148, 158))

  # scale everything once for speed.
  for key, val in list(assets.items()):
    if isinstance(val, list):
      assets[key] = [v.resize((v.width * SCALE, v.height * SCALE), Image.NEAREST) for v in val]
    else:
      assets[key] = val.resize((val.width * SCALE, val.height * SCALE), Image.NEAREST)

  return assets


def obstacle_schedule(seed: int = 20260528) -> list[Obstacle]:
  rng = random.Random(seed)
  obstacles: list[Obstacle] = []

  x = W + 120
  while x < W + SPEED * DURATION_S + 600:
    k = rng.random()
    if k < 0.40:
      kind = 'cactus_small'
      w, h = 17 * SCALE, 35 * SCALE
      y_bottom = GROUND_SURFACE_Y
      min_gap = 280
      max_gap = 420
    elif k < 0.75:
      kind = 'cactus_large'
      w, h = 25 * SCALE, 50 * SCALE
      y_bottom = GROUND_SURFACE_Y
      min_gap = 300
      max_gap = 460
    else:
      kind = 'bird'
      w, h = 46 * SCALE, 40 * SCALE
      if rng.random() < 0.8:
        # low bird -> duck
        y_bottom = GROUND_SURFACE_Y - 30
      else:
        # mid bird, still duck-safe
        y_bottom = GROUND_SURFACE_Y - 40
      min_gap = 360
      max_gap = 540

    obstacles.append(Obstacle(kind=kind, x=x, y_bottom=y_bottom, w=w, h=h))
    x += rng.randint(min_gap, max_gap)

  return obstacles


def score_value(distance_px: float) -> int:
  return max(0, int(round(distance_px * 0.025)))


def draw_score(img: Image.Image, assets: dict, score: int, hi: int) -> None:
  digits = assets['digits']
  assert isinstance(digits, list)
  # digits indices 0..9, H=10, I=11
  hi_text = ['H', 'I'] + list(f'{hi:05d}')
  sc_text = list(f'{score:05d}')

  x0 = 626
  y0 = 16

  for i, ch in enumerate(hi_text):
    idx = 10 if ch == 'H' else 11 if ch == 'I' else int(ch)
    img.alpha_composite(digits[idx], (x0 + i * 11, y0))

  x1 = 705
  for i, ch in enumerate(sc_text):
    img.alpha_composite(digits[int(ch)], (x1 + i * 11, y0))


def bbox_intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
  ax1, ay1, ax2, ay2 = a
  bx1, by1, bx2, by2 = b
  return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def simulate_and_render(theme: str, out_path: Path) -> None:
  assets = build_assets(theme)
  obstacles = obstacle_schedule()
  dino = DinoState()
  frames: list[Image.Image] = []

  bg = (255, 255, 255, 255) if theme == 'light' else (13, 17, 23, 255)
  line = (83, 83, 83, 255) if theme == 'light' else (139, 148, 158, 255)

  cloud0 = 780.0
  cloud1 = 980.0

  total_distance = 0.0
  hi = 420
  collisions = 0

  for fi in range(FRAMES):
    t = fi * DT

    # choose action from nearest obstacle
    dino.ducking = False
    nearest = None
    for ob in obstacles:
      if ob.x + ob.w >= DINO_X - 10:
        nearest = ob
        break

    if nearest is not None:
      dx = nearest.x - DINO_X
      is_bird = nearest.kind == 'bird'
      bird_low = is_bird and nearest.y_bottom >= GROUND_SURFACE_Y - 14
      need_duck = bird_low and (0 < dx < DUCK_TRIGGER)
      need_jump = (not bird_low) and (0 < dx < JUMP_TRIGGER)

      if need_jump:
        dino.start_jump()
      if need_duck and not dino.jumping:
        dino.ducking = True

    dino.update(DT)

    # move world
    step = SPEED * DT
    total_distance += step
    for ob in obstacles:
      ob.x -= step

    # render
    frame = Image.new('RGBA', (W, H), bg)
    draw = ImageDraw.Draw(frame)

    # clouds
    cloud = assets['cloud']
    assert isinstance(cloud, Image.Image)
    cloud0 -= 24 * DT
    cloud1 -= 18 * DT
    if cloud0 < -cloud.width:
      cloud0 = W + 120
    if cloud1 < -cloud.width:
      cloud1 = W + 260
    frame.alpha_composite(cloud, (int(cloud0), 36))
    frame.alpha_composite(cloud, (int(cloud1), 60))

    # horizon line strips
    hz = assets['horizon']
    assert isinstance(hz, Image.Image)
    offset = int((total_distance * 0.95) % hz.width)
    frame.alpha_composite(hz, (30 - offset, 152))
    frame.alpha_composite(hz, (30 - offset + hz.width, 152))
    frame.alpha_composite(hz, (30 - offset + hz.width * 2, 152))

    # ground rule
    draw.line((30, GROUND_LINE_Y, 770, GROUND_LINE_Y), fill=line, width=1)

    # obstacles
    for ob in obstacles:
      if ob.x > W + 20 or ob.x + ob.w < -20:
        continue
      if ob.kind == 'bird':
        bird = assets['bird']
        assert isinstance(bird, list)
        spr = bird[(fi // 3) % 2]
      else:
        spr_list = assets[ob.kind]
        assert isinstance(spr_list, list)
        spr = spr_list[0]
      frame.alpha_composite(spr, (int(ob.x), int(ob.y_bottom - ob.h)))

    # dino sprite
    if dino.jumping:
      ds = assets['dino_jump']
      assert isinstance(ds, list)
      spr = ds[0]
      dy = int(GROUND_SURFACE_Y - 47 * SCALE - dino.y)
    elif dino.ducking:
      ds = assets['dino_duck']
      assert isinstance(ds, list)
      spr = ds[(fi // 3) % 2]
      dy = int(GROUND_SURFACE_Y - 25 * SCALE)
    else:
      ds = assets['dino_run']
      assert isinstance(ds, list)
      spr = ds[(fi // 2) % 2]
      dy = int(GROUND_SURFACE_Y - 47 * SCALE)

    frame.alpha_composite(spr, (DINO_X, dy))

    # coarse collision audit
    if dino.ducking:
      dbox = (DINO_X + 8, dy + 15, DINO_X + 50, dy + 24)
    else:
      dbox = (DINO_X + 10, dy + 8, DINO_X + 31, dy + 39)

    for ob in obstacles:
      if ob.x > DINO_X + 140 or ob.x + ob.w < DINO_X:
        continue
      obox = (int(ob.x) + 6, int(ob.y_bottom - ob.h) + 6, int(ob.x + ob.w) - 6, int(ob.y_bottom) - 4)
      if bbox_intersects(dbox, obox):
        collisions += 1

    # score
    score = score_value(total_distance)
    draw_score(frame, assets, score=score, hi=hi)

    frames.append(frame.convert('P', palette=Image.ADAPTIVE, colors=255))

  if collisions:
    print(f'[{theme}] collision boxes overlap count: {collisions}')
  else:
    print(f'[{theme}] collision boxes overlap count: 0')

  frames[0].save(
    out_path,
    save_all=True,
    append_images=frames[1:],
    duration=int(1000 / FPS),
    loop=0,
    optimize=True,
    disposal=2,
  )
  print(f'[{theme}] wrote {out_path}')


def main() -> None:
  simulate_and_render('light', OUT_LIGHT)
  simulate_and_render('dark', OUT_DARK)


if __name__ == '__main__':
  main()
