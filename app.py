from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pickle, json, re, datetime
from functools import wraps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "spamshield_secret_2024"

model      = pickle.load(open("model.pkl",      "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
metrics    = pickle.load(open("metrics.pkl",    "rb"))

USERS = {"admin": "admin123", "user": "user123"}
last_result = {}

SPAM_KEYWORDS = [
    "free","win","money","prize","click","offer","reward",
    "congratulations","claim","lottery","recharge","urgent",
    "limited","exclusive","guaranteed","cash","gift","bonus",
    "deal","cheap","discount","earn","income",
]

# ── Analysis Helpers ──────────────────────────────────

def get_difficulty(probability, keywords, links):
    score = len(keywords)*10 + len(links)*8 + probability*0.4
    if score >= 70:
        return "Easy Spam",     "Obvious patterns — very easy to detect",          "rh"
    elif score >= 40:
        return "Medium Spam",   "Mixed signals — moderately suspicious",            "rm"
    else:
        return "Advanced Spam", "Phishing-style — sophisticated, hard to detect",   "rl"

def get_emotion(email, prediction):
    t = email.lower()
    scores = {
        "Threatening": sum(1 for w in ["blocked","suspended","terminate","illegal","penalty","fraud","lawsuit"] if w in t),
        "Urgent":      sum(1 for w in ["urgent","immediately","asap","now","expire","warning","alert","quick"] if w in t),
        "Promotional": sum(1 for w in ["offer","sale","deal","discount","buy","free","win","prize","save"] if w in t),
        "Friendly":    sum(1 for w in ["hello","hi","hey","thanks","hope","meet","lunch","regards","dear"] if w in t),
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return ("Suspicious","🟠") if prediction=="spam" else ("Neutral","⚪")
    icons = {"Threatening":"🔴","Urgent":"🟠","Promotional":"🟡","Friendly":"🟢"}
    return best, icons[best]

def get_trust_score(probability, prediction, keywords, links):
    base    = (100 - probability) if prediction=="spam" else (100 - probability*0.3)
    penalty = len(keywords)*4 + len(links)*6
    score   = max(0, min(100, round(base - penalty)))
    if score <= 30:   return score, "Spam",       "trust-spam"
    elif score <= 60: return score, "Suspicious",  "trust-sus"
    else:             return score, "Safe",         "trust-safe"

def get_confidence_badge(probability):
    if probability >= 85:   return "HIGH",   "badge-high"
    elif probability >= 60: return "MEDIUM", "badge-med"
    else:                   return "LOW",    "badge-low"

def get_category(email, prediction, keywords):
    t = email.lower()
    sw  = sum(1 for w in ["meeting","project","report","deadline","team","office","agenda","client"] if w in t)
    pw  = sum(1 for w in ["friend","family","lunch","dinner","party","birthday","hey","weekend"]     if w in t)
    prw = sum(1 for w in ["offer","sale","deal","discount","buy","subscribe","newsletter","coupon"]  if w in t)
    if prediction == "spam":
        return ("Promotion","🎯") if prw >= 1 else ("Spam","🚨")
    if sw  >= 2: return "Work",      "💼"
    if pw  >= 2: return "Personal",  "💬"
    if prw >= 1: return "Promotion", "🎯"
    return "General", "📧"

def analyze_email(email, prediction, probability):
    detected  = [k for k in SPAM_KEYWORDS if k in email.lower()]
    links     = re.findall(r'https?://\S+', email)
    difficulty, diff_desc, diff_cls         = get_difficulty(probability, detected, links)
    emotion, emotion_icon                   = get_emotion(email, prediction)
    trust_score, trust_label, trust_cls     = get_trust_score(probability, prediction, detected, links)
    conf_badge, conf_cls                    = get_confidence_badge(probability)
    category, cat_icon                      = get_category(email, prediction, detected)
    return dict(
        keywords=detected, links=links,
        word_count=len(email.split()), char_count=len(email), exclamations=email.count('!'),
        difficulty=difficulty, diff_desc=diff_desc, diff_cls=diff_cls,
        emotion=emotion, emotion_icon=emotion_icon,
        trust_score=trust_score, trust_label=trust_label, trust_cls=trust_cls,
        conf_badge=conf_badge, conf_cls=conf_cls,
        category=category, cat_icon=cat_icon,
    )

def load_history():
    try: return json.load(open("history.json"))
    except: return []

def save_history(h):
    json.dump(h, open("history.json","w"), indent=2)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_metrics():
    return dict(
        accuracy =round(metrics["accuracy"] *100,2),
        precision=round(metrics["precision"]*100,2),
        recall   =round(metrics["recall"]   *100,2),
        f1       =round(metrics["f1"]       *100,2),
    )

# ── Routes ────────────────────────────────────────────

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if USERS.get(u) == p:
            session["username"] = u
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    global last_result
    email = request.form.get("email","").strip()
    if not email: return redirect(url_for("home"))

    vec        = vectorizer.transform([email])
    prediction = model.predict(vec)[0]
    proba      = round(model.predict_proba(vec)[0].max()*100, 2)
    analysis   = analyze_email(email, prediction, proba)

    history = load_history()
    history.append({
        "email": email, "result": prediction, "probability": proba,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": session.get("username",""),
        "category": analysis["category"], "emotion": analysis["emotion"],
        "trust_score": analysis["trust_score"],
    })
    save_history(history)
    last_result = dict(email=email, prediction=prediction, proba=proba, **analysis)
    return render_template("result.html", prediction=prediction, probability=proba,
                           email_input=email, **analysis)

@app.route("/dashboard")
@login_required
def dashboard():
    history = load_history()
    total = len(history)
    spam  = sum(1 for i in history if i["result"]=="spam")
    today     = datetime.date.today().strftime("%Y-%m-%d")
    yesterday = (datetime.date.today()-datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    spam_today     = sum(1 for i in history if i["result"]=="spam" and i.get("timestamp","").startswith(today))
    spam_yesterday = sum(1 for i in history if i["result"]=="spam" and i.get("timestamp","").startswith(yesterday))
    categories = {}
    for item in history:
        c = item.get("category","General")
        categories[c] = categories.get(c,0)+1
    return render_template("dashboard.html",
        total=total, spam=spam, ham=total-spam,
        cm=metrics["confusion_matrix"],
        spam_today=spam_today, spam_yesterday=spam_yesterday,
        categories=categories, **get_metrics())

@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html", history=load_history())

@app.route("/analytics")
@login_required
def analytics():
    history = load_history()
    emotions, categories = {}, {}
    for item in history:
        e = item.get("emotion","Neutral"); emotions[e]   = emotions.get(e,0)+1
        c = item.get("category","General"); categories[c] = categories.get(c,0)+1
    ts = [item.get("trust_score",50) for item in history]
    avg_trust = round(sum(ts)/len(ts),1) if ts else 0
    today = datetime.date.today()
    trend = []
    for i in range(6,-1,-1):
        day   = (today-datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        label = (today-datetime.timedelta(days=i)).strftime("%b %d")
        trend.append({
            "label": label,
            "spam": sum(1 for h in history if h["result"]=="spam" and h.get("timestamp","").startswith(day)),
            "ham":  sum(1 for h in history if h["result"]=="ham"  and h.get("timestamp","").startswith(day)),
        })
    return render_template("analytics.html",
        total=len(history), emotions=emotions, categories=categories,
        avg_trust=avg_trust, trend=json.dumps(trend))

@app.route("/about")
@login_required
def about():
    return render_template("about.html", **get_metrics())

@app.route("/clear_history")
@login_required
def clear_history():
    save_history([]); return redirect(url_for("admin"))

@app.route("/download")
@login_required
def download():
    filename = "spam_report.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    w, h = A4
    r = last_result

    c.setFillColor(colors.HexColor("#050810")); c.rect(0,0,w,h,fill=True,stroke=False)
    c.setFillColor(colors.HexColor("#0d1526")); c.rect(0,h-90,w,90,fill=True,stroke=False)
    c.setFillColor(colors.HexColor("#00d4ff")); c.rect(0,h-92,w,3,fill=True,stroke=False)
    c.setFillColor(colors.HexColor("#00d4ff")); c.setFont("Helvetica-Bold",20); c.drawString(40,h-48,"SPAMSHIELD")
    c.setFillColor(colors.HexColor("#4a6080")); c.setFont("Helvetica",9)
    c.drawString(40,h-64,"AI-Powered Email Security Report")
    c.drawString(40,h-78,f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    pred,proba = r.get("prediction","unknown"), r.get("proba",0)
    bcolor = "#dc2626" if pred=="spam" else "#16a34a"
    c.setFillColor(colors.HexColor(bcolor)); c.roundRect(40,h-162,190,44,8,fill=True,stroke=False)
    c.setFillColor(colors.HexColor("#ffffff")); c.setFont("Helvetica-Bold",14)
    c.drawString(54,h-136,"SPAM DETECTED" if pred=="spam" else "LEGITIMATE EMAIL")
    c.setFillColor(colors.HexColor("#ddeeff")); c.setFont("Helvetica-Bold",11)
    c.drawString(250,h-136,f"Confidence: {proba}%")

    bw = w-80
    c.setFillColor(colors.HexColor("#111d33")); c.roundRect(40,h-186,bw,14,4,fill=True,stroke=False)
    c.setFillColor(colors.HexColor(bcolor));    c.roundRect(40,h-186,bw*proba/100,14,4,fill=True,stroke=False)

    yi = h-210
    c.setFont("Helvetica-Bold",8)
    for lbl,val in [
        ("CATEGORY",      r.get("category","—")),
        ("EMOTION",       r.get("emotion","—")),
        ("DIFFICULTY",    r.get("difficulty","—")),
        ("TRUST SCORE",   f"{r.get('trust_score',0)}/100  ({r.get('trust_label','—')})"),
        ("AI CONFIDENCE", r.get("conf_badge","—")),
    ]:
        c.setFillColor(colors.HexColor("#4a6080")); c.drawString(40,yi,lbl)
        c.setFillColor(colors.HexColor("#ddeeff")); c.drawString(160,yi,str(val)); yi-=14

    c.setFillColor(colors.HexColor("#00d4ff")); c.setFont("Helvetica-Bold",8); c.drawString(40,yi-6,"EMAIL CONTENT")
    c.setFillColor(colors.HexColor("#0d1526")); c.roundRect(38,yi-130,w-76,116,6,fill=True,stroke=False)
    c.setFillColor(colors.HexColor("#ddeeff")); c.setFont("Courier",8)
    words = r.get("email","").split(); lines, line = [], ""
    for word in words:
        if len(line+" "+word)<95: line+=(" " if line else "")+word
        else: lines.append(line); line=word
    if line: lines.append(line)
    yy = yi-22
    for ln in lines[:8]: c.drawString(52,yy,ln); yy-=13
    if len(lines)>8: c.setFillColor(colors.HexColor("#4a6080")); c.drawString(52,yy,"…(truncated)")

    c.setFillColor(colors.HexColor("#4a6080")); c.setFont("Helvetica",8)
    c.drawString(40,28,"SpamShield — AI Email Classifier  |  Naive Bayes  |  Confidential")
    c.save()
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)