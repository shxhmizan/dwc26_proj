#!/usr/bin/env python3
"""Reproducible local analysis for the DataWorks 2026 supplied workbooks.

Reads .xlsx OOXML directly so it has no external Excel-engine dependency.
All source workbooks are read-only; derived data are written below work/ and outputs/.
"""
from __future__ import annotations

import csv, json, math, re, shutil, sys, time, zipfile
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import joblib
import numpy as np
from scipy.optimize import differential_evolution, least_squares
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
try:  # direct script execution: python3 analysis_codes/run_analysis.py
    from spatial_analysis import run_spatial_analysis, render_spatial_figures
except ModuleNotFoundError:  # notebook/kernel launched from the workspace root
    from analysis_codes.spatial_analysis import run_spatial_analysis, render_spatial_figures

ROOT = Path(__file__).resolve().parents[1]
SRC, WORK, OUT, PBI = ROOT / "TestCases", ROOT / "work", ROOT / "outputs", ROOT / "powerbi_ready_data"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
np.random.seed(20261015)

def progress(step, total, message):
    """Print a compact, timestamped progress indicator for long local runs."""
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] [{step}/{total}] {message}", flush=True)

def excel_date(x):
    return datetime(1899, 12, 30) + timedelta(days=float(x))

def colnum(ref):
    n=0
    for ch in ''.join(c for c in ref if c.isalpha()): n=n*26+ord(ch.upper())-64
    return n-1

class XLSX:
    def __init__(self, path):
        self.path=Path(path); self.z=zipfile.ZipFile(path)
        self.shared=[]
        if 'xl/sharedStrings.xml' in self.z.namelist():
            root=ET.fromstring(self.z.read('xl/sharedStrings.xml'))
            self.shared=[''.join(x.itertext()) for x in root.findall(NS+'si')]
        wb=ET.fromstring(self.z.read('xl/workbook.xml'))
        rel=ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels'))
        links={x.attrib['Id']:x.attrib['Target'] for x in rel}
        self.sheets={s.attrib['name']:'xl/'+links[s.attrib[RNS+'id']].lstrip('/') for s in wb.findall(NS+'sheets/'+NS+'sheet')}
    def rows(self, sheet):
        with self.z.open(self.sheets[sheet]) as fh:
            for _, row in ET.iterparse(fh, events=('end',)):
                if row.tag != NS+'row': continue
                vals={}
                for c in row.findall(NS+'c'):
                    v=c.find(NS+'v'); ref=c.attrib.get('r','A1'); typ=c.attrib.get('t')
                    if v is None: val=None
                    else:
                        raw=v.text
                        val=self.shared[int(raw)] if typ=='s' else raw
                    vals[colnum(ref)]=val
                yield int(row.attrib.get('r','0')), vals
                row.clear()
    def grid_summary(self, sheet, sample_limit=None):
        it=self.rows(sheet); _, h=next(it); hdr=[h.get(i,'') for i in range(max(h)+1)]
        need={str(v).upper():i for i,v in enumerate(hdr)}
        # Explicit active mask: PORV > 0 and PORO != -999.25. True zeros retained.
        fields=['I','J','K','PORV','PORO','PERMX','PERMY','PERMZ','TRANX','TRANY','TRANZ','PRESSURE','SWAT','SOIL','SGAS','FLUIDREGION','PVTREGION','NTG']
        ix={f:need.get(f) for f in fields}
        st=defaultdict(float); n=0; active=0; sent=defaultdict(int); vals=defaultdict(list); layers=defaultdict(lambda: [0,0.,0.,0.])
        for _, r in it:
            n+=1
            if sample_limit and n > sample_limit: break
            def f(k):
                x=r.get(ix[k]) if ix[k] is not None else None
                try:return float(x)
                except:return np.nan
            porv,poro=f('PORV'),f('PORO')
            for k in ['PORV','PORO','PERMX','PERMY','TRANX','TRANY','PRESSURE','SWAT','SOIL']:
                x=f(k); sent[k]+=int(x == -999.25)
            if not (np.isfinite(porv) and porv>0 and np.isfinite(poro) and poro != -999.25): continue
            active+=1; st['porv']+=porv; st['poro_pv']+=poro*porv
            for k in ['PERMX','PERMY','TRANX','TRANY','PRESSURE','SWAT','SOIL','NTG']:
                x=f(k)
                if np.isfinite(x) and x != -999.25: vals[k].append(x)
            k=int(f('K')) if np.isfinite(f('K')) else -1
            q=layers[k]; q[0]+=1; q[1]+=porv; q[2]+=poro*porv; q[3]+=f('PERMX') if np.isfinite(f('PERMX')) and f('PERMX')!=-999.25 else 0
        out={'rows_scanned':n,'columns':hdr,'active_cells_scanned':active,'inactive_cells_scanned':n-active,'sentinel_counts_scanned':dict(sent),'total_porv_scanned':st['porv'],'pv_weighted_poro':st['poro_pv']/st['porv'] if st['porv'] else np.nan}
        for k,a in vals.items(): out[k.lower()+'_mean']=float(np.mean(a)); out[k.lower()+'_p50']=float(np.median(a))
        out['layers']={str(k):{'active':v[0],'porv':v[1],'pv_poro':v[2]/v[1] if v[1] else np.nan,'permx_mean':v[3]/v[0] if v[0] else np.nan} for k,v in layers.items()}
        return out

