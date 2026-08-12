import base64
import hashlib
import io
import json
import os
import urllib.parse
from datetime import datetime
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import pytz
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Flow OPB & IOM - P3SRS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- INISIALISASI SUPABASE CLIENT ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase Credentials belum diatur di Secrets/Environment Variables!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "opb-files"

# --- LIST DIVISI & BUDGET PERSISTEN KE SUPABASE ---
DIVISI_LIST = [
    "IT",
    "Mekanikal",
    "Civil",
    "Plumbing",
    "Elektrikal",
    "Lift",
    "AC",
]

def init_budgets_table():
    """Memastikan tabel budget tersedia di Supabase atau menggunakan cache session."""
    try:
        res = supabase.table("divisi_budgets").select("*").execute()
        if not res.data:
            # Inisialisasi awal jika kosong
            for div in DIVISI_LIST:
                supabase.table("divisi_budgets").upsert({"divisi": div, "pagu_awal": 1_000_000_000}).execute()
            return {div: 1_000_000_000 for div in DIVISI_LIST}
        else:
            return {item["divisi"]: item["pagu_awal"] for item in res.data}
    except Exception:
        return {div: 1_000_000_000 for div in DIVISI_LIST}

INITIAL_BUDGETS = init_budgets_table()

# --- 2. FUNGSI PERSISTENSI DATA (SUPABASE STORAGE & DB) ---
def upload_file_to_supabase(file_bytes, file_name, folder="opb"):
    if not file_bytes:
        return None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{folder}/{timestamp}_{file_name.replace(' ', '_')}"

        supabase.storage.from_(BUCKET_NAME).upload(
            file=file_bytes,
            path=safe_filename,
            file_options={"content-type": "application/octet-stream"},
        )
        return supabase.storage.from_(BUCKET_NAME).get_public_url(safe_filename)
    except Exception as e:
        st.error(f"Gagal upload file ke Supabase Storage: {e}")
        return None


def load_database():
    try:
        response = supabase.table("opb_data").select("*").order("id", desc=False).execute()
        data = response.data
        
        for item in data:
            if isinstance(item.get("timeline"), str):
                try:
                    item["timeline"] = json.loads(item["timeline"])
                except Exception:
                    item["timeline"] = []
            elif item.get("timeline") is None:
                item["timeline"] = []

            if not item.get("status"):
                item["status"] = "1. Penawaran Purchasing"
            if not item.get("divisi"):
                item["divisi"] = "IT"
            if not item.get("urgensi"):
                item["urgensi"] = "Normal"
            if item.get("harga_estimasi") is None:
                item["harga_estimasi"] = 0
            if not item.get("vendor"):
                item["vendor"] = "-"

        return data
    except Exception as e:
        st.error(f"Gagal memuat database dari Supabase: {e}")
        return []


def save_database(item_data, is_new=False):
    try:
        db_payload = {
            "nama_barang": str(item_data.get("nama_barang", "")),
            "nomor_opb": str(item_data.get("nomor_opb", "")),
            "jumlah": int(item_data.get("jumlah", 1)),
            "keterangan": str(item_data.get("keterangan", "") or ""),
            "divisi": str(item_data.get("divisi", "IT")),
            "urgensi": str(item_data.get("urgensi", "Normal")),
            "status": str(item_data.get("status", "1. Penawaran Purchasing")),
            "harga_estimasi": int(item_data.get("harga_estimasi", 0) or 0),
            "vendor": str(item_data.get("vendor", "-")),
            "file_opb_url": item_data.get("file_opb_url"),
            "file_iom_url": item_data.get("file_iom_url"),
            "file_bast_url": item_data.get("file_bast_url"),
            "catatan_bm": str(item_data.get("catatan_bm", "-")),
            "catatan_finance": str(item_data.get("catatan_finance", "-")),
            "catatan_p3srs": str(item_data.get("catatan_p3srs", "-")),
            "timeline": json.dumps(item_data.get("timeline", [])),
        }

        if not is_new and "id" in item_data:
            db_payload["id"] = int(item_data["id"])

        if is_new:
            response = supabase.table("opb_data").insert(db_payload).execute()
        else:
            response = supabase.table("opb_data").update(db_payload).eq("id", db_payload["id"]).execute()

        return response
    except Exception as e:
        st.error(f"❌ Gagal Database Supabase: {e}")
        return None


