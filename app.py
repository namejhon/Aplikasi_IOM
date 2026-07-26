from datetime import datetime
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
import requests
import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Flow OPB & IOM - P3SRS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. DATABASE LOKAL TERPUSAT (JSON STORAGE UNTUK MULTI-DEVICE SYNC) ---
DB_FILE = "db_opb.json"


def load_db():
    """Membaca data OPB dari file JSON agar tersinkronisasi antar-device."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_db(data):
    """Menyimpan data OPB ke file JSON setiap ada perubahan data/status."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# Sync otomatis session_state dari database JSON setiap kali halaman di-refresh/interaksi
st.session_state["db_opb"] = load_db()


# --- 3. FUNGSI LOAD LOTTIE ANIMATION ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None


# --- 4. ADVANCED CUSTOM CSS (PREMIUM LUXURY DESIGN & ELEGAN TIMELINE) ---
st.markdown(
    """
    <style>
    /* Global App Background */
    .stApp {
        background: #f8fafc;
    }
    
    /* Header Utama Gradient */
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 28px 35px;
        border-radius: 18px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
    }
    .main-header h1 {
        color: #ffffff !important;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        font-size: 30px;
    }
    .main-header p {
        color: #c7d2fe;
        margin-top: 6px;
        margin-bottom: 0;
        font-size: 14px;
    }
    
    /* Custom Designed Metric Cards */
    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 25px -5px rgba(0, 0, 0, 0.08);
    }
    .kpi-blue { border-top: 4px solid #3b82f6; }
    .kpi-amber { border-top: 4px solid #f59e0b; }
    .kpi-emerald { border-top: 4px solid #10b981; }
    .kpi-purple { border-top: 4px solid #8b5cf6; }
    
    .kpi-title {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .kpi-value {
        color: #0f172a;
        font-size: 28px;
        font-weight: 800;
        margin-top: 6px;
    }
    .kpi-sub {
        font-size: 12px;
        font-weight: 600;
        margin-top: 4px;
    }
    
    /* User Profile Card SideBar */
    .user-profile-card {
        background: white;
        padding: 16px 20px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 15px;
    }
    .role-badge {
        background: #e0e7ff;
        color: #3730a3;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        display: inline-block;
        margin-top: 5px;
    }
    
    /* Notification Alert Box Interaktif */
    .notif-box {
        background: linear-gradient(135deg, #fffbe3 0%, #fef3c7 100%);
        border-left: 5px solid #f59e0b;
        color: #78350f;
        padding: 18px 22px;
        border-radius: 16px;
        margin-bottom: 22px;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.12);
    }
    
    /* Main Content Card Container */
    .content-box {
        background: white;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 15px -3px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    
    /* ================= ELEGAN TIMELINE DESIGN ================= */
    .timeline-container {
        position: relative;
        padding-left: 20px;
        margin: 15px 0 10px 10px;
        border-left: 2px dashed #cbd5e1;
    }
    
    .timeline-card {
        position: relative;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        transition: all 0.2s ease;
    }
    
    .timeline-card:hover {
        background: #ffffff;
        border-color: #cbd5e1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .timeline-card::before {
        content: '';
        position: absolute;
        left: -28px;
        top: 16px;
        width: 13px;
        height: 13px;
        border-radius: 50%;
        background-color: #6366f1;
        border: 3px solid #ffffff;
        box-shadow: 0 0 0 2px #6366f1;
    }
    
    .timeline-time {
        display: inline-block;
        background: #e0e7ff;
        color: #3730a3;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
        margin-bottom: 6px;
    }
    
    .timeline-desc {
        color: #1e293b;
        font-size: 13px;
        font-weight: 500;
        line-height: 1.4;
        margin: 0;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 5. DATABASE USER & PASSWORD (MULTI-ROLE) ---
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


# --- 6. FUNGSI SIMPAN FILE LOKAL & CATAT LOG ---
def upload_to_google_drive(file_name, file_bytes, mime_type, folder_id):
    try:
        upload_dir = os.path.join(os.getcwd(), "uploads")
        clean_file_name = file_name.replace("/", "_").replace("\\", "_")
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, clean_file_name)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return file_path
    except Exception as e:
        st.error(f"❌ Gagal menyimpan file: {e}")
        return None


def catat_log(item, pesan):
    wib = pytz.timezone("Asia/Jakarta")
    waktu_sekarang = datetime.now(wib).strftime("%d/%m/%Y %H:%M:%S")
    item["timeline"].append({"waktu": waktu_sekarang, "pesan": pesan})


# --- 7. FUNGSI CEK NOTIFIKASI PER DIVISI ---
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
                "6. Pembelian Barang (Purchasing)",
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
            x for x in db if x["status"] == "7. Penerimaan Barang (Engineering)"
        ]

    return pending_items


# --- 8. INITIALIZATION SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

if "notif_shown" not in st.session_state:
    st.session_state["notif_shown"] = False

if "target_focus_id" not in st.session_state:
    st.session_state["target_focus_id"] = None

# ==================== HALAMAN LOGIN INTERAKTIF ====================
if not st.session_state["logged_in"]:
    col_l1, col_l2, col_l3 = st.columns([1.2, 1.6, 1.2])

    with col_l2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: -20px;">
                <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
                <lottie-player src="https://assets2.lottiefiles.com/packages/lf20_mbe44xec.json" background="transparent" speed="1" style="width: 280px; height: 220px; margin: 0 auto;" loop autoplay></lottie-player>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2 style='color: #1e1b4b; font-weight: 800; margin: 0; font-size: 28px;'>Portal OPB & IOM - P3SRS</h2>
                <p style='color: #64748b; font-size: 14px; margin-top: 5px;'>Sistem Management Permintaan Barang Inter-Divisi P3SRS</p>
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
                "Password",
                type="password",
                placeholder="Masukkan password...",
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
                    st.toast("✅ Login Berhasil!", icon="🎉")
                    st.rerun()
                else:
                    st.error("❌ Username atau Password tidak sesuai!")

        with st.expander("ℹ️ Daftar Akun Login Skenario"):
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

    # --- POP-UP NOTIFIKASI TOAST ---
    pending_tasks = cek_notifikasi_user(role)
    if pending_tasks and not st.session_state["notif_shown"]:
        st.toast(
            f"🔔 **Pemberitahuan:** Ada {len(pending_tasks)} tugas baru menunggu tindakan Anda!",
            icon="📩",
        )
        st.session_state["notif_shown"] = True

    # --- SIDEBAR USER PROFILE ---
    st.sidebar.markdown(
        f"""
        <div class="user-profile-card">
            <h4 style="margin:0; color:#0f172a; font-size:15px; font-weight:700;">👤 {user_info['name']}</h4>
            <span class="role-badge">{user_info['role']}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if pending_tasks:
        st.sidebar.warning(f"🔔 **{len(pending_tasks)} Tugas Menunggu**")

    # Tombol Refresh Data Manual
    if st.sidebar.button("🔄 Refresh Data (Sync)", use_container_width=True):
        st.session_state["db_opb"] = load_db()
        st.toast("🔄 Data berhasil disinkronkan!", icon="⚡")
        st.rerun()

    if st.sidebar.button("🚪 Keluar / Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_info"] = None
        st.session_state["notif_shown"] = False
        st.session_state["target_focus_id"] = None
        st.rerun()

    st.sidebar.markdown("---")

    # --- HEADER BANNER ---
    st.markdown(
        f"""
        <div class="main-header">
            <h1>📋 Sistem Pengajuan OPB & IOM - P3SRS</h1>
            <p>Platform Integrasi Workflow Order Permintaan Barang & Inter-Office Memo | Hak Akses: <b>{role}</b></p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # ================= BANNER NOTIFIKASI INTERAKTIF =================
    if pending_tasks:
        st.markdown(
            f"""
            <div class="notif-box">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size:24px;">🔔</span>
                    <span style="font-size: 16px; font-weight: 700;">Notifikasi Tugas Masuk ({len(pending_tasks)} Berkas)</span>
                </div>
                <div style="font-size: 13px; margin-bottom: 12px; opacity: 0.9;">
                    Klik tombol di bawah ini untuk langsung menuju dan membuka berkas pekerjaan terkait:
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
                    st.toast(
                        f"🎯 Menuju berkas {item_task['nomor_opb']}", icon="⚡"
                    )
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    # ================= EXECUTIVE DASHBOARD =================
    st.markdown("### 📊 Dashboard Monitoring & Analisis P3SRS")

    TAHAPAN_OPB = [
        "1. Penawaran Purchasing",
        "2. Review BM",
        "3. Pembuatan IOM (Purchasing)",
        "4. Review Finance",
        "5. Approval Akhir (BM & P3SRS)",
        "6. Pembelian Barang (Purchasing)",
        "7. Penerimaan Barang (Engineering)",
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
                    <div class="kpi-value">{total_opb} <span style="font-size:15px; color:#64748b;">OPB</span></div>
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
                    <div class="kpi-value" style="color:#d97706;">{total_proses} <span style="font-size:15px; color:#64748b;">OPB</span></div>
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
                    <div class="kpi-value" style="color:#059669;">{total_selesai} <span style="font-size:15px; color:#64748b;">OPB</span></div>
                    <div class="kpi-sub" style="color:#059669;">✅ Barang Diterima</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        with m4:
            st.markdown(
                f"""
                <div class="kpi-card kpi-purple">
                    <div class="kpi-title">Total Estimasi Budget</div>
                    <div class="kpi-value" style="color:#7c3aed; font-size:22px;">Rp {total_anggaran:,.0f}</div>
                    <div class="kpi-sub" style="color:#7c3aed;">💰 Akumulasi Anggaran</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_dash1, col_dash2 = st.columns([1.3, 1])

        # PROGRESS WORKFLOW & TIMELINE DISPLAY
        with col_dash1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📌 Progress Live Status & Timeline Berkas")
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
                    st.caption(f"**{prog_pct}%** ({status_badge})")
                st.caption(
                    f"📍 Status: `{status_curr}` | 💰 Est: Rp {item['harga_estimasi']:,}"
                )

                with st.expander(
                    f"📜 Timeline & Jejak Berkas ({len(item['timeline'])} Aktivitas)"
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
                            else:
                                waktu_log = "Log"
                                pesan_log = str(log_entry)

                            st.markdown(
                                f"""
                                <div class="timeline-card">
                                    <span class="timeline-time">⏱️ {waktu_log}</span>
                                    <p class="timeline-desc">{pesan_log}</p>
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
                font=dict(
                    family="Inter, sans-serif", size=12, color="#475569"
                ),
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

    # ==================== MODUL USER PANELS ====================

    # 1. ROLE ENGINEERING
    if role == "Engineering":
        st.header("🔧 Panel Kerja Engineering")
        tab1, tab2 = st.tabs(
            ["📝 Buat Form OPB Baru", "📦 Konfirmasi Penerimaan Barang"]
        )

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("Pengajuan OPB Baru")

            with st.form(key="form_opb_engineering", clear_on_submit=True):
                nomor_opb = st.text_input(
                    "Nomor OPB P3SRS",
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
                    "Unggah Dokumen Lampiran OPB (PDF/Word/Excel)",
                    type=["pdf", "docx", "xlsx"],
                )

                submit = st.form_submit_button(
                    "🚀 Submit & Kirim OPB ke Purchasing",
                    type="primary",
                    use_container_width=True,
                )

            if submit:
                if nama_barang and file_opb:
                    with st.spinner("Menyimpan berkas..."):
                        link = upload_to_google_drive(
                            f"{nomor_opb}_{file_opb.name}",
                            file_opb.getvalue(),
                            file_opb.type,
                            "Engineering",
                        )
                        if link:
                            data_baru = {
                                "id": len(st.session_state["db_opb"]) + 1,
                                "nomor_opb": nomor_opb,
                                "nama_barang": nama_barang,
                                "jumlah": jumlah,
                                "keterangan": keterangan,
                                "link_opb": link,
                                "harga_estimasi": 0,
                                "vendor": "-",
                                "link_iom": "-",
                                "catatan_bm": "-",
                                "catatan_finance": "-",
                                "catatan_p3srs": "-",
                                "status": "1. Penawaran Purchasing",
                                "timeline": [],
                            }
                            catat_log(
                                data_baru,
                                "OPB Dibuat & Diajukan oleh Engineering ke Purchasing",
                            )
                            st.session_state["db_opb"].append(data_baru)
                            save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
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
            st.subheader("Barang Siap Diterima di Lapangan")
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"] == "7. Penerimaan Barang (Engineering)"
            ]
            if not items:
                st.info(
                    "Tidak ada barang yang menunggu verifikasi penerimaan."
                )
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
                    st.write(f"**Lokasi File:** `{item['link_opb']}`")
                    if st.button(
                        f"✅ Konfirmasi Barang Sudah Diterima #{item['id']}",
                        type="primary",
                    ):
                        item["status"] = "8. Selesai"
                        catat_log(
                            item,
                            "Barang telah diterima oleh Engineering. Workflow SELESAI.",
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
                        st.session_state["target_focus_id"] = None
                        st.toast(
                            "✅ Barang Diterima! Status OPB Selesai.", icon="🎉"
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
                "3. Eksekusi Pembelian",
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
                    st.write(f"**Berkas OPB:** `{item['link_opb']}`")
                    if item["catatan_bm"] != "-":
                        st.error(f"Catatan Revisi BM: {item['catatan_bm']}")

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
                    ):
                        item["vendor"] = vendor
                        item["harga_estimasi"] = harga
                        item["status"] = "2. Review BM"
                        catat_log(
                            item,
                            f"Purchasing menentukan vendor ({vendor}) & estimasi harga (Rp {harga:,}). Dikirim ke BM.",
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
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
                    file_iom = st.file_uploader(
                        "Unggah Draft Dokumen IOM",
                        type=["pdf", "docx"],
                        key=f"fiom_{item['id']}",
                    )
                    if st.button(
                        "Kirim Berkas IOM ke Finance",
                        key=f"btn_p2_{item['id']}",
                        type="primary",
                    ):
                        if file_iom:
                            link = upload_to_google_drive(
                                f"IOM_{item['nomor_opb']}_{file_iom.name}",
                                file_iom.getvalue(),
                                file_iom.type,
                                "Purchasing",
                            )
                            item["link_iom"] = link
                            item["status"] = "4. Review Finance"
                            catat_log(
                                item,
                                "Purchasing mengunggah draft IOM dan meneruskan ke Finance.",
                            )
                            save_db(
                                st.session_state["db_opb"]
                            )  # SIMPAN KE JSON
                            st.session_state["target_focus_id"] = None
                            st.toast(
                                "📩 Draft IOM Dikirim ke Finance!", icon="✅"
                            )
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("IOM Fully Approved -> Eksekusi Pembelian")
            items = [
                x
                for x in st.session_state["db_opb"]
                if x["status"] == "6. Pembelian Barang (Purchasing)"
            ]
            if not items:
                st.info("Belum ada barang yang perlu dibeli saat ini.")
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
                    st.write(f"**Path Dokumen IOM:** `{item['link_iom']}`")
                    if st.button(
                        "Barang Sudah Dibelikan (Kirim ke Engineering)",
                        key=f"btn_p3_{item['id']}",
                        type="primary",
                    ):
                        item["status"] = "7. Penerimaan Barang (Engineering)"
                        catat_log(
                            item,
                            "Purchasing melakukan eksekusi pembelian barang.",
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
                        st.session_state["target_focus_id"] = None
                        st.toast(
                            "📦 Barang dibeli & dikirim ke Engineering!",
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
                    st.write(f"**Path Berkas OPB:** `{item['link_opb']}`")
                    catatan = st.text_input(
                        "Catatan / Alasan jika Minta Revisi",
                        key=f"c_bm1_{item['id']}",
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "✅ Setujui OPB",
                            key=f"app_bm1_{item['id']}",
                            type="primary",
                        ):
                            item["status"] = "3. Pembuatan IOM (Purchasing)"
                            catat_log(
                                item,
                                "BM menyetujui OPB. Meneruskan ke Purchasing untuk buat IOM.",
                            )
                            save_db(
                                st.session_state["db_opb"]
                            )  # SIMPAN KE JSON
                            st.session_state["target_focus_id"] = None
                            st.toast("✅ OPB Disetujui!", icon="👍")
                            st.rerun()
                    with col2:
                        if st.button(
                            "❌ Tolak / Minta Revisi", key=f"rej_bm1_{item['id']}"
                        ):
                            item["catatan_bm"] = catatan
                            item["status"] = "Revisi BM (OPB)"
                            catat_log(
                                item, f"BM meminta revisi OPB: {catatan}"
                            )
                            save_db(
                                st.session_state["db_opb"]
                            )  # SIMPAN KE JSON
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
                    st.write(f"**Path Berkas IOM:** `{item['link_iom']}`")
                    if st.button(
                        "✅ Approve IOM (BM)",
                        key=f"app_bm2_{item['id']}",
                        type="primary",
                    ):
                        catat_log(item, "BM menyetujui IOM Final.")
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
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
                st.write(f"**Path Berkas IOM:** `{item['link_iom']}`")
                catatan = st.text_input(
                    "Catatan Verifikasi Anggaran", key=f"c_fin_{item['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ Verifikasi Budget OK",
                        key=f"app_fin_{item['id']}",
                        type="primary",
                    ):
                        item["status"] = "5. Approval Akhir (BM & P3SRS)"
                        catat_log(
                            item,
                            "Finance memverifikasi ketersediaan budget IOM.",
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
                        st.session_state["target_focus_id"] = None
                        st.toast("💰 Budget Disetujui!", icon="✅")
                        st.rerun()
                with col2:
                    if st.button(
                        "❌ Minta Revisi Budget", key=f"rej_fin_{item['id']}"
                    ):
                        item["catatan_finance"] = catatan
                        item["status"] = "Revisi Finance"
                        catat_log(
                            item, f"Finance meminta revisi budget: {catatan}"
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
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
                st.write(
                    f"**Total Anggaran:** Rp {item['harga_estimasi']:,}"
                )
                st.write(f"**Path Berkas IOM:** `{item['link_iom']}`")
                catatan = st.text_input(
                    "Catatan Persetujuan", key=f"c_p3srs_{item['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ ACC & Instruksikan Pembelian",
                        key=f"app_p3srs_{item['id']}",
                        type="primary",
                    ):
                        item["status"] = "6. Pembelian Barang (Purchasing)"
                        catat_log(
                            item,
                            "P3SRS menyetujui IOM Final. Memerintahkan Purchasing melakukan pembelian.",
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
                        st.session_state["target_focus_id"] = None
                        st.toast("🎉 IOM Disetujui P3SRS!", icon="✅")
                        st.rerun()
                with col2:
                    if st.button(
                        "❌ Minta Revisi", key=f"rej_p3srs_{item['id']}"
                    ):
                        item["catatan_p3srs"] = catatan
                        item["status"] = "Revisi BM/P3SRS (IOM)"
                        catat_log(
                            item,
                            f"P3SRS menolak/meminta revisi IOM: {catatan}",
                        )
                        save_db(st.session_state["db_opb"])  # SIMPAN KE JSON
                        st.session_state["target_focus_id"] = None
                        st.toast(
                            "⚠️ Revisi Dikirim ke Purchasing!", icon="🔄"
                        )
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
