import os, re, time, random, string, threading
from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)
USERNAME_RE = re.compile(r"^[a-z0-9._]{3,30}$")
LOCK = threading.Lock()
LAST_CHECK = 0.0
MIN_DELAY = float(os.environ.get("MIN_CHECK_DELAY", "8"))
ALPHABET = string.ascii_lowercase

PAGE = r"""
<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Triple Username Scanner</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#eef2ff;font-family:Arial,sans-serif}
main{max-width:1000px;margin:30px auto;padding:18px}.panel{background:#151d33;border:1px solid #2b3858;border-radius:16px;padding:20px;margin:14px 0}
h1{margin:0 0 8px;font-size:25px}.muted{color:#aab6d3;line-height:1.7}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}input,button{padding:12px;border-radius:9px;border:1px solid #405071;background:#0e1730;color:white}
button{background:#6478ff;border:0;font-weight:bold;cursor:pointer}button:disabled{opacity:.5}
.stat{display:inline-block;padding:10px 14px;background:#0e1730;border-radius:10px;margin:4px}
table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #2b3858;text-align:right}
.badge{padding:5px 8px;border-radius:7px}.available{background:#124b38;color:#8ff0c2}.taken{background:#54232d;color:#ffb2bd}.unknown{background:#55451d;color:#ffe19a}
#log{max-height:360px;overflow:auto}progress{width:100%;height:12px}
</style></head><body><main>
<div class="panel"><h1>فاحص أسماء Instagram</h1>
<div class="muted">يبدأ بثلاثة أحرف فقط. بعد كل 15 اسمًا دون العثور على اسم متاح مبدئيًا، يزيد عدد النقاط أو الشرطات السفلية تدريجيًا. قد تكون نتائج Instagram غير حاسمة.</div></div>
<div class="panel"><h3>إعداد الفحص</h3><div class="row">
<label>عدد الأسماء <input id="count" type="number" min="1" max="300" value="60"></label>
<button id="start">ابدأ الفحص</button><button id="stop" disabled>إيقاف</button>
</div><p class="muted">الرموز المستخدمة: النقطة . والشرطة السفلية _. لا تُستخدم الشرطة العادية - لأنها غير مقبولة في أسماء Instagram. الفحص متتابع بفاصل زمني محافظ.</p>
<div id="status" class="muted">جاهز.</div><progress id="progress" value="0" max="100"></progress>
<div><span class="stat">تم الفحص: <b id="checked">0</b></span><span class="stat">متاح مبدئيًا: <b id="available">0</b></span><span class="stat">محجوز: <b id="taken">0</b></span><span class="stat">غير معروف: <b id="unknown">0</b></span></div></div>
<div class="panel"><div class="row" style="justify-content:space-between"><h3>النتائج</h3><button id="csv">تصدير CSV</button></div>
<div id="log"><table><thead><tr><th>الاسم</th><th>النتيجة</th><th>التفاصيل</th></tr></thead><tbody id="results"></tbody></table></div></div>
<script>
let stopFlag=false, rows=[];
const $=id=>document.getElementById(id);
function addRow(x){rows.unshift(x);let tr=document.createElement('tr');
let cls=x.status==='available'?'available':x.status==='taken'?'taken':'unknown';
let label=x.status==='available'?'متاح مبدئيًا':x.status==='taken'?'محجوز':'غير معروف';
for(const val of [x.username,label,x.detail||'']){let td=document.createElement('td');if(val===label){let b=document.createElement('span');b.className='badge '+cls;b.textContent=val;td.appendChild(b)}else td.textContent=val;tr.appendChild(td)}
$('results').prepend(tr);updateStats();}
function updateStats(){ $('checked').textContent=rows.length;
$('available').textContent=rows.filter(x=>x.status==='available').length;
$('taken').textContent=rows.filter(x=>x.status==='taken').length;
$('unknown').textContent=rows.filter(x=>x.status==='unknown').length;}
$('start').onclick=async()=>{
stopFlag=false;$('start').disabled=true;$('stop').disabled=false;$('results').innerHTML='';rows=[];updateStats();
try{
let total=Math.max(1,Math.min(300,+$('count').value||60));
let checked=0, stage=0, stageTried=0, found=false;
while(checked<total&&!stopFlag){
let g=await fetch('/api/next',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage})});
let candidate=await g.json(); if(!g.ok)throw Error(candidate.error||'تعذر توليد الاسم');
if(candidate.done){stage++;stageTried=0;continue;}
$('status').textContent=`المرحلة ${stage+1} — يفحص: ${candidate.username}`;
let res=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:candidate.username})});
let item=await res.json();addRow(item);checked++;stageTried++;
$('progress').value=(checked/total)*100;
if(item.status==='available'){found=true;stageTried=0;}
if(stageTried>=15&&!found){stage++;stageTried=0;$('status').textContent=`لم يجد اسمًا متاحًا بعد 15 محاولة؛ ينتقل إلى ${stage} رمز/رموز.`;}
if(found){stage=0;stageTried=0;found=false;}
}
$('status').textContent=stopFlag?'تم إيقاف الفحص.':'انتهى الفحص.';
}catch(e){$('status').textContent='خطأ: '+e.message;}
$('start').disabled=false;$('stop').disabled=true;
};
$('stop').onclick=()=>{stopFlag=true;$('status').textContent='جارٍ إيقاف الفحص بعد الطلب الحالي...';};
$('csv').onclick=()=>{let csv='username,status,detail\n'+rows.map(x=>[x.username,x.status,x.detail].map(v=>'"'+String(v||'').replaceAll('"','""')+'"').join(',')).join('\n');
let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download='instagram-check-results.csv';a.click();};
</script></main></body></html>
"""