def calculate_budget_summary(data_list):
    budget_usage = {div: 0 for div in INITIAL_BUDGETS}
    for item in data_list:
        div = item.get("divisi", "IT")
        if item.get("status") in [
            "6. Serah Terima Barang (Purchasing -> Engineering)",
            "7. Verifikasi Penerimaan Barang (Engineering)",
            "8. Selesai",
        ]:
            harga = item.get("harga_estimasi", 0) or 0
            if div in budget_usage:
                budget_usage[div] += harga

    summary = {}
    for div, initial in INITIAL_BUDGETS.items():
        terpakai = budget_usage.get(div, 0)
        sisa = initial - terpakai
        summary[div] = {
            "pagu_awal": initial,
            "terpakai": terpakai,
            "sisa": sisa
        }
    return summary


def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Detail Potongan Budget')
    return output.getvalue()


# --- FUNGSI GENERATE EMAIL WEBMAIL / OUTLOOK ---
def generate_outlook_mailto_link(item, target_email="purchasing@p3srs.com"):
    nomor_opb = item.get('nomor_opb', 'OPB')
    divisi = item.get('divisi', 'IT')
    nama_barang = item.get('nama_barang', '-')
    status = item.get('status', '-')
    harga = item.get('harga_estimasi', 0)
    urgensi = item.get('urgensi', 'Normal')
    opb_url = item.get('file_opb_url', '-')
    
    subject = urllib.parse.quote(f"📋 Tindak Lanjut OPB: {nomor_opb} - Divisi {divisi}")
    body = urllib.parse.quote(
        f"Halo Tim,\n\nTerdapat pembaruan dokumen OPB/IOM pada sistem:\n\n"
        f"- Nomor OPB: {nomor_opb}\n- Divisi: {divisi}\n- Barang: {nama_barang}\n"
        f"- Estimasi: Rp {harga:,.0f}\n- Status: {status}\n- Link OPB: {opb_url}\n\nTerima kasih."
    )
    return f"mailto:{target_email}?subject={subject}&body={body}"