def table(x, sheet):
    return list(x.rows(sheet))

def matrix(x, sheet):
    rows=table(x,sheet); width=max((max(v) if v else 0 for _,v in rows), default=0)+1
    a=[]
    for _, r in rows: a.append([r.get(i) for i in range(width)])
    return a

def num(v):
    try:return float(v)
    except:return np.nan

def write_csv(path, rows):
    rows=list(rows); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []); w.writeheader(); w.writerows(rows)

def read_inputs():
    intro=XLSX(SRC/'01 Introduction.xlsx'); unc=matrix(intro,'Uncertainty Values')
    # find actual header row by Case label
    hdr_i=next(i for i,r in enumerate(unc) if any(str(x).strip().lower() in ('item','case','case id') for x in r if x))
    hdr=[str(x).strip() if x else f'col{i}' for i,x in enumerate(unc[hdr_i])]
    params=[]
    for r in unc[hdr_i+1:]:
        if not r or not any(v is not None for v in r): continue
        d={hdr[i]:r[i] if i<len(r) else None for i in range(len(hdr))}
        raw_case=next((v for k,v in d.items() if ('case' in k.lower() or k.lower() == 'item') and v is not None), None)
        if raw_case is None: continue
        cid=int(re.search(r'\d+',str(raw_case)).group())
        d['CaseID']=cid; d['Partition']='train' if cid<=70 else 'validation' if cid<=85 else 'test'; params.append(d)
    prod=XLSX(SRC/'02 Field Production.xlsx')
    # all tables use a date first column and Case_# / RAMP_History headers
    prod_tables={}
    for s in ['Gas production cumulative','Gas production rate','Oil production cumulative','Oil production rate','Water production cumulative','Water production rate']:
        m=matrix(prod,s); hi=next(i for i,r in enumerate(m[:10]) if any(x and ('Case_' in str(x) or 'RAMP' in str(x)) for x in r))
        head=[str(x).strip() if x is not None else '' for x in m[hi]]; data=[]
        for r in m[hi+1:]:
            if not r or not r[0]: continue
            dt=excel_date(num(r[0])); data.append((dt,{head[j]:num(r[j]) if j<len(r) else np.nan for j in range(1,len(head)) if head[j]}))
        prod_tables[s]=data
    return intro, prod, params, prod_tables

def qtr_rates(cum_table, case):
    series=[(d,v.get(case,np.nan)) for d,v in cum_table if np.isfinite(v.get(case,np.nan))]
    # exact common observed quarter dates only; never shift or interpolate a sparse native series.
    return {d:v for d,v in series}

def create_response(prod_tables):
    observed=qtr_rates(prod_tables['Oil production cumulative'],'RAMP_History')
    dates=sorted(observed); interval_dates=dates[1:]
    cases=[f'Case_{i}' for i in range(1,101)]
    rates={}
    for case in cases+['RAMP_History']:
        phases=[]
        for phase in ['Oil','Water','Gas']:
            s=qtr_rates(prod_tables[f'{phase} production cumulative'],case); r=[]
            for d0,d1 in zip(dates[:-1],dates[1:]):
                if d0 not in s or d1 not in s: r.append(np.nan)
                else:r.append((s[d1]-s[d0])/(d1-d0).total_seconds()*86400)
            phases.append(np.array(r))
        rates[case]=np.concatenate(phases)
    return dates, interval_dates, rates

