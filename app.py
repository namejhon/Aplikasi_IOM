import base64
import hashlib
import json
import os
from datetime import datetime
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import pytz
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
from supabase import Client, create_client

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Flow OPB & IOM - P3SRS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- 1.1 AUTO REFRESH (Polling Realtime Data tiap 5 detik) ---
st_autorefresh(interval=5000, limit=None, key="opb_datarefresh")

# --- INISIALISASI SUPABASE CLIENT ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase Credentials belum diatur di Secrets/Environment Variables!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "opb-files"

# --- 2. FUNGSI PERSISTENSI DATA (SUPABASE STORAGE & DB) ---
def upload_file_to_supabase(file_bytes, file_name, folder="opb"):
    """Mengunggah file ke Supabase Storage dan mengembalikan URL Publiknya."""
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

        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(
            safe_filename
        )
        return public_url
    except Exception as e:
        st.error(f"Gagal upload file ke Supabase Storage: {e}")
        return None


def load_database():
    """Membaca seluruh data OPB dari tabel Supabase."""
    try:
        response = (
            supabase.table("opb_data")
            .select("*")
            .order("id", desc=False)
            .execute()
        )
        data = response.data
        for item in data:
            if isinstance(item.get("timeline"), str):
                try:
                    item["timeline"] = json.loads(item["timeline"])
                except Exception:
                    item["timeline"] = []
            elif item.get("timeline") is None:
                item["timeline"] = []
        return data
    except Exception as e:
        st.error(f"Gagal memuat database dari Supabase: {e}")
        return []


def save_database(item_data, is_new=False):
    """Menyimpan item tunggal ke Supabase (Insert jika baru, Update jika ada)."""
    try:
        db_payload = item_data.copy()

        db_payload.pop("file_opb_bytes", None)
        db_payload.pop("file_iom_bytes", None)
        db_payload.pop("file_bast_bytes", None)

        if isinstance(db_payload.get("timeline"), list):
            db_payload["timeline"] = json.dumps(db_payload["timeline"])

        if is_new:
            db_payload.pop("id", None)
            response = supabase.table("opb_data").insert(db_payload).execute()
        else:
            response = (
                supabase.table("opb_data")
                .update(db_payload)
                .eq("id", db_payload["id"])
                .execute()
            )

        return response
    except Exception as e:
        st.error(f"Gagal menyimpan ke Supabase: {e}")


