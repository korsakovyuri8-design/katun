#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Страницы для ссылок.

Сайт — одна страница с хеш-маршрутами, а хеш до сервера не доходит: любая
ссылка, отправленная в WhatsApp или Instagram, показывает один и тот же
предпросмотр. Этот скрипт читает каталог прямо из index.html и кладёт рядом
по маленькой странице на каждую вещь и на каждую готовую запись — со своим
заголовком, описанием, картинкой 1200×630 и переходом внутрь сайта.

Запускать после любой правки каталога:  python3 build-share-pages.py
"""

import io, json, os, re, subprocess, sys, html
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://katunheritage.com'
OUT_PAGES = os.path.join(ROOT, 'p')
OUT_CARDS = os.path.join(ROOT, 'share')

CREAM, CARD, INK, MADDER, GREY = '#F7F3ED', '#EBE3D6', '#1A1614', '#7B1612', '#665E58'
SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'
SERIF_B = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
SANS = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
SANS_B = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'


def read_data():
    """Каталог берём из самого сайта, чтобы не держать вторую копию."""
    src = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    lines = src.split('\n')
    i = next(n for n, l in enumerate(lines) if 'const DATA = {' in l)
    j = next(n for n, l in enumerate(lines) if n > i and l == '    };')
    body = '\n'.join(lines[i:j + 1])
    js = body + '\nprocess.stdout.write(JSON.stringify(DATA));'
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit('не удалось прочитать каталог: ' + out.stderr[:400])
    return json.loads(out.stdout)


def fit(draw, text, font_path, max_w, start, min_size=28):
    """Подобрать кегль, чтобы строка влезла в ширину."""
    size = start
    while size > min_size:
        f = ImageFont.truetype(font_path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(font_path, min_size)


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_chart(im, box, rows):
    """Фрагмент орнамента, а не вся схема.

    На сайте схема закрыта до покупки, и в открытой карточке ей тоже не место:
    один увеличенный кусок показывает руку и характер узора, но по нему нельзя
    связать вещь и незачем платить за запись."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    d.rectangle(box, fill=CARD)
    if not rows:
        return
    rows = [str(r) for r in rows]
    cols = max(len(r) for r in rows)
    win_r = min(9, len(rows))
    win_c = min(9, cols)
    r0 = max(0, (len(rows) - win_r) // 2)
    c0 = max(0, (cols - win_c) // 2)
    piece = [r[c0:c0 + win_c] for r in rows[r0:r0 + win_r]]

    cell = min((x1 - x0) / (win_c + 1.6), (y1 - y0) / (win_r + 1.6))
    ox = x0 + ((x1 - x0) - cell * win_c) / 2
    oy = y0 + ((y1 - y0) - cell * win_r) / 2
    for r, row in enumerate(piece):
        for c, ch in enumerate(row):
            if ch == '1':
                d.rectangle([ox + c * cell, oy + r * cell,
                             ox + (c + 1) * cell - 1, oy + (r + 1) * cell - 1], fill=INK)


def make_card(path_out, photo, title, sub, price, chart=None):
    """Карточка 1200×630: слева текст на кремовом, справа фотография или сетка."""
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), CREAM)
    d = ImageDraw.Draw(im)

    photo_w = 470
    if photo and os.path.exists(os.path.join(ROOT, photo)):
        src = ImageOps.exif_transpose(Image.open(os.path.join(ROOT, photo))).convert('RGB')
        im.paste(ImageOps.fit(src, (photo_w, H), Image.LANCZOS, centering=(0.5, 0.4)), (W - photo_w, 0))
    elif chart:
        draw_chart(im, (W - photo_w, 0, W, H), chart)
    else:
        # ни фотографии, ни сетки: текст занимает всю карточку, пустой плашки нет
        photo_w = 0

    x, right = 72, W - photo_w - 72
    d.text((x, 66), 'K A T U N', font=ImageFont.truetype(SERIF_B, 26), fill=MADDER)

    ft = fit(d, title, SERIF_B, right - x, 62, 34)
    lines = wrap(d, title, ft, right - x)[:3]
    y = 168
    for ln in lines:
        d.text((x, y), ln, font=ft, fill=INK)
        y += int(ft.size * 1.18)

    y += 14
    if sub:
        fs = ImageFont.truetype(SANS, 26)
        for ln in wrap(d, sub, fs, right - x)[:2]:
            d.text((x, y), ln, font=fs, fill=GREY)
            y += 34

    if price:
        d.text((x, H - 118), price, font=ImageFont.truetype(SERIF_B, 46), fill=MADDER)

    im.save(path_out, 'JPEG', quality=86, optimize=True, progressive=True)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_esc} · KATUN</title>