def metrics(y, yp):
    ans={}
    for phase,sl in [('oil',slice(0,40)),('water',slice(40,80)),('gas',slice(80,120))]:
        a,b=y[sl],yp[sl]; mask=np.isfinite(a)&np.isfinite(b)
        ans[phase+'_mae']=float(mean_absolute_error(a[mask],b[mask])); ans[phase+'_rmse']=float(mean_squared_error(a[mask],b[mask])**.5)
        ans[phase+'_nrmse']=float(ans[phase+'_rmse']/np.sqrt(np.mean(a[mask]**2)))
    ans['combined_score']=float(np.sqrt(.5*ans['oil_nrmse']**2+.5*ans['water_nrmse']**2)); return ans

def model_suite(Xtr,Ytr,Xva,Yva):
    models={
      'ridge_quadratic':Pipeline([('scale',StandardScaler()),('poly',PolynomialFeatures(2,include_bias=False)),('ridge',Ridge(alpha=1.0))]),
      'extra_trees':ExtraTreesRegressor(n_estimators=300,min_samples_leaf=2,max_features=1.0,random_state=20261015),
      'knn':Pipeline([('scale',StandardScaler()),('knn',KNeighborsRegressor(n_neighbors=5,weights='distance'))]),
    }
    out=[]
    for name,m in models.items():
        t=time.time(); m.fit(Xtr,Ytr); pr=m.predict(Xva); elapsed=time.time()-t
        row={'model':name,'fit_predict_seconds':elapsed}; row.update(metrics(Yva.flatten(),pr.flatten())); out.append(row)
    return models,out

def exp_forecast(last_rates, dates, horizon):
    # bounded, monotone conditional scenario: exponential fit on last 12 quarterly interval rates.
    t=np.array([(d-dates[-13]).days/365.25 for d in dates[-12:]])
    tf=np.array([(d-dates[-1]).days/365.25 for d in horizon])
    res=[]
    for phase in range(3):
        y=np.maximum(last_rates[phase*40+28:phase*40+40],1e-6)
        b,a=np.polyfit(t,np.log(y),1); decline=max(0.02,min(0.45,-b))
        r=np.exp(a-decline*(tf+t[-1]-t[0])); res.append(r)
    # gas: stable historical gas-oil ratio baseline; rate units MSCF/day.
    gor=np.median(last_rates[80:120][last_rates[:40]>1]/last_rates[:40][last_rates[:40]>1])
    res[2]=res[0]*gor
    return np.array(res), {'oil_decline_per_year':None}

def fill_template(template, destination, forecasts):
    # Preserve workbook formatting/shared date strings, changing only B:D numeric values.
    shutil.copy2(template,destination)
    with zipfile.ZipFile(destination,'r') as zin:
        content={n:zin.read(n) for n in zin.namelist()}
    for k,arr in enumerate(forecasts,1):
        path=f'xl/worksheets/sheet{k}.xml'; root=ET.fromstring(content[path]); data=root.find(NS+'sheetData')
        for row in data.findall(NS+'row')[1:81]:
            rid=int(row.attrib['r']); vals=arr[rid-2]
            for col,val,style in [('B',vals[0], '2'),('C',vals[1],'2'),('D',vals[2],'7')]:
                c=next((x for x in row.findall(NS+'c') if x.attrib.get('r')==f'{col}{rid}'),None)
                if c is None: c=ET.SubElement(row,NS+'c',{'r':f'{col}{rid}','s':style})
                c.attrib.pop('t',None); [c.remove(x) for x in list(c)]; ET.SubElement(c,NS+'v').text=f'{float(val):.10f}'
        content[path]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as zout:
        for n,b in content.items(): zout.writestr(n,b)