# --- 3. RESPONSIVE CUSTOM CSS (OPTIMIZED FOR MOBILE & DESKTOP) ---
st.markdown(
    """
    <style>
    /* Styling Dasar Dashboard */
    .stApp { background: #f8fafc; }
    
    /* Header Utama */
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 24px 28px;
        border-radius: 18px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
    }
    .main-header h1 { color: #ffffff !important; font-weight: 800; letter-spacing: -0.5px; margin: 0; font-size: 26px; }
    .main-header p { color: #c7d2fe; margin-top: 6px; margin-bottom: 0; font-size: 13px; }
    
    /* KPI Card Responsif */
    .kpi-card {
        background: white; border-radius: 16px; padding: 18px 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
        position: relative; overflow: hidden; transition: all 0.3s ease; margin-bottom: 10px;
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.08); }
    .kpi-blue { border-top: 4px solid #3b82f6; }
    .kpi-amber { border-top: 4px solid #f59e0b; }
    .kpi-emerald { border-top: 4px solid #10b981; }
    .kpi-purple { border-top: 4px solid #8b5cf6; }
    
    .kpi-title { color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
    .kpi-value { color: #0f172a; font-size: 24px; font-weight: 800; margin-top: 4px; }
    .kpi-sub { font-size: 11px; font-weight: 600; margin-top: 4px; }
    
    /* User Profile Card */
    .user-profile-card {
        background: white; padding: 14px 18px; border-radius: 14px;
        border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 15px;
    }
    .role-badge {
        background: #e0e7ff; color: #3730a3; padding: 3px 10px;
        border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 5px;
    }
    
    /* Notification Card */
    .notif-box {
        background: linear-gradient(135deg, #fffbe3 0%, #fef3c7 100%);
        border-left: 5px solid #f59e0b; color: #78350f; padding: 16px 20px;
        border-radius: 16px; margin-bottom: 18px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.12);
    }
    
    /* Content Boxes */
    .content-box {
        background: white; border-radius: 16px; padding: 20px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.03); margin-bottom: 20px;
    }

    /* Animasi Timeline */
    .timeline-container { position: relative; padding-left: 20px; margin: 15px 0 10px 5px; border-left: 3px solid #e2e8f0; }
    .timeline-card {
        position: relative; background: #ffffff; border: 1px solid #e2e8f0;
        border-radius: 12px; padding: 12px 16px; margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03); transition: all 0.2s ease;
    }
    .timeline-card:hover { border-color: #818cf8; }
    .timeline-card::before {
        content: ''; position: absolute; left: -27px; top: 16px; width: 12px; height: 12px;
        border-radius: 50%; background-color: #6366f1; border: 3px solid #ffffff;
    }
    .timeline-time {
        display: inline-flex; align-items: center; background: #e0e7ff;
        color: #3730a3; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin-bottom: 6px;
    }
    .timeline-desc { color: #0f172a; font-size: 13px; font-weight: 500; line-height: 1.4; margin: 0; }
    .digital-signature-badge {
        display: inline-block; background: #ecfdf5; border: 1px dashed #10b981;
        color: #047857; font-size: 10.5px; padding: 3px 8px; border-radius: 6px; margin-top: 6px; font-family: monospace; word-break: break-all;
    }

    /* MEDIA QUERIES UNTUK HP (MOBILE ADAPTATIVE) */
    @media (max-width: 768px) {
        .main-header { padding: 18px 20px; border-radius: 14px; }
        .main-header h1 { font-size: 20px !important; }
        .main-header p { font-size: 12px !important; }
        .content-box { padding: 15px; border-radius: 12px; }
        .kpi-value { font-size: 20px; }
        .stButton>button { width: 100% !important; }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 4. DATABASE USER & PASSWORD ---
USERS = {
    "engineering": {
        "password": "eng123",
        "name": "Tim Engineering",
        "role": "Engineering",
    },
    "purchasing": {
        "password": "pur123",
        "name": "Tim Purchasing",
        "role": "Purchasing",
    },
    "bm": {
        "password": "bm123",
        "name": "Building Manager",
        "role": "BM (Building Manager)",
    },
    "finance": {
        "password": "fin123",
        "name": "Tim Finance",
        "role": "Finance",
    },
    "p3srs": {
        "password": "p3srs123",
        "name": "Pengurus P3SRS",
        "role": "P3SRS",
    },
}


# --- 5. FUNGSI LOG DAN TANDA TANGAN DIGITAL ---
def generate_digital_signature(user_role, user_name, doc_id):
    wib = pytz.timezone("Asia/Jakarta")
    waktu = datetime.now(wib).strftime("%Y-%m-%d %H:%M:%S")
    raw_data = f"{doc_id}-{user_role}-{user_name}-{waktu}"
    sig_hash = hashlib.sha256(raw_data.encode()).hexdigest()[:12].upper()
    return {
        "signed_by": user_name,
        "role": user_role,
        "timestamp": waktu,
        "hash": f"DS-P3SRS-{sig_hash}",
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


def render_download_buttons(item, key_prefix="dl"):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if item.get("file_opb_url"):
            st.markdown(
                f"[📥 Download OPB]({item['file_opb_url']})"
            )
        else:
            resume_text = f"RESUME DOKUMEN OPB\nNomor: {item['nomor_opb']}\nNama Barang: {item['nama_barang']}\nJumlah: {item['jumlah']}\nKeterangan: {item['keterangan']}"
            st.download_button(
                label=f"📄 Draft OPB",
                data=resume_text.encode("utf-8"),
                file_name=f"{item['nomor_opb'].replace('/', '_')}.txt",
                mime="text/plain",
                key=f"{key_prefix}_opb_txt_{item['id']}",
                use_container_width=True,
            )

    with col2:
        if item.get("file_iom_url"):
            st.markdown(
                f"[📥 Download IOM]({item['file_iom_url']})"
            )
        else:
            st.caption("ℹ️ IOM Belum Ada")

    with col3:
        if item.get("file_bast_url"):
            st.markdown(
                f"[📦 Download BAST]({item['file_bast_url']})"
            )
        else:
            st.caption("ℹ️ BAST Belum Ada")


def render_signature_pad(key_id):
    """HTML Canvas Tanda Tangan Digital yang Responsif di HP & PC."""
    canvas_html = f"""
    <div style="border:1px dashed #6366f1; padding:8px; border-radius:12px; background:#f8fafc; text-align:center; max-width:100%;">
        <label style="font-size:12px; font-weight:bold; color:#3730a3; display:block; margin-bottom:6px;">
            ✍️ Goreskan Tanda Tangan Digital Anda (Touchscreen Ready):
        </label>
        <canvas id="sigCanvas_{key_id}" style="border:1px solid #cbd5e1; border-radius:8px; background:#ffffff; cursor:crosshair; touch-action:none; width:100%; height:120px;"></canvas>
        <br>
        <button onclick="clearCanvas_{key_id}()" style="margin-top:6px; background:#f1f5f9; border:1px solid #cbd5e1; padding:4px 12px; border-radius:6px; font-size:11px; cursor:pointer;">
            🗑️ Bersihkan Canvas
        </button>
    </div>
    <script>
        var canvas_{key_id} = document.getElementById('sigCanvas_{key_id}');
        var ctx_{key_id} = canvas_{key_id}.getContext('2d');
        
        // Auto Adjust Canvas Resolution
        canvas_{key_id}.width = canvas_{key_id}.offsetWidth;
        canvas_{key_id}.height = canvas_{key_id}.offsetHeight;

        var drawing_{key_id} = false;

        function getPos(e) {{
            var rect = canvas_{key_id}.getBoundingClientRect();
            var clientX = e.clientX || (e.touches && e.touches[0].clientX);
            var clientY = e.clientY || (e.touches && e.touches[0].clientY);
            return {{
                x: clientX - rect.left,
                y: clientY - rect.top
            }};
        }}

        function startDraw(e) {{ drawing_{key_id} = true; ctx_{key_id}.beginPath(); var pos = getPos(e); ctx_{key_id}.moveTo(pos.x, pos.y); }}
        function moveDraw(e) {{ if (!drawing_{key_id}) return; var pos = getPos(e); ctx_{key_id}.lineTo(pos.x, pos.y); ctx_{key_id}.strokeStyle = '#1e1b4b'; ctx_{key_id}.lineWidth = 2.5; ctx_{key_id}.stroke(); }}
        function stopDraw() {{ drawing_{key_id} = false; }}

        canvas_{key_id}.addEventListener('mousedown', startDraw);
        canvas_{key_id}.addEventListener('mousemove', moveDraw);
        canvas_{key_id}.addEventListener('mouseup', stopDraw);
        
        canvas_{key_id}.addEventListener('touchstart', function(e){{ startDraw(e); e.preventDefault(); }}, false);
        canvas_{key_id}.addEventListener('touchmove', function(e){{ moveDraw(e); e.preventDefault(); }}, false);
        canvas_{key_id}.addEventListener('touchend', stopDraw, false);

        function clearCanvas_{key_id}() {{
            ctx_{key_id}.clearRect(0, 0, canvas_{key_id}.width, canvas_{key_id}.height);
        }}
    </script>
    """
    components.html(canvas_html, height=185)


def cek_notifikasi_user(role):
    db = st.session_state["db_opb"]
    pending_items = []

    if role == "Purchasing":
        pending_items = [
            x
            for x in db
            if x["status"]
            in [
                "1. Penawaran Purchasing",
                "3. Pembuatan IOM (Purchasing)",
                "6. Serah Terima Barang (Purchasing -> Engineering)",
                "Revisi BM (OPB)",
                "Revisi Finance",
                "Revisi BM/P3SRS (IOM)",
            ]
        ]
    elif role == "BM (Building Manager)":
        pending_items = [
            x
            for x in db
            if x["status"]
            in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]
        ]
    elif role == "Finance":
        pending_items = [x for x in db if x["status"] == "4. Review Finance"]
    elif role == "P3SRS":
        pending_items = [
            x for x in db if x["status"] == "5. Approval Akhir (BM & P3SRS)"
        ]
    elif role == "Engineering":
        pending_items = [
            x
            for x in db
            if x["status"] == "7. Verifikasi Penerimaan Barang (Engineering)"
        ]

    return pending_items


# --- 6. INITIALIZATION SESSION STATE BERBASIS SUPABASE & COOKIE ---
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

if "notif_shown" not in st.session_state:
    st.session_state["notif_shown"] = False
if "target_focus_id" not in st.session_state:
    st.session_state["target_focus_id"] = None

# ==================== HALAMAN LOGIN INTERAKTIF & RESPONSIF ====================
if not st.session_state["logged_in"]:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])

    with col_l2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: -15px;">
                <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
                <lottie-player src="https://assets2.lottiefiles.com/packages/lf20_mbe44xec.json" background="transparent" speed="1" style="width: 220px; height: 180px; margin: 0 auto;" loop autoplay></lottie-player>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2 style='color: #1e1b4b; font-weight: 800; margin: 0; font-size: 24px;'>Portal OPB & IOM - P3SRS</h2>
                <p style='color: #64748b; font-size: 13px; margin-top: 5px;'>Sistem Digitalisasi OPB, IOM & Serah Terima Barang Inter-Divisi</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            st.markdown("##### 🔑 Silakan Login Akun Divisi")
            username_input = st.text_input(
                "Username",
                placeholder="Contoh: engineering, purchasing, bm, p3srs...",
            )
            password_input = st.text_input(
                "Password", type="password", placeholder="Masukkan password..."
            )
            submit_login = st.form_submit_button(
                "🔒 Masuk ke Portal", type="primary", use_container_width=True
            )

            if submit_login:
                user_data = USERS.get(username_input.lower().strip())
                if user_data and user_data["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user_data
                    st.session_state["notif_shown"] = False

                    cookie_manager.set(
                        "opb_p3srs_user", user_data, key="set_cookie_login"
                    )

                    st.toast("✅ Login Berhasil!", icon="🎉")
                    st.rerun()
                else:
                    st.error("❌ Username atau Password tidak sesuai!")

        with st.expander("ℹ️ Daftar Akun Login"):
            st.markdown("""
            - **Engineering**: `engineering` / `eng123`
            - **Purchasing**: `purchasing` / `pur123`
            - **BM**: `bm` / `bm123`
            - **Finance**: `finance` / `fin123`
            - **P3SRS**: `p3srs` / `p3srs123`
            """)

else:
    # ==================== APLIKASI UTAMA ====================
    user_info = st.session_state["user_info"]
    role = user_info["role"]

    pending_tasks = cek_notifikasi_user(role)
    if pending_tasks and not st.session_state["notif_shown"]:
        st.toast(
            f"🔔 **Pemberitahuan:** Ada {len(pending_tasks)} tugas baru menunggu tindakan Anda!",
            icon="📩",
        )
        st.session_state["notif_shown"] = True

    st.sidebar.markdown(
        f"""
        <div class="user-profile-card">
            <h4 style="margin:0; color:#0f172a; font-size:14px; font-weight:700;">👤 {user_info['name']}</h4>
            <span class="role-badge">{user_info['role']}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if pending_tasks:
        st.sidebar.warning(f"🔔 **{len(pending_tasks)} Tugas Menunggu**")

    if st.sidebar.button("🚪 Keluar / Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_info"] = None
        st.session_state["notif_shown"] = False
        st.session_state["target_focus_id"] = None

        cookie_manager.delete("opb_p3srs_user", key="delete_cookie_logout")
        st.rerun()

    st.sidebar.markdown("---")

    st.markdown(
        f"""
        <div class="main-header">
            <h1>📋 Sistem Pengajuan OPB & IOM - P3SRS</h1>
            <p>Platform Integrasi OPB, IOM & Digital Signature Handover | Hak Akses: <b>{role}</b></p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if pending_tasks:
        st.markdown(
            f"""
            <div class="notif-box">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <span style="font-size:20px;">🔔</span>
                    <span style="font-size: 15px; font-weight: 700;">Notifikasi Tugas Masuk ({len(pending_tasks)} Berkas)</span>
                </div>
                <div style="font-size: 12px; margin-bottom: 10px; opacity: 0.9;">
                    Klik tombol di bawah ini untuk langsung menuju berkas pekerjaan terkait:
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        btn_cols = st.columns(min(len(pending_tasks), 4))
        for i, item_task in enumerate(pending_tasks):
            col_idx = i % 4
            with btn_cols[col_idx]:
                if st.button(
                    f"👉 Kelola: {item_task['nomor_opb']}",
                    key=f"quick_btn_{item_task['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["target_focus_id"] = item_task["id"]
                    components.html(
                        """
                        <script>
                            window.parent.document.getElementById("anchor-kelola-opb").scrollIntoView({behavior: "smooth"});
                        </script>
                        """,
                        height=0,
                    )
        st.markdown("<br>", unsafe_allow_html=True)

    # ================= EXECUTIVE DASHBOARD =================
    st.markdown("### 📊 Dashboard Monitoring & Analisis P3SRS")

    TAHAPAN_OPB = [
        "1. Penawaran Purchasing",
        "2. Review BM",
        "3. Pembuatan IOM (Purchasing)",
        "4. Review Finance",
        "5. Approval Akhir (BM & P3SRS)",
        "6. Serah Terima Barang (Purchasing -> Engineering)",
        "7. Verifikasi Penerimaan Barang (Engineering)",
        "8. Selesai",
    ]

    total_opb = len(st.session_state["db_opb"])

    if total_opb > 0:
        df_opb = pd.DataFrame(st.session_state["db_opb"])
        total_selesai = len(df_opb[df_opb["status"] == "8. Selesai"])
        total_proses = total_opb - total_selesai
        total_anggaran = df_opb["harga_estimasi"].sum()

        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.markdown(
                f"""
                <div class="kpi-card kpi-blue">
                    <div class="kpi-title">Total Permintaan</div>
                    <div class="kpi-value">{total_opb} <span style="font-size:13px; color:#64748b;">OPB</span></div>
                    <div class="kpi-sub" style="color:#2563eb;">📂 Seluruh Berkas</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        with m2:
            st.markdown(
                f"""
                <div class="kpi-card kpi-amber">
                    <div class="kpi-title">Dalam Process</div>
                    <div class="kpi-value" style="color:#d97706;">{total_proses} <span style="font-size:13px; color:#64748b;">OPB</span></div>
                    <div class="kpi-sub" style="color:#d97706;">⏳ On Progress</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        with m3:
            st.markdown(
                f"""
                <div class="kpi-card kpi-emerald">
                    <div class="kpi-title">Selesai (Completed)</div>
                    <div class="kpi-value" style="color:#059669;">{total_selesai} <span style="font-size:13px; color:#64748b;">OPB</span></div>
                    <div class="kpi-sub" style="color:#059669;">✅ Verified</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        with m4:
            st.markdown(
                f"""
                <div class="kpi-card kpi-purple">
                    <div class="kpi-title">Total Estimasi Budget</div>
                    <div class="kpi-value" style="color:#7c3aed; font-size:20px;">Rp {total_anggaran:,.0f}</div>
                    <div class="kpi-sub" style="color:#7c3aed;">💰 Total Anggaran</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_dash1, col_dash2 = st.columns([1.3, 1])

        with col_dash1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown(
                "##### 📌 Progress Live Status & Timeline Berkas"
            )
            st.markdown("<br>", unsafe_allow_html=True)
            for idx, item in enumerate(st.session_state["db_opb"]):
                status_curr = item["status"]

                if "Revisi" in status_curr:
                    prog_pct = 25
                    status_badge = "⚠️ Minta Revisi"
                elif status_curr in TAHAPAN_OPB:
                    step_idx = TAHAPAN_OPB.index(status_curr) + 1
                    prog_pct = int((step_idx / len(TAHAPAN_OPB)) * 100)
                    status_badge = f"Tahap {step_idx}/{len(TAHAPAN_OPB)}"
                else:
                    prog_pct = 0
                    status_badge = "Draft"

                st.markdown(
                    f"**{item['nomor_opb']}** — {item['nama_barang']} (`{item['vendor']}`)"
                )
                c_a, c_b = st.columns([4, 1])
                with c_a:
                    st.progress(prog_pct)
                with c_b:
                    st.caption(f"**{prog_pct}%**")
                st.caption(
                    f"📍 Status: `{status_curr}` | 💰 Est: Rp {item['harga_estimasi']:,}"
                )

                st.markdown("📂 **Unduh Lampiran Berkas:**")
                render_download_buttons(item, key_prefix=f"dash_{idx}")

                with st.expander(
                    f"📜 Timeline & Jejak Verifikasi ({len(item['timeline'])} Aktivitas)"
                ):
                    if item["timeline"]:
                        st.markdown(
                            "<div class='timeline-container'>",
                            unsafe_allow_html=True,
                        )
                        for log_entry in item["timeline"]:
                            if isinstance(log_entry, dict):
                                waktu_log = log_entry.get("waktu", "")
                                pesan_log = log_entry.get("pesan", "")
                                sig = log_entry.get("signature", None)
                            else:
                                waktu_log = "Log"
                                pesan_log = str(log_entry)
                                sig = None

                            sig_badge_html = ""
                            if sig:
                                sig_badge_html = f"""
                                <br><span class="digital-signature-badge">
                                    🔏 Signed by <b>{sig['signed_by']}</b> ({sig['role']}) | {sig['hash']}
                                </span>
                                """

                            st.markdown(
                                f"""
                                <div class="timeline-card">
                                    <span class="timeline-time">⏱️ {waktu_log}</span>
                                    <p class="timeline-desc">{pesan_log}{sig_badge_html}</p>
                                </div>
                            """,
                                unsafe_allow_html=True,
                            )
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.caption("Belum ada riwayat aktivitas.")

                st.markdown(
                    "<hr style='margin:12px 0;'>", unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_dash2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📈 Distribusi Berkas per Tahapan")

            status_counts = df_opb["status"].value_counts().reset_index()
            status_counts.columns = ["Status Tahapan", "Jumlah OPB"]

            fig = px.bar(
                status_counts,
                x="Jumlah OPB",
                y="Status Tahapan",
                orientation="h",
                color="Jumlah OPB",
                color_continuous_scale="Purples",
                text="Jumlah OPB",
            )

            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                xaxis_title="Jumlah OPB",
                yaxis_title=None,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=11, color="#475569"),
                coloraxis_showscale=False,
            )
            fig.update_traces(
                textposition="outside",
                marker_line_color="rgb(99, 102, 241)",
                marker_line_width=1.5,
                opacity=0.85,
            )

            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info(
            "💡 **Dashboard Masih Kosong:** Belum ada data pengajuan OPB. Silakan login sebagai **Engineering** untuk membuat OPB baru."
        )

    st.markdown("---")

    # ==================== TARGET ANCHOR LOKASI KELOLA ====================
    st.markdown('<div id="anchor-kelola-opb"></div>', unsafe_allow_html=True)

    # ==================== MODUL USER PANELS ====================

    # 1. ROLE ENGINEERING
    if role == "Engineering":
        st.header("🔧 Panel Kerja Engineering")

        focus_id = st.session_state.get("target_focus_id")
        has_pending_eng_verif = any(
            x["id"] == focus_id
            for x in st.session_state["db_opb"]
            if x["status"] == "7. Verifikasi Penerimaan Barang (Engineering)"
        )

        tab1, tab2 = st.tabs(
            [
                "📝 Buat Form OPB Baru",
                "📦 Verifikasi & Tanda Tangan Penerimaan Barang (BAST)",
            ]
        )

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("Pengajuan OPB Baru")

            with st.form(key="form_opb_engineering", clear_on_submit=True):
                nomor_opb = st.text_input(
                    "Nomor OPB ",
                    f"OPB/{datetime.now().strftime('%Y%m%d/%H%M')}",
                )
                nama_barang = st.text_input(
                    "Nama Barang / Jenis Pekerjaan",
                    placeholder="Contoh: Lampu LED Tube 18W",
                )
                jumlah = st.number_input(
                    "Jumlah / Kuantitas Unit", min_value=1, value=1
                )
                keterangan = st.text_area(
                    "Alasan Kebutuhan & Spesifikasi Detail",
                    placeholder="Tuliskan alasan kebutuhan dan spesifikasi...",
                )
                file_opb = st.file_uploader(
                    "Unggah Dokumen Lampiran BA (PDF/Word/Excel)",
                    type=["pdf", "docx", "xlsx"],
                )

                submit = st.form_submit_button(
                    "🚀 Submit & Kirim OPB ke Purchasing",
                    type="primary",
                    use_container_width=True,
                )

            if submit:
                if nama_barang and file_opb:
                    with st.spinner("Menyimpan berkas ke Supabase..."):
                        file_bytes = file_opb.getvalue()
                        file_name = file_opb.name

                        file_url = upload_file_to_supabase(
                            file_bytes, file_name, folder="opb"
                        )

                        sig_eng = generate_digital_signature(
                            "Engineering", user_info["name"], nomor_opb
                        )
                        data_baru = {
                            "nomor_opb": nomor_opb,
                            "nama_barang": nama_barang,
                            "jumlah": jumlah,
                            "keterangan": keterangan,
                            "file_opb_url": file_url,
                            "file_opb_name": file_name,
                            "harga_estimasi": 0,
                            "vendor": "-",
                            "file_iom_url": None,
                            "file_iom_name": "-",
                            "file_bast_url": None,
                            "file_bast_name": "-",
                            "catatan_bm": "-",
                            "catatan_finance": "-",
                            "catatan_p3srs": "-",
                            "status": "1. Penawaran Purchasing",
                            "timeline": [],
                        }
                        catat_log(
                            data_baru,
                            f"OPB Dibuat & Diajukan oleh {user_info['name']} ke Purchasing",
                            digital_sig=sig_eng,
                        )

                        save_database(data_baru, is_new=True)

                        st.toast(
                            "🚀 OPB Berhasil diteruskan ke Purchasing!",
                            icon="✅",
                        )
                        st.rerun()
                else:
                    st.warning(
                        "Mohon lengkapi Nama Barang dan Unggah Berkas OPB."
                    )
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader(
                "📦 Serah Terima Barang Masuk dari Purchasing (Penerimaan)"
            )
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"]
                == "7. Verifikasi Penerimaan Barang (Engineering)"
            ]
            if not items:
                st.info("Tidak ada barang yang menunggu verifikasi penerimaan.")
            for item in items:
                is_expanded = (
                    st.session_state["target_focus_id"] == item["id"]
                )
                with st.expander(
                    f"📦 {item['nomor_opb']} - {item['nama_barang']}",
                    expanded=is_expanded,
                ):
                    st.write(f"**Jumlah:** {item['jumlah']}")
                    st.write(f"**Vendor:** {item['vendor']}")
                    st.markdown("📂 **Tinjau Berkas & BAST dari Purchasing:**")
                    render_download_buttons(item, key_prefix="eng_tab2")
                    st.markdown("<br>", unsafe_allow_html=True)

                    st.markdown("##### ✍️ Pad Tanda Tangan Digital Penerima")
                    render_signature_pad(f"eng_rcv_{item['id']}")

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(
                        f"✅ Konfirmasi & Tanda Tangan Penerimaan BAST #{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        sig_rcv = generate_digital_signature(
                            "Engineering (Penerima)",
                            user_info["name"],
                            item["nomor_opb"],
                        )
                        item["status"] = "8. Selesai"
                        catat_log(
                            item,
                            f"Barang telah diverifikasi fisik dan diterima oleh {user_info['name']} (Engineering). BAST Ditandatangani.",
                            digital_sig=sig_rcv,
                        )

                        save_database(item, is_new=False)

                        st.session_state["target_focus_id"] = None
                        st.toast(
                            "✅ Berita Acara Serah Terima Selesai!", icon="🎉"
                        )
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. ROLE PURCHASING
    elif role == "Purchasing":
        st.header("🛒 Panel Kerja Purchasing")
        tab1, tab2, tab3 = st.tabs(
            [
                "1. Input Penawaran Harga",
                "2. Buat & Unggah IOM",
                "3. Serah Terima Barang ke Engineering",
            ]
        )

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("OPB Masuk (Perlu Penawaran & Harga Vendor)")
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"] in ["1. Penawaran Purchasing", "Revisi BM (OPB)"]
            ]
            if not items:
                st.info("Tidak ada tugas penawaran barang saat ini.")
            for item in items:
                is_expanded = (
                    st.session_state["target_focus_id"] == item["id"]
                )
                with st.expander(
                    f"📌 {item['nomor_opb']} - {item['nama_barang']}",
                    expanded=is_expanded,
                ):
                    st.write(f"**Spesifikasi/Kebutuhan:** {item['keterangan']}")
                    st.markdown("📄 **Tinjau Dokumen OPB dari Engineering:**")
                    render_download_buttons(item, key_prefix="pur_tab1")

                    if item["catatan_bm"] != "-":
                        st.error(f"Catatan Revisi BM: {item['catatan_bm']}")

                    st.divider()
                    vendor = st.text_input(
                        "Nama Vendor/Pemasok Pilihan",
                        value=item["vendor"],
                        key=f"v_{item['id']}",
                    )
                    harga = st.number_input(
                        "Estimasi Total Harga (Rp)",
                        min_value=0,
                        value=int(item["harga_estimasi"]),
                        key=f"h_{item['id']}",
                    )

                    if st.button(
                        "Kirim ke BM untuk Review",
                        key=f"btn_p1_{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        sig_pur = generate_digital_signature(
                            "Purchasing", user_info["name"], item["nomor_opb"]
                        )
                        item["vendor"] = vendor
                        item["harga_estimasi"] = harga
                        item["status"] = "2. Review BM"
                        catat_log(
                            item,
                            f"Purchasing menentukan vendor ({vendor}) & estimasi harga (Rp {harga:,}). Dikirim ke BM.",
                            digital_sig=sig_pur,
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast("📩 Berhasil dikirim ke BM!", icon="✅")
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("OPB Disetujui BM -> Buat & Upload IOM")
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"]
                in [
                    "3. Pembuatan IOM (Purchasing)",
                    "Revisi Finance",
                    "Revisi BM/P3SRS (IOM)",
                ]
            ]
            if not items:
                st.info("Tidak ada IOM yang perlu dibuat/direvisi.")
            for item in items:
                is_expanded = (
                    st.session_state["target_focus_id"] == item["id"]
                )
                with st.expander(
                    f"📑 {item['nomor_opb']} - {item['nama_barang']}",
                    expanded=is_expanded,
                ):
                    st.write(
                        f"**Vendor Pilihan:** {item['vendor']} | **Estimasi Harga:** Rp {item['harga_estimasi']:,}"
                    )
                    st.markdown("📄 **Lihat Berkas Terkait:**")
                    render_download_buttons(item, key_prefix="pur_tab2")

                    st.divider()
                    file_iom = st.file_uploader(
                        "Unggah Draft Dokumen IOM",
                        type=["pdf", "docx"],
                        key=f"fiom_{item['id']}",
                    )
                    if st.button(
                        "Kirim Berkas IOM ke Finance",
                        key=f"btn_p2_{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if file_iom:
                            iom_bytes = file_iom.getvalue()
                            iom_name = file_iom.name
                            iom_url = upload_file_to_supabase(
                                iom_bytes, iom_name, folder="iom"
                            )

                            sig_pur_iom = generate_digital_signature(
                                "Purchasing (IOM Draft)",
                                user_info["name"],
                                item["nomor_opb"],
                            )
                            item["file_iom_url"] = iom_url
                            item["file_iom_name"] = iom_name
                            item["status"] = "4. Review Finance"
                            catat_log(
                                item,
                                "Purchasing mengunggah draft IOM dan meneruskan ke Finance.",
                                digital_sig=sig_pur_iom,
                            )

                            save_database(item, is_new=False)
                            st.session_state["target_focus_id"] = None
                            st.toast(
                                "📩 Draft IOM Dikirim ke Finance!", icon="✅"
                            )
                            st.rerun()
                        else:
                            st.warning(
                                "Silakan unggah file IOM terlebih dahulu."
                            )
            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("🤝 Serah Terima Barang & Upload BAST ke Engineering")
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"]
                in [
                    "6. Pembelian Barang (Purchasing)",
                    "6. Serah Terima Barang (Purchasing -> Engineering)",
                ]
            ]
            if not items:
                st.info("Belum ada barang yang perlu diserahterimakan.")
            for item in items:
                is_expanded = (
                    st.session_state["target_focus_id"] == item["id"]
                )
                with st.expander(
                    f"💳 {item['nomor_opb']} - {item['nama_barang']}",
                    expanded=is_expanded,
                ):
                    st.write(
                        f"**Vendor:** {item['vendor']} | **Budget Approved:** Rp {item['harga_estimasi']:,}"
                    )
                    st.markdown("📂 **Unduh Lampiran Lengkap:**")
                    render_download_buttons(item, key_prefix="pur_tab3")

                    st.divider()
                    st.markdown(
                        "##### 📄 Upload Dokumen BAST / Foto Fisik Serah Terima Barang"
                    )
                    file_bast = st.file_uploader(
                        "Unggah Berita Acara Serah Terima (BAST)",
                        type=["pdf", "jpg", "png"],
                        key=f"bast_file_{item['id']}",
                    )

                    st.markdown(
                        "##### ✍️ Pad Tanda Tangan Penyerah (Purchasing)"
                    )
                    render_signature_pad(f"pur_bast_{item['id']}")

                    if st.button(
                        "🚚 Serahkan Barang & BAST ke Engineering",
                        key=f"btn_p3_{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if file_bast:
                            bast_bytes = file_bast.getvalue()
                            bast_name = file_bast.name
                            bast_url = upload_file_to_supabase(
                                bast_bytes, bast_name, folder="bast"
                            )
                            item["file_bast_url"] = bast_url
                            item["file_bast_name"] = bast_name

                        sig_handover = generate_digital_signature(
                            "Purchasing (Penyerah)",
                            user_info["name"],
                            item["nomor_opb"],
                        )
                        item[
                            "status"
                        ] = "7. Verifikasi Penerimaan Barang (Engineering)"
                        catat_log(
                            item,
                            f"Purchasing ({user_info['name']}) telah menyerahkan fisik barang & BAST ke Engineering.",
                            digital_sig=sig_handover,
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast(
                            "📦 Barang & BAST berhasil diserahkan ke Engineering!",
                            icon="🚚",
                        )
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 3. ROLE BUILDING MANAGER
    elif role == "BM (Building Manager)":
        st.header("👔 Panel Building Manager (BM)")
        tab1, tab2 = st.tabs(
            ["Review OPB (Awal)", "Approval Final IOM (Bersama P3SRS)"]
        )

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"] == "2. Review BM"
            ]
            if not items:
                st.info("Tidak ada OPB baru menunggu persetujuan.")
            for item in items:
                is_expanded = (
                    st.session_state["target_focus_id"] == item["id"]
                )
                with st.expander(
                    f"🧐 Review OPB: {item['nomor_opb']} - {item['nama_barang']}",
                    expanded=is_expanded,
                ):
                    st.write(f"**Vendor:** {item['vendor']}")
                    st.write(
                        f"**Estimasi Harga:** Rp {item['harga_estimasi']:,}"
                    )
                    st.markdown("📂 **Tinjau Dokumen OPB dari Engineering:**")
                    render_download_buttons(item, key_prefix="bm_tab1")

                    st.divider()
                    st.markdown("##### ✍️ Pad Tanda Tangan Digital BM")
                    render_signature_pad(f"bm1_sig_{item['id']}")

                    catatan = st.text_input(
                        "Catatan / Alasan jika Minta Revisi",
                        key=f"c_bm1_{item['id']}",
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "✅ Setujui & Tanda Tangan OPB",
                            key=f"app_bm1_{item['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            sig_bm = generate_digital_signature(
                                "Building Manager",
                                user_info["name"],
                                item["nomor_opb"],
                            )
                            item["status"] = "3. Pembuatan IOM (Purchasing)"
                            catat_log(
                                item,
                                "BM menyetujui OPB. Meneruskan ke Purchasing untuk buat IOM.",
                                digital_sig=sig_bm,
                            )

                            save_database(item, is_new=False)
                            st.session_state["target_focus_id"] = None
                            st.toast("✅ OPB Disetujui!", icon="👍")
                            st.rerun()
                    with col2:
                        if st.button(
                            "❌ Tolak / Minta Revisi",
                            key=f"rej_bm1_{item['id']}",
                            use_container_width=True,
                        ):
                            item["catatan_bm"] = catatan
                            item["status"] = "Revisi BM (OPB)"
                            catat_log(
                                item, f"BM meminta revisi OPB: {catatan}"
                            )

                            save_database(item, is_new=False)
                            st.session_state["target_focus_id"] = None
                            st.toast(
                                "⚠️ Diminta Revisi ke Purchasing", icon="🔄"
                            )
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"] == "5. Approval Akhir (BM & P3SRS)"
            ]
            if not items:
                st.info("Tidak ada IOM menunggu persetujuan final.")
            for item in items:
                is_expanded = (
                    st.session_state["target_focus_id"] == item["id"]
                )
                with st.expander(
                    f"📑 Approval IOM: {item['nomor_opb']} - {item['nama_barang']}",
                    expanded=is_expanded,
                ):
                    st.write(
                        f"**Vendor:** {item['vendor']} | **Total Budget:** Rp {item['harga_estimasi']:,}"
                    )
                    st.markdown("📂 **Tinjau Dokumen OPB & IOM:**")
                    render_download_buttons(item, key_prefix="bm_tab2")

                    st.divider()
                    st.markdown("##### ✍️ Pad Tanda Tangan Digital BM")
                    render_signature_pad(f"bm2_sig_{item['id']}")

                    if st.button(
                        "✅ Approve & Tanda Tangan IOM Final (BM)",
                        key=f"app_bm2_{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        sig_bm_iom = generate_digital_signature(
                            "Building Manager (IOM Final)",
                            user_info["name"],
                            item["nomor_opb"],
                        )
                        catat_log(
                            item,
                            "BM menyetujui IOM Final.",
                            digital_sig=sig_bm_iom,
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast("✅ Persetujuan BM dicatat!", icon="👍")
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 4. ROLE FINANCE
    elif role == "Finance":
        st.header("💰 Panel Finance & Budgeting")
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        items = [
            x
            for x in st.session_state["db_opb"]
            if x["status"] == "4. Review Finance"
        ]
        if not items:
            st.info(
                "Tidak ada IOM yang membutuhkan verifikasi Finance saat ini."
            )
        for item in items:
            is_expanded = st.session_state["target_focus_id"] == item["id"]
            with st.expander(
                f"💵 Review IOM: {item['nomor_opb']} - {item['nama_barang']}",
                expanded=is_expanded,
            ):
                st.write(f"**Vendor:** {item['vendor']}")
                st.write(f"**Pengajuan Dana:** Rp {item['harga_estimasi']:,}")
                st.markdown(
                    "📂 **Tinjau Lampiran OPB dari Engineering & IOM:**"
                )
                render_download_buttons(item, key_prefix="fin_panel")

                st.divider()
                st.markdown("##### ✍️ Pad Tanda Tangan Digital Finance")
                render_signature_pad(f"fin_sig_{item['id']}")

                catatan = st.text_input(
                    "Catatan Verifikasi Anggaran", key=f"c_fin_{item['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ Verifikasi Budget & Tanda Tangan",
                        key=f"app_fin_{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        sig_fin = generate_digital_signature(
                            "Finance Officer",
                            user_info["name"],
                            item["nomor_opb"],
                        )
                        item["status"] = "5. Approval Akhir (BM & P3SRS)"
                        catat_log(
                            item,
                            "Finance memverifikasi ketersediaan budget IOM.",
                            digital_sig=sig_fin,
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast("💰 Budget Disetujui!", icon="✅")
                        st.rerun()
                with col2:
                    if st.button(
                        "❌ Minta Revisi Budget",
                        key=f"rej_fin_{item['id']}",
                        use_container_width=True,
                    ):
                        item["catatan_finance"] = catatan
                        item["status"] = "Revisi Finance"
                        catat_log(
                            item, f"Finance meminta revisi budget: {catatan}"
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast("⚠️ Permintaan Revisi dikirim!", icon="🔄")
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. ROLE P3SRS
    elif role == "P3SRS":
        st.header("🏛️ Panel P3SRS (Approval Akhir)")
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        items = [
            x
            for x in st.session_state["db_opb"]
            if x["status"] == "5. Approval Akhir (BM & P3SRS)"
        ]
        if not items:
            st.info("Tidak ada IOM yang menunggu persetujuan P3SRS.")
        for item in items:
            is_expanded = st.session_state["target_focus_id"] == item["id"]
            with st.expander(
                f"⚖️ Persetujuan Final: {item['nomor_opb']} - {item['nama_barang']}",
                expanded=is_expanded,
            ):
                st.write(f"**Vendor:** {item['vendor']}")
                st.write(f"**Total Anggaran:** Rp {item['harga_estimasi']:,}")
                st.markdown(
                    "📂 **Tinjau Dokumen OPB dari Engineering & IOM:**"
                )
                render_download_buttons(item, key_prefix="p3srs_panel")

                st.divider()
                st.markdown("##### ✍️ Pad Tanda Tangan Digital Pengurus P3SRS")
                render_signature_pad(f"p3srs_sig_{item['id']}")

                catatan = st.text_input(
                    "Catatan Persetujuan", key=f"c_p3srs_{item['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ ACC, Tanda Tangan & Serah Terima",
                        key=f"app_p3srs_{item['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        sig_p3srs = generate_digital_signature(
                            "Pengurus P3SRS",
                            user_info["name"],
                            item["nomor_opb"],
                        )
                        item[
                            "status"
                        ] = "6. Serah Terima Barang (Purchasing -> Engineering)"
                        catat_log(
                            item,
                            "P3SRS menyetujui IOM Final. Memerintahkan Purchasing melakukan pembelian & serah terima ke Engineering.",
                            digital_sig=sig_p3srs,
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast("🎉 IOM Disetujui P3SRS!", icon="✅")
                        st.rerun()
                with col2:
                    if st.button(
                        "❌ Minta Revisi",
                        key=f"rej_p3srs_{item['id']}",
                        use_container_width=True,
                    ):
                        item["catatan_p3srs"] = catatan
                        item["status"] = "Revisi BM/P3SRS (IOM)"
                        catat_log(
                            item,
                            f"P3SRS menolak/meminta revisi IOM: {catatan}",
                        )

                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.toast("⚠️ Revisi Dikirim ke Purchasing!", icon="🔄")
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
