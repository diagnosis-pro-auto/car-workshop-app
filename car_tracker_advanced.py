import os
import streamlit as st
import sqlite3
from datetime import datetime
from collections import Counter

USING_SUPABASE = False
supabase = None
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        USING_SUPABASE = True
    except Exception:  # pragma: no cover - supabase optional
        USING_SUPABASE = False

# --- قاعدة البيانات ---
if not USING_SUPABASE:
    conn = sqlite3.connect("workshop.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id TEXT,
            owner_phone TEXT,
            status TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id TEXT,
            status TEXT,
            note TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()

# --- بيانات تسجيل الدخول الافتراضي ---
USERS = {
    "admin": "admin",   # اسم مستخدم وكلمة مرور للموظف/مدير
    "user": "1234"      # موظف عادي (للتجربة)
}

# --- الوظائف ---

def add_car(car_id, owner_phone):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if USING_SUPABASE:
        supabase.table("cars").insert({
            "car_id": car_id,
            "owner_phone": owner_phone,
            "status": "تم الاستلام",
            "notes": "",
            "created_at": now,
            "updated_at": now,
        }).execute()
        supabase.table("history").insert({
            "car_id": car_id,
            "status": "تم الاستلام",
            "note": "",
            "timestamp": now,
        }).execute()
    else:
        c.execute('INSERT INTO cars (car_id, owner_phone, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                  (car_id, owner_phone, "تم الاستلام", "", now, now))
        c.execute('INSERT INTO history (car_id, status, note, timestamp) VALUES (?, ?, ?, ?)',
                  (car_id, "تم الاستلام", "", now))
        conn.commit()

def update_car_status(car_id, status, note=""):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if USING_SUPABASE:
        supabase.table("cars").update({
            "status": status,
            "notes": note,
            "updated_at": now,
        }).eq("car_id", car_id).execute()
        supabase.table("history").insert({
            "car_id": car_id,
            "status": status,
            "note": note,
            "timestamp": now,
        }).execute()
    else:
        c.execute('UPDATE cars SET status=?, notes=?, updated_at=? WHERE car_id=?',
                  (status, note, now, car_id))
        c.execute('INSERT INTO history (car_id, status, note, timestamp) VALUES (?, ?, ?, ?)',
                  (car_id, status, note, now))
        conn.commit()
    # --------- مكان إرسال إشعار واتساب ---------
    # send_whatsapp_message(owner_phone, status, note) 
    # --------------------------------------------

def get_all_cars():
    if USING_SUPABASE:
        result = supabase.table("cars").select(
            "car_id, owner_phone, status, notes, created_at, updated_at"
        ).order("updated_at", desc=True).execute()
        return [
            (
                item["car_id"],
                item["owner_phone"],
                item["status"],
                item["notes"],
                item["created_at"],
                item["updated_at"],
            )
            for item in result.data
        ]
    c.execute('SELECT car_id, owner_phone, status, notes, created_at, updated_at FROM cars ORDER BY updated_at DESC')
    return c.fetchall()

def get_car(identifier):
    """Retrieve a car record using either its ID or the owner's phone number.

    Args:
        identifier (str): Car identifier or owner's phone number.

    Returns:
        tuple | None: Database row representing the car or ``None`` if not
        found.
    """

    if USING_SUPABASE:
        result = (
            supabase.table("cars")
            .select("car_id, owner_phone, status, notes, created_at, updated_at")
            .or_(f"car_id.eq.{identifier},owner_phone.eq.{identifier}")
            .limit(1)
            .execute()
        )
        if result.data:
            item = result.data[0]
            return (
                item["car_id"],
                item["owner_phone"],
                item["status"],
                item["notes"],
                item["created_at"],
                item["updated_at"],
            )
        return None
    c.execute(
        """
        SELECT car_id, owner_phone, status, notes, created_at, updated_at
        FROM cars
        WHERE car_id=? OR owner_phone=?
        """,
        (identifier, identifier),
    )
    return c.fetchone()

def get_history(car_id):
    if USING_SUPABASE:
        result = (
            supabase.table("history")
            .select("status, note, timestamp")
            .eq("car_id", car_id)
            .order("timestamp", asc=True)
            .execute()
        )
        return [
            (item["status"], item["note"], item["timestamp"]) for item in result.data
        ]
    c.execute('SELECT status, note, timestamp FROM history WHERE car_id=? ORDER BY timestamp ASC', (car_id,))
    return c.fetchall()

def get_stats():
    if USING_SUPABASE:
        result = supabase.table("cars").select("owner_phone, status").execute()
        cars = result.data
        status_counter = Counter([car["status"] for car in cars])
        phone_counter = Counter([car["owner_phone"] for car in cars])
        stats = dict(status_counter)
        top_customers = list(phone_counter.most_common())
        all_status = [(car["status"],) for car in cars]
        return stats, top_customers, all_status
    c.execute('SELECT status, COUNT(*) FROM cars GROUP BY status')
    stats = dict(c.fetchall())
    c.execute('SELECT owner_phone, COUNT(*) FROM cars GROUP BY owner_phone ORDER BY COUNT(*) DESC')
    top_customers = c.fetchall()
    c.execute('SELECT status FROM cars')
    all_status = c.fetchall()
    return stats, top_customers, all_status

# --- تسجيل دخول بسيط ---

def login():
    st.subheader("تسجيل الدخول للموظفين/المدير")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")
    login_btn = st.button("دخول")
    if login_btn:
        if username in USERS and USERS[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success("تم تسجيل الدخول بنجاح!")
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
    return st.session_state.get("logged_in", False)

# --- التطبيق ---

st.set_page_config(page_title="متابعة صيانة سيارتي", layout="wide")
st.title("🚗 مركز التشخيص الإحترافي – متابعة مراحل الصيانة")

tabs = st.tabs(["الرئيسية", "إدارة الورشة", "التقارير", "استعلام العميل"])

with tabs[0]:
    st.header("مرحباً بك في نظام متابعة الصيانة!")
    st.markdown("""
    - استعلم عن حالة سيارتك أو سجل كموظف لتحديث بيانات العملاء
    - التطبيق يحفظ جميع البيانات ولا تضيع حتى بعد إغلاق الجهاز
    - أي تحديث على حالة السيارة سيظهر مباشرة للعميل ويُحفظ تلقائياً
    - إشعارات واتساب/رسائل ستتوفر عند التفعيل (hook موجود)
    """)

with tabs[1]:
    st.header("إدارة الورشة – للموظفين فقط")
    if login():
        st.subheader("إضافة سيارة جديدة")
        car_id = st.text_input("رقم السيارة/رقم الجوال (لتتبع العميل)")
        owner_phone = st.text_input("رقم جوال العميل (لإشعارات واتساب)")
        if st.button("إضافة السيارة"):
            if car_id and owner_phone:
                add_car(car_id, owner_phone)
                st.success("تمت إضافة السيارة بنجاح!")
            else:
                st.warning("الرجاء إدخال جميع البيانات")

        st.subheader("تحديث بيانات السيارات الحالية")
        all_cars = get_all_cars()
        for car in all_cars:
            with st.expander(f"🚗 السيارة: {car[0]} | {car[2]} | العميل: {car[1]}"):
                st.write(f"آخر تحديث: {car[5]}")
                st.write("ملاحظة سابقة:", car[3])
                status = st.selectbox(
                    "تحديث الحالة",
                    [
                        "تم الاستلام",
                        "تحت التشخيص",
                        "بانتظار موافقة العميل",
                        "تحت الإصلاح",
                        "جاهزة للاستلام",
                        "مكتمل",
                    ],
                    index=[
                        "تم الاستلام",
                        "تحت التشخيص",
                        "بانتظار موافقة العميل",
                        "تحت الإصلاح",
                        "جاهزة للاستلام",
                        "مكتمل",
                    ].index(car[2]),
                    key=f"status_{car[0]}",
                )
                note = st.text_area("ملاحظة للعميل (اختياري):", key=f"note_{car[0]}")
                if st.button("حفظ التحديثات", key=f"update_{car[0]}"):
                    update_car_status(car[0], status, note)
                    st.success("تم تحديث البيانات!")
                st.write("سجل الحالات:")
                for h in get_history(car[0]):
                    st.write(f"- {h[0]} | {h[2]}")
                st.write("ملاحظات:")
                for h in get_history(car[0]):
                    if h[1]:
                        st.write(f"- {h[1]}")

with tabs[2]:
    st.header("التقارير الإحصائية")
    stats, top_customers, all_status = get_stats()
    st.subheader("حالات السيارات حالياً")
    st.write(stats)
    st.subheader("أكثر العملاء تكراراً (حسب الجوال)")
    st.write(top_customers)
    st.subheader("عدد كل حالة:")
    for status in ["تم الاستلام", "تحت التشخيص", "بانتظار موافقة العميل", "تحت الإصلاح", "جاهزة للاستلام", "مكتمل"]:
        st.write(f"{status}: {stats.get(status,0)}")

with tabs[3]:
    st.header("استعلام العميل عن حالة السيارة")
    query_id = st.text_input("أدخل رقم سيارتك أو جوالك (للعميل):")
    if st.button("استعلم"):
        car = get_car(query_id)
        if car:
            st.success(f"الحالة الحالية: {car[2]}")
            st.write(f"تاريخ آخر تحديث: {car[5]}")
            st.write("ملاحظات الورشة:", car[3])
            st.write("سجل الحالة:")
            for h in get_history(car[0]):
                st.write(f"- {h[0]} | {h[2]}")
        else:
            st.error("لم يتم العثور على السيارة!")

st.caption("نظام متكامل – الإصدار التجريبي. جاهز للتطوير والإضافات حسب متطلباتك!")

# ------------ هوك إشعار واتساب ------------
# اكتب هنا دالة send_whatsapp_message إذا فعلت WhatsApp API لاحقاً.
