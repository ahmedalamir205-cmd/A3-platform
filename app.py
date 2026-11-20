import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "A3_AGRI_SUPER_SECRET_KEY"
DB_NAME = "a3_database.db"

OWNER_PASS = "ALAMIR A3"
ADMIN_PASS = "ALAMIR"

# --- إعداد قاعدة البيانات ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # جدول المستخدمين واهتماماتهم
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            interests TEXT DEFAULT 'عام',
            created_at TEXT
        )
    """)
    # جدول الأقسام (الأساسية + التي يضيفها المالك)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            icon TEXT NOT NULL,
            description TEXT
        )
    """)
    # جدول المنشورات والأخبار والكورسات
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_slug TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            post_type TEXT DEFAULT 'منشور',
            price TEXT DEFAULT 'مجاني',
            author TEXT,
            created_at TEXT
        )
    """)
    # جدول الشات الجماعي
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name TEXT NOT NULL,
            sender_role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT
        )
    """)
    # جدول إعدادات الشكل والتطبيق (يتحكم بها المالك)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # الإعدادات الافتراضية
    default_settings = {
        "app_name": "A3 - منصة طلاب كلية الزراعة",
        "primary_color": "#1b5e20",
        "accent_color": "#2e7d32",
        "welcome_msg": "أهلاً بك في مجتمع طلاب كلية الزراعة الذكي"
    }
    for k, v in default_settings.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # الأقسام الافتراضية المطلوبة
    default_sections = [
        ("posts", "منشورات الأدمن والأخبار", "📢", "أحدث الأخبار الزراعية والبوستات التعليمية والكورسات"),
        ("services", "الخدمات الزراعية", "🌾", "استشارات زراعية، تحليل تربة، وخدمات ميدانية للطلاب"),
        ("notes", "المذكرات والملخصات", "📚", "ملخصات ومذكرات جميع الفرق الدراسية بكلية الزراعة"),
        ("courses", "الكورسات المدفوعة والتدريب", "🎓", "دورات متخصصة في الإنتاج النباتي والحيواني واللاندسكيب"),
    ]
    for slug, title, icon, desc in default_sections:
        c.execute("INSERT OR IGNORE INTO sections (slug, title, icon, description) VALUES (?, ?, ?, ?)",
                  (slug, title, icon, desc))

    conn.commit()
    conn.close()

def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

