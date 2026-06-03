import re, os, subprocess, tempfile, sys
SRC=sys.argv[1] if len(sys.argv)>1 else "rrss/instagram/carousel-trasvase-paloma.html"
OUTDIR=sys.argv[2] if len(sys.argv)>2 else "rrss/instagram/trasvase-png"
PREFIX=sys.argv[3] if len(sys.argv)>3 else "trasvase-slide"
os.makedirs(OUTDIR,exist_ok=True)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
html=open(SRC,encoding='utf-8').read()
head=re.search(r"<head>(.*?)</head>",html,re.S).group(1)
sections=re.findall(r"(<section class=\"slide.*?</section>)",html,re.S)
print(f"{len(sections)} slides → {OUTDIR}",file=sys.stderr)
tmpd=tempfile.mkdtemp()
for i,sec in enumerate(sections,1):
    page=f"<!DOCTYPE html><html lang=es><head>{head}</head><body style='margin:0'>{sec}</body></html>"
    fp=os.path.join(tmpd,f"s{i}.html"); open(fp,'w',encoding='utf-8').write(page)
    out=os.path.abspath(os.path.join(OUTDIR,f"{PREFIX}-{i}.png"))
    subprocess.run([CHROME,"--headless=new","--disable-gpu","--hide-scrollbars","--force-device-scale-factor=1",
        "--window-size=1080,1080","--virtual-time-budget=6000",f"--screenshot={out}",f"file://{fp}"],check=True,capture_output=True)
    print(f"  ✓ {PREFIX}-{i}.png",file=sys.stderr)
print("DONE",file=sys.stderr)