# Per-stage random unique candidates; stage 0 = no symbols, stage 1 = one symbol, etc.
STAGE_CACHE = {}
STAGE_LOCK = threading.Lock()

def build_stage_candidates(stage, limit=500):
    symbols = "._"
    out=set()
    attempts=0
    while len(out)<limit and attempts<limit*100:
        attempts+=1
        # Exactly three letters, plus the stage number of punctuation symbols.
        slots=3+stage
        chars=[random.choice(ALPHABET) for _ in range(3)]
        positions=random.sample(range(slots), stage) if stage else []
        name=[]
        letter_i=0
        for i in range(slots):
            if i in positions:
                name.append(random.choice(symbols))
            else:
                name.append(chars[letter_i]); letter_i+=1
        candidate="".join(name)
        if candidate[0] not in symbols and candidate[-1] not in symbols and ".." not in candidate and "__" not in candidate:
            out.add(candidate)
    return list(out)

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.post("/api/next")
def next_name():
    data=request.get_json(silent=True) or {}
    stage=max(0,min(int(data.get("stage",0)),27))
    with STAGE_LOCK:
        if stage not in STAGE_CACHE or not STAGE_CACHE[stage]:
            STAGE_CACHE[stage]=build_stage_candidates(stage,500)
        if not STAGE_CACHE[stage]:
            return jsonify(done=True)
        return jsonify(username=STAGE_CACHE[stage].pop(),done=False)

def check_public_profile(username):
    global LAST_CHECK
    with LOCK:
        wait=MIN_DELAY-(time.time()-LAST_CHECK)
        if wait>0: time.sleep(wait)
        LAST_CHECK=time.time()
    try:
        r=requests.get(f"https://www.instagram.com/{username}/",
            headers={"User-Agent":"Mozilla/5.0"},timeout=15,allow_redirects=True)
        if r.status_code in (401,403,429) or "login" in r.url.lower() or "challenge" in r.url.lower():
            return "unknown",f"Instagram قيّد الطلب أو طلب تسجيل الدخول (HTTP {r.status_code})"
        if r.status_code==404:
            return "available","404 مؤشر أولي فقط؛ لا يثبت إمكانية التسجيل"
        if r.status_code==200:
            body=r.text.lower()
            if f'"username":"{username}"' in body:
                return "taken","ظهرت بيانات الملف؛ تحقق يدويًا"
            return "unknown","استجابة 200 غير حاسمة"
        return "unknown",f"استجابة غير حاسمة (HTTP {r.status_code})"
    except requests.RequestException as e:
        return "unknown","تعذّر الاتصال: "+type(e).__name__

@app.post("/api/check")
def check():
    data=request.get_json(silent=True) or {}
    username=str(data.get("username","")).lower()
    if not USERNAME_RE.fullmatch(username) or sum(c in string.ascii_lowercase for c in username)<3:
        return jsonify(username=username,status="unknown",detail="يجب أن يحتوي الاسم على ثلاثة أحرف إنجليزية على الأقل"),400
    if username.startswith((".", "_")) or username.endswith((".", "_")) or ".." in username or "__" in username:
        return jsonify(username=username,status="unknown",detail="موضع الرموز غير صالح"),400
    status,detail=check_public_profile(username)
    return jsonify(username=username,status=status,detail=detail)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
