"""Genera un HTML autocontenido con los eventos: se abre con doble clic, sin servidor ni red.

    cd research && uv run python src/export_events_html.py

Entrada : data/events_export.parquet + reports/eventos_export.json (los crea src/export_events.py)
Salida  : reports/eventos.html

Por qué existe además de la vista de la SPA: para ver los eventos en la SPA hacen falta Python,
uv, el intérprete correcto, un servidor levantado y salida a internet (la SPA carga Chart.js de un
CDN). Este fichero no necesita nada de eso — los datos van incrustados y el CSS y el JS son
inline — así que se puede abrir en cualquier máquina y mandar por correo.

Navega como el producto: cartera -> grupo -> empresa. Sin selección se ve la cartera entera en
un mes; al elegir un grupo se ven sus empresas hermanas (que se prestan caja entre ellas antes que
a un banco, así que se miran juntas); al elegir una empresa, su historia completa mes a mes.

Reutiliza los tokens de app/DESIGN.md: el violeta es sólo acento de marca y nunca codifica un
valor; las severidades usan los tokens de estado (riesgo=--crit, mejora=--good, ruido=--muted).
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from export_events import CATALOG, COLS, TEXTS, month_label  # noqa: E402

SPA = ROOT / "app" / "static" / "index.html"
OUT = ROOT / "reports" / "eventos.html"


def spa_tokens() -> str:
    """Los bloques :root de la SPA, para que este HTML se vea exactamente igual que el producto."""
    s = SPA.read_text(encoding="utf-8")
    light = re.search(r"(:root \{.*?\n\})", s, re.S)
    dark = re.search(r'(@media \(prefers-color-scheme: dark\) \{.*?\n  \}\n\})', s, re.S)
    out = light.group(1) if light else ""
    if dark:
        out += "\n" + dark.group(1)
    return out


def build_rows(ev: pd.DataFrame) -> list[dict]:
    rows = []
    for r in ev.itertuples(index=False):
        for t in COLS:
            if int(getattr(r, t, 0)) > 0:
                rows.append({"c": r.company_id, "g": r.group_id, "m": r.month, "t": t,
                             "x": TEXTS[t].format(c=r.company_id)})
    rows.sort(key=lambda e: (e["m"], e["c"], e["t"]))
    return rows


def company_meta() -> dict[str, dict]:
    """Moneda y ERP por empresa, de data/companies.csv (está en el repo, no es LFS)."""
    f = ROOT.parent / "data" / "companies.csv"
    if not f.exists():
        return {}
    c = pd.read_csv(f, usecols=["company_id", "group_id", "currency", "erp"])
    return {r.company_id: {"g": r.group_id, "cur": r.currency,
                           "erp": (r.erp if isinstance(r.erp, str) and r.erp else None)}
            for r in c.itertuples(index=False)}


CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 var(--font)}
.wrap{max-width:1280px;margin:0 auto;padding:28px clamp(16px,4vw,40px) 64px}
header.top{border-bottom:1px solid var(--line);background:var(--surface);position:sticky;top:0;z-index:5}
header.top .inner{max-width:1280px;margin:0 auto;padding:14px clamp(16px,4vw,40px);display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.logo{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;background:var(--accent);color:var(--accent-ink);font-weight:700}
.brand{font-weight:600;letter-spacing:-.02em}
.tag{color:var(--muted);font-size:12.5px;border-left:1px solid var(--line);padding-left:14px}
h1{font-size:clamp(26px,4vw,34px);letter-spacing:-.03em;margin:26px 0 8px}
.lede{color:var(--ink-2);max-width:78ch;margin:0 0 22px}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}
.tile{text-align:left;padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--surface);cursor:pointer;font:inherit;color:inherit;box-shadow:var(--shadow)}
.tile:hover{border-color:var(--line-strong)}
.tile[aria-pressed="true"]{border-color:var(--ink);box-shadow:inset 0 0 0 1px var(--ink)}
.tile-label{display:flex;gap:8px;align-items:center;font-size:12.5px;color:var(--ink-2);font-weight:500}
.tile-value{display:block;font-size:30px;font-weight:600;letter-spacing:-.02em;line-height:1.15}
.tile-sub{display:block;font-size:12px;color:var(--muted)}
.bar{display:block;height:4px;border-radius:2px;background:var(--surface-3);overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;border-radius:2px}
.filterbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0 16px}
.seg{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--line);border-radius:999px;background:var(--surface-2)}
.seg button{border:0;background:none;font:inherit;color:var(--ink-2);padding:6px 13px;border-radius:999px;cursor:pointer;display:inline-flex;gap:7px;align-items:center}
.seg button[aria-pressed="true"]{background:var(--ink);color:var(--bg)}
.seg .n{opacity:.62;font-size:12px}
select{font:inherit;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:7px 11px}
.row{display:grid;grid-template-columns:118px 1fr auto;gap:14px;align-items:center;padding:13px 16px;border:1px solid var(--line);border-radius:12px;background:var(--surface);margin-bottom:8px}
.row.riesgo{border-left:3px solid var(--crit)}
.row.mejora{border-left:3px solid var(--good)}
.row.ruido{border-left:3px solid var(--line-strong)}
.chip{display:inline-flex;gap:6px;align-items:center;padding:3px 9px;border:1px solid var(--line);border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.chip.riesgo{color:var(--crit-text)}
.chip.mejora{color:var(--good-text)}
.chip.ruido{color:var(--muted)}
.chip.ghost{font-weight:500;color:var(--ink-2)}
.top-line{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:3px}
.cid{font-family:var(--mono);font-weight:600;font-size:13px}
.txt{margin:0;font-size:14px}
.why{margin:3px 0 0;font-size:12.5px;color:var(--muted)}
.when{color:var(--muted);font-size:12px}
.empty{padding:34px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:12px}
.foot{display:flex;justify-content:center;padding:14px 0}
.btn{font:inherit;padding:7px 14px;border:1px solid var(--line);border-radius:9px;background:var(--surface);color:var(--ink);cursor:pointer}
.btn:hover{border-color:var(--line-strong)}
details.cat{margin-top:26px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
details.cat summary{padding:14px 16px;cursor:pointer;font-weight:600}
.catgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:0 16px 16px}
.card{border:1px solid var(--line);border-radius:10px;padding:14px;background:var(--bg)}
.card h3{margin:0 0 6px;font-size:14px;display:flex;gap:8px;align-items:center}
.card p{margin:0 0 6px;font-size:13px;line-height:1.5}
.card .excl{font-style:italic;color:var(--ink-2)}
.note{margin-top:26px;padding:14px 16px;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;background:var(--surface);color:var(--ink-2);font-size:13px}
.note b{color:var(--ink)}
.pickers{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin:0 0 18px}
.picker{display:flex;flex-direction:column;gap:4px}
[hidden]{display:none!important}
.picker label{font-size:12px;color:var(--muted)}
.picker select{min-width:260px;max-width:min(420px,90vw)}
.crumbs{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:6px;font-size:12.5px}
.crumb{border:0;background:none;font:inherit;font-size:12.5px;color:var(--muted);cursor:pointer;padding:0;text-decoration:underline;text-underline-offset:2px}
.crumb.on{color:var(--ink);font-weight:600;cursor:default;text-decoration:none}
.crumbs .sep{color:var(--line-strong)}
.metachips{display:inline-flex;gap:6px;margin-left:10px;flex-wrap:wrap}
.mhead{margin:16px 0 8px;font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}
.link{border:0;background:none;padding:0;cursor:pointer;color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.link:hover{color:var(--brand)}
@media(max-width:900px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.catgrid{grid-template-columns:1fr}.row{grid-template-columns:1fr;gap:8px}.picker select{min-width:0;width:100%}.picker{width:100%}}
"""

