#!/usr/bin/env python3
"""
BPCO OOH*PRODUCTION — PWA app icon generator.

The mark is the brand's "*" rendered from Helvetica-metric Liberation Sans Bold,
cropped to its ink box and set in --blue on the opaque --ink field.
Supersampled 4x, downsampled with LANCZOS.

Outputs (opaque, square, full-bleed background — iOS/Android apply their own mask):
  apple-touch-icon.png   180x180
  icon-192.png           192x192
  icon-512.png           512x512
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---- brand palette (index.html :root) ----
INK = (13, 15, 20)        # --ink   #0D0F14
INK_HI = (30, 34, 43)     # lift
BLUE = (37, 78, 219)      # --blue  #254EDB
PAPER = (238, 239, 237)   # --paper #EEEFED

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SS = 4  # supersampling factor


def star_mask(px_height):
    """Asterisk glyph cropped to its ink box, as an L mask of the given height."""
    font = ImageFont.truetype(FONT, 1200)
    big = Image.new("L", (1600, 1600), 0)
    ImageDraw.Draw(big).text((200, 1000), "*", font=font, fill=255, anchor="ls")
    bbox = big.getbbox()
    glyph = big.crop(bbox)
    w = round(px_height * glyph.width / glyph.height)
    return glyph.resize((w, px_height), Image.LANCZOS)


def build(size, lockup=False, star_ratio=0.60, bg=INK, mark=BLUE):
    S = size * SS
    base = Image.new("RGB", (S, S), bg)

    # faint radial lift for depth — background stays fully opaque
    lift = Image.new("L", (S, S), 0)
    ImageDraw.Draw(lift).ellipse(
        [-S * 0.20, -S * 0.42, S * 1.20, S * 1.02], fill=30
    )
    lift = lift.filter(ImageFilter.GaussianBlur(S * 0.10))
    img = Image.composite(Image.new("RGB", (S, S), INK_HI), base, lift)

    if lockup:
        sh = int(S * 0.40)
        cy = int(S * 0.455)
    else:
        sh = int(S * star_ratio)
        cy = int(S * 0.5)

    star = star_mask(sh)
    sx, sy = S // 2 - star.width // 2, cy - star.height // 2
    img.paste(Image.new("RGB", star.size, mark), (sx, sy), star)

    d = ImageDraw.Draw(img)

    if lockup:
        fsize = int(S * 0.105)
        font = ImageFont.truetype(FONT, fsize)
        txt, track = "BPCO", fsize * 0.34
        widths = [d.textlength(c, font=font) for c in txt]
        total = sum(widths) + track * (len(txt) - 1)
        x = S / 2 - total / 2
        y = int(S * 0.775)
        for c, w in zip(txt, widths):
            d.text((x, y), c, font=font, fill=PAPER)
            x += w + track
        # pixel-width alignment fix for fractional start
        d.rectangle([0, 0, 0, 0])

    return img.resize((size, size), Image.LANCZOS)


def make_all(outdir=OUT, **kw):
    for name, px in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
        build(px, **kw).save(os.path.join(outdir, name), optimize=True)


if __name__ == "__main__":
    if "--preview" in sys.argv:
        build(512).save(os.path.join(HERE, "d_glyph.png"))
        build(512, lockup=True).save(os.path.join(HERE, "e_lockup.png"))
        build(512, star_ratio=0.52).save(os.path.join(HERE, "f_glyph_small.png"))
        # how it reads at home-screen size
        strip = Image.new("RGB", (900, 360), (210, 213, 218))
        for i, k in enumerate((180, 120, 60)):
            im = build(k)
            strip.paste(im, (100 + i * 230, 60))
        strip.save(os.path.join(HERE, "g_homescreen.png"))
        print("previews written")
    else:
        make_all()
        print("icons written")