<meta name="description" content="{desc_esc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="KATUN">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{desc_esc}">
<meta property="og:image" content="{card}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title_esc}">
<meta name="twitter:description" content="{desc_esc}">
<meta name="twitter:image" content="{card}">
<link rel="icon" type="image/png" href="/favicon.png">
<script>location.replace('/{hash}');</script>
<meta http-equiv="refresh" content="0; url=/{hash}">
<style>
  body {{ margin:0; background:#F7F3ED; color:#1A1614;
         font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .wrap {{ max-width:640px; margin:0 auto; padding:64px 24px; text-align:center; }}
  h1 {{ font-family:'EB Garamond',Georgia,serif; font-weight:500; font-size:34px; margin:0 0 12px; }}
  p {{ color:#665E58; line-height:1.6; }}
  a {{ color:#7B1612; }}
  img {{ max-width:100%; height:auto; margin-bottom:24px; }}
</style>
</head>
<body>
  <div class="wrap">
    <img src="{card_rel}" alt="{title_esc}">
    <h1>{title_esc}</h1>
    <p>{desc_esc}</p>
    <p><a href="/{hash}">Open on katunheritage.com</a></p>
  </div>
</body>
</html>
"""


def main():
    data = read_data()
    os.makedirs(OUT_PAGES, exist_ok=True)
    os.makedirs(OUT_CARDS, exist_ok=True)
    made = []

    for c in data['countries'].values():
        for p in c.get('products') or []:
            if p.get('price') is None:
                continue
            sub = ' · '.join(x for x in [p.get('workshop'), p.get('region'), c.get('name')] if x)
            desc = (p.get('description') or '').strip()
            if not desc or desc.startswith('PLACEHOLDER'):
                desc = 'Made by hand by %s in %s. Shipping included; made to your measurement.' % (
                    p.get('workshop', 'a named maker'), c.get('name', 'the region'))
            card_name = 'share/%s.jpg' % p['id']
            make_card(os.path.join(ROOT, card_name), p.get('photo'), p['title'], sub, '€%s' % p['price'])
            made.append((p['id'], p['title'], desc, card_name, 'item/%s' % p['id'], 'product'))

        for s in c.get('schemes') or []:
            if s.get('price') is None:
                continue
            story = (s.get('originStory') or '').strip()
            if not story or story.startswith('PLACEHOLDER'):
                story = 'An ornament recorded from its source in %s and written down so it can be worked again.' % c.get('name', 'the region')
            sub = ' · '.join(x for x in [s.get('region'), c.get('name')] if x)
            card_name = 'share/%s.jpg' % s['id']
            make_card(os.path.join(ROOT, card_name), None, s['name'], sub,
                      '€%s' % s['price'], chart=s.get('chart'))
            made.append((s['id'], s['name'], story, card_name, 'pattern/%s' % s['id'], 'article'))

    for pid, title, desc, card, route, og_type in made:
        desc1 = re.sub(r'\s+', ' ', desc)
        if len(desc1) > 180:
            # обрезаем по слову, а не посреди него
            desc1 = desc1[:180].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'
        page = PAGE.format(
            title_esc=html.escape(title, quote=True),
            desc_esc=html.escape(desc1, quote=True),
            url='%s/p/%s.html' % (SITE, pid),
            card='%s/%s' % (SITE, card),
            card_rel='/' + card,
            hash='#/' + route,
            og_type=og_type)
        io.open(os.path.join(OUT_PAGES, pid + '.html'), 'w', encoding='utf-8').write(page)

    urls = ['%s/' % SITE] + ['%s/p/%s.html' % (SITE, m[0]) for m in made]
    io.open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join('  <url><loc>%s</loc></url>\n' % u for u in urls)
        + '</urlset>\n')

    io.open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write(
        'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE)

    print('страниц для ссылок: %d' % len(made))
    for m in made:
        print('   /p/%s.html  →  %s' % (m[0], m[1]))
    print('карточек 1200×630: %d  |  sitemap.xml и robots.txt обновлены' % len(made))


if __name__ == '__main__':
    main()
