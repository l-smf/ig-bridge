import os, re, time, csv, io, itertools, string, threading
from flask import Flask, request, jsonify, render_template_string, Response
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this")
USERNAME_RE = re.compile(r"^[a-z0-9._]{3}$")
ALPHABET = string.ascii_lowercase + string.digits
LOCK = threading.Lock()
LAST_CHECK = 0.0
MIN_DELAY = float(os.environ.get("MIN_CHECK_DELAY", "8"))

PAGE = r"""
<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Triple Username Scanner</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#eef2ff;font-family:Arial,sans-serif}
main{max-width:1000px;margin:35px auto;padding:20px}.panel{background:#151d33;border:1px solid #2b3858;border-radius:16px;padding:20px;margin:14px 0}
h1{margin:0 0 8px;font-size:27px}.muted{color:#aab6d3;line-height:1.7}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}input,select,button{padding:12px;border-radius:9px;border:1px solid #405071;background:#0e1730;color:white}
button{background:#6478ff;border:0;font-weight:bold;cursor:pointer}button:disabled{opacity:.5}
.stat{display:inline-block;padding:10px 14px;background:#0e1730;border-radius:10px;margin:4px}
table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #2b3858;text-align:right}
.badge{padding:5px 8px;border-radius:7px}.available{background:#124b38;color:#8ff0c2}.taken{background:#54232d;color:#ffb2bd}.unknown{background:#55451d;color:#ffe19a}
#log{max-height:330px;overflow:auto}a{color:#aabaff}progress{width:100%;height:12px}
</style></head><body><main>
<div class="panel"><h1>فاحص أسماء Instagram الثلاثية</h1>
<div class="muted">الفحص يعمل من السيرفر السحابي. النتائج تقديرية فقط؛ Instagram قد يمنع الطلبات أو يعرض صفحة تسجيل دخول، وعندها ستظهر النتيجة «غير معروف».</div></div>
<div class="panel"><h3>إعداد الفحص</h3><div class="row">
<label>عدد الأسماء <input id="count" type="number" min="1" max="300" value="30"></label>
<label>النمط <select id="mode"><option value="letters">حروف فقط</option><option value="alnum">حروف وأرقام</option><option value="all">حروف وأرقام ونقطة وشرطة سفلية</option></select></label>
<label>بادئة اختيارية <input id="prefix" maxlength="2" placeholder="مثال: sa"></label>
<button id="start">ابدأ الفحص</button><button id="stop" disabled>إيقاف</button>
</div><p class="muted">لمنع الضغط على الخدمة، الفحص متتابع وبفاصل زمني لا يقل عن عدة ثوانٍ. لا تستخدمه لإرسال طلبات كثيفة.</p>
<div id="status" class="muted">جاهز.</div><progress id="progress" value="0" max="100"></progress>
<div><span class="stat">تم الفحص: <b id="checked">0</b></span><span class="stat">متاح مبدئيًا: <b id="available">0</b></span><span class="stat">محجوز: <b id="taken">0</b></span><span class="stat">غير معروف: <b id="unknown">0</b></span></div>
</div>
<div class="panel"><div class="row" style="justify-content:space-between"><h3>النتائج</h3><button id="csv">تصدير CSV</button></div>
<div id="log"><table><thead><tr><th>الاسم</th><th>النتيجة</th><th>التفاصيل</th></tr></thead><tbody id="results"></tbody></table></div></div>
<script>
let stopFlag=false, rows=[];
const $=id=>document.getElementById(id);
function addRow(x){rows.unshift(x);let tr=document.createElement('tr');
let cls=x.status==='available'?'available':x.status==='taken'?'taken':'unknown';
let label=x.status==='available'?'متاح مبدئيًا':x.status==='taken'?'محجوز':'غير معروف';
tr.innerHTML=`<td><b>${x.username}</b></td><td><span class="badge ${cls}">${label}</span></td><td>${x.detail||''}</td>`;
$('results').prepend(tr);updateStats();}
function updateStats(){ $('checked').textContent=rows.length;
$('available').textContent=rows.filter(x=>x.status==='available').length;
$('taken').textContent=rows.filter(x=>x.status==='taken').length;
$('unknown').textContent=rows.filter(x=>x.status==='unknown').length;}
$('start').onclick=async()=>{
stopFlag=false;$('start').disabled=true;$('stop').disabled=false;
$('results').innerHTML='';rows=[];updateStats();
try{
let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({count:+$('count').value,mode:$('mode').value,prefix:$('prefix').value})});
let data=await r.json();if(!r.ok)throw Error(data.error||'تعذر إنشاء القائمة');
let names=data.usernames;
for(let i=0;i<names.length;i++){
if(stopFlag)break;
$('status').textContent=`يفحص ${i+1} من ${names.length}: ${names[i]}`;
$('progress').value=(i/names.length)*100;
let res=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:names[i]})});
let item=await res.json();addRow(item);
}
$('progress').value=100;$('status').textContent=stopFlag?'تم إيقاف الفحص.':'انتهى الفحص.';
}catch(e){$('status').textContent='خطأ: '+e.message;}
$('start').disabled=false;$('stop').disabled=true;
};
$('stop').onclick=()=>{stopFlag=true;$('status').textContent='جارٍ إيقاف الفحص بعد الطلب الحالي...';};
$('csv').onclick=()=>{let csv='username,status,detail\\n'+rows.map(x=>[x.username,x.status,x.detail].map(v=>'"'+String(v||'').replaceAll('"','""')+'"').join(',')).join('\\n');
let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download='instagram-check-results.csv';a.click();};
</script></main></body></html>
"""

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.post("/api/generate")
def generate():
    data=request.get_json(silent=True) or {}
    count=max(1,min(int(data.get("count",30)),300))
    mode=data.get("mode","letters")
    chars=string.ascii_lowercase if mode=="letters" else (string.ascii_lowercase+string.digits if mode=="alnum" else string.ascii_lowercase+string.digits+"._")
    prefix=str(data.get("prefix","")).lower()
    if len(prefix)>2 or any(c not in string.ascii_lowercase+string.digits+"._" for c in prefix):
        return jsonify(error="البادئة يجب أن تكون حرفين أو أقل ومن الحروف/الأرقام/._"),400
    out=[]
    # Deterministic bounded generator; avoid invalid Instagram dot patterns.
    for tup in itertools.product(chars, repeat=3-len(prefix)):
        name=prefix+"".join(tup)
        if name.startswith(".") or name.endswith(".") or ".." in name: continue
        if name not in out: out.append(name)
        if len(out)>=count: break
    return jsonify(usernames=out)

