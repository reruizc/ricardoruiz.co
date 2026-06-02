import re, os, subprocess, tempfile, sys
SRC="rrss/instagram/carousel-trasvase-paloma.html"
OUTDIR="rrss/instagram/trasvase-png"; os.makedirs(OUTDIR,exist_ok=True)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
html=open(SRC,encoding='utf-8').read()
head=re.search(r"<head>(.*?)</head>",html,re.S).group(1)
sections=re.findall(r"(<section class=\"slide.*?</section>)",html,re.S)
print(f"{len(sections)} slides",file=sys.stderr)
tmpd=tempfile.mkdtemp()
for i,sec in enumerate(sections,1):
    page=f"<!DOCTYPE html><html lang=es><head>{head}</head><body style='margin:0'>{sec}</body></html>"
    fp=os.path.join(tmpd,f"s{i}.html"); open(fp,'w',encoding='utf-8').write(page)
    out=os.path.abspath(os.path.join(OUTDIR,f"trasvase-slide-{i}.png"))
    subprocess.run([CHROME,"--headless=new","--disable-gpu","--hide-scrollbars",
        "--force-device-scale-factor=1","--window-size=1080,1080",
        "--virtual-time-budget=6000",f"--screenshot={out}",f"file://{fp}"],
        check=True,capture_output=True)
    print(f"  ✓ trasvase-slide-{i}.png",file=sys.stderr)
print("DONE",file=sys.stderr)
