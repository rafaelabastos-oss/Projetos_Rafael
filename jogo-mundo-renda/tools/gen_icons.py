#!/usr/bin/env python3
"""Gera os ícones do app Mundo Renda (legado + adaptativo) com Pillow, sem imagens externas."""
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'android', 'res')
S = 1024  # tela de desenho (supersample)

FONT_CANDIDATES = [
    '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
]


def font(size):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def art(scale=1.0):
    """Desenho principal: ladrilho isométrico com casa, broto e moeda."""
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def P(x, y):
        return (512 + (x - 512) * scale, 512 + (y - 512) * scale)

    def poly(pts, fill):
        d.polygon([P(*p) for p in pts], fill=fill)

    # sombra suave do terreno
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([P(222, 640), P(512, 495), P(802, 640), P(512, 800)], fill=(0, 0, 0, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18 * scale)))

    # terreno
    poly([(212, 600), (512, 750), (512, 800), (212, 650)], '#4f9a3f')
    poly([(512, 750), (812, 600), (812, 650), (512, 800)], '#3a7f33')
    poly([(212, 600), (512, 450), (812, 600), (512, 750)], '#8fe07a')
    poly([(262, 600), (512, 475), (762, 600), (512, 725)], '#9ce887')
    # estradinha
    poly([(470, 729), (712, 608), (742, 623), (500, 744)], '#d9b77f')

    # casa
    poly([(330, 600), (430, 650), (430, 525), (330, 475)], '#fff3dc')
    poly([(430, 650), (530, 600), (530, 475), (430, 525)], '#e2cba3')
    poly([(330, 475), (430, 525), (430, 365)], '#f26b3a')
    poly([(430, 525), (530, 475), (430, 365)], '#c4492a')
    poly([(468, 637), (500, 621), (500, 560), (468, 576)], '#7a4f2e')
    poly([(352, 560), (400, 584), (400, 548), (352, 524)], '#5a86ad')
    poly([(352, 524), (400, 548), (400, 538), (352, 514)], '#86aed0')

    # broto
    d.line([P(640, 640), P(640, 560)], fill='#2f8f3a', width=int(16 * scale))
    leafL = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(leafL).ellipse([P(540, 500), P(640, 560)], fill='#45c24f')
    leafL = leafL.rotate(-25, center=P(640, 560))
    leafR = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(leafR).ellipse([P(640, 470), P(760, 540)], fill='#6ad65a')
    leafR = leafR.rotate(28, center=P(640, 540))
    im.alpha_composite(leafL)
    im.alpha_composite(leafR)

    # moeda
    cx, cy, r = 700, 340, 118
    sh2 = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh2).ellipse([P(cx - r + 10, cy - r + 16), P(cx + r + 10, cy + r + 16)], fill=(0, 0, 0, 80))
    im.alpha_composite(sh2.filter(ImageFilter.GaussianBlur(10 * scale)))
    d = ImageDraw.Draw(im)
    d.ellipse([P(cx - r, cy - r), P(cx + r, cy + r)], fill='#e09a12')
    d.ellipse([P(cx - r + 14, cy - r + 14), P(cx + r - 14, cy + r - 14)], fill='#ffcb45')
    d.ellipse([P(cx - r + 30, cy - r + 30), P(cx + r - 30, cy + r - 30)], outline='#f0ad1c', width=int(6 * scale))
    f = font(int(96 * scale))
    d.text(P(cx, cy + 4), 'R$', font=f, fill='#7a4a00', anchor='mm')
    return im


def legacy():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bg = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(bg)
    for y in range(S):
        t = y / S
        c = (int(46 + (20 - 46) * t), int(170 + (104 - 170) * t), int(110 + (70 - 110) * t), 255)
        g.line([(0, y), (S, y)], fill=c)
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=220, fill=255)
    im.paste(bg, (0, 0), mask)
    im.alpha_composite(art(1.0))
    return im


def foreground():
    return art(0.72)


def save(img, path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.resize((size, size), Image.LANCZOS).save(path, optimize=True)


def main():
    dens = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
    leg, fg = legacy(), foreground()
    for name, m in dens.items():
        save(leg, os.path.join(RES, 'mipmap-' + name, 'ic_launcher.png'), int(48 * m))
        save(fg, os.path.join(RES, 'mipmap-' + name, 'ic_launcher_foreground.png'), int(108 * m))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'dist', 'icone-512.png')
    save(leg, out, 512)
    print('ícones gerados em', RES)


if __name__ == '__main__':
    main()