JS = """
// mismos iconos que la SPA (app/static/index.html), para que la previsión se vea como el producto
const ICONS={alert:'<path d="M8 2.5l6 11H2z"/><path d="M8 6.5v3M8 11.6v.1"/>',up:'<path d="M3 11l5-5 5 5"/>',flat:'<path d="M2.5 8h11M10 5l3 3-3 3"/>'};
const ico=(n,color)=>{const s=document.createElement('span');s.setAttribute('aria-hidden','true');s.style.display='inline-flex';if(color)s.style.color=color;s.innerHTML='<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'+(ICONS[n]||'')+'</svg>';return s};
const SEV={riesgo:{l:'Riesgo',i:'alert',c:'var(--crit)'},mejora:{l:'Mejora',i:'up',c:'var(--good)'},ruido:{l:'Ruido',i:'flat',c:'var(--muted)'}};
const BY=Object.fromEntries(D.catalog.map(c=>[c.type,c]));
const NF=new Intl.NumberFormat('es-ES');
const st={group:'',company:'',month:D.month,type:'',sev:'',limit:60};
const $=s=>document.querySelector(s);
const el=(t,a,...k)=>{const n=document.createElement(t);for(const[p,v]of Object.entries(a||{})){if(p==='class')n.className=v;else if(p.startsWith('on'))n.addEventListener(p.slice(2),v);else if(v!=null)n.setAttribute(p,v)}for(const c of k.flat())if(c!=null)n.append(c.nodeType?c:document.createTextNode(c));return n};
const rate=t=>{const r=D.rates[t];if(!r)return'';return (r.tasa>=1?NF.format(Math.round(r.tasa)):r.tasa.toFixed(2).replace('.',','))+' % histórico'};
const plural=(n,a,b)=>NF.format(n)+' '+(n===1?a:b);

/* Ámbito: empresa (toda su historia) > grupo (todas sus hermanas) > cartera (un mes). */
function scope(){
  if(st.company) return {rows:D.rows.filter(r=>r.c===st.company),kind:'empresa'};
  if(st.group)   return {rows:D.rows.filter(r=>r.g===st.group),kind:'grupo'};
  return {rows:D.rows.filter(r=>r.m===st.month),kind:'cartera'};
}

function fillGroups(){
  const g=$('#group');
  g.replaceChildren(el('option',{value:''},'Toda la cartera ('+NF.format(D.groups.length)+' grupos)'),
    ...D.groups.map(x=>el('option',{value:x.id},x.id+' — '+plural(x.n,'empresa','empresas')+', '+plural(x.ev,'evento','eventos'))));
  g.value=st.group;
}
function fillCompanies(){
  const c=$('#company');
  const list=st.group?D.companies.filter(x=>x.g===st.group):D.companies;
  c.replaceChildren(el('option',{value:''},st.group?'Todas las del grupo ('+list.length+')':'Todas las empresas ('+NF.format(list.length)+')'),
    ...list.map(x=>el('option',{value:x.id},x.id+' — '+plural(x.ev,'evento','eventos'))));
  c.value=st.company;
  c.disabled=list.length===0;
}

function draw(){
  fillCompanies();
  const {rows:all,kind}=scope();
  const perMonth=kind==='cartera';
  $('#monthwrap').hidden=!perMonth;

  // Cabecera contextual: quién estoy mirando y qué abarca
  const meta=st.company?D.meta[st.company]:null;
  $('#crumb').replaceChildren(...[
    el('button',{class:'crumb'+(st.group||st.company?'':' on'),type:'button',onclick:()=>{st.group='';st.company='';st.limit=60;draw()}},'Cartera'),
    st.group?el('span',{class:'sep'},'/'):null,
    st.group?el('button',{class:'crumb'+(st.company?'':' on'),type:'button',onclick:()=>{st.company='';st.limit=60;draw()}},st.group):null,
    st.company?el('span',{class:'sep'},'/'):null,
    st.company?el('span',{class:'crumb on'},st.company):null
  ].filter(x=>x!=null));
  $('#title').textContent=st.company||st.group||'Eventos de la cartera';
  const uniq=new Set(all.map(r=>r.c)).size;
  $('#sub').replaceChildren(...[
    perMonth?plural(all.length,'evento','eventos')+' en '+plural(uniq,'empresa','empresas')+' · '+(D.labels[st.month]||st.month)
      :plural(all.length,'evento','eventos')+' en toda la historia'+(kind==='grupo'?' · '+plural(uniq,'empresa con eventos','empresas con eventos'):''),
    meta?el('span',{class:'metachips'},
      el('span',{class:'chip ghost'},'Grupo '+meta.g),
      el('span',{class:'chip ghost'},meta.cur||'—'),
      el('span',{class:'chip ghost'},meta.erp?('ERP '+meta.erp.toUpperCase()):'Sin ERP')):null
  ].filter(x=>x!=null));

  // Tiles por tipo, sobre el ámbito elegido
  const counts={};D.catalog.forEach(c=>counts[c.type]=0);all.forEach(r=>counts[r.t]++);
  $('#tiles').replaceChildren(...D.catalog.map(c=>{
    const n=counts[c.type]||0,s=SEV[c.severity]||SEV.ruido,on=st.type===c.type;
    return el('button',{class:'tile','aria-pressed':String(on),title:c.desc,onclick:()=>{st.type=on?'':c.type;st.limit=60;draw()}},
      el('span',{class:'tile-label'},ico(s.i,s.c),c.label),
      el('span',{class:'tile-value'},NF.format(n)),
      el('span',{class:'tile-sub'},[rate(c.type),c.horizon].filter(Boolean).join(' · ')),
      el('span',{class:'bar','aria-hidden':'true'},el('i',{style:'width:'+(all.length?100*n/all.length:0)+'%;background:'+s.c})));
  }));

  const sevN=s=>all.filter(r=>(BY[r.t]||{}).severity===s).length;
  const mk=(v,l,n)=>el('button',{type:'button','aria-pressed':String(st.sev===v),onclick:()=>{st.sev=v;st.limit=60;draw()}},l,el('span',{class:'n'},NF.format(n)));
  $('#seg').replaceChildren(mk('','Todas',all.length),...Object.keys(SEV).map(k=>mk(k,SEV[k].l,sevN(k))));

  let shown=all.filter(r=>(!st.type||r.t===st.type)&&(!st.sev||(BY[r.t]||{}).severity===st.sev));
  if(!perMonth) shown=[...shown].reverse();      // ficha: lo más reciente primero
  const page=shown.slice(0,st.limit);

  // En ámbito empresa/grupo la lista se agrupa por mes: es una historia, no un listado
  const out=[];let last=null;
  for(const r of page){
    if(!perMonth&&r.m!==last){last=r.m;out.push(el('div',{class:'mhead'},D.labels[r.m]||r.m))}
    const c=BY[r.t]||{},s=SEV[c.severity]||SEV.ruido;
    out.push(el('article',{class:'row '+(c.severity||'ruido')},
      el('div',null,el('span',{class:'chip '+(c.severity||'ruido')},ico(s.i),s.l)),
      el('div',null,
        el('div',{class:'top-line'},
          st.company?null:el('button',{class:'cid link',type:'button',onclick:()=>{st.company=r.c;st.group=r.g;st.limit=60;draw();window.scrollTo(0,0)}},r.c),
          el('span',{class:'chip ghost'},(c.code||r.t)+' · '+(c.label||r.t)),
          perMonth?el('span',{class:'when'},D.labels[r.m]||r.m):null),
        el('p',{class:'txt'},r.x),
        c.short?el('p',{class:'why'},c.short):null),
      el('div',null)));
  }
  $('#list').replaceChildren(...(page.length?out:[el('div',{class:'empty'},
    st.company?'Esta empresa no tiene ningún evento en toda la serie.':'No hay eventos con este filtro.')]));
  $('#foot').replaceChildren(shown.length>page.length
    ?el('button',{class:'btn',type:'button',onclick:()=>{st.limit+=60;draw()}},'Ver más ('+NF.format(shown.length-page.length)+' restantes)')
    :el('span',{class:'when'},shown.length?NF.format(shown.length)+' eventos mostrados.':''));
}

const selM=$('#month');
D.months.forEach(m=>selM.append(el('option',{value:m,...(m===st.month?{selected:'selected'}:{})},D.labels[m]||m)));
selM.addEventListener('change',e=>{st.month=e.target.value;st.limit=60;draw()});
$('#group').addEventListener('change',e=>{st.group=e.target.value;st.company='';st.limit=60;draw()});
$('#company').addEventListener('change',e=>{st.company=e.target.value;if(st.company)st.group=D.meta[st.company]?D.meta[st.company].g:st.group;fillGroups();st.limit=60;draw()});
$('#cat').replaceChildren(...D.catalog.map(c=>{
  const s=SEV[c.severity]||SEV.ruido,r=D.rates[c.type];
  return el('article',{class:'card'},
    el('h3',null,ico(s.i,s.c),c.label,el('span',{class:'when'},c.horizon)),
    el('p',null,c.desc),el('p',{class:'why'},c.why),c.excl?el('p',{class:'excl'},c.excl):null,
    r?el('p',{class:'when'},NF.format(r.positivos)+' de '+NF.format(r.n)+' meses etiquetados.'):null);
}));
fillGroups();draw();
"""


