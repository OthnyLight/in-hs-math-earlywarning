// 01b_fetch_urban_browser.js — the exact script run (in three pieces) in the author's browser on
// 2026-10-09 to produce data/raw/urban_ccd_dir_2022_hs.csv and
// data/raw/urban_crdc_hs_2017_2020_2023.csv. Kept verbatim for provenance.
// The build sandbox could not reach educationdata.urban.org; the outputs were carried over
// as text and verified by SHA-256 (see data/raw/PROVENANCE.txt).
// code/01b_fetch_urban.py is the maintained Python equivalent.
//
// KNOWN QUIRK (documented in docs/LIMITATIONS.md): in the add() helper below, a blank API value
// coerces to 0, and a negative "not applicable" code (-2) for grade 7 followed by a real grade-8
// count is summed (e.g. -2 + 30 = 28). This affects only the a1e78/a1p78 columns (Algebra I taken
// in grades 7–8 inside a building that also serves grade 12), which the model does not use.

// ---- piece 1: fetch -------------------------------------------------------------------------
async function all(u){let out=[];let next=u;while(next){const j=await (await fetch(next)).json();out=out.concat(j.results);next=j.next;}return out;}
function csv(rows){if(!rows.length)return'';const k=Object.keys(rows[0]);return [k.join(',')].concat(rows.map(r=>k.map(c=>{const v=r[c];return v==null?'':(typeof v==='string'&&/[",]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v)}).join(','))).join('\n');}
const B="https://educationdata.urban.org/api/v1/schools/";
const jobs={
 "crdc_algebra1_2017.csv":B+"crdc/algebra1/2017/race/sex/?fips=18&race=99&sex=99",
 "crdc_algebra1_2020.csv":B+"crdc/algebra1/2020/race/sex/?fips=18&race=99&sex=99",
 "crdc_algebra1_2021.csv":B+"crdc/algebra1/2021/race/sex/?fips=18&race=99&sex=99",
 "crdc_mathsci_2017.csv":B+"crdc/math-and-science/2017/race/sex/?fips=18&race=99&sex=99",
 "crdc_mathsci_2020.csv":B+"crdc/math-and-science/2020/race/sex/?fips=18&race=99&sex=99",
 "crdc_mathsci_2021.csv":B+"crdc/math-and-science/2021/race/sex/?fips=18&race=99&sex=99",
 "crdc_offerings_2017.csv":B+"crdc/offerings/2017/?fips=18",
 "crdc_offerings_2020.csv":B+"crdc/offerings/2020/?fips=18",
 "crdc_offerings_2021.csv":B+"crdc/offerings/2021/?fips=18",
 "crdc_offerings_2023.csv":B+"crdc/offerings/2023/?fips=18",
 "ccd_directory_2022.csv":B+"ccd/directory/2022/?fips=18"};
window.__crdc={};
for(const [n,u] of Object.entries(jobs)){const rows=await all(u);window.__crdc[n]=csv(rows);}

// ---- piece 2: reduce to high schools (highest grade offered = 12) ----------------------------
const c=window.__crdc;
function parse(text){const rows=[];let row=[],f='',q=false;for(let i=0;i<text.length;i++){const ch=text[i];if(q){if(ch=='"'){if(text[i+1]=='"'){f+='"';i++}else q=false}else f+=ch}else{if(ch=='"')q=true;else if(ch==','){row.push(f);f=''}else if(ch=='\n'){row.push(f);rows.push(row);row=[];f=''}else f+=ch}}row.push(f);rows.push(row);return rows;}
function obj(name){const d=parse(c[name]);const h=d[0];return d.slice(1).filter(r=>r.length==h.length).map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i]])));}
const dir=obj('ccd_directory_2022.csv').filter(r=>r.highest_grade_offered=='12');
const hs=new Set(dir.map(r=>r.ncessch));
const D=dir.map(r=>[r.ncessch,r.seasch,r.latitude,r.longitude,r.urban_centric_locale,r.charter,r.enrollment,r.free_or_reduced_price_lunch,r.lowest_grade_offered,r.virtual||''].join(','));
const rec={};const g=(s,y)=>{const k=s+'|'+y;return rec[k]||(rec[k]={s,y})};
for(const y of [2017,2020,2021]){
 for(const r of obj('crdc_algebra1_'+y+'.csv')){if(!hs.has(r.ncessch))continue;const o=g(r.ncessch,y);const gc=r.grade_crdc;const b=(gc=='20'||gc=='7'||gc=='8')?'78':gc=='21'?'910':gc=='22'?'1112':null;if(!b)continue;const add=(k,v)=>{v=+v;if(isNaN(v))return;o[k]=(o[k]==null?0:o[k])+(v<0&&o[k]!=null&&o[k]>=0?0:v);};add('a1e'+b,r.enrl_algebra1);add('a1p'+b,r.students_passing_algebra1);}
 for(const r of obj('crdc_mathsci_'+y+'.csv')){if(!hs.has(r.ncessch))continue;const o=g(r.ncessch,y);o.e_alg2=r.enrl_algebra2;o.e_adv=r.enrl_advanced_math;o.e_calc=r.enrl_calculus;o.e_geom=r.enrl_geometry;}}
for(const y of [2017,2020,2021,2023]) for(const r of obj('crdc_offerings_'+y+'.csv')){if(!hs.has(r.ncessch))continue;const o=g(r.ncessch,y);o.c_alg2=r.num_classes_algebra2;o.c_adv=r.num_classes_advanced_math;o.c_calc=r.num_classes_calculus;o.ap_math=r.ap_courses_math_indicator;o.n_ap=r.num_courses_ap;o.dual=r.sch_dual_indicator;o.fte_math=r.num_fte_teachers_certified_math;}
const cols=['s','y','a1e78','a1p78','a1e910','a1p910','a1e1112','a1p1112','e_alg2','e_adv','e_calc','e_geom','c_alg2','c_adv','c_calc','ap_math','n_ap','dual','fte_math'];
const C=Object.values(rec).map(o=>cols.map(k=>o[k]==null?'':o[k]).join(','));
window.__dirtxt='ncessch,seasch,lat,lon,locale,charter,enrollment,frl,lowgr,virtual\n'+D.join('\n');
window.__crdctxt=cols.join(',')+'\n'+C.join('\n');

// ---- piece 3: tidy codes, drop CRDC 2021-22 rows, round coordinates --------------------------
// Urban missing-data codes: -1 missing, -2 not applicable, -3 suppressed  ->  -2 => NA, -1/-3 => X
{const L=window.__crdctxt.split('\n');const h=L[0].split(',');const drop=['e_geom','fte_math'].map(k=>h.indexOf(k));
window.__T=L.map(l=>l.split(',').filter((_,i)=>!drop.includes(i)).map(v=>v.replace(/\.0+$/,'').replace(/^-2$/,'NA').replace(/^-[13]$/,'X')).join(',')).join('\n');
window.__D=window.__dirtxt.split('\n').map(l=>{const f=l.split(',');if(f[2]&&!isNaN(+f[2])){f[2]=(+f[2]).toFixed(4);f[3]=(+f[3]).toFixed(4);}return f.join(',')}).join('\n');
window.__T2=window.__T.split('\n').filter((l,i)=>i==0||l.split(',')[1]!=='2021').join('\n');}
// urban_ccd_dir_2022_hs.csv          = window.__D   (sha256 3926f7e3…)
// urban_crdc_hs_2017_2020_2023.csv   = window.__T2  (sha256 49db48b0…)