def check_public_profile(username):
    global LAST_CHECK
    # Enforce a conservative global interval on this single-instance service.
    with LOCK:
        wait=MIN_DELAY-(time.time()-LAST_CHECK)
        if wait>0: time.sleep(wait)
        LAST_CHECK=time.time()
    url=f"https://www.instagram.com/{username}/"
    try:
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0 (compatible; UsernameAvailabilityCheck/1.0)"},timeout=15,allow_redirects=True)
        # Instagram responses are not authoritative; login walls and anti-bot pages are ambiguous.
        if r.status_code in (429,403,401) or "login" in r.url.lower() or "challenge" in r.url.lower():
            return "unknown", f"Instagram قيّد الطلب أو طلب تسجيل الدخول (HTTP {r.status_code})"
        if r.status_code == 404:
            return "available", "الصفحة أعادت 404؛ مؤشر غير مؤكد وليس ضمانًا"
        if r.status_code == 200:
            # Most profile pages include the username in page metadata. If absent, avoid guessing.
            body=r.text.lower()
            if f'"username":"{username}"' in body or f'/{username}/' in r.url.lower():
                return "taken", "ظهرت استجابة صفحة الملف؛ تحقق يدويًا قبل الاعتماد"
            return "unknown", "استجابة 200 لكن تعذّر تأكيد حالة الحساب"
        return "unknown", f"استجابة غير حاسمة (HTTP {r.status_code})"
    except requests.RequestException as e:
        return "unknown", "تعذّر الاتصال: "+type(e).__name__

@app.post("/api/check")
def check():
    data=request.get_json(silent=True) or {}
    username=str(data.get("username","")).lower()
    if not USERNAME_RE.fullmatch(username) or username.startswith(".") or username.endswith(".") or ".." in username:
        return jsonify(username=username,status="unknown",detail="صيغة الاسم غير صالحة"),400
    status,detail=check_public_profile(username)
    return jsonify(username=username,status=status,detail=detail)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
