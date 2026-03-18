"""Скачать холст и сохранить как PPM-изображение.

Использование:
    python examples/board_to_ppm.py out.ppm
"""
import sys
from itd import ITDClient
from itd.client import PIXEL_COLORS

COOKIES = input()
WIDTH = 1024
HEIGHT = 1024


def color_hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


RGB_PALETTE = [color_hex_to_rgb(c) for c in PIXEL_COLORS]


def board_to_ppm(data: bytes, path: str) -> None:
    with open(path, 'wb') as f:
        f.write(f'P6\n{WIDTH} {HEIGHT}\n255\n'.encode())
        for byte in data:
            rgb = RGB_PALETTE[byte] if byte < len(RGB_PALETTE) else (255, 0, 255)
            f.write(bytes(rgb))
    print(f'Сохранено: {path}  ({WIDTH}x{HEIGHT})')


if __name__ == '__main__':
    output = sys.argv[1] if len(sys.argv) > 1 else 'board.ppm'
    client = ITDClient(cookies=COOKIES)
    print('Загрузка холста...')
    data = client.get_board()
    board_to_ppm(data, output)
