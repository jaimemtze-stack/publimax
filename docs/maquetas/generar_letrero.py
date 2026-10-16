"""Reemplaza el letrero de la foto por el logotipo de Publimax en letra 3D con luz posterior."""
import sys
import numpy as np
from collections import deque
from PIL import Image, ImageFilter

src, logo_src, out_prefix = sys.argv[1], sys.argv[2], sys.argv[3]
photo = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
H, W = photo.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# --- 1. Borrar el letrero: rellenar la pared con un degradado ajustado + grano ---
ceil = 690 - 0.354 * (xx - 130)          # borde techo / pared
mold = 1003 + 0.05 * xx                   # zoclo de madera
wall = (yy > ceil + 4) & (yy < mold - 4) & (xx >= 128)
purple = (xx < 128) & (yy > 640) & (yy < mold - 4)
lum = photo.mean(axis=2)

def fill(region, clean):
    ys, xs = np.nonzero(clean[::4, ::4]); ys *= 4; xs *= 4
    A = np.c_[xs, ys, np.ones_like(xs)].astype(np.float64)
    out = photo.copy()
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, photo[ys, xs, c], rcond=None)
        plane = coef[0] * xx + coef[1] * yy + coef[2]
        out[..., c] = np.where(region, plane, photo[..., c])
    return out

base = fill(wall, wall & (lum < 32))
photo2 = base
base = fill(purple, purple & (lum < 60) & (yy > 700))
photo2 = np.where(purple[..., None], base, photo2)
rng = np.random.default_rng(7)
grain = rng.normal(0, 2.2, (H, W, 1)).astype(np.float32)
erase = wall | purple
photo2 = np.where(erase[..., None], photo2 + grain, photo2)
# suavizar la costura del borrado
m = Image.fromarray((erase * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
a = np.asarray(m, np.float32)[..., None] / 255
clean_bg = photo * (1 - a) + photo2 * a

# --- 2. Logotipo en alta resolución: máscaras de PUB (azul) y MAX (rojo) ---
L = np.asarray(Image.open(logo_src).convert("RGB")).astype(np.int16)
r, g, b = L[..., 0], L[..., 1], L[..., 2]
navy = (b > r + 40) & (b > 100)
red = (r > 150) & (g < 120) & (b < 120)
ys, xs = np.nonzero(navy | red)
y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
# altura de mayúscula de PUB: filas con mucho azul
rows = navy.sum(axis=1)
cap = np.nonzero(rows > rows.max() * 0.35)[0]
cap_top, cap_base = cap.min(), cap.max()

# --- 3. Homografía: logotipo plano -> pared en perspectiva ---
def top(x): return 548 - 0.19 * (x - 870)
def bot(x): return 800 - 0.105 * (x - 960)
XL, XR = 175, 1440
dst = [(XL, top(XL)), (XR, top(XR)), (XR, bot(XR)), (XL, bot(XL))]
srcp = [(x0, cap_top), (x1, cap_top), (x1, cap_base), (x0, cap_base)]

def homography(p_from, p_to):
    A, B = [], []
    for (x, y), (u, v) in zip(p_from, p_to):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        B += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(B, float))

coef = homography(dst, srcp)  # imagen -> plano (lo que pide PIL)

def warp(mask, offset=(0, 0)):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    w = im.transform((W, H), Image.PERSPECTIVE, tuple(coef), Image.BILINEAR)
    if offset != (0, 0):
        w = w.transform((W, H), Image.AFFINE, (1, 0, -offset[0], 0, 1, -offset[1]), Image.BILINEAR)
    return np.asarray(w, np.float32) / 255

f_navy, f_red = warp(navy), warp(red)
face = np.clip(f_navy + f_red, 0, 1)

# profundidad: el fondo de la letra se ve desplazado hacia abajo a la izquierda,
# y más a la izquierda de la foto (más lejos de la cámara) el desplazamiento crece
depth_steps = 48
def back_offset(t):  # t de 0 a 1
    return (-11 * t, 40 * t)

sides = np.zeros((H, W), np.float32)
side_shade = np.zeros((H, W), np.float32)
face_img = Image.fromarray((face * 255).astype(np.uint8))
for k in range(depth_steps, 0, -1):
    t = k / depth_steps
    dx, dy = back_offset(t)
    s = np.asarray(face_img.transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, -dy), Image.BILINEAR), np.float32) / 255
    newly = s * (1 - sides)
    side_shade += newly * t
    sides = np.maximum(sides, s)
side_only = np.clip(sides - face, 0, 1)
back = np.asarray(face_img.transform((W, H), Image.AFFINE, (1, 0, 11, 0, 1, -40), Image.BILINEAR), np.float32) / 255

# --- 4. Halo de luz blanca sobre la pared ---
bimg = Image.fromarray((back * 255).astype(np.uint8))
ring = np.asarray(bimg.filter(ImageFilter.MaxFilter(9)), np.float32) / 255
core = np.asarray(Image.fromarray((ring * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255
soft = np.asarray(bimg.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(16)), np.float32) / 255
wide = np.asarray(bimg.filter(ImageFilter.GaussianBlur(60)), np.float32) / 255
glow = np.clip(core * 1.7 + soft * 0.95 + wide * 0.4, 0, 1.6)
glow = np.where(back > 0.5, glow * 0.25, glow)  # dentro de la silueta la luz queda tapada
light = np.array([248, 252, 255], np.float32)

img = clean_bg + glow[..., None] * (light - clean_bg) * np.clip(glow, 0, 1)[..., None]
img = np.clip(img, 0, 255)

def render(face_colors, name):
    out = img.copy()
    # cantos (retornos) de aluminio: oscuros al frente, iluminados junto a la pared
    t = np.clip(side_shade, 0, 1)
    sc = 22 + 70 * t ** 3
    side_rgb = np.stack([sc * 0.97, sc * 0.98, sc * 1.0], -1)
    out = out * (1 - side_only[..., None]) + side_rgb * side_only[..., None]
    # caras: color con ligera variación de luz (más claras arriba a la derecha)
    shade = 0.85 + 0.25 * np.clip((xx - 150) / 1300, 0, 1) - 0.12 * np.clip((yy - 450) / 450, 0, 1)
    for mask, col in face_colors:
        c = np.array(col, np.float32) * shade[..., None]
        out = out * (1 - mask[..., None]) + c * mask[..., None]
    # canto superior fino iluminado para dar volumen
    edge = np.clip(face - np.asarray(face_img.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, 2), Image.BILINEAR), np.float32) / 255, 0, 1)
    out = out + edge[..., None] * 40
    out = out + rng.normal(0, 2.0, (H, W, 1)).astype(np.float32) * np.maximum(face, side_only)[..., None]
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    res.save(f"{out_prefix}-{name}.jpg", quality=90)

render([(f_navy, (46, 50, 118)), (f_red, (190, 42, 40))], "colores")
render([(face, (112, 106, 98))], "plata")