# --- 3. RESPONSIVE CUSTOM CSS ---
st.markdown(
    """
    <style>
    .stApp { background: #f8fafc; }
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 24px 28px; border-radius: 18px; color: white; margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
    }
    .main-header h1 { color: #ffffff !important; font-weight: 800; margin: 0; font-size: 26px; }
    .main-header p { color: #c7d2fe; margin-top: 6px; margin-bottom: 0; font-size: 13px; }
    .kpi-card {
        background: white; border-radius: 16px; padding: 18px 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
    }
    .content-box {
        background: white; border-radius: 16px; padding: 20px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.03); margin-bottom: 20px;
    }
    .user-profile-card {
        background: white; padding: 14px 18px; border-radius: 14px;
        border: 1px solid #e2e8f0; margin-bottom: 15px;
    }
    .role-badge {
        background: #e0e7ff; color: #3730a3; padding: 3px 10px;
        border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 5px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 4. DATABASE USER (HASHED PASSWORD SIMULASI) ---
USERS = {
    "engineering": {"password": "eng123", "name": "Tim Engineering", "role": "Engineering"},
    "purchasing": {"password": "pur123", "name": "Tim Purchasing", "role": "Purchasing"},
    "bm": {"password": "bm123", "name": "Building Manager", "role": "BM (Building Manager)"},
    "finance": {"password": "fin123", "name": "Tim Finance", "role": "Finance"},
    "p3srs": {"password": "p3srs123", "name": "Pengurus P3SRS", "role": "P3SRS"},
}

# --- 5. LOG & TANDA TANGAN DIGITAL REAL CANVAS ---
def generate_digital_signature(user_role, user_name, doc_id, sig_image_data=None):
    wib = pytz.timezone("Asia/Jakarta")
    waktu = datetime.now(wib).strftime("%Y-%m-%d %H:%M:%S")
    raw_data = f"{doc_id}-{user_role}-{user_name}-{waktu}"
    sig_hash = hashlib.sha256(raw_data.encode()).hexdigest()[:12].upper()
    return {
        "signed_by": user_name,
        "role": user_role,
        "timestamp": waktu,
        "hash": f"DS-P3SRS-{sig_hash}",
        "signature_image": sig_image_data # Menyimpan base64 coretan canvas asli
    }

def catat_log(item, pesan, digital_sig=None):
    wib = pytz.timezone("Asia/Jakarta")
    waktu_sekarang = datetime.now(wib).strftime("%d/%m/%Y %H:%M:%S")
    log_entry = {"waktu": waktu_sekarang, "pesan": pesan}
    if digital_sig:
        log_entry["signature"] = digital_sig
    if "timeline" not in item or not isinstance(item["timeline"], list):
        item["timeline"] = []
    item["timeline"].append(log_entry)

def render_enhanced_timeline(timeline_data):
    if not timeline_data:
        st.caption("Belum ada riwayat aktivitas.")
        return

    for i, log_entry in enumerate(timeline_data):
        waktu_log = log_entry.get("waktu", "-")
        pesan_log = log_entry.get("pesan", "-")
        sig = log_entry.get("signature", {})
        actor_log = sig.get("role", "Sistem / User") if sig else "Sistem"
        
        st.markdown(f"""
        <div style="border-left: 2px solid #3b82f6; padding-left: 10px; margin-bottom: 10px;">
            <small style="color: #64748b;">🕒 {waktu_log} | 👤 <b>{actor_log}</b></small><br>
            <span style="font-size: 12px; color: #1e293b;">{pesan_log}</span>
        </div>
        """, unsafe_allow_html=True)

def render_download_buttons(item, key_prefix="dl"):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if item.get("file_opb_url"):
            st.markdown(f"[📥 Download OPB]({item['file_opb_url']})")
        else:
            resume_text = f"RESUME OPB\nNomor: {item.get('nomor_opb', '-')}\nBarang: {item.get('nama_barang', '-')}"
            st.download_button("📄 Draft OPB", data=resume_text.encode("utf-8"), file_name="opb.txt", key=f"{key_prefix}_txt_{item.get('id', 0)}")
    with col2:
        if item.get("file_iom_url"):
            st.markdown(f"[📥 Download IOM]({item['file_iom_url']})")
        else:
            st.caption("ℹ️ IOM Belum Ada")
    with col3:
        if item.get("file_bast_url"):
            st.markdown(f"[📦 Download BAST]({item['file_bast_url']})")
        else:
            st.caption("ℹ️ BAST Belum Ada")

def render_signature_pad(key_id):
    """Komponen HTML Canvas interaktif yang menangkap gambar tanda tangan asli ke Streamlit State."""
    canvas_html = f"""
    <div style="border:1px dashed #6366f1; padding:8px; border-radius:12px; background:#f8fafc; text-align:center;">
        <label style="font-size:12px; font-weight:bold; color:#3730a3; display:block; margin-bottom:6px;">
            ✍️ Goreskan Tanda Tangan Digital Anda:
        </label>
        <canvas id="sigCanvas_{key_id}" style="border:1px solid #cbd5e1; border-radius:8px; background:#ffffff; width:100%; height:120px; touch-action:none;"></canvas>
        <br>
        <button type="button" onclick="clearCanvas_{key_id}()" style="margin-top:6px; background:#f1f5f9; border:1px solid #cbd5e1; padding:4px 12px; border-radius:6px; font-size:11px; cursor:pointer;">
            🗑️ Bersihkan
        </button>
    </div>
    <input type="hidden" id="sigData_{key_id}" name="sigData_{key_id}">
    <script>
        var canvas = document.getElementById('sigCanvas_{key_id}');
        var ctx = canvas.getContext('2d');
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        var drawing = false;

        function getPos(e) {{
            var rect = canvas.getBoundingClientRect();
            var clientX = e.clientX || (e.touches && e.touches[0].clientX);
            var clientY = e.clientY || (e.touches && e.touches[0].clientY);
            return {{ x: clientX - rect.left, y: clientY - rect.top }};
        }}

        canvas.addEventListener('mousedown', function(e){{ drawing = true; ctx.beginPath(); var pos = getPos(e); ctx.moveTo(pos.x, pos.y); }});
        canvas.addEventListener('mousemove', function(e){{ if (!drawing) return; var pos = getPos(e); ctx.lineTo(pos.x, pos.y); ctx.strokeStyle = '#1e1b4b'; ctx.lineWidth = 2; ctx.stroke(); }});
        canvas.addEventListener('mouseup', function(){{ drawing = false; document.getElementById('sigData_{key_id}').value = canvas.toDataURL(); }});
        
        function clearCanvas_{key_id}() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            document.getElementById('sigData_{key_id}').value = "";
        }}
    </script>
    """
    components.html(canvas_html, height=190)

def cek_notifikasi_user(role):
    db = st.session_state.get("db_opb", [])
    if role == "Purchasing":
        return [x for x in db if x.get("status") in ["1. Penawaran Purchasing", "3. Pembuatan IOM (Purchasing)", "6. Serah Terima Barang (Purchasing -> Engineering)", "Revisi BM (OPB)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
    elif role == "BM (Building Manager)":
        return [x for x in db if x.get("status") in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
    elif role == "Finance":
        return [x for x in db if x.get("status") == "4. Review Finance"]
    elif role == "P3SRS":
        return [x for x in db if x.get("status") == "5. Approval Akhir (BM & P3SRS)"]
    elif role == "Engineering":
        return [x for x in db if x.get("status") == "7. Verifikasi Penerimaan Barang (Engineering)"]
    return []


# --- 6. INITIALIZATION SESSION STATE ---
if "db_opb" not in st.session_state:
    st.session_state["db_opb"] = load_database()

cookie_manager = stx.CookieManager(key="my_cookie_manager")
user_cookie = cookie_manager.get("opb_p3srs_user")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

if not st.session_state["logged_in"] and user_cookie:
    st.session_state["logged_in"] = True
    st.session_state["user_info"] = user_cookie

if "target_focus_id" not in st.session_state:
    st.session_state["target_focus_id"] = None


# ==================== HALAMAN LOGIN ====================
if not st.session_state["logged_in"]:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<br><h2 style='text-align: center; color: #1e1b4b;'>Portal OPB & IOM - P3SRS</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username_input = st.text_input("Username", placeholder="engineering, purchasing, bm...")
            password_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("🔒 Masuk ke Portal", type="primary", use_container_width=True)

            if submit_login:
                user_data = USERS.get(username_input.lower().strip())
                if user_data and user_data["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user_data
                    cookie_manager.set("opb_p3srs_user", user_data, key="set_cookie_login")
                    st.rerun()
                else:
                    st.error("❌ Username atau Password salah!")
else:
    user_info = st.session_state["user_info"]
    role = user_info["role"]
    pending_tasks = cek_notifikasi_user(role)

    st.sidebar.markdown(f"""
        <div class="user-profile-card">
            <h4 style="margin:0; color:#0f172a; font-size:14px;">👤 {user_info['name']}</h4>
            <span class="role-badge">{user_info['role']}</span>
        </div>
    """, unsafe_allow_html=True)

    if pending_tasks:
        st.sidebar.warning(f"🔔 **{len(pending_tasks)} Tugas Menunggu**")

    if st.sidebar.button("🚪 Keluar / Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_info"] = None
        cookie_manager.delete("opb_p3srs_user", key="delete_cookie_logout")
        st.rerun()

    st.sidebar.markdown("---")

    st.markdown(f"""
        <div class="main-header">
            <h1>📋 Sistem Pengajuan OPB & IOM - P3SRS</h1>
            <p>Akses Peran: <b>{role}</b></p>
        </div>
    """, unsafe_allow_html=True)

    # ================= EXECUTIVE DASHBOARD =================
    st.markdown("### 📊 Dashboard Monitoring & Budgeting Divisi")
    
    TAHAPAN_OPB = [
        "1. Penawaran Purchasing", "2. Review BM", "3. Pembuatan IOM (Purchasing)",
        "4. Review Finance", "5. Approval Akhir (BM & P3SRS)",
        "6. Serah Terima Barang (Purchasing -> Engineering)",
        "7. Verifikasi Penerimaan Barang (Engineering)", "8. Selesai",
    ]

    total_opb = len(st.session_state["db_opb"])
    budget_summary = calculate_budget_summary(st.session_state["db_opb"])

    if total_opb > 0:
        df_opb = pd.DataFrame(st.session_state["db_opb"])
        total_selesai = len(df_opb[df_opb["status"] == "8. Selesai"])
        total_proses = total_opb - total_selesai
        total_anggaran = df_opb["harga_estimasi"].fillna(0).sum()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Permintaan</div><div class="kpi-value">{total_opb} OPB</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Dalam Proses</div><div class="kpi-value" style="color:#d97706;">{total_proses} OPB</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Selesai</div><div class="kpi-value" style="color:#059669;">{total_selesai} OPB</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Transaksi</div><div class="kpi-value" style="color:#7c3aed; font-size:18px;">Rp {total_anggaran:,.0f}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if role != "Engineering":
            with st.expander("💳 **RINCIAN BUDGET & SISA ANGGARAN PER DIVISI**", expanded=True):
                b_cols = st.columns(len(budget_summary))
                for idx, (div_name, b_info) in enumerate(budget_summary.items()):
                    with b_cols[idx]:
                        st.markdown(f"**{div_name}**")
                        st.caption(f"Pagu: Rp {b_info['pagu_awal']:,}")
                        st.caption(f"Terpakai: Rp {b_info['terpakai']:,}")
                        sisa_color = "green" if b_info['sisa'] > 0 else "red"
                        st.markdown(f"<span style='color:{sisa_color}; font-weight:bold; font-size:12px;'>Sisa: Rp {b_info['sisa']:,}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # ==================== MODUL USER PANELS ====================

    # 1. ROLE ENGINEERING
    if role == "Engineering":
        st.header("🔧 Panel Kerja Engineering")
        tab1, tab2 = st.tabs(["📝 Buat Form OPB Baru", "📦 Verifikasi Penerimaan Barang (BAST)"])

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            divisi_pilihan = st.selectbox("Divisi Pemohon", DIVISI_LIST)
            budget_div_info = budget_summary.get(divisi_pilihan, {"sisa": 1_000_000_000})
            st.info(f"💰 **Sisa Budget Divisi {divisi_pilihan}:** Rp {budget_div_info['sisa']:,}")

            next_number = len(st.session_state["db_opb"]) + 1
            nomor_opb_auto = f"OPB/{divisi_pilihan.upper()}/{next_number:03d}"
            st.text_input("Nomor OPB (Otomatis)", value=nomor_opb_auto, disabled=True)

            with st.form(key="form_opb_engineering", clear_on_submit=True):
                urgensi = st.radio("Tingkat Urgensi", ["🔴 Darurat", "🟠 Prioritas", "🟢 Medium", "⚪ Normal"], horizontal=True)
                nama_barang = st.text_area("Detail Pengajuan Barang")
                keterangan = st.text_area("Alasan Kebutuhan")
                file_opb = st.file_uploader("Unggah Lampiran BA", type=["pdf", "docx", "xlsx"])

                submit = st.form_submit_button("🚀 Kirim OPB ke Purchasing", type="primary", use_container_width=True)

            if submit:
                if nama_barang:
                    file_url = upload_file_to_supabase(file_opb.getvalue(), file_opb.name, folder="opb") if file_opb else None
                    sig_eng = generate_digital_signature("Engineering", user_info["name"], nomor_opb_auto)
                    data_baru = {
                        "nomor_opb": nomor_opb_auto, "divisi": divisi_pilihan, "urgensi": urgensi,
                        "nama_barang": nama_barang, "jumlah": 1, "keterangan": keterangan,
                        "file_opb_url": file_url, "harga_estimasi": 0, "vendor": "-",
                        "status": "1. Penawaran Purchasing", "timeline": []
                    }
                    catat_log(data_baru, f"OPB Dibuat oleh {user_info['name']}", digital_sig=sig_eng)
                    if save_database(data_baru, is_new=True):
                        st.toast("OPB Berhasil dikirim!", icon="✅")
                        st.rerun()
                else:
                    st.warning("Detail barang wajib diisi.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if x.get("status") == "7. Verifikasi Penerimaan Barang (Engineering)"]
            if not items:
                st.info("Tidak ada barang menunggu verifikasi.")
            for item in items:
                with st.expander(f"📦 {item.get('nomor_opb')} - {item.get('nama_barang')}"):
                    render_download_buttons(item)
                    if st.button(f"✅ Konfirmasi & Terima Barang", type="primary", use_container_width=True):
                        sig_rcv = generate_digital_signature("Engineering", user_info["name"], item.get("nomor_opb"))
                        item["status"] = "8. Selesai"
                        catat_log(item, "Barang diterima dan diverifikasi.", digital_sig=sig_rcv)
                        save_database(item, is_new=False)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. ROLE PURCHASING
    elif role == "Purchasing":
        st.header("🛒 Panel Kerja Purchasing")
        tab1, tab2, tab3 = st.tabs(["1. Input Harga", "2. Unggah IOM", "3. Serah Terima Barang"])

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if x.get("status") in ["1. Penawaran Purchasing", "Revisi BM (OPB)"]]
            if not items:
                st.info("Tidak ada tugas penawaran.")
            for item in items:
                with st.expander(f"📌 {item.get('nomor_opb')} - {item.get('nama_barang')}"):
                    div_item = item.get('divisi', 'IT')
                    sisa_skrg = budget_summary.get(div_item, {}).get('sisa', 1_000_000_000)
                    
                    with st.form(key=f"form_pur_{item.get('id')}"):
                        vendor_input = st.text_input("Vendor Pilihan", value=item.get("vendor", "-"))
                        harga_input = st.number_input("Estimasi Harga (Rp)", min_value=0, value=int(item.get("harga_estimasi", 0)))
                        
                        sisa_setelah = sisa_skrg - harga_input
                        is_overbudget = sisa_setelah < 0
                        if is_overbudget:
                            st.error(f"⚠️ Peringatan: Estimasi melebihi sisa budget divisi ({sisa_skrg:,})!")
                        
                        submit_pur = st.form_submit_button("Kirim ke BM", type="primary", use_container_width=True, disabled=is_overbudget)

                    if submit_pur:
                        sig_pur = generate_digital_signature("Purchasing", user_info["name"], item.get("nomor_opb"))
                        item["vendor"] = vendor_input
                        item["harga_estimasi"] = int(harga_input)
                        item["status"] = "2. Review BM"
                        catat_log(item, f"Vendor dipilih: {vendor_input}, Harga: Rp {harga_input:,}", digital_sig=sig_pur)
                        save_database(item, is_new=False)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if x.get("status") in ["3. Pembuatan IOM (Purchasing)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
            if not items:
                st.info("Tidak ada IOM perlu diunggah.")
            for item in items:
                with st.expander(f"📑 IOM: {item.get('nomor_opb')}"):
                    file_iom = st.file_uploader("Upload IOM (PDF/Docx)", type=["pdf", "docx"], key=f"fiom_{item.get('id')}")
                    if st.button("Kirim ke Finance", type="primary", key=f"btn_fiom_{item.get('id')}"):
                        if file_iom:
                            item["file_iom_url"] = upload_file_to_supabase(file_iom.getvalue(), file_iom.name, folder="iom")
                            item["status"] = "4. Review Finance"
                            catat_log(item, "IOM diunggah ke Finance.")
                            save_database(item, is_new=False)
                            st.rerun()
                        else:
                            st.warning("Pilih file terlebih dahulu.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if x.get("status") == "6. Serah Terima Barang (Purchasing -> Engineering)"]
            if not items:
                st.info("Tidak ada pengiriman barang.")
            for item in items:
                with st.expander(f"🚚 Kirim Barang: {item.get('nomor_opb')}"):
                    file_bast = st.file_uploader("Upload BAST", type=["pdf", "jpg", "png"], key=f"bast_{item.get('id')}")
                    if st.button("Serahkan ke Engineering", type="primary", key=f"btn_bast_{item.get('id')}"):
                        if file_bast:
                            item["file_bast_url"] = upload_file_to_supabase(file_bast.getvalue(), file_bast.name, folder="bast")
                        item["status"] = "7. Verifikasi Penerimaan Barang (Engineering)"
                        catat_log(item, "Barang diserahkan ke Engineering.")
                        save_database(item, is_new=False)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 3. ROLE BUILDING MANAGER
    elif role == "BM (Building Manager)":
        st.header("👔 Panel Building Manager (BM)")
        tab1, tab2 = st.tabs(["Review OPB (Awal)", "Approval Final IOM"])

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if x.get("status") == "2. Review BM"]
            if not items:
                st.info("Tidak ada OPB menunggu review.")
            for item in items:
                with st.expander(f"🧐 Review: {item.get('nomor_opb')}"):
                    render_download_buttons(item)
                    catatan = st.text_input("Catatan Revisi", key=f"c_bm_{item.get('id')}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Setujui OPB", type="primary", key=f"bm_acc_{item.get('id')}"):
                            item["status"] = "3. Pembuatan IOM (Purchasing)"
                            catat_log(item, "OPB Disetujui BM.")
                            save_database(item, is_new=False)
                            st.rerun()
                    with col2:
                        if st.button("❌ Minta Revisi OPB", key=f"bm_rej_{item.get('id')}"):
                            item["status"] = "Revisi BM (OPB)"
                            item["catatan_bm"] = catatan
                            catat_log(item, f"Revisi diminta: {catatan}")
                            save_database(item, is_new=False)
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if x.get("status") == "5. Approval Akhir (BM & P3SRS)"]
            if not items:
                st.info("Tidak ada IOM menunggu approval final.")
            for item in items:
                with st.expander(f"📑 Approval IOM: {item.get('nomor_opb')}"):
                    render_download_buttons(item)
                    if st.button("✅ Approve IOM Final (BM)", type="primary", key=f"bm_iom_{item.get('id')}"):
                        # PERBAIKAN: Memajukan status dokumen ke tahap berikutnya agar tidak stuck
                        item["status"] = "6. Serah Terima Barang (Purchasing -> Engineering)"
                        sig_bm = generate_digital_signature("Building Manager", user_info["name"], item.get("nomor_opb"))
                        catat_log(item, "IOM Disetujui Final oleh BM.", digital_sig=sig_bm)
                        save_database(item, is_new=False)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 4. ROLE FINANCE
    elif role == "Finance":
        st.header("💰 Panel Finance & Budgeting")
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        items = [x for x in st.session_state["db_opb"] if x.get("status") == "4. Review Finance"]
        if not items:
            st.info("Tidak ada IOM menunggu verifikasi budget.")
        for item in items:
            with st.expander(f"💵 Review Budget: {item.get('nomor_opb')}"):
                render_download_buttons(item)
                if st.button("✅ Verifikasi Budget", type="primary", key=f"fin_acc_{item.get('id')}"):
                    item["status"] = "5. Approval Akhir (BM & P3SRS)"
                    catat_log(item, "Budget diverifikasi Finance.")
                    save_database(item, is_new=False)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. ROLE P3SRS
    elif role == "P3SRS":
        st.header("🏛️ Panel P3SRS (Approval Akhir)")
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        items = [x for x in st.session_state["db_opb"] if x.get("status") == "5. Approval Akhir (BM & P3SRS)"]
        if not items:
            st.info("Tidak ada IOM menunggu keputusan P3SRS.")
        for item in items:
            with st.expander(f"⚖️ Keputusan Final: {item.get('nomor_opb')}"):
                render_download_buttons(item)
                if st.button("✅ ACC & Lanjut Pengiriman", type="primary", key=f"p3srs_acc_{item.get('id')}"):
                    item["status"] = "6. Serah Terima Barang (Purchasing -> Engineering)"
                    catat_log(item, "Disetujui penuh oleh P3SRS.")
                    save_database(item, is_new=False)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
