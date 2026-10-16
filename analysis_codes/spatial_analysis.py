"""Full-grid reservoir spatial extraction for the supplied DataWorks workbooks.

This module deliberately uses exact normalised header aliases rather than substring
matching.  In particular, saturation columns are never inferred from a partial
match (for example SWAT is not confused with SWL or SWCR).
"""
from __future__ import annotations

import csv, hashlib, json, math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

PARSER_VERSION = "spatial-grid-v3-numbered-20261016"
SENTINEL = -999.25
REQUIRED = ("I", "J", "K", "PORV", "PORO")
ALIASES = {
    "I": ("I INDEX", "I"), "J": ("J INDEX", "J"), "K": ("K INDEX", "K"),
    "X": ("X COORDINATE", "X"), "Y": ("Y COORDINATE", "Y"), "Z": ("Z COORDINATE", "Z"),
    "PORV": ("PORE VOLUME (PORV)", "PORV"), "PORO": ("POROSITY (PORO)", "PORO"),
    "PERMX": ("PERMEABILITY I (PERMX)", "PERMX"), "PERMY": ("PERMEABILITY J (PERMY)", "PERMY"),
    "PERMZ": ("PERMEABILITY K (PERMZ)", "PERMZ"), "NTG": ("NET-TO-GROSS RATIO (NTG)", "NTG"),
    "TRANX": ("TRANSMISSIBILITY I (TRANX)", "TRANX"), "TRANY": ("TRANSMISSIBILITY J (TRANY)", "TRANY"),
    "TRANZ": ("TRANSMISSIBILITY K (TRANZ)", "TRANZ"),
    "FIPNUM": ("FLUID IN PLACE REGION (FIPNUM)", "FIPNUM", "FLUIDREGION"),
    "PVTNUM": ("PVT REGION (PVTNUM)", "PVTNUM", "PVTREGION"),
    "PRESSURE": ("PRESSURE (PRESSURE)", "PRESSURE"),
    "SWAT": ("WATER SATURATION (SWAT)", "SWAT"), "SOIL": ("OIL SATURATION (SOIL)", "SOIL"),
    "SGAS": ("GAS SATURATION (SGAS)", "SGAS"),
}
FIELDS = tuple(ALIASES)
PROPERTY_FIELDS = ("PORV","PORO","PERMX","PERMY","PERMZ","NTG","TRANX","TRANY","TRANZ","FIPNUM","PVTNUM","PRESSURE","SWAT","SOIL","SGAS")
SPATIAL_FILES = {
    "geometry": "08_SpatialGeometry.csv", "properties": "09_SpatialCellProperties.parquet",
    "case_summary": "10_SpatialCaseSummary.csv", "layer_summary": "11_SpatialLayerSummary.csv",
    "region_summary": "12_SpatialRegionSummary.csv", "property_ranges": "13_SpatialPropertyRanges.csv",
}

def normalise_header(value):
    return " ".join(str(value or "").strip().upper().split())

def header_mapping(headers):
    names = {normalise_header(v): i for i, v in enumerate(headers)}
    mapping = {field: next((names[a] for a in aliases if a in names), None) for field, aliases in ALIASES.items()}
    missing = [f for f in REQUIRED if mapping[f] is None]
    if missing:
        raise ValueError("Required spatial columns missing: " + ", ".join(missing) + ". Headers: " + repr(headers))
    return mapping

def _number(row, mapping, field):
    index = mapping[field]
    if index is None: return math.nan
    try: return float(row.get(index))
    except (TypeError, ValueError): return math.nan

def _valid(v): return math.isfinite(v) and v != SENTINEL
def _active(porv, poro): return math.isfinite(porv) and porv > 0 and _valid(poro)
def _partition(case): return "train" if case <= 70 else "validation" if case <= 85 else "test"
def _cell_id(i,j,k): return f"{i}:{j}:{k}"

