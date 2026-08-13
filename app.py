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
import pymysql
import pytz
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Flow OPB & IOM - P3SRS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- 1.1 AUTO REFRESH (Polling Realtime Data tiap 5 detik) ---
st_autorefresh(interval=5000, limit=None, key="opb_datarefresh")

MYSQL_HOST = st.secrets["mysql"]["host"]
MYSQL_USER = st.secrets["mysql"]["user"]
MYSQL_PASSWORD = st.secrets["mysql"]["password"]
MYSQL_DATABASE = st.secrets["mysql"]["database"]
MYSQL_PORT = int(st.secrets["mysql"]["port"])

def get_mysql_connection():
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return connection
    except Exception as e:
        st.error(f"⚠️ Gagal terhubung ke Database MySQL: {e}")
        return None

# --- LIST DIVISI & BUDGET 1 MILIAR PER DIVISI ---
DIVISI_LIST = [
    "IT",
    "Mekanikal",
    "Civil",
    "Plumbing",
    "Elektrikal",
    "Lift",
    "AC",
]

INITIAL_BUDGETS = {div: 1_000_000_000 for div in DIVISI_LIST}

# --- 2. FUNGSI PERSISTENSI DATA (MYSQL & STORAGE LOKAL) ---
def init_mysql_table():
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS opb_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nama_barang TEXT,
                        nomor_opb VARCHAR(100),
                        jumlah INT,
                        keterangan TEXT,
                        divisi VARCHAR(50),
                        urgensi VARCHAR(50),
                        status VARCHAR(100),
                        harga_estimasi BIGINT,
                        vendor VARCHAR(150),
                        file_opb_data LONGTEXT,
                        file_opb_name VARCHAR(255),
                        file_iom_data LONGTEXT,
                        file_iom_name VARCHAR(255),
                        file_bast_data LONGTEXT,
                        file_bast_name VARCHAR(255),
                        catatan_bm TEXT,
                        catatan_finance TEXT,
                        catatan_p3srs TEXT,
                        timeline LONGTEXT
                    )
                """)
        except Exception as e:
            st.error(f"Gagal membuat tabel MySQL: {e}")
        finally:
            conn.close()

init_mysql_table()

def load_database():
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM opb_data ORDER BY id ASC")
            data = cursor.fetchall()
        
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
        st.error(f"Gagal memuat database dari MySQL: {e}")
        return []
    finally:
        conn.close()

def save_database(item_data, is_new=False):
    conn = get_mysql_connection()
    if not conn:
        return None
    try:
        timeline_str = json.dumps(item_data.get("timeline", []))
        
        with conn.cursor() as cursor:
            if is_new:
                sql = """
                    INSERT INTO opb_data 
                    (nama_barang, nomor_opb, jumlah, keterangan, divisi, urgensi, status, harga_estimasi, vendor, 
                     file_opb_data, file_opb_name, file_iom_data, file_iom_name, file_bast_data, file_bast_name, 
                     catatan_bm, catatan_finance, catatan_p3srs, timeline)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                val = (
                    str(item_data.get("nama_barang", "")),
                    str(item_data.get("nomor_opb", "")),
                    int(item_data.get("jumlah", 1)),
                    str(item_data.get("keterangan", "") or ""),
                    str(item_data.get("divisi", "IT")),
                    str(item_data.get("urgensi", "Normal")),
                    str(item_data.get("status", "1. Penawaran Purchasing")),
                    int(item_data.get("harga_estimasi", 0) or 0),
                    str(item_data.get("vendor", "-")),
                    item_data.get("file_opb_data"),
                    item_data.get("file_opb_name"),
                    item_data.get("file_iom_data"),
                    item_data.get("file_iom_name"),
                    item_data.get("file_bast_data"),
                    item_data.get("file_bast_name"),
                    str(item_data.get("catatan_bm", "-")),
                    str(item_data.get("catatan_finance", "-")),
                    str(item_data.get("catatan_p3srs", "-")),
                    timeline_str
                )
                cursor.execute(sql, val)
            else:
                sql = """
                    UPDATE opb_data SET 
                    nama_barang=%s, nomor_opb=%s, jumlah=%s, keterangan=%s, divisi=%s, urgensi=%s, status=%s, 
                    harga_estimasi=%s, vendor=%s, file_opb_data=%s, file_opb_name=%s, file_iom_data=%s, 
                    file_iom_name=%s, file_bast_data=%s, file_bast_name=%s, 
                    catatan_bm=%s, catatan_finance=%s, catatan_p3srs=%s, timeline=%s
                    WHERE id=%s
                """
                val = (
                    str(item_data.get("nama_barang", "")),
                    str(item_data.get("nomor_opb", "")),
                    int(item_data.get("jumlah", 1)),
                    str(item_data.get("keterangan", "") or ""),
                    str(item_data.get("divisi", "IT")),
                    str(item_data.get("urgensi", "Normal")),
                    str(item_data.get("status", "1. Penawaran Purchasing")),
                    int(item_data.get("harga_estimasi", 0) or 0),
                    str(item_data.get("vendor", "-")),
                    item_data.get("file_opb_data"),
                    item_data.get("file_opb_name"),
                    item_data.get("file_iom_data"),
                    item_data.get("file_iom_name"),
                    item_data.get("file_bast_data"),
                    item_data.get("file_bast_name"),
                    str(item_data.get("catatan_bm", "-")),
                    str(item_data.get("catatan_finance", "-")),
                    str(item_data.get("catatan_p3srs", "-")),
                    timeline_str,
                    int(item_data.get("id"))
                )
                cursor.execute(sql, val)
        return True
    except Exception as e:
        st.error(f"❌ Gagal Database MySQL: {e}")
        return None
    finally:
        conn.close()

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
    processed_data = output.getvalue()
    return processed_data

