#!/usr/bin/env python3
"""Extrae de Edadygenero.xlsx la composición etaria por PUESTO de Risaralda
(dep 24, Registraduría) para 2019 Autoridades Locales y 2022 Congreso.
Agrega mesas -> puesto. Salida JSON keyed por `${mun}-${zz}-${pp}` (== llaves
de los *-puestos.json de voto). 10 bandas de edad + sufragantes + sexo.
"""
import openpyxl, json, os, collections, time

BASE="Bases de datos"; SRC=os.path.join(BASE,"Edadygenero.xlsx")
OUT=os.path.join(BASE,"output_edad_risaralda"); os.makedirs(OUT,exist_ok=True)
DEP=24  # Risaralda registraduría
# (año, fragmento tipo) -> nombre salida
TARGETS={(2019,"Autoridades Locales"):"edad-2019-local.json",
         (2022,"Congreso"):"edad-2022-congreso.json"}
BANDS=list(range(12,22))  # 18-20 ... Mayor a 60
BAND_NAMES=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]

def main():
    t0=time.time()
    wb=openpyxl.load_workbook(SRC,read_only=True,data_only=True); ws=wb.active
    hdr=None; agg={k:collections.defaultdict(lambda:{"suf":0,"h":0,"m":0,"bands":[0]*10,"mesas":0}) for k in TARGETS}
    n=0
    for row in ws.iter_rows(values_only=True):
        n+=1
        if hdr is None:
            hdr=list(row)
            i_dep=hdr.index("Cód. Depto"); i_tipo=hdr.index("Datos de tipo de elección"); i_anio=hdr.index("Año")
            i_mun=hdr.index("Cód. Municipio"); i_zz=hdr.index("Cód. Comuna / Localidad"); i_pp=hdr.index("Cód. Puesto de Votación")
            i_suf=hdr.index("Cantidad de Sufragantes"); i_h=hdr.index("Cantidad Hombres"); i_m=hdr.index("Cantidad de Mujeres")
            continue
        if row[i_dep]!=DEP: continue
        t=str(row[i_tipo] or ""); a=row[i_anio]; ay=a.year if hasattr(a,"year") else None
        key=None
        for (yy,frag),fn in TARGETS.items():
            if ay==yy and frag in t: key=(yy,frag); break
        if key is None: continue
        try:
            mun=int(row[i_mun]); zz=int(row[i_zz]); pp=int(row[i_pp])
        except (TypeError,ValueError): continue
        pk=f"{mun}-{zz:02d}-{pp:02d}"
        d=agg[key][pk]
        d["suf"]+=int(row[i_suf] or 0); d["h"]+=int(row[i_h] or 0); d["m"]+=int(row[i_m] or 0); d["mesas"]+=1
        for bi,ci in enumerate(BANDS): d["bands"][bi]+=int(row[ci] or 0)
        if n%150000==0: print(f"  ...{n} ({time.time()-t0:.0f}s)",flush=True)
    wb.close()
    for key,fn in TARGETS.items():
        data={pk:{"suf":v["suf"],"h":v["h"],"m":v["m"],"mesas":v["mesas"],
                  "bands":dict(zip(BAND_NAMES,v["bands"]))} for pk,v in agg[key].items()}
        json.dump({"bandas":BAND_NAMES,"puestos":data}, open(os.path.join(OUT,fn),"w"))
        tot=sum(v["suf"] for v in agg[key].values())
        print(f"{key}: {len(data)} puestos, {tot} sufragantes -> {fn}")
    print(f"filas totales {n} en {time.time()-t0:.0f}s")

if __name__=="__main__": main()
