from datetime import datetime
import json
import os
import pandas as pd
import plotly.express as px
import pytz
import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Flow OPB & IOM - P3SRS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. DATABASE LOKAL TERPUSAT (JSON STORAGE) ---
DB_FILE = "db_opb.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if "db_opb" not in st.session_state:
    st.session_state["db_opb"] = load_db()

# --- 3. CUSTOM CSS CLEAN & COMPACT ---
st.markdown(
    """
    <style>
    .stApp { background: #f8fafc; }
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 20px 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 20px;
    }
    .main-header h1 { color: #ffffff !important; font-weight: 800; margin: 0; font-size: 24px; }
    .main-header p { color: #c7d2fe; margin-top: 4px; margin-bottom: 0; font-size: 13px; }
    .kpi-card { background: white; border-radius: 12px; padding: 16px; border: 1px solid #e2e8f0; }
    .kpi-blue { border-top: 4px solid #3b82f6; }
    .kpi-amber { border-top: 4px solid #f59e0b; }
    .kpi-emerald { border-top: 4px solid #10b981; }
    .kpi-purple { border-top: 4px solid #8b5cf6; }
    .kpi-title { color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .kpi-value { color: #0f172a; font-size: 24px; font-weight: 800; margin-top: 4px; }
    .user-profile-card { background: white; padding: 12px 16px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 12px; }
    .role-badge { background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; }
    .content-box { background: white; border-radius: 12px; padding: 18px; border: 1px solid #e2e8f0; margin-bottom: 15px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 4. DATABASE USER ---
USERS = {
    "engineering": {"password": "eng123", "name": "Tim Engineering", "role": "Engineering"},
    "purchasing": {"password": "pur123", "name": "Tim Purchasing", "role": "Purchasing"},
    "bm": {"password": "bm123", "name": "Building Manager", "role": "BM (Building Manager)"},
    "finance": {"password": "fin123", "name": "Tim Finance", "role": "Finance"},
    "p3srs": {"password": "p3srs123", "name": "Pengurus P3SRS", "role": "P3SRS"},
}

# --- 5. HELPER FILE & LOGGING ---
def upload_to_google_drive(file_name, file_bytes, mime_type, folder_id):
    try:
        upload_dir = os.path.join(os.getcwd(), "uploads")
        clean_file_name = file_name.replace("/", "_").replace("\\", "_")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, clean_file_name)
        if os.path.exists(file_path): os.remove(file_path)
        with open(file_path, "wb") as f: f.write(file_bytes)
        return file_path
    except Exception as e:
        st.error(f"❌ Gagal menyimpan file: {e}")
        return None

def delete_physical_file(file_path):
    try:
        if file_path and file_path != "-" and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception: pass
    return False

def catat_log(item, pesan):
    wib = pytz.timezone("Asia/Jakarta")
    waktu_sekarang = datetime.now(wib).strftime("%d/%m/%Y %H:%M:%S")
    item["timeline"].append({"waktu": waktu_sekarang, "pesan": pesan})

# --- 6. HELPER DOWNLOAD & CETAK CLEAN ---
def render_download_link(file_path, label):
    if file_path and file_path != "-" and os.path.exists(file_path):
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            st.download_button(
                label=f"📥 Download {label}",
                data=f.read(),
                file_name=filename,
                key=f"dl_{label}_{filename}_{file_path.replace('/', '_')}",
                use_container_width=True
            )
    else:
        st.caption(f"ℹ️ {label} belum tersedia")

def render_cetak_html(item, role_user):
    if role_user == "Engineering": return
    timeline_html = "".join([f"<li><b>[{t.get('waktu', '')}]</b> {t.get('pesan', '')}</li>" for t in item.get("timeline", [])])
    printable_html = f"""
    <html><head><title>Cetak Resume - {item['nomor_opb']}</title>
    <style>body {{ font-family: sans-serif; padding: 15px; }} .table {{ width:100%; border-collapse:collapse; margin-top:10px; }} .table th, .table td {{ border:1px solid #ccc; padding:8px; text-align:left; }}</style>
    </head><body>
    <button onclick="window.print()" style="padding:8px 15px; background:#2563eb; color:white; border:none; border-radius:4px; cursor:pointer;">🖨️ Cetak / Save to PDF</button>
    <h3 style="margin-top:15px;">P3SRS - RESUME PENGAJUAN OPB & IOM</h3>
    <p>Nomor Dokumen: <b>{item['nomor_opb']}</b></p>
    <table class="table">
        <tr><th>Nama Barang</th><td>{item['nama_barang']}</td></tr>
        <tr><th>Jumlah</th><td>{item['jumlah']}</td></tr>
        <tr><th>Vendor</th><td>{item['vendor']}</td></tr>
        <tr><th>Estimasi Harga</th><td>Rp {item['harga_estimasi']:,}</td></tr>
        <tr><th>Status</th><td><b>{item['status']}</b></td></tr>
    </table>
    <h4>📜 Jejak Audit</h4><ul>{timeline_html}</ul>
    </body></html>
    """
    st.components.v1.html(printable_html, height=280, scrolling=True)

# --- 7. NOTIFIKASI ---
def cek_notifikasi_user(role):
    db = st.session_state["db_opb"]
    if role == "Purchasing": return [x for x in db if x["status"] in ["1. Penawaran Purchasing", "3. Pembuatan IOM (Purchasing)", "6. Pembelian Barang (Purchasing)", "Revisi BM (OPB)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
    elif role == "BM (Building Manager)": return [x for x in db if x["status"] in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
    elif role == "Finance": return [x for x in db if x["status"] == "4. Review Finance"]
    elif role == "P3SRS": return [x for x in db if x["status"] == "5. Approval Akhir (BM & P3SRS)"]
    elif role == "Engineering": return [x for x in db if x["status"] == "7. Penerimaan Barang (Engineering)"]
    return []

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "user_info" not in st.session_state: st.session_state["user_info"] = None

# ==================== LOGIN ====================
if not st.session_state["logged_in"]:
    _, col2, _ = st.columns([1.2, 1.6, 1.2])
    with col2:
        st.markdown("<br><h2 style='text-align:center;'>Portal OPB & IOM - P3SRS</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username_input = st.text_input("Username", placeholder="engineering, purchasing, bm...")
            password_input = st.text_input("Password", type="password")
            if st.form_submit_button("🔒 Masuk", type="primary", use_container_width=True):
                user_data = USERS.get(username_input.lower().strip())
                if user_data and user_data["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user_data
                    st.rerun()
                else: st.error("❌ Login gagal!")

else:
    # ==================== UTAMA ====================
    user_info = st.session_state["user_info"]
    role = user_info["role"]

    st.sidebar.markdown(f"<div class='user-profile-card'><b>👤 {user_info['name']}</b><br><span class='role-badge'>{user_info['role']}</span></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.session_state["db_opb"] = load_db()
        st.rerun()
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

    st.markdown(f"<div class='main-header'><h1>📋 Sistem OPB & IOM P3SRS</h1><p>Akses: <b>{role}</b></p></div>", unsafe_allow_html=True)

    # --- DASHBOARD KPI ---
    total_opb = len(st.session_state["db_opb"])
    if total_opb > 0:
        df_opb = pd.DataFrame(st.session_state["db_opb"])
        total_selesai = len(df_opb[df_opb["status"] == "8. Selesai"])
        total_proses = total_opb - total_selesai
        total_anggaran = df_opb["harga_estimasi"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='kpi-card kpi-blue'><div class='kpi-title'>Total Pengajuan</div><div class='kpi-value'>{total_opb}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='kpi-card kpi-amber'><div class='kpi-title'>Proses</div><div class='kpi-value' style='color:#d97706;'>{total_proses}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='kpi-card kpi-emerald'><div class='kpi-title'>Selesai</div><div class='kpi-value' style='color:#059669;'>{total_selesai}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='kpi-card kpi-purple'><div class='kpi-title'>Total Budget</div><div class='kpi-value' style='color:#7c3aed;'>Rp {total_anggaran:,.0f}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_dash1, col_dash2 = st.columns([1.5, 1])
        with col_dash1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📌 Daftar Berkas & Ringkasan Status")
            
            # --- TAMPILAN BERSIH MENGGUNAKAN EXPANDER COMPACT ---
            for item in st.session_state["db_opb"]:
                header_title = f"{item['nomor_opb']} — {item['nama_barang']}  |  🟡 {item['status']}"
                
                with st.expander(header_title):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Jumlah:** {item['jumlah']} unit")
                        st.write(f"**Vendor:** {item['vendor']}")
                        st.write(f"**Estimasi Harga:** Rp {item['harga_estimasi']:,}")
                    with c2:
                        st.write("**File Lampiran:**")
                        col_f1, col_f2 = st.columns(2)
                        with col_f1: render_download_link(item.get("link_opb"), "OPB")
                        with col_f2: render_download_link(item.get("link_iom"), "IOM")

                    # Cetak Resume HANYA jika expander dibuka dan role BUKAN Engineering
                    if role != "Engineering":
                        st.markdown("---")
                        render_cetak_html(item, role)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_dash2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📈 Distribusi Berkas")
            status_counts = df_opb["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Jumlah"]
            fig = px.bar(status_counts, x="Jumlah", y="Status", orientation="h", color="Jumlah", color_continuous_scale="Blues")
            fig.update_layout(margin=dict(l=5, r=5, t=5, b=5), height=260)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==================== MODUL USER PANELS ====================
    if role == "Engineering":
        st.header("🔧 Panel Engineering")
        tab1, tab2 = st.tabs(["📝 Buat OPB Baru", "📦 Konfirmasi Barang Diterima"])
        with tab1:
            with st.form("form_opb", clear_on_submit=True):
                nomor_opb = st.text_input("Nomor OPB", f"OPB/{datetime.now().strftime('%Y%m%d/%H%M')}")
                nama_barang = st.text_input("Nama Barang")
                jumlah = st.number_input("Jumlah", min_value=1, value=1)
                keterangan = st.text_area("Keterangan")
                file_opb = st.file_uploader("Upload OPB (PDF/Word/Excel)")
                if st.form_submit_button("🚀 Submit", type="primary") and nama_barang and file_opb:
                    link = upload_to_google_drive(f"{nomor_opb}_{file_opb.name}", file_opb.getvalue(), file_opb.type, "Engineering")
                    if link:
                        data_baru = {
                            "id": len(st.session_state["db_opb"]) + 1, "nomor_opb": nomor_opb,
                            "nama_barang": nama_barang, "jumlah": jumlah, "keterangan": keterangan,
                            "link_opb": link, "harga_estimasi": 0, "vendor": "-", "link_iom": "-",
                            "status": "1. Penawaran Purchasing", "timeline": []
                        }
                        catat_log(data_baru, "OPB dibuat oleh Engineering")
                        st.session_state["db_opb"].append(data_baru)
                        save_db(st.session_state["db_opb"])
                        st.rerun()

        with tab2:
            items = [x for x in st.session_state["db_opb"] if x["status"] == "7. Penerimaan Barang (Engineering)"]
            for item in items:
                with st.expander(f"📦 {item['nomor_opb']} - {item['nama_barang']}"):
                    if st.button("✅ Terima Barang", key=f"rec_{item['id']}", type="primary"):
                        item["status"] = "8. Selesai"
                        catat_log(item, "Barang diterima. Selesai.")
                        save_db(st.session_state["db_opb"])
                        st.rerun()

    elif role == "Purchasing":
        st.header("🛒 Panel Purchasing")
        tab1, tab2, tab3 = st.tabs(["1. Penawaran Harga", "2. Upload IOM", "3. Pembelian"])
        with tab1:
            items = [x for x in st.session_state["db_opb"] if x["status"] in ["1. Penawaran Purchasing", "Revisi BM (OPB)"]]
            for item in items:
                with st.expander(f"📌 {item['nomor_opb']} - {item['nama_barang']}"):
                    vendor = st.text_input("Vendor", value=item["vendor"], key=f"v_{item['id']}")
                    harga = st.number_input("Harga", min_value=0, value=int(item["harga_estimasi"]), key=f"h_{item['id']}")
                    if st.button("Kirim ke BM", key=f"p1_{item['id']}", type="primary"):
                        item["vendor"], item["harga_estimasi"], item["status"] = vendor, harga, "2. Review BM"
                        catat_log(item, f"Vendor {vendor} (Rp {harga:,}) diajukan ke BM")
                        save_db(st.session_state["db_opb"])
                        st.rerun()

        with tab2:
            items = [x for x in st.session_state["db_opb"] if x["status"] in ["3. Pembuatan IOM (Purchasing)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
            for item in items:
                with st.expander(f"📑 {item['nomor_opb']} - {item['nama_barang']}"):
                    file_iom = st.file_uploader("Upload IOM Baru", type=["pdf", "docx"], key=f"fiom_{item['id']}")
                    if st.button("Kirim ke Finance", key=f"p2_{item['id']}", type="primary") and file_iom:
                        link = upload_to_google_drive(f"IOM_{item['nomor_opb']}_{file_iom.name}", file_iom.getvalue(), file_iom.type, "Purchasing")
                        item["link_iom"], item["status"] = link, "4. Review Finance"
                        catat_log(item, "IOM dikirim ke Finance")
                        save_db(st.session_state["db_opb"])
                        st.rerun()

        with tab3:
            items = [x for x in st.session_state["db_opb"] if x["status"] == "6. Pembelian Barang (Purchasing)"]
            for item in items:
                with st.expander(f"💳 {item['nomor_opb']} - {item['nama_barang']}"):
                    if st.button("Sudah Dibelikan", key=f"p3_{item['id']}", type="primary"):
                        item["status"] = "7. Penerimaan Barang (Engineering)"
                        catat_log(item, "Barang telah dibeli")
                        save_db(st.session_state["db_opb"])
                        st.rerun()

    elif role in ["BM (Building Manager)", "Finance", "P3SRS"]:
        st.header(f"⚖️ Panel {role}")
        if role == "BM (Building Manager)": items = [x for x in st.session_state["db_opb"] if x["status"] in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
        elif role == "Finance": items = [x for x in st.session_state["db_opb"] if x["status"] == "4. Review Finance"]
        elif role == "P3SRS": items = [x for x in st.session_state["db_opb"] if x["status"] == "5. Approval Akhir (BM & P3SRS)"]

        for item in items:
            with st.expander(f"📌 {item['nomor_opb']} - {item['nama_barang']}"):
                catatan = st.text_input("Catatan Revisi", key=f"cat_{item['id']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Approve", key=f"app_{item['id']}", type="primary"):
                        if item["status"] == "2. Review BM": item["status"] = "3. Pembuatan IOM (Purchasing)"
                        elif item["status"] == "4. Review Finance": item["status"] = "5. Approval Akhir (BM & P3SRS)"
                        elif item["status"] == "5. Approval Akhir (BM & P3SRS)":
                            if role == "P3SRS": item["status"] = "6. Pembelian Barang (Purchasing)"
                        catat_log(item, f"Disetujui oleh {role}")
                        save_db(st.session_state["db_opb"])
                        st.rerun()
                with c2:
                    if st.button("❌ Revisi", key=f"rej_{item['id']}"):
                        item["status"] = "Revisi BM (OPB)" if item["status"] == "2. Review BM" else "Revisi Finance"
                        catat_log(item, f"Diminta revisi oleh {role}: {catatan}")
                        save_db(st.session_state["db_opb"])
                        st.rerun()
