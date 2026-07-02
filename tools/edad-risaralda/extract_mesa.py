#!/usr/bin/env python3
"""Edad por MESA (no puesto) para Risaralda, 2019 local + 2022 congreso.
Clave `${mun}-${zz}-${pp}-${mesa}`. Para el método de efectos fijos de puesto."""
import openpyxl, json, os, collections, time
BASE="Bases de datos"; SRC=os.path.join(BASE,"Edadygenero.xlsx")
OUT=os.path.join(BASE,"output_edad_risaralda"); os.makedirs(OUT,exist_ok=True)
DEP=24
TARGETS={(2019,"Autoridades Locales"):"edad-2019-local-mesa.json",(2022,"Congreso"):"edad-2022-congreso-mesa.json"}
BANDS=list(range(12,22)); BN=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]
def main():
    t0=time.time(); wb=openpyxl.load_workbook(SRC,read_only=True,data_only=True); ws=wb.active
    hdr=None; agg={k:{} for k in TARGETS}; n=0
    for row in ws.iter_rows(values_only=True):
        n+=1
        if hdr is None:
            hdr=list(row); i_dep=hdr.index("Cód. Depto"); i_tipo=hdr.index("Datos de tipo de elección"); i_anio=hdr.index("Año")
            i_mun=hdr.index("Cód. Municipio"); i_zz=hdr.index("Cód. Comuna / Localidad"); i_pp=hdr.index("Cód. Puesto de Votación")
            i_ms=hdr.index("Mesa"); i_suf=hdr.index("Cantidad de Sufragantes"); continue
        if row[i_dep]!=DEP: continue
        t=str(row[i_tipo] or ""); a=row[i_anio]; ay=a.year if hasattr(a,"year") else None
        key=None
        for (yy,frag) in TARGETS:
            if ay==yy and frag in t: key=(yy,frag); break
        if key is None: continue
        try: mun=int(row[i_mun]); zz=int(row[i_zz]); pp=int(row[i_pp]); ms=int(row[i_ms])
        except (TypeError,ValueError): continue
        mk=f"{mun}-{zz:02d}-{pp:02d}-{ms:03d}"
        bands=[int(row[ci] or 0) for ci in BANDS]
        agg[key][mk]={"suf":int(row[i_suf] or 0),"bands":dict(zip(BN,bands)),"pcode":f"{mun}-{zz:02d}-{pp:02d}","mesa":ms}
    wb.close()
    for key,fn in TARGETS.items():
        json.dump({"bandas":BN,"mesas":agg[key]}, open(os.path.join(OUT,fn),"w"))
        print(f"{key}: {len(agg[key])} mesas -> {fn}")
    print(f"{n} filas en {time.time()-t0:.0f}s")
if __name__=="__main__": main()