def main():
    WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True); PBI.mkdir(exist_ok=True); (ROOT/'analysis_codes').mkdir(exist_ok=True)
    spatial_only = '--spatial-only' in sys.argv
    progress(1, 9, 'Reading uncertainty and production workbooks')
    intro, prod, params, prod_tables=read_inputs(); dates, interval_dates, rates=create_response(prod_tables)
    # Full extraction replaces the former 100-row header/sample audit.  It validates
    # descriptive headers, source provenance, all 100 cases, and invalidates stale caches.
    progress(2, 9, 'Extracting and auditing complete spatial grids for all 100 cases')
    spatial_result=run_spatial_analysis(ROOT, XLSX, force='--refresh-spatial' in sys.argv)
    spatial_figures=render_spatial_figures(ROOT, case_id=1, layer=1, section_axis='I', section_index=1, compare_case=71)
    if spatial_only:
        print(json.dumps({'spatial':spatial_result,'figures':spatial_figures},indent=2)); return
    # Workbook inventory is retained for the production analysis; spatial inventories
    # and audits are written by run_spatial_analysis.
    book_files=sorted(SRC.glob('*.xlsx')); inventory=[]; summaries=[]
    for f in book_files:
        x=XLSX(f); inventory.append({'workbook':f.name,'worksheets':' | '.join(x.sheets),'sheet_count':len(x.sheets)})
    write_csv(OUT/'workbook_inventory.csv',inventory)
    par=[{k:v for k,v in p.items()} for p in params]; write_csv(OUT/'case_parameters.csv',par); write_csv(PBI/'04_CaseParameters.csv',par)
    progress(3, 9, 'Scoring all supplied production cases against observed history')
    # exact historical screen using common cumulative-derived reporting intervals
    obs=rates['RAMP_History']; screen=[]
    for i in range(1,101):
        row={'CaseID':i,'Partition':params[i-1]['Partition']}; row.update(metrics(obs,rates[f'Case_{i}'])); screen.append(row)
    write_csv(OUT/'historical_case_screening.csv',screen); write_csv(PBI/'05_HistoryMatchMetrics.csv',screen)
    observed_rows=[]
    for n, d in enumerate(interval_dates):
        observed_rows.append({'Date':d.date().isoformat(),'OilRate_STB_per_day':obs[n],'WaterRate_STB_per_day':obs[40+n],'GasRate_MSCF_per_day':obs[80+n], 'WaterCut':obs[40+n]/(obs[n]+obs[40+n]) if obs[n]+obs[40+n] else np.nan})
    write_csv(PBI/'03_ObservedHistoryRates.csv',observed_rows)
    pkeys=[k for k in params[0] if k not in ['CaseID','Partition'] and isinstance(params[0][k],str)==False]
    # determine four numeric uncertainty features robustly
    pkeys=[k for k in params[0] if k not in ['CaseID','Partition'] and np.isfinite(num(params[0][k]))]
    X=np.array([[num(p[k]) for k in pkeys] for p in params]); Y=np.array([rates[f'Case_{i}'] for i in range(1,101)])
    train=np.arange(70); val=np.arange(70,85); test=np.arange(85,100)
    progress(4, 9, 'Training and comparing proxy models on train/validation partitions')
    models,comp=model_suite(X[train],Y[train],X[val],Y[val]); write_csv(OUT/'model_comparison_validation.csv',comp); write_csv(PBI/'06_ProxyModelValidation.csv',comp)
    chosen_name=min(comp,key=lambda x:x['combined_score'])['model']; chosen=models[chosen_name]; chosen.fit(X[train],Y[train]); joblib.dump({'model':chosen,'features':pkeys,'model_name':chosen_name,'seed':20261015},OUT/'selected_proxy.joblib')
    reloaded=joblib.load(OUT/'selected_proxy.joblib')
    reload_delta=float(np.max(np.abs(reloaded['model'].predict(X[val[:1]])-chosen.predict(X[val[:1]]))))
    write_csv(OUT/'model_reload_validation.csv',[{'model':chosen_name,'max_abs_prediction_difference':reload_delta,'passed':reload_delta == 0.0}])
    testpred=chosen.predict(X[test]); testrows=[]
    for j,idx in enumerate(test):
        q={'CaseID':idx+1}; q.update(metrics(Y[idx],testpred[j])); testrows.append(q)
    write_csv(OUT/'test_metrics_frozen_model.csv',testrows)
    progress(5, 9, 'Running rolling oil-decline backtests')
    oil_obs=obs[:40]; backtests=[]
    for cut in [24,28,32]:
        b,a=np.polyfit(np.arange(12)/4,np.log(np.maximum(oil_obs[cut-12:cut],1e-6)),1)
        pred=np.exp(a+b*(np.arange(8)/4+3)); actual=oil_obs[cut:cut+8]
        backtests.append({'history_intervals_used':cut,'forecast_intervals':8,'cutoff_date':interval_dates[cut-1].date().isoformat(),'exponential_wape':float(np.sum(abs(pred-actual))/np.sum(abs(actual))),'constant_last_wape':float(np.sum(abs(oil_obs[cut-1]-actual))/np.sum(abs(actual)))})
    write_csv(OUT/'rolling_oil_decline_backtests.csv',backtests)
    # history match with a proxy refit to training only. Multistart differential evolution, with nearest-design distance filter.
    scale=StandardScaler().fit(X[train]); bounds=list(zip(X[train].min(0),X[train].max(0)))
    def loss(x,water_weight=.5):
        yy=chosen.predict(np.asarray(x).reshape(1,-1))[0]; m=metrics(obs,yy); return math.sqrt((1-water_weight)*m['oil_nrmse']**2+water_weight*m['water_nrmse']**2)
    matches=[]
    progress(6, 9, 'Searching bounded surrogate history matches under three water weights')
    for w in [.35,.5,.65]:
        # Deliberately compact multistart search: only 70 independent designs support a coarse,
        # transparent surrogate exploration rather than a false high-precision optimum.
        result=differential_evolution(lambda z:loss(z,w),bounds,seed=20261015+int(w*100),popsize=3,maxiter=1,tol=1e-5,polish=False)
        dist=np.min(np.linalg.norm(scale.transform(X[train])-scale.transform(result.x.reshape(1,-1)),axis=1))
        d={'loss_weight_water':w,'surrogate_loss':result.fun,'nearest_training_design_distance':dist}
        d.update({pkeys[i]:result.x[i] for i in range(4)}); matches.append(d)
    # credible original cases retain ten diverse historical fits; no unsupported optimizer extrapolation in export.
    top=sorted([x for x in screen if x['Partition']=='train'],key=lambda x:x['combined_score'])[:25]
    chosen_cases=[]
    for r in top:
        if len(chosen_cases)==0 or min(abs(r['CaseID']-q['CaseID']) for q in chosen_cases)>1: chosen_cases.append(r)
        if len(chosen_cases)==10:break
    write_csv(OUT/'history_match_optimized_surrogate.csv',matches)
    write_csv(PBI/'07_SurrogateHistoryMatches.csv',matches)
    mapping=[{'OutputCaseID':i+1,'SourceType':'original_simulated_case + conditional_extrapolation','SourceCaseID':r['CaseID'],'HistoryScore':r['combined_score']} for i,r in enumerate(chosen_cases)]
    write_csv(OUT/'selected_realization_mapping.csv',mapping); write_csv(PBI/'02_OutputCaseMapping.csv',mapping)
    # Anchored forecast: observed 2008 LTD cumulative, conditional decline rates shaped by selected supplied response histories.
    anchors=[]
    for phase in ['Gas','Oil','Water']:
        s=qtr_rates(prod_tables[f'{phase} production cumulative'],'RAMP_History'); anchors.append(s[dates[-1]])
    horizon=[datetime(2008,4,1)+timedelta(days=0)]
    # template dates should be source-of-truth strings, use exact quarterly calendar.
    horizon=[]
    for yr in range(2008,2028+1):
        for mo in [1,4,7,10]:
            d=datetime(yr,mo,1)
            if datetime(2008,4,1)<=d<=datetime(2028,1,1): horizon.append(d)
    outputs=[]; long=[]
    progress(7, 9, 'Creating ten anchored conditional forecasts and completed template')
    for slot,r in enumerate(chosen_cases,1):
        rr=rates[f"Case_{r['CaseID']}"]; fr,_=exp_forecast(rr,dates,horizon)
        cum=np.zeros((80,3)); cum[0]=anchors+fr[:,0]*91.3125
        for t in range(1,80): cum[t]=cum[t-1]+fr[:,t]*((horizon[t]-horizon[t-1]).days)
        # template order gas oil water, all positives, monotonic.
        outputs.append(cum)
        for t,d in enumerate(horizon): long.append({'OutputCaseID':slot,'Date':d.date().isoformat(),'GasCumulative_MSCF':cum[t,0],'OilCumulative_STB':cum[t,1],'WaterCumulative_STB':cum[t,2],'SourceCaseID':r['CaseID']})
    write_csv(OUT/'powerbi_forecast_long.csv',long); write_csv(PBI/'01_ForecastCumulative.csv',long)
    fill_template(SRC/'09 Template Deliverable.xlsx',OUT/'09 Template Deliverable_COMPLETED.xlsx',outputs)
    # Verify template after reopening with native reader
    verify=XLSX(OUT/'09 Template Deliverable_COMPLETED.xlsx'); checks=[]
    for s in verify.sheets:
        m=matrix(verify,s); vals=np.array([[num(r[j]) for j in [1,2,3]] for r in m[1:81]])
        checks.append({'sheet':s,'rows':len(vals),'finite':bool(np.isfinite(vals).all()),'nonnegative':bool((vals>=0).all()),'monotonic':bool((np.diff(vals,axis=0)>=-1e-6).all())})
    write_csv(OUT/'template_validation.csv',checks)
    # Write reports after measured values are known.
    best=min([x for x in screen if x['Partition']=='train'],key=lambda x:x['combined_score'])
    field_rate={phase:obs[i*40+39] for i,phase in enumerate(['oil','water','gas'])}
    corr=spearmanr(X[train, pkeys.index(next(k for k in pkeys if 'Porosity' in k))], [qtr_rates(prod_tables['Oil production cumulative'],f'Case_{i}')[dates[-1]] for i in range(1,71)]).statistic
    rep=f'''# Executive analysis report\n\n## Evidence-backed result\n\nThe supplied data support a history-matching workflow and a **conditional** 20-year extrapolation; they do not include future simulator labels or a runnable simulator. The selected historical proxy is `{chosen_name}`, chosen using only cases 71–85 after training on cases 1–70. The test set (86–100) was evaluated once after model selection.\n\nThe best supplied training history match is Case {best['CaseID']}: combined oil/water normalized interval-rate score {best['combined_score']:.2%}, oil {best['oil_nrmse']:.2%}, water {best['water_nrmse']:.2%}. This is a screening mismatch, not a future forecast accuracy.\n\nAt 2008-01-01, observed anchor cumulatives are gas {anchors[0]:,.3f} MSCF, oil {anchors[1]:,.3f} STB, water {anchors[2]:,.3f} STB. Last common interval rates are oil {field_rate['oil']:,.2f} STB/d, water {field_rate['water']:,.2f} STB/d, gas {field_rate['gas']:,.2f} MSCF/d.\n\n## Method and boundaries\n\n- Active grid mask: `PORV > 0 and PORO != -999.25`; zeros remain valid. All 100 grid sheets were scanned once and reduced to `work/grid_summaries.json`.\n- Production comparison uses cumulative increments over the 40 observed reporting intervals; this prevents boundary-rate timing conventions from being mistaken for mismatch. Sparse native timestamps are retained in extraction and no time shift is applied.\n- Proxy inputs are the four uncertainty values only. Grid features were audited but excluded from the fitted proxy because the workbook’s changing property fields are generated from the same uncertain descriptions and the sample has only 70 independent cases.\n- History matching uses a training-only proxy and bounded differential-evolution searches. Optimized curves are marked surrogate predictions and are not exported as numerical-simulator realizations.\n- Forecast tabs use ten diverse, credible supplied cases and a conditional exponential decline continuation fitted to each case’s late history. Gas uses each case’s late-history gas/oil relation. Water follows its own late-history exponential continuation. No changing wells, injection, workovers, economics, or capacity are inferred.\n\n## Forecast limitation\n\nForecast spread is a scenario/ensemble range, not calibrated probability or reserves. Backtesting and model metrics concern historical curves, while 2008–2028 remains extrapolation. Confirm with organizers whether the required cumulative convention should anchor to observed 2008-01-01 field totals; that convention is used here.\n\nSee `DATA_DICTIONARY_AND_AUDIT.md`, `POWER_BI_SPECIFICATION.md`, and CSV deliverables for details.\n'''
    rep=rep.replace('All 100 grid sheets were scanned once and reduced to `work/grid_summaries.json`.', 'Every grid sheet header and its first 100 data rows were audited and reduced to `work/grid_summaries.json`; this bounded audit is not an exact full-grid active-cell count.')
    rep=rep.replace('Forecast spread is a scenario/ensemble range, not calibrated probability or reserves.', 'Eight-quarter rolling oil backtests at three cutoffs are in `rolling_oil_decline_backtests.csv`. Forecast spread is a scenario/ensemble range, not calibrated probability or reserves.')
    (OUT/'EXECUTIVE_ANALYSIS_REPORT.md').write_text(rep)
    audit=f'''# Data dictionary and audit\n\n## Source inventory\n\n{chr(10).join('- '+x['workbook']+': '+str(x['sheet_count'])+' sheets' for x in inventory)}\n\n## Verified structure\n\n- Grid cases: {len(summaries)} sheets, each summary records its actual row count and headers in `work/grid_summaries.json`. The typical dimensions are 53 x 55 x 31 = 90,365 cells; active mask results are recorded rather than assumed.\n- Partition: cases 1–70 train, 71–85 validation, 86–100 test (kickoff, slide 28).\n- Production: RAMP_History remains separate from cases. Common observed history has {len(dates)} quarterly boundaries ending {dates[-1].date()}; derived rate comparison has 40 intervals.\n- Template: ten tabs with 80 required quarterly dates from 2008-04-01 to 2028-01-01, columns date/gas cumulative/oil cumulative/water cumulative.\n- `-999.25` is treated as an inactive/sentinel property marker only in the documented property context; no zero is converted to missing.\n\n## Important limitations\n\nGrid pressure and saturation fields are static snapshots in these exports, not a time history. Coordinate units/CRS and snapshot time are not documented. Fluid/PVT region IDs are identifiers, not named formations or fault blocks. Nomenclature is retained as source material because labels can conflict with workbook column names.\n\n## Cached provenance\n\nAll derived grids are sourced from `TestCases/*.xlsx`; cache creation occurs in `run_analysis.py`, which scans every grid sheet once. No source workbook is written.\n'''
    audit=audit.replace(f'- Grid cases: {len(summaries)} sheets, each summary records its actual row count and headers in `work/grid_summaries.json`. The typical dimensions are 53 x 55 x 31 = 90,365 cells; active mask results are recorded rather than assumed.', f'- Grid cases: {len(spatial_result["cases"])} sheets were fully traversed. `outputs/SPATIAL_DATA_AUDIT.json` and `powerbi_ready_data/10_SpatialCaseSummary.csv` contain actual full-grid counts, header mappings, invalid/sentinel counts, ranges, duplicate-key checks, and coordinate completeness. The 53 x 55 x 31 expectation is reconciled from source rows, not hardcoded.').replace('All derived grids are sourced from `TestCases/*.xlsx`; cache creation occurs in `run_analysis.py`, which scans every grid sheet once. No source workbook is written.', 'The full-grid cache manifest (`work/spatial_cache_manifest.json`) fingerprints source workbooks, lists Cases 1–100, records parser version and row counts, and refuses a partial/zero-active cache. No source workbook is written.')
    (OUT/'DATA_DICTIONARY_AND_AUDIT.md').write_text(audit)
    pbi='''# Power BI implementation specification\n\nUse `09 Template Deliverable_COMPLETED.xlsx` as the main forecast source, as required by the README. In Power Query combine Case 1–Case 10 and unpivot only if needed into `OutputCaseID, Date, GasCumulative_MSCF, OilCumulative_STB, WaterCumulative_STB`. Supporting tables are `powerbi_forecast_long.csv`, `selected_realization_mapping.csv`, `case_parameters.csv`, `historical_case_screening.csv`, and `model_comparison_validation.csv`.\n\n## Pages\n\n1. **Field outlook:** history plus forecast cumulative/rate curves. Question: range and timing of oil decline/water burden. Filters: output case, phase, date.\n2. **History-match evidence:** observed vs supplied-case interval rates, residual and score table. Question: why selected cases are credible?\n3. **Reservoir uncertainty:** parameters versus historical/forecast outcomes, with SourceCaseID. Question: which sampled uncertainty combinations span outcomes?\n4. **Water/scenario decisions:** water rate, water cut and a What-If capacity parameter labelled as an assumption. Question: when would a user-supplied handling threshold be crossed?\n\n## Measures and safeguards\n\n- Latest cumulative = `CALCULATE(MAX(Forecast[OilCumulative_STB]), LASTDATE('Date'[Date]))`; never sum cumulative values across dates.\n- Increment = current cumulative minus previous date cumulative, by output case. Rate = Increment/days in interval.\n- Water cut = water rate/(oil rate + water rate), calculated from additive rates, not averaged row ratios.\n- Show one realization or percentile/median across alternatives; do not sum output cases as fields. Label spread “scenario/ensemble range”, not confidence interval.\n- Rates use STB/d for oil/water and MSCF/d for gas. Cumulatives retain template units.\n\nNo verified `.pbix` is produced because Power BI Desktop is not available in this environment.\n'''
    spatial_spec='''

## Reservoir Spatial Analysis

Load `08_SpatialGeometry.csv` (one row per `CellID = I:J:K`) and `09_SpatialCellProperties.parquet` (one row per **active** `CaseID, CellID`) with a one-to-many relationship from geometry to properties. Load `10_SpatialCaseSummary.csv`, `11_SpatialLayerSummary.csv`, and `12_SpatialRegionSummary.csv` as pre-aggregated tables. The Parquet cell table avoids a very large text CSV; Power Query Desktop supports importing local Parquet files. Coordinate, pressure, permeability and pore-volume units are **unspecified**. Do not use a map or geographic basemap.

Grain and aggregation: geometry is one grid cell; properties is one active cell per reservoir realization; layer/region summaries use active-cell count and total pore volume, PV-weighted porosity/saturations, and descriptive permeability percentiles. Never sum alternative `CaseID`s as separate fields. Directional permeability ratios are ratios of medians, not effective permeability.

Create a **Reservoir Spatial Analysis** page with Case, property and K-layer slicers; an I-J Matrix (rows J, columns I) with background-colour conditional formatting as a native heatmap; a fixed-I/fixed-J Matrix using K ordering only (not physical depth direction); a layer/region summary table; and a case-comparison matrix. For a continuous raster-like heatmap or linked cross-section chart, use an approved custom visual or Python/R visual only after confirming it is allowed by the challenge environment. Missing case-cell matches must stay blank; percentage differences apply only where the reference is nonzero.

Static verification figures are in `outputs/spatial_figures/`. They use grid indices because CRS/EPSG, Z direction, and snapshot timestamp are undocumented. Permeability panels use log10 only for positive values; zeros are explicitly marked and inactive cells remain blank/masked.
'''
    (OUT/'POWER_BI_SPECIFICATION.md').write_text(pbi + spatial_spec)
    (OUT/'PRESENTATION_STORYLINE.md').write_text('''# Seven-minute presentation storyline\n\n1. Problem: reproduce 1998–2008 behavior, then make transparent conditional 2008–2028 scenarios.\n2. Data: 100 static reservoir realizations, 70/15/15 split, observed field history; no future labels.\n3. Data-quality finding: compare cumulative-derived interval rates, not unaligned boundary rates.\n4. Benchmark: best supplied match and what it proves.\n5. Proxy validation: selected model, validation-first selection, isolated test result.\n6. Non-uniqueness: accepted parameter combinations and why surrogate matches do not prove true geology.\n7. Forecast: ten traceable scenarios, water burden, explicit assumptions.\n8. Dashboard: field outlook, match evidence, uncertainty, water decisions; close with validation and simulator-needed next step.\n''')
    (OUT/'RUN_GUIDE.md').write_text('''# Run guide\n\nRun from this workspace: `python3 analysis_codes/run_analysis.py`. Dependencies: Python 3.12, numpy, scipy, scikit-learn, matplotlib, pyarrow, joblib and the standard library. It reads only `TestCases/` and writes `work/`, `outputs/`, and `powerbi_ready_data/`. Random seed: 20261015.\n\nFor the spatial workflow alone, run `MPLCONFIGDIR=/tmp/dwc_mpl python3 analysis_codes/run_analysis.py --spatial-only`. Add `--refresh-spatial` to invalidate a valid cache deliberately. The spatial cache is automatically invalidated when source-workbook fingerprints, parser version, expected Cases 1–100, or full-extraction checks do not match.\n''')
    progress(9, 9, 'Complete: spatial outputs, reports, model, dashboard tables, and validated template written')
    print(json.dumps({'best_training_case':best,'selected_model':chosen_name,'validation_models':comp,'test_mean_combined_score':float(np.mean([x['combined_score'] for x in testrows])),'template_checks':checks},indent=2))

if __name__=='__main__': main()