def generate_outlook_mailto_link(item, target_email="purchasing@p3srs.com"):
    nomor_opb = item.get('nomor_opb', 'OPB')
    divisi = item.get('divisi', 'IT')
    nama_barang = item.get('nama_barang', '-')
    status = item.get('status', '-')
    harga = item.get('harga_estimasi', 0)
    urgensi = item.get('urgensi', 'Normal')
    
    is_darurat = "darurat" in urgensi.lower()
    prefix_subjek = "🚨 [URGENT/DARURAT] " if is_darurat else "📋 "
    
    subject = urllib.parse.quote(f"{prefix_subjek}Tindak Lanjut OPB: {nomor_opb} - Divisi {divisi}")
    body = urllib.parse.quote(
        f"{'⚠️ PERHATIAN: BERKAS INI BERSTATUS DARURAT (1x24 JAM) ⚠️\n\n' if is_darurat else ''}"
        f"Halo Tim,\n\n"
        f"Terdapat pembaruan/pengajuan dokumen OPB/IOM yang memerlukan tindakan pada Sistem P3SRS:\n\n"
        f"- Nomor OPB: {nomor_opb}\n"
        f"- Tingkat Urgensi: {urgensi}\n"
        f"- Divisi Pemohon: {divisi}\n"
        f"- Rincian Barang: {nama_barang}\n"
        f"- Estimasi Biaya: Rp {harga:,.0f}\n"
        f"- Status Berkas: {status}\n\n"
        f"Silakan akses portal aplikasi untuk melakukan verifikasi, persetujuan, dan tanda tangan digital.\n\n"
        f"Terima kasih.\n"
        f"(Notifikasi Otomatis Sistem Flow OPB & IOM - P3SRS)"
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
    .main-header h1 { color: #ffffff !important; font-weight: 800; letter-spacing: -0.5px; margin: 0; font-size: 26px; }
    .main-header p { color: #c7d2fe; margin-top: 6px; margin-bottom: 0; font-size: 13px; }
    
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
    .kpi-value { color: #0f172a; font-size: 22px; font-weight: 800; margin-top: 4px; }
    .kpi-sub { font-size: 11px; font-weight: 600; margin-top: 4px; }
    
    .user-profile-card {
        background: white; padding: 14px 18px; border-radius: 14px;
        border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 15px;
    }
    .role-badge {
        background: #e0e7ff; color: #3730a3; padding: 3px 10px;
        border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 5px;
    }
    
    .notif-box {
        background: linear-gradient(135deg, #fffbe3 0%, #fef3c7 100%);
        border-left: 5px solid #f59e0b; color: #78350f; padding: 16px 20px;
        border-radius: 16px; margin-bottom: 18px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.12);
    }
    
    .content-box {
        background: white; border-radius: 16px; padding: 20px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.03); margin-bottom: 20px;
    }

    .digital-signature-badge {
        display: inline-block; 
        background: #ecfdf5; 
        border: 1px dashed #10b981;
        color: #047857; 
        font-size: 10.5px; 
        padding: 3px 8px; 
        border-radius: 6px; 
        margin-top: 6px; 
        font-family: monospace; 
        word-break: break-all;
    }
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

# --- 5. LOG & TANDA TANGAN DIGITAL ---
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

def render_enhanced_timeline(timeline_data):
    timeline_css = """
    <style>
    .opb-timeline-container {
        font-family: 'Inter', sans-serif;
        padding: 5px 10px;
    }
    .opb-tl-item {
        display: flex;
        position: relative;
        padding-bottom: 20px;
    }
    .opb-tl-item:last-child {
        padding-bottom: 0;
    }
    .opb-tl-item::before {
        content: '';
        position: absolute;
        left: 14px;
        top: 30px;
        bottom: 0;
        width: 2px;
        background: #e2e8f0;
    }
    .opb-tl-item:last-child::before {
        display: none;
    }
    .opb-tl-icon {
        position: relative;
        z-index: 2;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 11px;
        flex-shrink: 0;
        border: 2px solid #fff;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .icon-done { background: #10b981; color: white; }
    .icon-active { background: #f59e0b; color: white; box-shadow: 0 0 10px rgba(245, 158, 11, 0.4); }
    
    .opb-tl-content {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-left: 12px;
        width: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .opb-tl-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    .opb-tl-title {
        font-weight: 700;
        font-size: 12px;
        color: #1e293b;
    }
    .opb-tl-actor {
        font-size: 10.5px;
        font-weight: 600;
        color: #4338ca;
        background: #e0e7ff;
        padding: 1px 6px;
        border-radius: 4px;
    }
    .opb-tl-time {
        font-size: 10px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .opb-tl-desc {
        font-size: 11px;
        color: #334155;
        line-height: 1.3;
    }
    </style>
    """

    if not timeline_data:
        st.caption("Belum ada riwayat aktivitas.")
        return

    formatted_steps = []
    for i, log_entry in enumerate(timeline_data):
        if isinstance(log_entry, dict):
            waktu_log = log_entry.get("waktu", "-")
            pesan_log = log_entry.get("pesan", "-")
            sig = log_entry.get("signature", {})
            actor_log = sig.get("role", "Sistem / User") if sig else "Sistem"
        else:
            waktu_log = "-"
            pesan_log = str(log_entry)
            actor_log = "Sistem"

        is_last = (i == len(timeline_data) - 1)
        formatted_steps.append({
            "step": i + 1,
            "title": f"Tahap {i+1}",
            "actor": actor_log,
            "time": waktu_log,
            "desc": pesan_log,
            "status": "active" if is_last else "done"
        })

    html_code = f"{timeline_css}<div class='opb-timeline-container'>"

    for step in formatted_steps:
        icon_cls = "icon-active" if step["status"] == "active" else "icon-done"
        sig_badge_html = ""
        if isinstance(timeline_data[step["step"]-1], dict) and timeline_data[step["step"]-1].get("signature"):
            sig = timeline_data[step["step"]-1].get("signature")
            sig_badge_html = f"""
            <br><span class="digital-signature-badge">
                🔏 Signed by <b>{sig.get('signed_by', '-')}</b> ({sig.get('role', '-')}) | {sig.get('hash', '-')}
            </span>
            """

        html_code += f"""
        <div class="opb-tl-item">
            <div class="opb-tl-icon {icon_cls}">{step['step']}</div>
            <div class="opb-tl-content">
                <div class="opb-tl-header">
                    <span class="opb-tl-title">{step['title']}</span>
                    <span class="opb-tl-actor">👤 {step['actor']}</span>
                </div>
                <div class="opb-tl-time">🕒 {step['time']}</div>
                <div class="opb-tl-desc">{step['desc']}{sig_badge_html}</div>
            </div>
        </div>
        """

    html_code += "</div>"
    
    dynamic_height = max(130, len(timeline_data) * 115)
    components.html(html_code, height=dynamic_height, scrolling=False)

def render_download_buttons(item, key_prefix="dl"):
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        opb_data_b64 = item.get("file_opb_data")
        opb_filename = item.get("file_opb_name") or f"Dokumen_{item.get('nomor_opb', 'OPB').replace('/', '_')}.pdf"
        if opb_data_b64:
            try:
                decoded_bytes = base64.b64decode(opb_data_b64)
                st.download_button(
                    label="📥 Download OPB",
                    data=decoded_bytes,
                    file_name=opb_filename,
                    mime="application/octet-stream",
                    key=f"{key_prefix}_opb_{item.get('id', 0)}"
                )
            except Exception:
                st.download_button(
                    label="📥 Download OPB",
                    data=str(opb_data_b64).encode("utf-8"),
                    file_name=opb_filename,
                    mime="text/plain",
                    key=f"{key_prefix}_opb_{item.get('id', 0)}"
                )
        else:
            st.caption("ℹ️ File OPB Belum Ada")

    with col2:
        iom_data_b64 = item.get("file_iom_data")
        iom_filename = item.get("file_iom_name") or f"IOM_{item.get('nomor_opb', 'OPB').replace('/', '_')}.pdf"
        if iom_data_b64:
            try:
                decoded_bytes = base64.b64decode(iom_data_b64)
                st.download_button(
                    label="📥 Download IOM",
                    data=decoded_bytes,
                    file_name=iom_filename,
                    mime="application/octet-stream",
                    key=f"{key_prefix}_iom_{item.get('id', 0)}"
                )
            except Exception:
                st.download_button(
                    label="📥 Download IOM",
                    data=str(iom_data_b64).encode("utf-8"),
                    file_name=iom_filename,
                    mime="text/plain",
                    key=f"{key_prefix}_iom_{item.get('id', 0)}"
                )
        else:
            st.caption("ℹ️ IOM Belum Ada")

    with col3:
        bast_data_b64 = item.get("file_bast_data")
        bast_filename = item.get("file_bast_name") or f"BAST_{item.get('nomor_opb', 'OPB').replace('/', '_')}.pdf"
        if bast_data_b64:
            try:
                decoded_bytes = base64.b64decode(bast_data_b64)
                st.download_button(
                    label="📦 Download BAST",
                    data=decoded_bytes,
                    file_name=bast_filename,
                    mime="application/octet-stream",
                    key=f"{key_prefix}_bast_{item.get('id', 0)}"
                )
            except Exception:
                st.download_button(
                    label="📦 Download BAST",
                    data=str(bast_data_b64).encode("utf-8"),
                    file_name=bast_filename,
                    mime="text/plain",
                    key=f"{key_prefix}_bast_{item.get('id', 0)}"
                )
        else:
            st.caption("ℹ️ BAST Belum Ada")

def render_signature_pad(key_id):
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
        canvas_{key_id}.width = canvas_{key_id}.offsetWidth;
        canvas_{key_id}.height = canvas_{key_id}.offsetHeight;
        var drawing_{key_id} = false;

        function getPos(e) {{
            var rect = canvas_{key_id}.getBoundingClientRect();
            var clientX = e.clientX || (e.touches && e.touches[0].clientX);
            var clientY = e.clientY || (e.touches && e.touches[0].clientY);
            return {{ x: clientX - rect.left, y: clientY - rect.top }};
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
        pending_items = [x for x in db if x.get("status") in ["1. Penawaran Purchasing", "3. Pembuatan IOM (Purchasing)", "6. Serah Terima Barang (Purchasing -> Engineering)", "Revisi BM (OPB)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"] or not x.get("status")]
    elif role == "BM (Building Manager)":
        pending_items = [x for x in db if x.get("status") in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
    elif role == "Finance":
        pending_items = [x for x in db if x.get("status") == "4. Review Finance"]
    elif role == "P3SRS":
        pending_items = [x for x in db if x.get("status") == "5. Approval Akhir (BM & P3SRS)"]
    elif role == "Engineering":
        pending_items = [x for x in db if x.get("status") == "7. Verifikasi Penerimaan Barang (Engineering)"]

    return pending_items


# --- 6. INITIALIZATION SESSION STATE ---
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


# ==================== HALAMAN LOGIN ====================
if not st.session_state["logged_in"]:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])

    with col_l2:
        st.markdown("<br>", unsafe_allow_html=True)
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
            username_input = st.text_input("Username", placeholder="engineering, purchasing, bm...")
            password_input = st.text_input("Password", type="password", placeholder="Masukkan password...")
            submit_login = st.form_submit_button("🔒 Masuk ke Portal", type="primary", use_container_width=True)

            if submit_login:
                user_data = USERS.get(username_input.lower().strip())
                if user_data and user_data["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user_data
                    st.session_state["notif_shown"] = False
                    cookie_manager.set("opb_p3srs_user", user_data, key="set_cookie_login")
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
        st.toast(f"🔔 **Pemberitahuan:** Ada {len(pending_tasks)} tugas baru!", icon="📩")
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
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                    <span style="font-size:20px;">🔔</span>
                    <span style="font-size: 15px; font-weight: 700;">Notifikasi Tugas Masuk ({len(pending_tasks)} Berkas Menunggu Tindakan)</span>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        task_options = {
            f"👉 [{t.get('nomor_opb', 'OPB')}] — Divisi: {t.get('divisi', 'IT')} | Barang: {t.get('nama_barang', '-')} ({t.get('status', 'Pending')})": t 
            for t in pending_tasks
        }

        col_sel1, col_sel2 = st.columns([3, 1])
        with col_sel1:
            selected_task_label = st.selectbox(
                "Pilih Berkas Tugas untuk Langsung Diproses:",
                options=list(task_options.keys()),
                key="dropdown_notif_tugas"
            )
        with col_sel2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Buka & Fokus ke Tugas", type="primary", use_container_width=True):
                chosen_task = task_options[selected_task_label]
                st.session_state["target_focus_id"] = chosen_task.get("id")
                components.html('<script>window.parent.document.getElementById("anchor-kelola-opb").scrollIntoView({behavior: "smooth"});</script>', height=0)
                st.toast(f"Mengarahkan ke berkas {chosen_task.get('nomor_opb')}...", icon="🎯")
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    # ================= EXECUTIVE DASHBOARD & BUDGET PER DIVISI =================
    st.markdown("### 📊 Dashboard Monitoring & Budgeting Divisi")

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
    budget_summary = calculate_budget_summary(st.session_state["db_opb"])

    if total_opb > 0:
        df_opb = pd.DataFrame(st.session_state["db_opb"])
        if "status" not in df_opb.columns:
            df_opb["status"] = "1. Penawaran Purchasing"
        if "harga_estimasi" not in df_opb.columns:
            df_opb["harga_estimasi"] = 0

        total_selesai = len(df_opb[df_opb["status"] == "8. Selesai"])
        total_proses = total_opb - total_selesai
        total_anggaran = df_opb["harga_estimasi"].fillna(0).sum()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="kpi-card kpi-blue"><div class="kpi-title">Total Permintaan</div><div class="kpi-value">{total_opb} OPB</div><div class="kpi-sub" style="color:#2563eb;">📂 Seluruh Berkas</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="kpi-card kpi-amber"><div class="kpi-title">Dalam Process</div><div class="kpi-value" style="color:#d97706;">{total_proses} OPB</div><div class="kpi-sub" style="color:#d97706;">⏳ On Progress</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="kpi-card kpi-emerald"><div class="kpi-title">Selesai</div><div class="kpi-value" style="color:#059669;">{total_selesai} OPB</div><div class="kpi-sub" style="color:#059669;">✅ Verified</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="kpi-card kpi-purple"><div class="kpi-title">Total Anggaran Transaksi</div><div class="kpi-value" style="color:#7c3aed; font-size:18px;">Rp {total_anggaran:,.0f}</div><div class="kpi-sub" style="color:#7c3aed;">💰 Realisasi Anggaran</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if role != "Engineering":
            with st.expander("💳 **RINCIAN BUDGET & SISA ANGGARAN PER DIVISI (ALOKASI @ Rp 1 MILIAR)**", expanded=True):
                b_cols = st.columns(len(budget_summary))
                for idx, (div_name, b_info) in enumerate(budget_summary.items()):
                    with b_cols[idx]:
                        st.markdown(f"**{div_name}**")
                        st.caption(f"Pagu: Rp {b_info['pagu_awal']:,}")
                        st.caption(f"Terpakai: Rp {b_info['terpakai']:,}")
                        sisa_color = "green" if b_info['sisa'] > 0 else "red"
                        st.markdown(f"<span style='color:{sisa_color}; font-weight:bold; font-size:12px;'>Sisa: Rp {b_info['sisa']:,}</span>", unsafe_allow_html=True)

        if role in ["Finance", "P3SRS"]:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("📊 **RINCIAN MUTASI POTONGAN ANGGARAN & EKSPOR EXCEL (KHUSUS FINANCE & P3SRS)**", expanded=True):
                items_potongan = [
                    x for x in st.session_state["db_opb"]
                    if x.get("status") in [
                        "6. Serah Terima Barang (Purchasing -> Engineering)",
                        "7. Verifikasi Penerimaan Barang (Engineering)",
                        "8. Selesai",
                    ]
                ]

                if items_potongan:
                    rows = []
                    for item in items_potongan:
                        last_date = "-"
                        if item.get("timeline"):
                            last_date = item["timeline"][-1].get("waktu", "-")

                        rows.append({
                            "No OPB": item.get("nomor_opb", "-"),
                            "Divisi Pemohon": item.get("divisi", "-"),
                            "Rincian Barang/Pengajuan": item.get("nama_barang", "-"),
                            "Vendor": item.get("vendor", "-"),
                            "Nilai Potongan (Rp)": item.get("harga_estimasi", 0),
                            "Status": item.get("status", "-"),
                            "Tanggal Disetujui": last_date
                        })

                    df_potongan = pd.DataFrame(rows)

                    st.dataframe(
                        df_potongan.style.format({"Nilai Potongan (Rp)": "Rp {:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

                    col_exp1, col_exp2 = st.columns([1, 4])
                    with col_exp1:
                        excel_data = convert_df_to_excel(df_potongan)
                        st.download_button(
                            label="📥 Export Ke Excel (.xlsx)",
                            data=excel_data,
                            file_name=f"Laporan_Potongan_Budget_P3SRS_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )
                    with col_exp2:
                        csv_data = df_potongan.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📄 Export Ke CSV",
                            data=csv_data,
                            file_name=f"Laporan_Potongan_Budget_P3SRS_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                        )
                else:
                    st.info("ℹ️ Belum ada pengajuan OPB/IOM yang disetujui (memotong budget).")

        st.markdown("<br>", unsafe_allow_html=True)

        col_dash1, col_dash2 = st.columns([1.3, 1])

        with col_dash1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.markdown("##### 📌 Progress Live Status & Timeline Berkas")
            st.markdown("<br>", unsafe_allow_html=True)
            
            opb_options = {
                f"[{item.get('nomor_opb', '-')}] — Divisi: {item.get('divisi','IT')} | Status: {item.get('status', '1. Penawaran Purchasing')}": item 
                for item in st.session_state["db_opb"]
            }
            
            selected_opb_label = st.selectbox(
                "🔍 Pilih Dokumen OPB untuk Dilihat Detailnya:",
                options=list(opb_options.keys())
            )
            
            if selected_opb_label:
                selected_item = opb_options[selected_opb_label]
                status_curr = selected_item.get("status") or "1. Penawaran Purchasing"

                if "Revisi" in str(status_curr):
                    prog_pct = 25
                elif status_curr in TAHAPAN_OPB:
                    step_idx = TAHAPAN_OPB.index(status_curr) + 1
                    prog_pct = int((step_idx / len(TAHAPAN_OPB)) * 100)
                else:
                    prog_pct = 0

                harga_est = selected_item.get('harga_estimasi', 0) or 0
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"**Urgensi:** `{selected_item.get('urgensi','Normal')}`")
                c_a, c_b = st.columns([4, 1])
                with c_a:
                    st.progress(prog_pct)
                with c_b:
                    st.caption(f"**{prog_pct}%**")
                
                st.markdown(f"📦 **Daftar Barang:** {selected_item.get('nama_barang', '-')}")
                st.caption(f"📍 Status: `{status_curr}` | 💰 Est Biaya: **Rp {harga_est:,}**")

                render_download_buttons(selected_item, key_prefix="single_select_dl")
                
                mailto_link = generate_outlook_mailto_link(selected_item)
                st.markdown(f'<a href="{mailto_link}" target="_blank" style="display:inline-block; background:#0284c7; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:bold; margin-top:8px;">📧 Kirim Auto Email (Outlook)</a>', unsafe_allow_html=True)

                timeline_list = selected_item.get("timeline", [])
                st.markdown("<br><h6>📜 Jejak Timeline Verifikasi:</h6>", unsafe_allow_html=True)
                render_enhanced_timeline(timeline_list)

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
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("💡 **Dashboard Masih Kosong:** Belum ada data pengajuan OPB.")

    st.markdown("---")
    st.markdown('<div id="anchor-kelola-opb"></div>', unsafe_allow_html=True)

    # ==================== MODUL USER PANELS ====================

    # 1. ROLE ENGINEERING
    if role == "Engineering":
        st.header("🔧 Panel Kerja Engineering")
        tab1, tab2 = st.tabs(["📝 Buat Form OPB Baru", "📦 Verifikasi & Tanda Tangan Penerimaan Barang (BAST)"])

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("Pengajuan OPB Baru")
            
            divisi_pilihan = st.selectbox("Divisi Pemohon", DIVISI_LIST, key="select_divisi_pemohon")
            budget_div_info = budget_summary.get(divisi_pilihan, {"sisa": 1_000_000_000})
            st.info(f"💰 **Sisa Budget Terkini Divisi {divisi_pilihan}:** Rp {budget_div_info['sisa']:,}")

            next_number = len(st.session_state["db_opb"]) + 1
            code_div = divisi_pilihan.upper().replace(" ", "")
            nomor_opb_auto = f"OPB/{code_div}/{next_number:03d}"

            st.text_input("Nomor OPB (Otomatis)", value=nomor_opb_auto, disabled=True)

            with st.form(key="form_opb_engineering", clear_on_submit=True):
                urgensi = st.radio(
                    "Tingkat Urgensi / Jenis OPB",
                    options=[
                        "🔴 Darurat (1x24 Jam)",
                        "🟠 Prioritas (3x24 Jam)",
                        "🟢 Medium (5x24 Jam)",
                        "⚪ Normal (7x24 Jam)"
                    ],
                    horizontal=True
                )
                nama_barang = st.text_area("Detail Pengajuan Barang", placeholder="Misal: 1 RAM, 2 SSD...")
                keterangan = st.text_area("Alasan Kebutuhan & Spesifikasi")
                file_opb = st.file_uploader("Unggah Dokumen Lampiran OPB/BA", type=["pdf", "docx", "xlsx", "jpg", "png"])

                submit = st.form_submit_button("🚀 Submit & Kirim OPB ke Purchasing", type="primary", use_container_width=True)

                if submit:
                    if not nama_barang.strip():
                        st.error("Detail pengajuan barang tidak boleh kosong!")
                    else:
                        file_data_b64 = None
                        file_name_val = None
                        if file_opb is not None:
                            file_bytes = file_opb.read()
                            file_data_b64 = base64.b64encode(file_bytes).decode("utf-8")
                            file_name_val = file_opb.name

                        new_item = {
                            "nomor_opb": nomor_opb_auto,
                            "divisi": divisi_pilihan,
                            "urgensi": urgensi,
                            "nama_barang": nama_barang,
                            "jumlah": 1,
                            "keterangan": keterangan,
                            "status": "1. Penawaran Purchasing",
                            "harga_estimasi": 0,
                            "vendor": "-",
                            "file_opb_data": file_data_b64,
                            "file_opb_name": file_name_val,
                            "file_iom_data": None,
                            "file_iom_name": None,
                            "file_bast_data": None,
                            "file_bast_name": None,
                            "catatan_bm": "-",
                            "catatan_finance": "-",
                            "catatan_p3srs": "-",
                            "timeline": []
                        }
                        sig_eng = generate_digital_signature("Engineering", user_info["name"], nomor_opb_auto)
                        catat_log(new_item, f"OPB baru dibuat oleh {user_info['name']} ({divisi_pilihan}).", digital_sig=sig_eng)
                        
                        res = save_database(new_item, is_new=True)
                        if res is not None:
                            st.success("✅ OPB Berhasil Disubmit & Dikirim ke Purchasing!")
                            st.session_state["db_opb"] = load_database()
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("📦 Serah Terima Barang Masuk dari Purchasing")
            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "7. Verifikasi Penerimaan Barang (Engineering)"]
            if not items:
                st.info("Tidak ada barang yang menunggu verifikasi penerimaan.")
            for item in items:
                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
                with st.expander(f"📦 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')}")
                    render_download_buttons(item, key_prefix="eng_tab2")
                    render_signature_pad(f"eng_rcv_{item.get('id', 0)}")

                    if st.button(f"✅ Konfirmasi & Tanda Tangan BAST", type="primary", use_container_width=True):
                        sig_rcv = generate_digital_signature("Engineering (Penerima)", user_info["name"], item.get("nomor_opb", "OPB"))
                        item["status"] = "8. Selesai"
                        catat_log(item, f"Barang diterima oleh {user_info['name']}. BAST Ditandatangani.", digital_sig=sig_rcv)
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. ROLE PURCHASING
    elif role == "Purchasing":
        st.header("🛒 Panel Kerja Purchasing")
        tab1, tab2, tab3 = st.tabs(["1. Input Penawaran Harga", "2. Buat & Unggah IOM", "3. Serah Terima Barang ke Engineering"])

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("OPB Masuk (Perlu Penawaran & Harga Vendor)")
            
            items = [
                x for x in st.session_state["db_opb"]
                if str(x.get("status")).strip() in ["1. Penawaran Purchasing", "Revisi BM (OPB)"]
                or not x.get("status")
            ]

            if not items:
                st.info("Tidak ada tugas penawaran barang saat ini.")
            for item in items:
                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
                item_id = item.get("id", 0)
                with st.expander(f"📌 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
                    st.write(f"**Divisi Pemohon:** {item.get('divisi','IT')} | **Urgensi:** {item.get('urgensi','Normal')}")
                    st.write(f"**Detail:** {item.get('nama_barang', '-')}")
                    render_download_buttons(item, key_prefix=f"pur_tab1_{item_id}")

                    st.divider()
                    with st.form(key=f"form_pur_input_{item_id}"):
                        vendor_input = st.text_input("Nama Vendor/Pemasok Pilihan", value=item.get("vendor", "-"))
                        harga_input = st.number_input("Estimasi Total Harga (Rp)", min_value=0, value=int(item.get("harga_estimasi", 0)))

                        div_item = item.get('divisi', 'IT')
                        sisa_skrg = budget_summary.get(div_item, {}).get('sisa', 1_000_000_000)
                        sisa_setelah = sisa_skrg - harga_input
                        st.caption(f"💡 **Simulasi Budget Divisi {div_item}:** Sisa Awal: Rp {sisa_skrg:,} → **Sisa Setelah Potongan OPB Ini: Rp {sisa_setelah:,}**")

                        submit_pur = st.form_submit_button("Kirim ke BM untuk Review", type="primary", use_container_width=True)

                        if submit_pur:
                            sig_pur = generate_digital_signature("Purchasing", user_info["name"], item.get("nomor_opb", "OPB"))
                            item["vendor"] = vendor_input
                            item["harga_estimasi"] = int(harga_input)
                            item["status"] = "2. Review BM"
                            catat_log(item, f"Purchasing menentukan vendor ({vendor_input}) & harga Rp {harga_input:,}.", digital_sig=sig_pur)
                            
                            res = save_database(item, is_new=False)
                            if res is not None:
                                st.session_state["target_focus_id"] = None
                                st.success("📩 Berhasil dikirim ke BM!")
                                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("OPB Disetujui BM -> Buat & Upload IOM")
            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() in ["3. Pembuatan IOM (Purchasing)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
            if not items:
                st.info("Tidak ada IOM yang perlu dibuat/direvisi.")
            for item in items:
                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
                item_id = item.get("id", 0)
                with st.expander(f"📑 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')}")
                    render_download_buttons(item, key_prefix=f"pur_tab2_{item_id}")

                    st.divider()
                    file_iom = st.file_uploader("Unggah Draft Dokumen IOM Asli", type=["pdf", "docx", "xlsx"], key=f"fiom_{item_id}")
                    if st.button("Kirim Berkas IOM ke Finance", key=f"btn_p2_{item_id}", type="primary", use_container_width=True):
                        if file_iom:
                            iom_bytes = file_iom.read()
                            item["file_iom_data"] = base64.b64encode(iom_bytes).decode("utf-8")
                            item["file_iom_name"] = file_iom.name

                            sig_pur_iom = generate_digital_signature("Purchasing (IOM Draft)", user_info["name"], item.get("nomor_opb", "OPB"))
                            item["status"] = "4. Review Finance"
                            catat_log(item, "Purchasing mengunggah draft IOM ke Finance.", digital_sig=sig_pur_iom)
                            save_database(item, is_new=False)
                            st.session_state["target_focus_id"] = None
                            st.rerun()
                        else:
                            st.warning("Silakan unggah file IOM terlebih dahulu.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.subheader("🤝 Serah Terima Barang & Upload BAST ke Engineering")
            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() in ["6. Pembelian Barang (Purchasing)", "6. Serah Terima Barang (Purchasing -> Engineering)"]]
            if not items:
                st.info("Belum ada barang yang perlu diserahterimakan.")
            for item in items:
                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
                item_id = item.get("id", 0)
                with st.expander(f"💳 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')}")
                    render_download_buttons(item, key_prefix=f"pur_tab3_{item_id}")

                    st.divider()
                    file_bast = st.file_uploader("Unggah BAST Asli", type=["pdf", "jpg", "png", "docx"], key=f"bast_file_{item_id}")
                    render_signature_pad(f"pur_bast_{item_id}")

                    if st.button("🚚 Serahkan Barang & BAST ke Engineering", key=f"btn_p3_{item_id}", type="primary", use_container_width=True):
                        if file_bast:
                            bast_bytes = file_bast.read()
                            item["file_bast_data"] = base64.b64encode(bast_bytes).decode("utf-8")
                            item["file_bast_name"] = file_bast.name

                        sig_handover = generate_digital_signature("Purchasing (Penyerah)", user_info["name"], item.get("nomor_opb", "OPB"))
                        item["status"] = "7. Verifikasi Penerimaan Barang (Engineering)"
                        catat_log(item, f"Purchasing menyerahkan fisik barang & BAST ke Engineering.", digital_sig=sig_handover)
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 3. ROLE BUILDING MANAGER
    elif role == "BM (Building Manager)":
        st.header("👔 Panel Building Manager (BM)")
        tab1, tab2 = st.tabs(["Review OPB (Awal)", "Approval Final IOM"])

        with tab1:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "2. Review BM"]
            if not items:
                st.info("Tidak ada OPB baru menunggu persetujuan.")
            for item in items:
                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
                item_id = item.get("id", 0)
                with st.expander(f"🧐 Review OPB: {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')} | **Estimasi:** Rp {item.get('harga_estimasi', 0):,}")
                    render_download_buttons(item, key_prefix=f"bm_tab1_{item_id}")

                    st.divider()
                    render_signature_pad(f"bm1_sig_{item_id}")
                    catatan = st.text_input("Catatan / Alasan jika Minta Revisi", key=f"c_bm1_{item_id}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Setujui & Tanda Tangan OPB", key=f"app_bm1_{item_id}", type="primary", use_container_width=True):
                            sig_bm = generate_digital_signature("Building Manager", user_info["name"], item.get("nomor_opb", "OPB"))
                            item["status"] = "3. Pembuatan IOM (Purchasing)"
                            catat_log(item, "BM menyetujui OPB. Diteruskan ke Purchasing.", digital_sig=sig_bm)
                            save_database(item, is_new=False)
                            st.session_state["target_focus_id"] = None
                            st.rerun()
                    with col2:
                        if st.button("❌ Tolak / Minta Revisi", key=f"rej_bm1_{item_id}", use_container_width=True):
                            item["catatan_bm"] = catatan
                            item["status"] = "Revisi BM (OPB)"
                            catat_log(item, f"BM meminta revisi OPB: {catatan}")
                            save_database(item, is_new=False)
                            st.session_state["target_focus_id"] = None
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "5. Approval Akhir (BM & P3SRS)"]
            if not items:
                st.info("Tidak ada IOM menunggu persetujuan final.")
            for item in items:
                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
                item_id = item.get("id", 0)
                with st.expander(f"📑 Approval IOM: {item.get('nomor_opb', '-')}", expanded=is_expanded):
                    render_download_buttons(item, key_prefix=f"bm_tab2_{item_id}")
                    render_signature_pad(f"bm2_sig_{item_id}")
                    if st.button("✅ Approve & Tanda Tangan IOM Final (BM)", key=f"app_bm2_{item_id}", type="primary", use_container_width=True):
                        sig_bm_iom = generate_digital_signature("Building Manager (IOM Final)", user_info["name"], item.get("nomor_opb", "OPB"))
                        catat_log(item, "BM menyetujui IOM Final.", digital_sig=sig_bm_iom)
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # 4. ROLE FINANCE
    elif role == "Finance":
        st.header("💰 Panel Finance & Budgeting")
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "4. Review Finance"]
        if not items:
            st.info("Tidak ada IOM yang membutuhkan verifikasi Finance saat ini.")
        for item in items:
            is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
            item_id = item.get("id", 0)
            with st.expander(f"💵 Review IOM: {item.get('nomor_opb', '-')}", expanded=is_expanded):
                div_item = item.get("divisi", "IT")
                b_info = budget_summary.get(div_item, {})
                st.write(f"**Divisi Pemohon:** {div_item} | **Nilai:** Rp {item.get('harga_estimasi', 0):,}")
                render_download_buttons(item, key_prefix=f"fin_{item_id}")

                render_signature_pad(f"fin_sig_{item_id}")
                catatan = st.text_input("Catatan", key=f"c_fin_{item_id}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Verifikasi Budget", key=f"app_fin_{item_id}", type="primary", use_container_width=True):
                        sig_fin = generate_digital_signature("Finance Officer", user_info["name"], item.get("nomor_opb", "OPB"))
                        item["status"] = "5. Approval Akhir (BM & P3SRS)"
                        catat_log(item, f"Finance memverifikasi budget Divisi {div_item}.", digital_sig=sig_fin)
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
                with col2:
                    if st.button("❌ Minta Revisi Budget", key=f"rej_fin_{item_id}", use_container_width=True):
                        item["catatan_finance"] = catatan
                        item["status"] = "Revisi Finance"
                        catat_log(item, f"Finance meminta revisi budget: {catatan}")
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. ROLE P3SRS
    elif role == "P3SRS":
        st.header("🏛️ Panel P3SRS (Approval Akhir)")
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "5. Approval Akhir (BM & P3SRS)"]
        if not items:
            st.info("Tidak ada IOM yang menunggu persetujuan P3SRS.")
        for item in items:
            is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
            item_id = item.get("id", 0)
            with st.expander(f"⚖️ Persetujuan Final: {item.get('nomor_opb', '-')}", expanded=is_expanded):
                div_item = item.get("divisi", "IT")
                harga_nilai = item.get("harga_estimasi", 0)
                render_download_buttons(item, key_prefix=f"p3srs_{item_id}")

                render_signature_pad(f"p3srs_sig_{item_id}")
                catatan = st.text_input("Catatan", key=f"c_p3srs_{item_id}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ ACC & Potong Budget Divisi", key=f"app_p3srs_{item_id}", type="primary", use_container_width=True):
                        sig_p3srs = generate_digital_signature("Pengurus P3SRS", user_info["name"], item.get("nomor_opb", "OPB"))
                        item["status"] = "6. Serah Terima Barang (Purchasing -> Engineering)"
                        catat_log(item, f"P3SRS menyetujui IOM Final. Budget Divisi {div_item} terpotong Rp {harga_nilai:,}.", digital_sig=sig_p3srs)
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
                with col2:
                    if st.button("❌ Minta Revisi", key=f"rej_p3srs_{item_id}", use_container_width=True):
                        item["catatan_p3srs"] = catatan
                        item["status"] = "Revisi BM/P3SRS (IOM)"
                        catat_log(item, f"P3SRS meminta revisi IOM: {catatan}")
                        save_database(item, is_new=False)
                        st.session_state["target_focus_id"] = None
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
