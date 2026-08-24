#!/usr/bin/env python3
# Versiones LinkedIn de 3 gráficos clave: añade barra de marca Ricardo.Ruiz + crédito
# (SIN watermark confidencial — estas imágenes son públicas). -> rrss/linkedin/
from PIL import Image, ImageDraw, ImageFont
import os
G='Bases de datos/output_2v/graficos'; OUT='rrss/linkedin'; os.makedirs(OUT,exist_ok=True)
PAPER=(244,241,234); MUT=(107,98,88); LINE=(216,208,196)
logo=Image.open('Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png').convert('RGBA')
fr=ImageFont.truetype('tools/pacto-1v-2026/fonts/Inter-Regular.ttf',19)
CHARTS=[('g_estrategias','1-tres-estrategias'),('g_margen_depto','2-antioquia-decide'),('g_trasvases','3-trasvases')]
for ch,name in CHARTS:
    im=Image.open(f'{G}/{ch}.png').convert('RGB'); w,h=im.size
    bar=64; out=Image.new('RGB',(w,h+bar),PAPER); out.paste(im,(0,0))
    d=ImageDraw.Draw(out)
    d.line([(28,h+9),(w-28,h+9)],fill=LINE,width=1)
    lw=180; lh=round(lw*logo.height/logo.width); lg=logo.resize((lw,lh))
    out.paste(lg,(w-lw-28,h+(bar-lh)//2+5),lg)
    d.text((28,h+bar//2+3),'Preconteo 2ª vuelta presidencial · 21 jun 2026 · cifras no oficiales',font=fr,fill=MUT,anchor='lm')
    out.save(f'{OUT}/{name}.png'); print('->',f'{OUT}/{name}.png',out.size)