# --- القوالب (HTML + CSS) ---
BASE_STYLE = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {
    --primary: {{ cfg.primary_color }};
    --accent: {{ cfg.accent_color }};
  }
  * { box-sizing: border-box; }
  body { font-family: Tahoma, Arial, sans-serif; background: #f2f7f2; margin: 0; color: #1f2933; }
  header { background: linear-gradient(135deg, var(--primary), var(--accent)); color: #fff; padding: 18px 15px; border-bottom-left-radius: 22px; border-bottom-right-radius: 22px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
  header h1 { margin: 0; font-size: 22px; }
  header p { margin: 6px 0 0; font-size: 13px; opacity: 0.92; }
  .container { max-width: 680px; margin: 18px auto; padding: 0 14px 40px; }
  .card { background: #fff; border-radius: 14px; padding: 16px; margin-bottom: 14px; box-shadow: 0 3px 10px rgba(0,0,0,0.06); }
  .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
  .menu-item { background: #fff; border-radius: 14px; padding: 18px 12px; text-align: center; text-decoration: none; color: #1f2933; box-shadow: 0 3px 10px rgba(0,0,0,0.06); transition: 0.2s; display: flex; flex-direction: column; align-items: center; justify-content: center; border-bottom: 4px solid var(--accent); }
  .menu-item:hover { transform: translateY(-3px); }
  .menu-icon { font-size: 32px; margin-bottom: 8px; }
  .menu-title { font-weight: bold; font-size: 14px; }
  input, select, textarea { width: 100%; padding: 11px; margin: 6px 0 12px; border: 1px solid #cbd5e1; border-radius: 9px; font-family: inherit; font-size: 14px; }
  button, .btn { display: inline-block; background: var(--accent); color: #fff; border: none; padding: 11px 18px; border-radius: 9px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; }
  .btn-danger { background: #c62828; }
  .btn-owner { background: #b45309; }
  .badge { display: inline-block; padding: 3px 9px; border-radius: 20px; font-size: 11px; background: #e8f5e9; color: var(--primary); font-weight: bold; }
  .nav-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
  .alert { background: #e8f5e9; color: #1b5e20; padding: 10px; border-radius: 8px; margin-bottom: 12px; text-align: center; font-size: 13px; }
  .err { background: #ffebee; color: #c62828; }
</style>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>دخول - {{ cfg.app_name }}</title>""" + BASE_STYLE + """</head>
<body>
  <header>
    <h1>🌱 {{ cfg.app_name }}</h1>
    <p>{{ cfg.welcome_msg }}</p>
  </header>
  <div class="container">
    <div class="card">
      <h3 style="margin-top:0; color:var(--primary); text-align:center;">تسجيل الدخول</h3>
      {% if error %}<div class="alert err">{{ error }}</div>{% endif %}
      <form method="POST">
        <label>نوع الحساب</label>
        <select name="role" id="roleSelect" onchange="togglePass()">
          <option value="student">طالب كلية زراعة</option>
          <option value="admin">أدمن (مشرف)</option>
          <option value="owner">المالك (تحكم كامل)</option>
        </select>
        <label>الاسم بالكامل</label>
        <input type="text" name="name" placeholder="اكتب اسمك" required>
        <label>البريد الإلكتروني (Gmail)</label>
        <input type="email" name="email" placeholder="example@gmail.com" required>
        <div id="interestBox">
          <label>اهتمامك الزراعي الأساسي (لتخصيص المحتوى لك)</label>
          <select name="interest">
            <option value="إنتاج نباتي ومحاصيل">إنتاج نباتي ومحاصيل</option>
            <option value="إنتاج حيواني وداجني">إنتاج حيواني وداجني</option>
            <option value="وقاية نبات ومبيدات">وقاية نبات ومبيدات</option>
            <option value="أراضي ومياه">أراضي ومياه</option>
            <option value="صناعات غذائية وألبان">صناعات غذائية وألبان</option>
            <option value="لاندسكيب وزينة">لاندسكيب وزينة</option>
          </select>
        </div>
        <div id="passBox" style="display:none;">
          <label>كلمة مرور الإدارة / المالك</label>
          <input type="password" name="password" placeholder="أدخل كلمة المرور الخاصة">
        </div>
        <button type="submit" style="width:100%;">دخول إلى التطبيق</button>
      </form>
    </div>
  </div>
  <script>
    function togglePass() {
      var r = document.getElementById("roleSelect").value;
      document.getElementById("passBox").style.display = (r === "student") ? "none" : "block";
      document.getElementById("interestBox").style.display = (r === "student") ? "block" : "none";
    }
  </script>
</body>
</html>
"""

HOME_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>الرئيسية - {{ cfg.app_name }}</title>""" + BASE_STYLE + """</head>
<body>
  <header>
    <h1>🌿 {{ cfg.app_name }}</h1>
    <p>مرحباً {{ user.name }} ({{ role_ar }}) | اهتمامك: {{ user.interest }}</p>
  </header>
  <div class="container">
    <div class="nav-bar">
      {% if user.role == 'owner' %}
        <a href="/owner" class="btn btn-owner">👑 لوحة تحكم المالك الكاملة</a>
      {% endif %}
      {% if user.role in ['owner', 'admin'] %}
        <a href="/admin_publish" class="btn">➕ نشر محتوى / كورس / خبر</a>
      {% endif %}
      <a href="/logout" class="btn btn-danger">خروج</a>
    </div>

    {% if recommended %}
    <div class="card" style="border-right: 5px solid var(--accent);">
      <span class="badge">🎯 مقترح لك بناءً على اهتمامك ({{ user.interest }})</span>
      <h4 style="margin:8px 0 4px;">{{ recommended.title }}</h4>
      <p style="margin:0; font-size:13px; color:#475569;">{{ recommended.content[:120] }}...</p>
    </div>
    {% endif %}

    <div class="grid">
      {% for sec in sections %}
        <a href="/sec/{{ sec.slug }}" class="menu-item">
          <span class="menu-icon">{{ sec.icon }}</span>
          <span class="menu-title">{{ sec.title }}</span>
        </a>
      {% endfor %}
      <a href="/group_chat" class="menu-item">
        <span class="menu-icon">💬</span>
        <span class="menu-title">الشات الجماعي للطلاب</span>
      </a>
      <a href="/ai_agri" class="menu-item">
        <span class="menu-icon">🤖</span>
        <span class="menu-title">المساعد الزراعي الذكي AI</span>
      </a>
    </div>
  </div>
</body>
</html>
"""

SECTION_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>{{ sec.title }}</title>""" + BASE_STYLE + """</head>
<body>
  <header>
    <h1>{{ sec.icon }} {{ sec.title }}</h1>
    <p>{{ sec.description }}</p>
  </header>
  <div class="container">
    <div class="nav-bar">
      <a href="/home" class="btn">⬅ الرئيسية</a>
      {% if user.role in ['owner', 'admin'] %}
        <a href="/admin_publish" class="btn">➕ إضافة هنا</a>
      {% endif %}
    </div>
    {% if not posts %}
      <div class="card" style="text-align:center;">لا يوجد محتوى منشور في هذا القسم بعد.</div>
    {% endif %}
    {% for p in posts %}
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="badge">{{ p.post_type }} • {{ p.price }}</span>
          <small style="color:#64748b;">{{ p.created_at }}</small>
        </div>
        <h3 style="margin:10px 0 6px; color:var(--primary);">{{ p.title }}</h3>
        <p style="white-space:pre-line; line-height:1.6; margin:0 0 10px;">{{ p.content }}</p>
        <small style="color:#64748b;">بواسطة: {{ p.author }}</small>
        {% if user.role in ['owner', 'admin'] %}
          <a href="/delete_post/{{ p.id }}" class="btn btn-danger" style="padding:5px 10px; font-size:12px; float:left;">حذف</a>
        {% endif %}
      </div>
    {% endfor %}
  </div>
</body>
</html>
"""

CHAT_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>الشات الجماعي</title>""" + BASE_STYLE + """</head>
<body>
  <header>
    <h1>💬 الشات الجماعي لطلاب الزراعة</h1>
    <p>تواصل وتبادل الخبرات والمذكرات مع زملائك</p>
  </header>
  <div class="container">
    <div class="nav-bar"><a href="/home" class="btn">⬅ الرئيسية</a></div>
    <div class="card" style="max-height:380px; overflow-y:auto;">
      {% if not messages %}<p style="text-align:center; color:#64748b;">ابدأ أول رسالة في الشات الجماعي!</p>{% endif %}
      {% for m in messages %}
        <div style="border-bottom:1px solid #eee; padding:8px 0;">
          <strong>{{ m.sender_name }}</strong> <span class="badge">{{ m.sender_role }}</span>
          <small style="color:#94a3b8; float:left;">{{ m.created_at }}</small>
          <p style="margin:4px 0 0;">{{ m.message }}</p>
        </div>
      {% endfor %}
    </div>
    <form method="POST" class="card">
      <input type="text" name="message" placeholder="اكتب رسالتك لزملائك..." required>
      <button type="submit" style="width:100%;">إرسال الرسالة</button>
    </form>
  </div>
</body>
</html>
"""

AI_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>المساعد الزراعي AI</title>""" + BASE_STYLE + """</head>
<body>
  <header>
    <h1>🤖 المساعد الذكي لعلوم الزراعة</h1>
    <p>اسأل في المحاصيل، التربة، التسميد، الآفات، والإنتاج الحيواني</p>
  </header>
  <div class="container">
    <div class="nav-bar"><a href="/home" class="btn">⬅ الرئيسية</a></div>
    <form method="POST" class="card">
      <label>اكتب سؤالك الزراعي بالتفصيل:</label>
      <textarea name="question" rows="3" placeholder="مثال: ما هي أفضل برامج التسميد للقمح في الأراضي الرملية؟" required>{{ question or '' }}</textarea>
      <button type="submit" style="width:100%;">اسأل الخبير الزراعي</button>
    </form>
    {% if answer %}
      <div class="card" style="border-right: 5px solid var(--primary);">
        <h4 style="margin-top:0; color:var(--primary);">الإجابة العلمية:</h4>
        <p style="white-space:pre-line; line-height:1.7;">{{ answer }}</p>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""

PUBLISH_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>نشر محتوى جديد</title>""" + BASE_STYLE + """</head>
<body>
  <header><h1>➕ إضافة منشور / خبر / كورس</h1></header>
  <div class="container">
    <div class="nav-bar"><a href="/home" class="btn">⬅ الرئيسية</a></div>
    <form method="POST" class="card">
      <label>اختر القسم</label>
      <select name="section_slug">
        {% for s in sections %}
          <option value="{{ s.slug }}">{{ s.icon }} {{ s.title }}</option>
        {% endfor %}
      </select>
      <label>نوع المحتوى</label>
      <select name="post_type">
        <option value="منشور زراعي">منشور زراعي</option>
        <option value="خبر عاجل">خبر زراعي</option>
        <option value="كورس مدفوع">كورس مدفوع</option>
        <option value="ملخص / مذكرة">ملخص / مذكرة</option>
      </select>
      <label>السعر (اكتب مجاني أو السعر بالجنيه)</label>
      <input type="text" name="price" value="مجاني">
      <label>العنوان</label>
      <input type="text" name="title" required>
      <label>التفاصيل الكاملة أو رابط الكورس/الملف</label>
      <textarea name="content" rows="5" required></textarea>
      <button type="submit" style="width:100%;">نشر الآن</button>
    </form>
  </div>
</body>
</html>
"""

OWNER_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>لوحة تحكم المالك</title>""" + BASE_STYLE + """</head>
<body>
  <header style="background:#92400e;">
    <h1>👑 لوحة تحكم المالك الكاملة</h1>
    <p>تعديل الشكل، إضافة أقسام، أداة جلب الأخبار، وإدارة الأعضاء</p>
  </header>
  <div class="container">
    <div class="nav-bar"><a href="/home" class="btn">⬅ الرئيسية</a></div>
    {% if msg %}<div class="alert">{{ msg }}</div>{% endif %}

    <!-- 1. تغيير شكل واسم التطبيق -->
    <form method="POST" class="card">
      <h3 style="margin-top:0;">🎨 تخصيص شكل واسم التطبيق</h3>
      <input type="hidden" name="action" value="update_theme">
      <label>اسم التطبيق</label>
      <input type="text" name="app_name" value="{{ cfg.app_name }}">
      <label>الرسالة الترحيبية</label>
      <input type="text" name="welcome_msg" value="{{ cfg.welcome_msg }}">
      <label>اللون الأساسي (كود اللون)</label>
      <input type="color" name="primary_color" value="{{ cfg.primary_color }}">
      <label>اللون الثانوي</label>
      <input type="color" name="accent_color" value="{{ cfg.accent_color }}">
      <button type="submit" class="btn-owner" style="width:100%;">حفظ التغييرات فوراً</button>
    </form>

    <!-- 2. إضافة قسم جديد -->
    <form method="POST" class="card">
      <h3 style="margin-top:0;">➕ إضافة قسم جديد للتطبيق</h3>
      <input type="hidden" name="action" value="add_section">
      <label>اسم القسم</label>
      <input type="text" name="title" placeholder="مثال: أمراض النبات أو سوق البذور" required>
      <label>أيقونة القسم (إيموجي)</label>
      <input type="text" name="icon" value="🌱" required>
      <label>وصف مختصر للقسم</label>
      <input type="text" name="description" placeholder="وصف يظهر أعلى القسم">
      <button type="submit" style="width:100%;">إنشاء القسم</button>
    </form>

    <!-- 3. أداة متابعة الأخبار الزراعية التلقائية -->
    <form method="POST" class="card">
      <h3 style="margin-top:0;">📡 أداة جلب ونشر الأخبار الزراعية</h3>
      <p style="font-size:13px; color:#475569;">تبحث في مصادر الأخبار الزراعية وتنزل أحدث خبر كبوست في التطبيق.</p>
      <input type="hidden" name="action" value="fetch_news">
      <button type="submit" style="width:100%;">تشغيل أداة الأخبار الزراعية الآن</button>
    </form>

    <!-- 4. قائمة المسجلين واهتماماتهم -->
    <div class="card">
      <h3 style="margin-top:0;">👥 الأعضاء واهتماماتهم ({{ users|length }})</h3>
      {% for u in users %}
        <div style="border-bottom:1px solid #eee; padding:6px 0; font-size:13px;">
          <strong>{{ u.name }}</strong> ({{ u.email }}) — <span class="badge">{{ u.role }}</span> | اهتمام: {{ u.interests }}
        </div>
      {% endfor %}
    </div>
  </div>
</body>
</html>
"""

# --- المسارات (Routes) ---
@app.route("/", methods=["GET", "POST"])
def login():
    cfg = get_settings()
    if session.get("user"):
        return redirect(url_for("home"))
    error = None
    if request.method == "POST":
        role = request.form.get("role")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        interest = request.form.get("interest", "عام")

        if role == "owner" and password != OWNER_PASS:
            error = "كلمة مرور المالك غير صحيحة!"
        elif role == "admin" and password != ADMIN_PASS:
            error = "كلمة مرور الأدمن غير صحيحة!"
        else:
            conn = get_db()
            conn.execute("""
                INSERT INTO users (name, email, role, interests, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET name=excluded.name, role=excluded.role, interests=excluded.interests
            """, (name, email, role, interest, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
            session["user"] = {"name": name, "email": email, "role": role, "interest": interest}
            return redirect(url_for("home"))

    return render_template_string(LOGIN_PAGE, cfg=cfg, error=error)

@app.route("/home")
def home():
    if not session.get("user"):
        return redirect(url_for("login"))
    cfg = get_settings()
    user = session["user"]
    role_map = {"owner": "المالك", "admin": "أدمن", "student": "طالب"}
    conn = get_db()
    sections = conn.execute("SELECT * FROM sections").fetchall()
    # ترشيح منشور يناسب اهتمام الطالب
    keyword = user.get("interest", "").split()[0]
    rec = conn.execute("SELECT * FROM posts WHERE title LIKE ? OR content LIKE ? ORDER BY id DESC LIMIT 1",
                       (f"%{keyword}%", f"%{keyword}%")).fetchone()
    if not rec:
        rec = conn.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return render_template_string(HOME_PAGE, cfg=cfg, user=user, role_ar=role_map.get(user["role"], "عضو"),
                                  sections=sections, recommended=rec)

@app.route("/sec/<slug>")
def view_section(slug):
    if not session.get("user"):
        return redirect(url_for("login"))
    cfg = get_settings()
    conn = get_db()
    sec = conn.execute("SELECT * FROM sections WHERE slug = ?", (slug,)).fetchone()
    if not sec:
        conn.close()
        return redirect(url_for("home"))
    # تحديث اهتمام الطالب تلقائياً بناءً على القسم الذي يتصفحه
    if session["user"]["role"] == "student":
        session["user"]["interest"] = sec["title"]
        session.modi
