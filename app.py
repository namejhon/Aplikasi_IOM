import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

st.set_page_config(
    page_title="Portal OPB & IOM - P3SRS",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

USERS = {
    "engineering": {"password": "eng123", "name": "Tim Engineering", "role": "Engineering"},
    "purchasing": {"password": "pur123", "name": "Tim Purchasing", "role": "Purchasing"},
    "bm": {"password": "bm123", "name": "Building Manager", "role": "BM (Building Manager)"},
    "finance": {"password": "fin123", "name": "Tim Finance", "role": "Finance"},
    "p3srs": {"password": "p3srs123", "name": "Pengurus P3SRS", "role": "P3SRS"}
}

INITIAL_DATA = [
    {
        "id": 1,
        "nomor_opb": "OPB/20260729/1314",
        "nama_barang": "Pompa Air Submersible Gedung Utama",
        "jumlah": 1,
        "harga_estimasi": 4800000,
        "vendor": "PT. Pump Tehnik Indonesia",
        "keterangan": "Penggantian unit pompa gedung A yang aus.",
        "link_opb": "OPB_Pompa_2026.pdf",
        "link_iom": "IOM_Pompa_2026.pdf",
        "status": "2. Review BM",
        "catatan_revisi": "",
        "timeline": [
            {"waktu": "29/07/2026 20:09:13", "pesan": "OPB Dibuat & Diajukan oleh Engineering"},
            {"waktu": "29/07/2026 20:19:53", "pesan": "Vendor PT. Pump Tehnik Indonesia (Rp 4.800.000) diajukan ke BM oleh Purchasing"}
        ]
    },
    {
        "id": 2,
        "nomor_opb": "OPB/20260728/0920",
        "nama_barang": "Kabel Power NYY 4x10mm 100m",
        "jumlah": 2,
        "harga_estimasi": 8500000,
        "vendor": "CV. Eka Listrik Mandiri",
        "keterangan": "Perbaikan instalasi penerangan area parkir basement.",
        "link_opb": "OPB_Kabel_Parkir.pdf",
        "link_iom": "IOM_Kabel_Parkir.pdf",
        "status": "8. Selesai",
        "catatan_revisi": "",
        "timeline": [
            {"waktu": "28/07/2026 09:20:00", "pesan": "OPB Dibuat oleh Engineering"},
            {"waktu": "28/07/2026 11:15:00", "pesan": "Vendor CV. Eka Listrik Mandiri diajukan oleh Purchasing"},
            {"waktu": "28/07/2026 14:00:00", "pesan": "Disetujui oleh BM (Building Manager)"},
            {"waktu": "28/07/2026 15:30:00", "pesan": "IOM dikirim ke Finance oleh Purchasing"},
            {"waktu": "28/07/2026 16:45:00", "pesan": "Disetujui oleh Finance"},
            {"waktu": "29/07/2026 09:00:00", "pesan": "Disetujui oleh P3SRS"},
            {"waktu": "29/07/2026 11:30:00", "pesan": "Barang telah dibeli oleh Purchasing"},
            {"waktu": "29/07/2026 14:20:00", "pesan": "Barang diterima oleh Engineering. Selesai."}
        ]
    }
]

if "db_opb" not in st.session_state:
    st.session_state.db_opb = INITIAL_DATA

if "user" not in st.session_state:
    st.session_state.user = None

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    .metric-card {
        background: white;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    .timeline-item {
        border-left: 3px solid #3b82f6;
        padding-left: 14px;
        margin-bottom: 12px;
        position: relative;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

def format_rupiah(val):
    return f"Rp {val:,.0f}".replace(",", ".")

def add_log(item, pesan):
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    item["timeline"].append({"waktu": now_str, "pesan": pesan})

def get_pending_tasks(role):
    db = st.session_state.db_opb
    if role == 'Purchasing':
        return [x for x in db if x['status'] in ['1. Penawaran Purchasing', '3. Pembuatan IOM (Purchasing)', '6. Pembelian Barang (Purchasing)', 'Revisi BM (OPB)', 'Revisi Finance']]
    elif role == 'BM (Building Manager)':
        return [x for x in db if x['status'] in ['2. Review BM', '5. Approval Akhir (BM & P3SRS)']]
    elif role == 'Finance':
        return [x for x in db if x['status'] == '4. Review Finance']
    elif role == 'P3SRS':
        return [x for x in db if x['status'] == '5. Approval Akhir (BM & P3SRS)']
    elif role == 'Engineering':
        return [x for x in db if x['status'] == '7. Penerimaan Barang (Engineering)']
    return []

if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center; color: #1e1b4b;'>🏢 Portal OPB & IOM P3SRS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Sistem Pengadaan Barang P3SRS (Versi Python)</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔑 Login System")
        username_input = st.text_input("Username", placeholder="engineering, purchasing, bm, finance, p3srs")
        password_input = st.text_input("Password", type="password")
        
        if st.button("Masuk ke Portal", type="primary", use_container_width=True):
            u = username_input.strip().lower()
            if u in USERS and USERS[u]["password"] == password_input:
                st.session_state.user = USERS[u]
                st.success(f"Selamat datang, {USERS[u]['name']}!")
                st.rerun()
            else:
                st.error("Username atau Password salah!")
        
        st.divider()
        st.caption("Akses Cepat Testing (Quick Login)")
        qcol1, qcol2 = st.columns(2)
        with qcol1:
            if st.button("🔧 Engineering", use_container_width=True):
                st.session_state.user = USERS["engineering"]
                st.rerun()
            if st.button("👔 Building Manager", use_container_width=True):
                st.session_state.user = USERS["bm"]
                st.rerun()
        with qcol2:
            if st.button("🛒 Purchasing", use_container_width=True):
                st.session_state.user = USERS["purchasing"]
                st.rerun()
            if st.button("💵 Finance", use_container_width=True):
                st.session_state.user = USERS["finance"]
                st.rerun()
        if st.button("🏢 Pengurus P3SRS", use_container_width=True):
            st.session_state.user = USERS["p3srs"]
            st.rerun()
            
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.title("📋 P3SRS Portal")
    st.info(f"**{user['name']}**\nRole: *{user['role']}*")
    
    current_tab = st.radio("Navigasi Utama", ["📊 Dashboard & Audit", "📋 Panel Tugas Saya"])
    
    st.divider()
    
    if user["role"] == "Engineering":
        if st.button("➕ Buat OPB Baru", type="primary", use_container_width=True):
            st.session_state.show_create_modal = True

    if st.button("🚪 Keluar System", use_container_width=True):
        st.session_state.user = None
        st.rerun()

if st.session_state.get("show_create_modal", False):
    with st.expander("📝 Form Pengajuan OPB Baru", expanded=True):
        now = datetime.now()
        auto_no = f"OPB/{now.strftime('%Y%m%d')}/{now.strftime('%H%M')}"
        
        st.text_input("Nomor OPB", value=auto_no, disabled=True)
        nama_barang = st.text_input("Nama Barang / Pengadaan", placeholder="Contoh: Lampu LED Gedung B")
        col_a, col_b = st.columns(2)
        with col_a:
            jumlah = st.number_input("Jumlah (Unit)", min_value=1, value=1)
        with col_b:
            harga = st.number_input("Estimasi Awal (Rp)", min_value=0, value=0, step=100000)
        keterangan = st.text_area("Keterangan Pengadaan")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Submit OPB", type="primary", use_container_width=True):
                if nama_barang:
                    new_item = {
                        "id": int(datetime.now().timestamp()),
                        "nomor_opb": auto_no,
                        "nama_barang": nama_barang,
                        "jumlah": jumlah,
                        "harga_estimasi": harga,
                        "vendor": "-",
                        "keterangan": keterangan,
                        "link_opb": f"{auto_no.replace('/', '_')}.pdf",
                        "link_iom": "-",
                        "status": "1. Penawaran Purchasing",
                        "catatan_revisi": "",
                        "timeline": [
                            {"waktu": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "pesan": "OPB Dibuat & Diajukan oleh Engineering"}
                        ]
                    }
                    st.session_state.db_opb.insert(0, new_item)
                    st.session_state.show_create_modal = False
                    st.success("Dokumen OPB berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.warning("Nama barang harus diisi!")
        with c2:
            if st.button("Batal", use_container_width=True):
                st.session_state.show_create_modal = False
                st.rerun()

if current_tab == "📊 Dashboard & Audit":
    st.title("📋 Sistem Flow OPB & IOM P3SRS")
    st.caption("Pantau workflow, approval, dan jejak audit pengadaan secara real-time.")

    db = st.session_state.db_opb
    total_doc = len(db)
    selesai_doc = len([x for x in db if x['status'] == '8. Selesai'])
    proses_doc = total_doc - selesai_doc
    total_budget = sum([x['harga_estimasi'] for x in db])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Pengajuan", total_doc)
    m2.metric("Dalam Proses", proses_doc)
    m3.metric("Selesai", selesai_doc)
    m4.metric("Total Budget Estimasi", format_rupiah(total_budget))

    st.divider()

    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        st.subheader("📁 Daftar Berkas OPB & IOM")
        search_query = st.text_input("🔍 Cari nomor OPB / barang / vendor...", "")
        
        filtered_db = [
            x for x in db if search_query.lower() in x['nomor_opb'].lower() 
            or search_query.lower() in x['nama_barang'].lower()
            or search_query.lower() in x['vendor'].lower()
        ]

        # Export Data to CSV
        if filtered_db:
            df_export = pd.DataFrame(filtered_db)[["nomor_opb", "nama_barang", "jumlah", "harga_estimasi", "vendor", "status"]]
            st.download_button("📥 Export CSV / Excel", data=df_export.to_csv(index=False), file_name="OPB_P3SRS_Report.csv", mime="text/csv")

        for item in filtered_db:
            with st.expander(f"📌 **{item['nomor_opb']}** | {item['nama_barang']} — `{item['status']}`"):
                st.write(f"**Jumlah:** {item['jumlah']} Unit")
                st.write(f"**Vendor:** {item['vendor']}")
                st.write(f"**Estimasi Harga:** {format_rupiah(item['harga_estimasi'])}")
                st.write(f"**Keterangan:** {item['keterangan']}")
                
                if st.button("Set Aktif Audit Timeline", key=f"sel_{item['id']}"):
                    st.session_state.selected_opb_id = item['id']

    with col_right:
        st.subheader("📜 Jejak Audit / Timeline")
        selected_id = st.session_state.get("selected_opb_id", db[0]['id'] if db else None)
        selected_item = next((x for x in db if x['id'] == selected_id), None)

        if selected_item:
            st.info(f"Target Dokumen: **{selected_item['nomor_opb']}**")
            for tl in reversed(selected_item['timeline']):
                st.markdown(f"""
                <div class='timeline-item'>
                    <span style='font-size:0.75rem; color:#64748b;'>⏱️ {tl['waktu']}</span><br>
                    <strong>{tl['pesan']}</strong>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("Pilih dokumen dari daftar di sebelah kiri.")

        st.divider()
        st.subheader("📊 Distribusi Status")
        status_counts = pd.DataFrame([x['status'] for x in db], columns=["Status"]).value_counts().reset_index()
        status_counts.columns = ["Status", "Jumlah"]
        fig = px.bar(status_counts, x="Status", y="Jumlah", color="Status", title="Status Dokumen Saat Ini")
        st.plotly_chart(fig, use_container_width=True)

elif current_tab == "📋 Panel Tugas Saya":
    st.title(f"⚡ Panel Tugas: {user['role']}")
    pending_tasks = get_pending_tasks(user['role'])

    if not pending_tasks:
        st.success("🎉 Semua tugas Anda telah selesai! Tidak ada pending dokumen.")
    else:
        for item in pending_tasks:
            with st.container():
                st.markdown(f"### 📄 {item['nomor_opb']} — {item['nama_barang']}")
                st.caption(f"Status Saat Ini: **{item['status']}** | Estimasi: **{format_rupiah(item['harga_estimasi'])}** | Vendor: **{item['vendor']}**")
                
                # Purchasing Action Forms
                if user['role'] == 'Purchasing':
                    if item['status'] in ['1. Penawaran Purchasing', 'Revisi BM (OPB)']:
                        v_input = st.text_input("Nama Vendor", value="" if item['vendor'] == "-" else item['vendor'], key=f"v_{item['id']}")
                        h_input = st.number_input("Harga Penawaran Vendor (Rp)", value=int(item['harga_estimasi']), step=500000, key=f"h_{item['id']}")
                        if st.button("🚀 Kirim Penawaran ke BM", key=f"btn_p_{item['id']}"):
                            if v_input:
                                item['vendor'] = v_input
                                item['harga_estimasi'] = h_input
                                item['status'] = '2. Review BM'
                                add_log(item, f"Vendor {v_input} ({format_rupiah(h_input)}) diajukan ke BM oleh Purchasing")
                                st.success("Penawaran diajukan ke BM!")
                                st.rerun()
                            else:
                                st.error("Isi nama vendor!")

                    elif item['status'] in ['3. Pembuatan IOM (Purchasing)', 'Revisi BM/P3SRS (IOM)']:
                        file_iom = st.file_uploader("Upload File IOM (PDF)", key=f"file_{item['id']}")
                        if st.button("📤 Kirim IOM ke Finance", key=f"btn_iom_{item['id']}"):
                            item['status'] = '4. Review Finance'
                            add_log(item, "Dokumen IOM diunggah dan dikirim ke Finance oleh Purchasing")
                            st.success("IOM Dikirim ke Finance!")
                            st.rerun()

                    elif item['status'] == '6. Pembelian Barang (Purchasing)':
                        if st.button("💳 Konfirmasi Barang Sudah Dibelikan", key=f"buy_{item['id']}"):
                            item['status'] = '7. Penerimaan Barang (Engineering)'
                            add_log(item, "Barang telah dibeli oleh Purchasing.")
                            st.success("Status diperbarui!")
                            st.rerun()

                # Approver Actions (BM, Finance, P3SRS)
                elif user['role'] in ['BM (Building Manager)', 'Finance', 'P3SRS']:
                    note = st.text_input("Catatan Approval / Catatan Revisi", key=f"note_{item['id']}")
                    c_app, c_rev = st.columns(2)
                    with c_app:
                        if st.button("✅ Setujui (Approve)", key=f"app_{item['id']}", type="primary", use_container_width=True):
                            if item['status'] == '2. Review BM':
                                item['status'] = '3. Pembuatan IOM (Purchasing)'
                            elif item['status'] == '4. Review Finance':
                                item['status'] = '5. Approval Akhir (BM & P3SRS)'
                            elif item['status'] == '5. Approval Akhir (BM & P3SRS)':
                                item['status'] = '6. Pembelian Barang (Purchasing)'
                            
                            add_log(item, f"Disetujui oleh {user['role']}. {f'Catatan: {note}' if note else ''}")
                            st.success("Dokumen Disetujui!")
                            st.rerun()

                    with c_rev:
                        if st.button("🔴 Minta Revisi", key=f"rev_{item['id']}", use_container_width=True):
                            if item['status'] == '2. Review BM':
                                item['status'] = 'Revisi BM (OPB)'
                            elif item['status'] == '4. Review Finance':
                                item['status'] = 'Revisi Finance'
                            else:
                                item['status'] = 'Revisi BM/P3SRS (IOM)'
                            
                            add_log(item, f"Revisi diminta oleh {user['role']}: {note if note else 'Tanpa catatan'}")
                            st.warning("Permintaan revisi dikirim!")
                            st.rerun()

                # Engineering Receive Action
                elif user['role'] == 'Engineering':
                    if item['status'] == '7. Penerimaan Barang (Engineering)':
                        if st.button("📦 Konfirmasi Penerimaan Barang", key=f"rec_{item['id']}", type="primary"):
                            item['status'] = '8. Selesai'
                            add_log(item, "Barang telah diterima oleh Tim Engineering. Selesai.")
                            st.success("Pengadaan Selesai Tuntas!")
                            st.rerun()

                st.divider()

st.markdown("---")
st.caption("System Portal OPB & IOM P3SRS — Powered by Python & Streamlit")