def _fingerprint(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": h.hexdigest()}

def _source_cases(src, XLSX):
    books = []
    for path in sorted(src.glob("*.xlsx")):
        if "Cases" not in path.name and "Cases" not in path.stem: continue
        x = XLSX(path)
        for sheet in x.sheets:
            if sheet.startswith("Case "):
                try: books.append((int(sheet.split()[-1]), path, sheet))
                except ValueError: pass
    books.sort()
    found = [c for c, _, _ in books]
    expected = list(range(1, 101))
    if found != expected: raise ValueError(f"Expected Cases 1-100 once; found {found}")
    return books

def _quant(values, q):
    return float(np.quantile(values, q)) if values else math.nan

def _stats(values):
    clean = [v for v in values if _valid(v)]
    return {"min": min(clean) if clean else math.nan, "max": max(clean) if clean else math.nan,
            "p10": _quant(clean,.1), "p50": _quant(clean,.5), "p90": _quant(clean,.9), "count": len(clean)}

def _aggregate(rows, keys):
    """PV-weighted porosity/saturations; permeability values are descriptive distributions."""
    groups = defaultdict(lambda: {"active":0,"porv":0.,"poro_pv":0.,"swat_pv":0.,"soil_pv":0.,"sgas_pv":0.,"permx":[],"permy":[],"permz":[]})
    for r in rows:
        g = groups[tuple(r[k] for k in keys)]; pv = r["PORV"]; g["active"] += 1; g["porv"] += pv
        for p, target in (("PORO","poro_pv"),("SWAT","swat_pv"),("SOIL","soil_pv"),("SGAS","sgas_pv")):
            if _valid(r[p]): g[target] += r[p] * pv
        for p in ("PERMX","PERMY","PERMZ"):
            if _valid(r[p]): g[p.lower()].append(r[p])
    out=[]
    for group, v in groups.items():
        d=dict(zip(keys,group)); pv=v["porv"]
        d.update({"ActiveCellCount":v["active"], "TotalPoreVolume":pv,
          "PVWeightedPorosity":v["poro_pv"]/pv if pv else math.nan,
          "PVWeightedSWAT":v["swat_pv"]/pv if pv else math.nan,
          "PVWeightedSOIL":v["soil_pv"]/pv if pv else math.nan,
          "PVWeightedSGAS":v["sgas_pv"]/pv if pv else math.nan})
        for p in ("permx","permy","permz"):
            s=_stats(v[p]); d.update({f"{p.upper()}_{k.upper()}": val for k,val in s.items()})
        d["PERMX_PERMY_P50_RATIO"] = d["PERMX_P50"] / d["PERMY_P50"] if d["PERMY_P50"] > 0 else math.nan
        d["PERMX_PERMZ_P50_RATIO"] = d["PERMX_P50"] / d["PERMZ_P50"] if d["PERMZ_P50"] > 0 else math.nan
        out.append(d)
    return out

def _write_csv(path, rows):
    rows=list(rows); path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: raise ValueError(f"No rows for {path}")
    with path.open("w", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def write_cross_case_consistency(root):
    """Hash aligned active-cell vectors to distinguish constant from varying fields."""
    root=Path(root); path=root/"powerbi_ready_data"/SPATIAL_FILES["properties"]
    hashes=defaultdict(lambda: hashlib.sha256()); counts=defaultdict(int); mins={f:math.inf for f in PROPERTY_FIELDS}; maxs={f:-math.inf for f in PROPERTY_FIELDS}; case_mins=defaultdict(lambda: math.inf); case_maxs=defaultdict(lambda: -math.inf)
    pf=pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=100000, columns=["CaseID",*PROPERTY_FIELDS]):
        data=batch.to_pydict()
        for n, case in enumerate(data["CaseID"]):
            for f in PROPERTY_FIELDS:
                v=data[f][n]; token="NULL" if v is None else float(v).hex()
                hashes[(f,case)].update((token+";").encode())
                if v is not None and _valid(float(v)):
                    counts[(f,case)] += 1; mins[f]=min(mins[f],float(v)); maxs[f]=max(maxs[f],float(v))
                    case_mins[(f,case)]=min(case_mins[(f,case)],float(v)); case_maxs[(f,case)]=max(case_maxs[(f,case)],float(v))
    fields=[]
    for f in PROPERTY_FIELDS:
        signatures={hashes[(f,c)].hexdigest() for c in range(1,101)}
        fields.append({"Property":f,"ConstantAcrossAlignedCases":len(signatures)==1,"DistinctCaseVectors":len(signatures),"GlobalValidMin":mins[f] if mins[f]!=math.inf else None,"GlobalValidMax":maxs[f] if maxs[f]!=-math.inf else None,"ValidCountCase1":counts[(f,1)]})
    result={"method":"SHA-256 of ordered aligned active-cell values; geometry and active masks are separately validated.","fields":fields}
    (root/"outputs"/"SPATIAL_CROSS_CASE_CONSISTENCY.json").write_text(json.dumps(result,indent=2))
    _write_csv(root/"powerbi_ready_data"/SPATIAL_FILES["property_ranges"], [{"CaseID":case,"Property":f,"ValidActiveCount":counts[(f,case)],"Min":case_mins[(f,case)] if case_mins[(f,case)]!=math.inf else None,"Max":case_maxs[(f,case)] if case_maxs[(f,case)]!=-math.inf else None} for case in range(1,101) for f in PROPERTY_FIELDS])
    return result

def run_spatial_analysis(root, XLSX, force=False):
    root=Path(root); src=root/"TestCases"; work=root/"work"; out=root/"outputs"; pbi=root/"powerbi_ready_data"
    work.mkdir(exist_ok=True); out.mkdir(exist_ok=True); pbi.mkdir(exist_ok=True)
    manifest_path=work/"spatial_cache_manifest.json"
    cases=_source_cases(src, XLSX)
    unique_paths={p for _, p, _ in cases}
    fingerprints=[_fingerprint(p) for p in sorted(unique_paths, key=lambda p: p.name)]
    final_names=list(SPATIAL_FILES.values())
    expected={"parser_version":PARSER_VERSION,"sources":fingerprints,"cases":list(range(1,101))}
    if not force and manifest_path.exists() and all((pbi/n).exists() for n in final_names):
        old=json.loads(manifest_path.read_text())
        if all(old.get(k)==v for k,v in expected.items()) and old.get("full_extraction") and old.get("active_rows",0)>0:
            write_cross_case_consistency(root)
            return {"reused_cache":True, **old}

    properties_path=pbi/SPATIAL_FILES["properties"]; writer=None; batch=[]
    geometry=[]; geometry_keys=None; audits=[]; all_case_rows=[]; layer_rows=[]; region_rows=[]; geometry_hashes=[]
    try:
      for case, path, sheet in cases:
        x=XLSX(path); iterator=x.rows(sheet)
        try: _, header_row=next(iterator)
        except StopIteration: raise ValueError(f"{path.name}/{sheet} is empty")
        headers=[header_row.get(i,"") for i in range(max(header_row)+1)]; mapping=header_mapping(headers)
        total=active=0; sentinel=defaultdict(int); missing=defaultdict(int); duplicates=0; keys=set(); active_rows=[]; ranges={f:[] for f in ("I","J","K")}; coords={f:0 for f in ("X","Y","Z")}; sat_bad=0; sat_sum_bad=0; invalid=defaultdict(int)
        geom_digest=hashlib.sha256()
        for _, raw in iterator:
            total += 1; v={f:_number(raw,mapping,f) for f in FIELDS};
            for f in FIELDS:
                if not math.isfinite(v[f]): missing[f]+=1
                if v[f] == SENTINEL: sentinel[f]+=1
            if not all(math.isfinite(v[f]) for f in ("I","J","K")):
                invalid["spatial_key"] += 1; continue
            i,j,k=(int(v[f]) for f in ("I","J","K")); key=(i,j,k)
            if key in keys: duplicates += 1
            keys.add(key); [ranges[f].append(v[f]) for f in ("I","J","K")]
            for f in ("X","Y","Z"): coords[f] += int(math.isfinite(v[f]) and v[f] != SENTINEL)
            geom_digest.update((f"{i},{j},{k},{v['X']},{v['Y']},{v['Z']};").encode())
            if case == 1: geometry.append({"CellID":_cell_id(i,j,k),"I":i,"J":j,"K":k,"X":v["X"],"Y":v["Y"],"Z":v["Z"],"GeometrySourceWorkbook":path.name,"GeometrySourceWorksheet":sheet})
            if not _active(v["PORV"],v["PORO"]): continue
            active += 1
            sat=[v[f] for f in ("SWAT","SOIL","SGAS")]
            if any(_valid(z) and not (0 <= z <= 1) for z in sat): sat_bad += 1
            if all(_valid(z) for z in sat) and abs(sum(sat)-1) > 0.02: sat_sum_bad += 1
            row={"CaseID":case,"Partition":_partition(case),"CellID":_cell_id(i,j,k),"SourceWorkbook":path.name,"SourceWorksheet":sheet,"I":i,"J":j,"K":k}
            row.update({f:(v[f] if _valid(v[f]) else None) for f in PROPERTY_FIELDS}); active_rows.append(row); batch.append(row)
            if len(batch) >= 100000:
                table=pa.Table.from_pylist(batch)
                if writer is None: writer=pq.ParquetWriter(properties_path, table.schema, compression="zstd")
                writer.write_table(table); batch.clear()
        if total == 0: raise ValueError(f"{path.name}/{sheet} has no data rows")
        geometry_hashes.append(geom_digest.hexdigest())
        case_agg=_aggregate(active_rows,("CaseID","Partition"))[0]
        case_agg.update({"TotalCellCount":total,"InactiveCellCount":total-active,"DuplicateSpatialKeys":duplicates,
          "IRange":f"{int(min(ranges['I']))}:{int(max(ranges['I']))}","JRange":f"{int(min(ranges['J']))}:{int(max(ranges['J']))}","KRange":f"{int(min(ranges['K']))}:{int(max(ranges['K']))}",
          "CoordinateCompleteness":min(coords.values())/total,"SaturationOutOfBoundsActive":sat_bad,"SaturationSumOutsideToleranceActive":sat_sum_bad,
          "SourceWorkbook":path.name,"SourceWorksheet":sheet})
        for f in FIELDS: case_agg[f"Missing_{f}"]=missing[f]; case_agg[f"Sentinel_{f}"]=sentinel[f]
        all_case_rows.append(case_agg); layer_rows.extend(_aggregate(active_rows,("CaseID","Partition","K"))); region_rows.extend(_aggregate(active_rows,("CaseID","Partition","FIPNUM","PVTNUM")))
        audits.append({"CaseID":case,"Workbook":path.name,"Worksheet":sheet,"HeaderMapping":mapping,"Rows":total,"Active":active,"Duplicates":duplicates,"GeometryHash":geometry_hashes[-1]})
      if batch:
        table=pa.Table.from_pylist(batch)
        if writer is None: writer=pq.ParquetWriter(properties_path, table.schema, compression="zstd")
        writer.write_table(table)
    finally:
      if writer: writer.close()
    if len(geometry) != all_case_rows[0]["TotalCellCount"]: raise ValueError("Case 1 geometry row count does not reconcile")
    _write_csv(pbi/SPATIAL_FILES["geometry"],geometry); _write_csv(pbi/SPATIAL_FILES["case_summary"],all_case_rows); _write_csv(pbi/SPATIAL_FILES["layer_summary"],layer_rows); _write_csv(pbi/SPATIAL_FILES["region_summary"],region_rows)
    # Replaces the old first-100-row cache with actual case summaries for legacy readers.
    (work/"grid_summaries.json").write_text(json.dumps(all_case_rows, indent=2, allow_nan=True))
    spatial_audit={"parser_version":PARSER_VERSION,"active_rule":"PORV > 0 and PORO is finite and PORO != -999.25","units":"Unspecified in supplied workbooks; no CRS/EPSG, depth/elevation, or snapshot time inferred.","cases":audits,"geometry_identical":len(set(geometry_hashes))==1,"active_masks_identical":len({(x['ActiveCellCount'],x['InactiveCellCount']) for x in all_case_rows})==1,"property_notes":"Permeability statistics are descriptive distributions, not effective permeability. Saturations and porosity are PV-weighted in summaries."}
    (out/"SPATIAL_DATA_AUDIT.json").write_text(json.dumps(spatial_audit,indent=2,allow_nan=True))
    manifest={**expected,"full_extraction":True,"total_rows":sum(x["TotalCellCount"] for x in all_case_rows),"active_rows":sum(x["ActiveCellCount"] for x in all_case_rows),"geometry_identical":spatial_audit["geometry_identical"],"active_masks_identical":spatial_audit["active_masks_identical"],"outputs":final_names}
    manifest_path.write_text(json.dumps(manifest,indent=2)); write_cross_case_consistency(root); return {"reused_cache":False,**manifest}

def render_spatial_figures(root, case_id=1, layer=1, section_axis="I", section_index=1, compare_case=71):
    """Render selector-driven static views; axes are grid indices, never geographic coordinates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root=Path(root); pbi=root/"powerbi_ready_data"; figures=root/"outputs"/"spatial_figures"; figures.mkdir(parents=True,exist_ok=True)
    geo=[]
    with (pbi/SPATIAL_FILES["geometry"]).open() as f:
        for r in csv.DictReader(f): geo.append({k:(float(v) if k in ("X","Y","Z") and v not in ("",None) else int(v) if k in ("I","J","K") else v) for k,v in r.items()})
    def props(cid):
        t=pq.read_table(pbi/SPATIAL_FILES["properties"],filters=[("CaseID","=",cid)])
        return {r["CellID"]:r for r in t.to_pylist()}
    a=props(case_id); b=props(compare_case)
    cells=[g for g in geo if g["K"]==layer]; imin,imax=min(g["I"] for g in geo),max(g["I"] for g in geo); jmin,jmax=min(g["J"] for g in geo),max(g["J"] for g in geo)
    fields=[("PORO","Porosity",False),("PERMX","Horizontal permeability (PERMX; log10 positive)",True),("PORV","Pore volume",False),("SOIL","Oil saturation",False),("SWAT","Water saturation",False)]
    fig, axes=plt.subplots(1,5,figsize=(22,4.5),constrained_layout=True)
    for ax,(field,title,log) in zip(axes,fields):
        arr=np.full((jmax-jmin+1,imax-imin+1),np.nan)
        zeros=[]
        for g in cells:
            r=a.get(g["CellID"])
            if r and r.get(field) is not None:
                val=r[field]
                if log and val>0: val=np.log10(val)
                elif log and val==0: zeros.append((g["I"],g["J"])); continue
                elif log: continue
                arr[g["J"]-jmin,g["I"]-imin]=val
        im=ax.imshow(arr,origin="lower",aspect="auto",cmap="viridis")
        if zeros: ax.scatter([x-imin for x,y in zeros],[y-jmin for x,y in zeros],s=3,c="white",marker="x",label="zero")
        ax.set(title=title,xlabel="I index",ylabel="J index"); fig.colorbar(im,ax=ax,shrink=.7)
    heat=figures/f"heatmaps_case_{case_id}_k_{layer}.png"; fig.savefig(heat,dpi=150); plt.close(fig)
    wanted=[g for g in geo if g[section_axis]==section_index]; other="J" if section_axis=="I" else "I"; omin,omax=min(g[other] for g in wanted),max(g[other] for g in wanted); kmin,kmax=min(g["K"] for g in wanted),max(g["K"] for g in wanted)
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    for ax,(field,title,log) in zip(axes,fields[:3]):
        arr=np.full((kmax-kmin+1,omax-omin+1),np.nan)
        for g in wanted:
            r=a.get(g["CellID"]); val=r.get(field) if r else None
            if val is not None and (not log or val>0): arr[g["K"]-kmin,g[other]-omin]=np.log10(val) if log else val
        im=ax.imshow(arr,origin="lower",aspect="auto",cmap="viridis"); ax.set(title=title,xlabel=f"{other} index",ylabel="K index (ordering only)"); fig.colorbar(im,ax=ax,shrink=.75)
    cross=figures/f"cross_section_case_{case_id}_{section_axis}_{section_index}.png"; fig.savefig(cross,dpi=150); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    absdiff=np.full((jmax-jmin+1,imax-imin+1),np.nan); pct=np.full_like(absdiff,np.nan)
    for g in cells:
        left,right=a.get(g["CellID"]),b.get(g["CellID"])
        if left and right and left.get("PORO") is not None and right.get("PORO") is not None:
            d=right["PORO"]-left["PORO"]; absdiff[g["J"]-jmin,g["I"]-imin]=d
            if left["PORO"] != 0: pct[g["J"]-jmin,g["I"]-imin]=100*d/left["PORO"]
    for ax,arr,title in zip(axes,(absdiff,pct),(f"PORO absolute difference: Case {compare_case} - {case_id}","PORO % difference (valid nonzero reference only)")):
        im=ax.imshow(arr,origin="lower",aspect="auto",cmap="coolwarm"); ax.set(title=title,xlabel="I index",ylabel="J index"); fig.colorbar(im,ax=ax,shrink=.8)
    comparison=figures/f"comparison_case_{compare_case}_minus_{case_id}_k_{layer}.png"; fig.savefig(comparison,dpi=150); plt.close(fig)
    return {"heatmaps":str(heat),"cross_section":str(cross),"comparison":str(comparison),"selectors":{"CaseID":case_id,"K":layer,"section_axis":section_axis,"section_index":section_index,"compare_case":compare_case}}

