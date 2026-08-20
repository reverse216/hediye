from collections import deque
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).parent


def clear_edge_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    px = rgba.load()
    width, height = rgba.size
    seen = bytearray(width * height)
    queue = deque()

    def is_background(x: int, y: int) -> bool:
        r, g, b, _ = px[x, y]
        return r > 225 and g > 225 and b > 225 and max(r, g, b) - min(r, g, b) < 18

    for x in range(width):
        if is_background(x, 0):
            queue.append((x, 0))
        if is_background(x, height - 1):
            queue.append((x, height - 1))
    for y in range(height):
        if is_background(0, y):
            queue.append((0, y))
        if is_background(width - 1, y):
            queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        index = y * width + x
        if seen[index] or not is_background(x, y):
            continue
        seen[index] = 1
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        if x:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))
    return rgba


def normalized_sprite(image: Image.Image, size=(96, 128), padding=4) -> Image.Image:
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    if not box:
        raise ValueError("Sprite has no visible pixels")
    sprite = image.crop(box)
    max_width, max_height = size[0] - padding * 2, size[1] - padding * 2
    scale = min(max_width / sprite.width, max_height / sprite.height)
    target = (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale)))
    sprite = sprite.resize(target, Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(sprite, ((size[0] - target[0]) // 2, size[1] - target[1] - padding))
    return canvas


def split_sheet(source: str, names: list[str]) -> None:
    image = clear_edge_background(Image.open(ROOT / source))
    cell_width = image.width / len(names)
    for index, name in enumerate(names):
        left = round(index * cell_width)
        right = round((index + 1) * cell_width)
        cell = image.crop((left, 0, right, image.height))
        normalized_sprite(cell).save(ROOT / name)


def split_delfin() -> None:
    image = Image.open(ROOT / "delfin-anim-v2.png").convert("RGBA")
    boundaries = [0, 410, 1000, 1510, image.width]
    names = ["delfin-idle.png", "delfin-run-1.png", "delfin-run-2.png", "delfin-jump.png"]
    for index, name in enumerate(names):
        cell = image.crop((boundaries[index], 0, boundaries[index + 1], image.height))
        normalized_sprite(cell).save(ROOT / name)


def process_single(source: str, destination: str) -> None:
    image = clear_edge_background(Image.open(ROOT / source))
    normalized_sprite(image).save(ROOT / destination)


def remove_gradient_background(image: Image.Image) -> Image.Image:
    """Remove ImageGen's smooth backdrop while retaining crisp pixel-art edges."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    sample = max(8, min(width, height) // 18)

    def corner(box: tuple[int, int, int, int]) -> tuple[int, int, int]:
        values = ImageStat.Stat(rgb.crop(box)).median
        return tuple(round(value) for value in values)

    top_left = corner((0, 0, sample, sample))
    top_right = corner((width - sample, 0, width, sample))
    bottom_left = corner((0, height - sample, sample, height))
    bottom_right = corner((width - sample, height - sample, width, height))
    backdrop = Image.new("RGB", rgb.size)
    backdrop_pixels = backdrop.load()
    for y in range(height):
        fy = y / max(1, height - 1)
        for x in range(width):
            fx = x / max(1, width - 1)
            backdrop_pixels[x, y] = tuple(
                round(
                    top_left[channel] * (1 - fx) * (1 - fy)
                    + top_right[channel] * fx * (1 - fy)
                    + bottom_left[channel] * (1 - fx) * fy
                    + bottom_right[channel] * fx * fy
                )
                for channel in range(3)
            )
    difference_rgb = ImageChops.difference(rgb, backdrop)
    red_difference, green_difference, blue_difference = difference_rgb.split()
    difference = ImageChops.lighter(red_difference, ImageChops.lighter(green_difference, blue_difference))
    red, green, blue = rgb.split()
    brightness = ImageChops.lighter(red, ImageChops.lighter(green, blue))
    changed = difference.point(lambda value: 255 if value > 34 else 0)
    bright = brightness.point(lambda value: 255 if value > 72 else 0)
    core = ImageChops.multiply(changed, bright)
    alpha = core.filter(ImageFilter.MaxFilter(7))
    result = rgb.convert("RGBA")
    result.putalpha(alpha)
    return result


def split_gifts() -> None:
    sheet = Image.open(ROOT / "gift-set-v2-raw.png")
    width, height = sheet.size
    half = height // 2
    cells = []
    for index in range(4):
        cells.append((round(index * width / 4), 0, round((index + 1) * width / 4), half))
    for index in range(3):
        cells.append((round(index * width / 3), half, round((index + 1) * width / 3), height))
    names = [
        "gift-sweater-v2.png",
        "gift-record-v2.png",
        "gift-surprise-v2.png",
        "gift-perfume-v2.png",
        "gift-photo-v2.png",
        "gift-chocolate-v2.png",
        "gift-hug-v2.png",
    ]
    for box, name in zip(cells, names):
        icon = remove_gradient_background(sheet.crop(box))
        normalized_sprite(icon, size=(96, 96), padding=3).save(ROOT / name)


split_sheet("crush-sprites.png", ["boss-arda.png", "boss-baris.png", "boss-batu.png", "boss-mirac.png", "boss-efe.png"])
split_sheet("extra-boss-sprites.png", ["boss-milan.png", "boss-oguzhan.png"])
split_delfin()
process_single("boss-milan-v2-raw.png", "boss-milan-v2.png")
process_single("boss-oguzhan-v2-raw.png", "boss-oguzhan-v2.png")
split_gifts()