def main() -> None:
    meta = json.loads((ROOT / "reports" / "eventos_export.json").read_text(encoding="utf-8"))
    ev = pd.read_parquet(ROOT / "data" / "events_export.parquet")
    rows = build_rows(ev)
    months = sorted({r["m"] for r in rows})
    cmeta = company_meta()

    # grupos y empresas con su recuento de eventos, para que los desplegables ya orienten
    ev_by_company: dict[str, int] = {}
    for r in rows:
        ev_by_company[r["c"]] = ev_by_company.get(r["c"], 0) + 1
    comp_group = {r["c"]: r["g"] for r in rows}
    companies = [{"id": c, "g": comp_group[c], "ev": n}
                 for c, n in sorted(ev_by_company.items(), key=lambda kv: (-kv[1], kv[0]))]
    groups: dict[str, dict] = {}
    for c in companies:
        g = groups.setdefault(c["g"], {"id": c["g"], "n": 0, "ev": 0})
        g["n"] += 1
        g["ev"] += c["ev"]
    groups = sorted(groups.values(), key=lambda g: (-g["ev"], g["id"]))

    data = {
        "month": meta["month"], "rows": rows, "months": months,
        "labels": {m: month_label(m) for m in months},
        "catalog": CATALOG, "rates": meta.get("rates_6m", {}),
        "groups": groups, "companies": companies,
        "meta": {c["id"]: cmeta.get(c["id"], {"g": c["g"]}) for c in companies},
        "last_observable": meta.get("last_observable", {}),
        "last_month_panel": meta.get("last_month_panel"),
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    obs = data["last_observable"]
    detalle = " · ".join(f"{k} hasta {v}" for k, v in obs.items() if k in ("E1_clean", "E2_strict", "E5_bache"))
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eventos · X-Ray</title>
<style>{spa_tokens()}{CSS}</style>
</head><body>
<header class="top"><div class="inner">
  <span class="logo" aria-hidden="true">X</span><span class="brand">X-Ray</span>
  <span class="tag">Eventos de salud financiera · previsión de la vista del front</span>
</div></header>
<div class="wrap">
  <p class="lede">Las etiquetas con las que se entrenará el modelo, tal y como se verán en el
  producto. Elige un grupo para ver sus empresas hermanas, o una empresa para su historia completa.</p>
  <div class="pickers">
    <div class="picker"><label for="group">Grupo</label><select id="group"></select></div>
    <div class="picker"><label for="company">Empresa</label><select id="company"></select></div>
    <div class="picker" id="monthwrap"><label for="month">Mes</label><select id="month"></select></div>
  </div>
  <div class="crumbs" id="crumb"></div>
  <h1 id="title"></h1>
  <p class="lede" id="sub"></p>
  <div class="tiles" id="tiles"></div>
  <div class="filterbar"><div class="seg" id="seg" role="group" aria-label="Filtrar por severidad"></div></div>
  <div id="list"></div><div class="foot" id="foot"></div>
  <details class="cat"><summary>Qué significa cada evento</summary><div class="catgrid" id="cat"></div></details>
  <p class="note"><b>Por qué los últimos meses parecen tranquilos.</b> Las etiquetas miran 6 meses
  hacia delante, así que en la cola del panel no se pueden calcular todavía: no es que no haya
  riesgo, es que aún no se puede saber. {detalle}. El panel llega a {data['last_month_panel']}.
  El mes que se abre por defecto ({month_label(data['month'])}) es el último en que todas las
  señales son observables.</p>
</div>
<script>const D={blob};{JS}</script>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    print(f"{OUT.relative_to(ROOT)}  ({kb:.0f} KB, {len(rows)} eventos, {len(months)} meses, "
          f"{len(data['companies'])} empresas, {len(data['groups'])} grupos)")
    print("Se abre con doble clic: no necesita servidor, ni Python, ni conexión.")


if __name__ == "__main__":
    main()
