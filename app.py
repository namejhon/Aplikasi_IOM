from datetime import datetime
import json
import os
import pandas as pd
import plotly.express as px
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

# --- 2. DATABASE LOKAL TERPUSAT (JSON STORAGE) ---
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

# Sync otomatis session_state dari database JSON
if "db_opb" not in st.session_state:
    st.session_state["db_opb"] = load_db()

# --- 3. CUSTOM CSS ---
st.markdown(
    """
    <style>
    .stApp { background: #f8fafc; }
    .main-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 28px 35px;
        border-radius: 18px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
    }
    .main-header h1 { color: #ffffff !important; font-weight: 800; margin: 0; font-size: 30px; }
    .main-header p { color: #c7d2fe; margin-top: 6px; margin-bottom: 0; font-size: 14px; }
    .kpi-card { background: white; border-radius: 16px; padding: 20px 24px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; }
    .kpi-blue { border-top: 4px solid #3b82f6; }
    .kpi-amber { border-top: 4px solid #f59e0b; }
    .kpi-emerald { border-top: 4px solid #10b981; }
    .kpi-purple { border-top: 4px solid #8b5cf6; }
    .kpi-title { color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .kpi-value { color: #0f172a; font-size: 28px; font-weight: 800; margin-top: 6px; }
    .user-profile-card { background: white; padding: 16px 20px; border-radius: 14px; border: 1px solid #e2e8f0; margin-bottom: 15px; }
    .role-badge { background: #e0e7ff; color: #3730a3; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 5px; }
    .content-box { background: white; border-radius: 16px; padding: 24px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 4. DATABASE USER & PASSWORD ---
USERS = {
    "engineering": {"password": "eng123", "name": "Tim Engineering", "role": "Engineering"},
    "purchasing": {"password": "pur123", "name": "Tim Purchasing", "role": "Purchasing"},
    "bm": {"password": "bm123", "name": "Building Manager", "role": "BM (Building Manager)"},
    "finance": {"password": "fin123", "name": "Tim Finance", "role": "Finance"},
    "p3srs": {"password": "p3srs123", "name": "Pengurus P3SRS", "role": "P3SRS"},
}

# --- 5. HELPER FILE & LOGGING ---
def upload_to_google_drive(file_name, file_bytes, mime_type, folder_id):
    """Menyimpan file ke folder uploads dan menimpa jika nama file sama."""
    try:
        upload_dir = os.path.join(os.getcwd(), "uploads")
        clean_file_name = file_name.replace("/", "_").replace("\\", "_")
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, clean_file_name)
        
        # Hapus file lama jika ada (agar refresh/overwrite bersih)
        if os.path.exists(file_path):
            os.remove(file_path)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return file_path
    except Exception as e:
        st.error(f"❌ Gagal menyimpan file: {e}")
        return None

def delete_physical_file(file_path):
    """Menghapus file fisik dari folder uploads."""
    try:
        if file_path and file_path != "-" and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        st.error(f"⚠️ Gagal menghapus file fisik: {e}")
    return False

def catat_log(item, pesan):
    wib = pytz.timezone("Asia/Jakarta")
    waktu_sekarang = datetime.now(wib).strftime("%d/%m/%Y %H:%M:%S")
    item["timeline"].append({"waktu": waktu_sekarang, "pesan": pesan})

# --- 6. KOMPONEN LIHAT, DOWNLOAD, DAN CETAK FILE ---
def render_file_action_buttons(file_path, label_prefix="Berkas"):
    """Menampilkan tombol Download dan info Path untuk berkas fisik."""
    if file_path and file_path != "-" and os.path.exists(file_path):
        filename = os.path.basename(file_path)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"📥 Download {label_prefix}",
                    data=f.read(),
                    file_name=filename,
                    mime="application/octet-stream",
                    key=f"dl_{label_prefix}_{filename}_{file_path.replace('/', '_')}",
                    use_container_width=True,
                )
        with col_btn2:
            st.caption(f"📁 `{filename}`")
    elif file_path and file_path != "-":
        st.caption(f"⚠️ Berkas dicatat, namun fisik file tidak ditemukan di server.")
    else:
        st.caption("ℹ️ Belum ada berkas diunggah.")

def render_cetak_laporan_button(item, role_user):
    """Menampilkan format Resume Dokumen Siap Cetak (Khusus non-Engineering)."""
    
    # Batasi agar Engineering tidak melihat tombol cetak
    if role_user == "Engineering":
        return

    timeline_html = "".join(
        [f"<li><b>[{t.get('waktu', '')}]</b> {t.get('pesan', '')}</li>" for t in item.get("timeline", [])]
    )

    printable_html = f"""
    <html>
    <head>
        <title>Cetak Resume - {item['nomor_opb']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; color: #1e293b; }}
            .header {{ text-align: center; border-bottom: 2px solid #334155; padding-bottom: 10px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            .table th, .table td {{ border: 1px solid #cbd5e1; padding: 10px; text-align: left; }}
            .table th {{ background-color: #f1f5f9; }}
            .timeline {{ margin-top: 20px; font-size: 13px; line-height: 1.6; }}
            @media print {{ .no-print {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 20px;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">
                🖨️ Klik Di Sini Untuk Cetak / Save to PDF
            </button>
        </div>
        <div class="header">
            <h2>P3SRS - RESUME PENGAJUAN OPB & IOM</h2>
            <p>Nomor Dokumen: <b>{item['nomor_opb']}</b></p>
        </div>
        <table class="table">
            <tr><th>Nama Barang / Pekerjaan</th><td>{item['nama_barang']}</td></tr>
            <tr><th>Jumlah Unit</th><td>{item['jumlah']}</td></tr>
            <tr><th>Spesifikasi / Kebutuhan</th><td>{item['keterangan']}</td></tr>
            <tr><th>Vendor Terpilih</th><td>{item['vendor']}</td></tr>
            <tr><th>Estimasi Total Harga</th><td>Rp {item['harga_estimasi']:,}</td></tr>
            <tr><th>Status Terakhir</th><td><b>{item['status']}</b></td></tr>
        </table>
        <h4>📜 Jejak Audit & Timeline Approval</h4>
        <div class="timeline"><ul>{timeline_html}</ul></div>
    </body>
    </html>
    """

    with st.expander("🖨️ Cetak / Print Resume Lembar Kerja OPB"):
        st.components.v1.html(printable_html, height=350, scrolling=True)

# --- 7. NOTIFIKASI PER DIVISI ---
def cek_notifikasi_user(role):
    db = st.session_state["db_opb"]
    if role == "Purchasing":
        return [x for x in db if x["status"] in ["1. Penawaran Purchasing", "3. Pembuatan IOM (Purchasing)", "6. Pembelian Barang (Purchasing)", "Revisi BM (OPB)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
    elif role == "BM (Building Manager)":
        return [x for x in db if x["status"] in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
    elif role == "Finance":
        return [x for x in db if x["status"] == "4. Review Finance"]
    elif role == "P3SRS":
        return [x for x in db if x["status"] == "5. Approval Akhir (BM & P3SRS)"]
    elif role == "Engineering":
        return [x for x in db if x["status"] == "7. Penerimaan Barang (Engineering)"]
    return []

# --- 8. INIT SESSION ---
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "user_info" not in st.session_state: st.session_state["user_info"] = None
if "target_focus_id" not in st.session_state: st.session_state["target_focus_id"] = None

# ==================== HALAMAN LOGIN ====================
if not st.session_state["logged_in"]:
    col_l1, col_l2, col_l3 = st.columns([1.2, 1.6, 1.2])
    with col_l2:
        st.markdown("<br><div style='text-align: center; margin-bottom: 20px;'><h2 style='color: #1e1b4b; font-weight: 800; font-size: 28px;'>Portal OPB & IOM - P3SRS</h2><p style='color: #64748b;'>Sistem Management Permintaan Barang</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            username_input = st.text_input("Username", placeholder="engineering, purchasing, bm...")
            password_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("🔒 Masuk ke Portal", type="primary", use_container_width=True)

            if submit_login:
                user_data = USERS.get(username_input.lower().strip())
                if user_data and user_data["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user_data
                    st.rerun()
                else:
                    st.error("❌ Username atau Password tidak sesuai!")

else:
    # ==================== APLIKASI UTAMA ====================
    user_info = st.session_state["user_info"]
    role = user_info["role"]
    pending_tasks = cek_notifikasi_user(role)

    # --- SIDEBAR ---
    st.sidebar.markdown(f"<div class='user-profile-card'><h4 style='margin:0; font-size:15px;'>👤 {user_info['name']}</h4><span class='role-badge'>{user_info['role']}</span></div>", unsafe_allow_html=True)
    
    if st.sidebar.button("🔄 Refresh Data (Sync)", use_container_width=True):
        st.session_state["db_opb"] = load_db()
        st.toast("🔄 Data berhasil disinkronkan!", icon="⚡")
        st.rerun()

    if st.sidebar.button("🚪 Keluar / Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_info"] = None
        st.rerun()

    # --- HEADER ---
    st.markdown(f"<div class='main-header'><h1>📋 Sistem Pengajuan OPB & IOM - P3SRS</h1><p>Hak Akses: <b>{role}</b></p></div>", unsafe_allow_html=True)

    # ================= EXECUTIVE DASHBOARD =================
    st.markdown("### 📊 Dashboard Monitoring")
    
    total_opb = len(st.session_state["db_opb"])
    if total_opb > 0:
        df_opb = pd.DataFrame(st.session_state["db_opb"])
        total_selesai = len(df_opb[df_opb["status"] == "8. Selesai"])
        total_proses = total_opb - total_selesai
        total_anggaran = df_opb["harga_estimasi"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='kpi-card kpi-blue'><div class='kpi-title'>Total Pengajuan</div><div class='kpi-value'>{total_opb}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='kpi-card kpi-amber'><div class='kpi-title'>Dalam Process</div><div class='kpi-value' style='color:#d97706;'>{total_proses}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='kpi-card kpi-emerald'><div class='kpi-title'>Selesai</div><div class='kpi-value' style='color:#059669;'>{total_selesai}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='kpi-card kpi-purple'><div class='kpi-title'>Total Budget</div><div class='kpi-value' style='color:#7c3aed; font-size:20px;'>Rp {total_anggaran:,.0f}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_dash1, col_dash2 = st.columns([1.3, 1])
        with col_dash1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📌 Live Status Berkas & Aksi Berkas")
            for idx, item in enumerate(st.session_state["db_opb"]):
                st.markdown(f"**{item['nomor_opb']}** — {item['nama_barang']} (`{item['status']}`)")
                
                # Render File Buttons
                st.markdown("###### 📎 Akses Dokumen Lampiran:")
                render_file_action_buttons(item.get("link_opb"), label_prefix="OPB")
                if item.get("link_iom") != "-":
                    render_file_action_buttons(item.get("link_iom"), label_prefix="IOM")

                # Tombol Cetak Laporan (Akan tersembunyi bagi Engineering)
                render_cetak_laporan_button(item, role_user=role)
                
                # Fitur Hapus Seluruh Pengajuan (Bisa diakses Admin/Engineering jika baru draft)
                if role == "Engineering" and item["status"] == "1. Penawaran Purchasing":
                    if st.button("🗑️ Tarik/Hapus Pengajuan Ini", key=f"del_opb_{item['id']}"):
                        delete_physical_file(item.get("link_opb"))
                        st.session_state["db_opb"] = [x for x in st.session_state["db_opb"] if x["id"] != item["id"]]
                        save_db(st.session_state["db_opb"])
                        st.toast("🗑️ Pengajuan berhasil ditarik/dihapus!", icon="✅")
                        st.rerun()

                st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_dash2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📈 Distribusi Berkas")
            status_counts = df_opb["status"].value_counts().reset_index()
            status_counts.columns = ["Status Tahapan", "Jumlah OPB"]
            fig = px.bar(status_counts, x="Jumlah OPB", y="Status Tahapan", orientation="h", color="Jumlah OPB", color_continuous_scale="Purples")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=280)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==================== MODUL USER PANELS ====================
    # 1. ROLE ENGINEERING
    if role == "Engineering":
        st.header("🔧 Panel Kerja Engineering")
        tab1, tab2 = st.tabs(["📝 Buat Form OPB Baru", "📦 Konfirmasi Penerimaan Barang"])
        
        with tab1:
            with st.form(key="form_opb", clear_on_submit=True):
                nomor_opb = st.text_input("Nomor OPB P3SRS", f"OPB/{datetime.now().strftime('%Y%m%d/%H%M')}")
                nama_barang = st.text_input("Nama Barang / Jenis Pekerjaan")
                jumlah = st.number_input("Jumlah Unit", min_value=1, value=1)
                keterangan = st.text_area("Spesifikasi Detail")
                file_opb = st.file_uploader("Unggah Dokumen Lampiran OPB (PDF/Word/Excel)")
                submit = st.form_submit_button("🚀 Submit & Kirim OPB ke Purchasing", type="primary")

                if submit and nama_barang and file_opb:
                    link = upload_to_google_drive(f"{nomor_opb}_{file_opb.name}", file_opb.getvalue(), file_opb.type, "Engineering")
                    if link:
                        data_baru = {
                            "id": len(st.session_state["db_opb"]) + 1,
                            "nomor_opb": nomor_opb, "nama_barang": nama_barang, "jumlah": jumlah,
                            "keterangan": keterangan, "link_opb": link, "harga_estimasi": 0,
                            "vendor": "-", "link_iom": "-", "catatan_bm": "-", "catatan_finance": "-",
                            "catatan_p3srs": "-", "status": "1. Penawaran Purchasing", "timeline": []
                        }
                        catat_log(data_baru, "OPB Dibuat & Diajukan oleh Engineering ke Purchasing")
                        st.session_state["db_opb"].append(data_baru)
                        save_db(st.session_state["db_opb"])
                        st.toast("🚀 OPB Berhasil diajukan!", icon="✅")
                        st.rerun()

        with tab2:
            items = [x for x in st.session_state["db_opb"] if x["status"] == "7. Penerimaan Barang (Engineering)"]
            for item in items:
                with st.expander(f"📦 {item['nomor_opb']} - {item['nama_barang']}"):
                    st.write(f"Vendor: {item['vendor']} | Jumlah: {item['jumlah']}")
                    if st.button(f"✅ Konfirmasi Barang Sudah Diterima #{item['id']}", type="primary"):
                        item["status"] = "8. Selesai"
                        catat_log(item, "Barang telah diterima oleh Engineering. Selesai.")
                        save_db(st.session_state["db_opb"])
                        st.toast("✅ Barang Diterima! Status OPB Selesai.", icon="🎉")
                        st.rerun()

    # 2. ROLE PURCHASING
    elif role == "Purchasing":
        st.header("🛒 Panel Kerja Purchasing")
        tab1, tab2, tab3 = st.tabs(["1. Input Penawaran Harga", "2. Buat & Unggah IOM", "3. Eksekusi Pembelian"])

        with tab1:
            items = [x for x in st.session_state["db_opb"] if x["status"] in ["1. Penawaran Purchasing", "Revisi BM (OPB)"]]
            for item in items:
                with st.expander(f"📌 {item['nomor_opb']} - {item['nama_barang']}"):
                    vendor = st.text_input("Nama Vendor", value=item["vendor"], key=f"v_{item['id']}")
                    harga = st.number_input("Estimasi Total Harga (Rp)", min_value=0, value=int(item["harga_estimasi"]), key=f"h_{item['id']}")
                    if st.button("Kirim ke BM untuk Review", key=f"btn_p1_{item['id']}", type="primary"):
                        item["vendor"] = vendor
                        item["harga_estimasi"] = harga
                        item["status"] = "2. Review BM"
                        catat_log(item, f"Purchasing menentukan vendor ({vendor}) Rp {harga:,}. Dikirim ke BM.")
                        save_db(st.session_state["db_opb"])
                        st.toast("📩 Berhasil dikirim ke BM!", icon="✅")
                        st.rerun()

        with tab2:
            items = [x for x in st.session_state["db_opb"] if x["status"] in ["3. Pembuatan IOM (Purchasing)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
            for item in items:
                with st.expander(f"📑 {item['nomor_opb']} - {item['nama_barang']}"):
                    st.write(f"Vendor: {item['vendor']} | Harga: Rp {item['harga_estimasi']:,}")
                    
                    # Fitur Hapus IOM Lama untuk Re-Upload Bersih
                    if item.get("link_iom") != "-":
                        if st.button("🗑️ Hapus File IOM Lama", key=f"del_iom_{item['id']}"):
                            delete_physical_file(item["link_iom"])
                            item["link_iom"] = "-"
                            catat_log(item, "Purchasing menghapus berkas IOM lama.")
                            save_db(st.session_state["db_opb"])
                            st.rerun()
                    
                    file_iom = st.file_uploader("Unggah Draft IOM Baru", type=["pdf", "docx"], key=f"fiom_{item['id']}")
                    if st.button("Kirim Berkas IOM ke Finance", key=f"btn_p2_{item['id']}", type="primary"):
                        if file_iom:
                            link = upload_to_google_drive(f"IOM_{item['nomor_opb']}_{file_iom.name}", file_iom.getvalue(), file_iom.type, "Purchasing")
                            item["link_iom"] = link
                            item["status"] = "4. Review Finance"
                            catat_log(item, "Purchasing mengunggah draft IOM dan meneruskan ke Finance.")
                            save_db(st.session_state["db_opb"])
                            st.toast("📩 Draft IOM Dikirim ke Finance!", icon="✅")
                            st.rerun()

        with tab3:
            items = [x for x in st.session_state["db_opb"] if x["status"] == "6. Pembelian Barang (Purchasing)"]
            for item in items:
                with st.expander(f"💳 {item['nomor_opb']} - {item['nama_barang']}"):
                    if st.button("Barang Sudah Dibelikan (Kirim ke Engineering)", key=f"btn_p3_{item['id']}", type="primary"):
                        item["status"] = "7. Penerimaan Barang (Engineering)"
                        catat_log(item, "Purchasing melakukan eksekusi pembelian barang.")
                        save_db(st.session_state["db_opb"])
                        st.toast("📦 Barang dibeli & dikirim ke Engineering!", icon="🚚")
                        st.rerun()

    # 3. ROLE BM, FINANCE, P3SRS (Persetujuan / Approval)
    elif role in ["BM (Building Manager)", "Finance", "P3SRS"]:
        st.header(f"⚖️ Panel Approval {role}")
        
        # Filter item berdasarkan role
        if role == "BM (Building Manager)":
            items = [x for x in st.session_state["db_opb"] if x["status"] in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
        elif role == "Finance":
            items = [x for x in st.session_state["db_opb"] if x["status"] == "4. Review Finance"]
        elif role == "P3SRS":
            items = [x for x in st.session_state["db_opb"] if x["status"] == "5. Approval Akhir (BM & P3SRS)"]

        for item in items:
            with st.expander(f"📌 {item['nomor_opb']} - {item['nama_barang']}"):
                catatan = st.text_input("Catatan / Alasan Revisi", key=f"cat_{item['id']}")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Setuju (Approve)", key=f"app_{item['id']}", type="primary"):
                        if item["status"] == "2. Review BM":
                            item["status"] = "3. Pembuatan IOM (Purchasing)"
                            catat_log(item, "BM menyetujui OPB.")
                        elif item["status"] == "4. Review Finance":
                            item["status"] = "5. Approval Akhir (BM & P3SRS)"
                            catat_log(item, "Finance memverifikasi budget IOM.")
                        elif item["status"] == "5. Approval Akhir (BM & P3SRS)":
                            if role == "P3SRS":
                                item["status"] = "6. Pembelian Barang (Purchasing)"
                                catat_log(item, "P3SRS menyetujui IOM Final. Memerintahkan Pembelian.")
                            else:
                                catat_log(item, "BM menyetujui IOM Final.")
                        save_db(st.session_state["db_opb"])
                        st.toast("✅ Persetujuan Berhasil!", icon="👍")
                        st.rerun()
                        
                with col2:
                    if st.button("❌ Tolak / Revisi", key=f"rej_{item['id']}"):
                        if item["status"] == "2. Review BM":
                            item["status"] = "Revisi BM (OPB)"
                        elif item["status"] == "4. Review Finance":
                            item["status"] = "Revisi Finance"
                        elif item["status"] == "5. Approval Akhir (BM & P3SRS)":
                            item["status"] = "Revisi BM/P3SRS (IOM)"
                        catat_log(item, f"{role} meminta revisi: {catatan}")
                        save_db(st.session_state["db_opb"])
                        st.toast("⚠️ Berkas dikembalikan untuk direvisi!", icon="🔄")
                        st.rerun()
