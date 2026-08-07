[cite: 4]import base64
[cite: 4]import hashlib
[cite: 4]import io
[cite: 4]import json
[cite: 4]import os
[cite: 4]from datetime import datetime
[cite: 4]import extra_streamlit_components as stx
[cite: 4]import pandas as pd
[cite: 4]import plotly.express as px
[cite: 4]import pytz
[cite: 4]import requests
[cite: 4]import streamlit as st
[cite: 4]import streamlit.components.v1 as components
[cite: 4]from streamlit_autorefresh import st_autorefresh
[cite: 4]from supabase import Client, create_client

[cite: 4]# --- 1. KONFIGURASI HALAMAN ---
[cite: 4]st.set_page_config(
[cite: 4]    page_title="Sistem Flow OPB & IOM - P3SRS",
[cite: 4]    page_icon="🏢",
[cite: 4]    layout="wide",
[cite: 4]    initial_sidebar_state="auto",
[cite: 4])

[cite: 4]# --- 1.1 AUTO REFRESH (Polling Realtime Data tiap 5 detik) ---
[cite: 4]st_autorefresh(interval=5000, limit=None, key="opb_datarefresh")

[cite: 4]# --- INISIALISASI SUPABASE CLIENT ---
[cite: 4]SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
[cite: 4]SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

[cite: 4]if not SUPABASE_URL or not SUPABASE_KEY:
[cite: 4]    st.error("⚠️ Supabase Credentials belum diatur di Secrets/Environment Variables!")

[cite: 4]supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
[cite: 4]BUCKET_NAME = "opb-files"

[cite: 4]# --- LIST DIVISI BARU & BUDGET 1 MILIAR PER DIVISI ---
[cite: 4]DIVISI_LIST = [
[cite: 4]    "IT",
[cite: 4]    "Mekanikal",
[cite: 4]    "Civil",
[cite: 4]    "Plumbing",
[cite: 4]    "Elektrikal",
[cite: 4]    "Lift",
[cite: 4]    "AC",
[cite: 4]]

[cite: 4]INITIAL_BUDGETS = {div: 1_000_000_000 for div in DIVISI_LIST}

[cite: 4]# --- 2. FUNGSI PERSISTENSI DATA (SUPABASE STORAGE & DB) ---
[cite: 4]def upload_file_to_supabase(file_bytes, file_name, folder="opb"):
[cite: 4]    """Mengunggah file ke Supabase Storage dan mengembalikan URL Publiknya."""
[cite: 4]    if not file_bytes:
[cite: 4]        return None
[cite: 4]    try:
[cite: 4]        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
[cite: 4]        safe_filename = f"{folder}/{timestamp}_{file_name.replace(' ', '_')}"

[cite: 4]        supabase.storage.from_(BUCKET_NAME).upload(
[cite: 4]            file=file_bytes,
[cite: 4]            path=safe_filename,
[cite: 4]            file_options={"content-type": "application/octet-stream"},
[cite: 4]        )

[cite: 4]        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(
[cite: 4]            safe_filename
[cite: 4]        )
[cite: 4]        return public_url
[cite: 4]    except Exception as e:
[cite: 4]        st.error(f"Gagal upload file ke Supabase Storage: {e}")
[cite: 4]        return None


[cite: 4]def load_database():
[cite: 4]    """Membaca seluruh data OPB dari tabel Supabase dengan Sanitasi Data."""
[cite: 4]    try:
[cite: 4]        response = (
[cite: 4]            supabase.table("opb_data")
[cite: 4]            .select("*")
[cite: 4]            .order("id", desc=False)
[cite: 4]            .execute()
[cite: 4]        )
[cite: 4]        data = response.data
        
[cite: 4]        for item in data:
[cite: 4]            if isinstance(item.get("timeline"), str):
[cite: 4]                try:
[cite: 4]                    item["timeline"] = json.loads(item["timeline"])
[cite: 4]                except Exception:
[cite: 4]                    item["timeline"] = []
[cite: 4]            elif item.get("timeline") is None:
[cite: 4]                item["timeline"] = []

[cite: 4]            if not item.get("status"):
[cite: 4]                item["status"] = "1. Penawaran Purchasing"

[cite: 4]            if not item.get("divisi"):
[cite: 4]                item["divisi"] = "IT"
[cite: 4]            if not item.get("urgensi"):
[cite: 4]                item["urgensi"] = "Normal"
[cite: 4]            if item.get("harga_estimasi") is None:
[cite: 4]                item["harga_estimasi"] = 0
[cite: 4]            if not item.get("vendor"):
[cite: 4]                item["vendor"] = "-"

[cite: 4]        return data
[cite: 4]    except Exception as e:
[cite: 4]        st.error(f"Gagal memuat database dari Supabase: {e}")
[cite: 4]        return []


[cite: 4]def save_database(item_data, is_new=False):
[cite: 4]    """Menyimpan item ke Supabase dengan Debugging Error Terperinci."""
[cite: 4]    try:
[cite: 4]        db_payload = {
[cite: 4]            "nama_barang": str(item_data.get("nama_barang", "")),
[cite: 4]            "nomor_opb": str(item_data.get("nomor_opb", "")),
[cite: 4]            "jumlah": int(item_data.get("jumlah", 1)),
[cite: 4]            "keterangan": str(item_data.get("keterangan", "") or ""),
[cite: 4]            "divisi": str(item_data.get("divisi", "IT")),
[cite: 4]            "urgensi": str(item_data.get("urgensi", "Normal")),
[cite: 4]            "status": str(item_data.get("status", "1. Penawaran Purchasing")),
[cite: 4]            "harga_estimasi": int(item_data.get("harga_estimasi", 0) or 0),
[cite: 4]            "vendor": str(item_data.get("vendor", "-")),
[cite: 4]            "file_opb_url": item_data.get("file_opb_url"),
[cite: 4]            "file_iom_url": item_data.get("file_iom_url"),
[cite: 4]            "file_bast_url": item_data.get("file_bast_url"),
[cite: 4]            "catatan_bm": str(item_data.get("catatan_bm", "-")),
[cite: 4]            "catatan_finance": str(item_data.get("catatan_finance", "-")),
[cite: 4]            "catatan_p3srs": str(item_data.get("catatan_p3srs", "-")),
[cite: 4]            "timeline": json.dumps(item_data.get("timeline", [])),
[cite: 4]        }

[cite: 4]        if not is_new and "id" in item_data:
[cite: 4]            db_payload["id"] = int(item_data["id"])

[cite: 4]        if is_new:
[cite: 4]            response = supabase.table("opb_data").insert(db_payload).execute()
[cite: 4]        else:
[cite: 4]            response = (
[cite: 4]                supabase.table("opb_data")
[cite: 4]                .update(db_payload)
[cite: 4]                .eq("id", db_payload["id"])
[cite: 4]                .execute()
[cite: 4]            )

[cite: 4]        return response
[cite: 4]    except Exception as e:
[cite: 4]        st.error(f"❌ Gagal Database Supabase: {e}")
[cite: 4]        return None


[cite: 4]def calculate_budget_summary(data_list):
[cite: 4]    budget_usage = {div: 0 for div in INITIAL_BUDGETS}
[cite: 4]    for item in data_list:
[cite: 4]        div = item.get("divisi", "IT")
[cite: 4]        if item.get("status") in [
[cite: 4]            "6. Serah Terima Barang (Purchasing -> Engineering)",
[cite: 4]            "7. Verifikasi Penerimaan Barang (Engineering)",
[cite: 4]            "8. Selesai",
[cite: 4]        ]:
[cite: 4]            harga = item.get("harga_estimasi", 0) or 0
[cite: 4]            if div in budget_usage:
[cite: 4]                budget_usage[div] += harga

[cite: 4]    summary = {}
[cite: 4]    for div, initial in INITIAL_BUDGETS.items():
[cite: 4]        terpakai = budget_usage.get(div, 0)
[cite: 4]        sisa = initial - terpakai
[cite: 4]        summary[div] = {
[cite: 4]            "pagu_awal": initial,
[cite: 4]            "terpakai": terpakai,
[cite: 4]            "sisa": sisa
[cite: 4]        }
[cite: 4]    return summary


[cite: 4]def convert_df_to_excel(df):
[cite: 4]    output = io.BytesIO()
[cite: 4]    with pd.ExcelWriter(output, engine='openpyxl') as writer:
[cite: 4]        df.to_excel(writer, index=False, sheet_name='Detail Potongan Budget')
[cite: 4]    processed_data = output.getvalue()
[cite: 4]    return processed_data


[cite: 4]# --- 3. RESPONSIVE CUSTOM CSS ---
[cite: 4]st.markdown(
[cite: 4]    """
[cite: 4]    <style>
[cite: 4]    .stApp { background: #f8fafc; }
[cite: 4]    .main-header {
[cite: 4]        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
[cite: 4]        padding: 24px 28px; border-radius: 18px; color: white; margin-bottom: 20px;
[cite: 4]        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
[cite: 4]    }
[cite: 4]    .main-header h1 { color: #ffffff !important; font-weight: 800; letter-spacing: -0.5px; margin: 0; font-size: 26px; }
[cite: 4]    .main-header p { color: #c7d2fe; margin-top: 6px; margin-bottom: 0; font-size: 13px; }
    
[cite: 4]    .kpi-card {
[cite: 4]        background: white; border-radius: 16px; padding: 18px 20px;
[cite: 4]        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
[cite: 4]        position: relative; overflow: hidden; transition: all 0.3s ease; margin-bottom: 10px;
[cite: 4]    }
[cite: 4]    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.08); }
[cite: 4]    .kpi-blue { border-top: 4px solid #3b82f6; }
[cite: 4]    .kpi-amber { border-top: 4px solid #f59e0b; }
[cite: 4]    .kpi-emerald { border-top: 4px solid #10b981; }
[cite: 4]    .kpi-purple { border-top: 4px solid #8b5cf6; }
    
[cite: 4]    .kpi-title { color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
[cite: 4]    .kpi-value { color: #0f172a; font-size: 22px; font-weight: 800; margin-top: 4px; }
[cite: 4]    .kpi-sub { font-size: 11px; font-weight: 600; margin-top: 4px; }
    
[cite: 4]    .user-profile-card {
[cite: 4]        background: white; padding: 14px 18px; border-radius: 14px;
[cite: 4]        border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 15px;
[cite: 4]    }
[cite: 4]    .role-badge {
[cite: 4]        background: #e0e7ff; color: #3730a3; padding: 3px 10px;
[cite: 4]        border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 5px;
[cite: 4]    }
    
[cite: 4]    .notif-box {
[cite: 4]        background: linear-gradient(135deg, #fffbe3 0%, #fef3c7 100%);
[cite: 4]        border-left: 5px solid #f59e0b; color: #78350f; padding: 16px 20px;
[cite: 4]        border-radius: 16px; margin-bottom: 18px; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.12);
[cite: 4]    }
    
[cite: 4]    .content-box {
[cite: 4]        background: white; border-radius: 16px; padding: 20px;
[cite: 4]        border: 1px solid #e2e8f0; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.03); margin-bottom: 20px;
[cite: 4]    }

[cite: 4]    .digital-signature-badge {
[cite: 4]        display: inline-block; 
[cite: 4]        background: #ecfdf5; 
[cite: 4]        border: 1px dashed #10b981;
[cite: 4]        color: #047857; 
[cite: 4]        font-size: 10.5px; 
[cite: 4]        padding: 3px 8px; 
[cite: 4]        border-radius: 6px; 
[cite: 4]        margin-top: 6px; 
[cite: 4]        font-family: monospace; 
[cite: 4]        word-break: break-all;
[cite: 4]    }
[cite: 4]    </style>
[cite: 4]""",
[cite: 4]    unsafe_allow_html=True,
[cite: 4])

[cite: 4]# --- 4. DATABASE USER ---
[cite: 4]USERS = {
[cite: 4]    "engineering": {"password": "eng123", "name": "Tim Engineering", "role": "Engineering"},
[cite: 4]    "purchasing": {"password": "pur123", "name": "Tim Purchasing", "role": "Purchasing"},
[cite: 4]    "bm": {"password": "bm123", "name": "Building Manager", "role": "BM (Building Manager)"},
[cite: 4]    "finance": {"password": "fin123", "name": "Tim Finance", "role": "Finance"},
[cite: 4]    "p3srs": {"password": "p3srs123", "name": "Pengurus P3SRS", "role": "P3SRS"},
[cite: 4]}

[cite: 4]# --- 5. LOG & TANDA TANGAN DIGITAL ---
[cite: 4]def generate_digital_signature(user_role, user_name, doc_id):
[cite: 4]    wib = pytz.timezone("Asia/Jakarta")
[cite: 4]    waktu = datetime.now(wib).strftime("%Y-%m-%d %H:%M:%S")
[cite: 4]    raw_data = f"{doc_id}-{user_role}-{user_name}-{waktu}"
[cite: 4]    sig_hash = hashlib.sha256(raw_data.encode()).hexdigest()[:12].upper()
[cite: 4]    return {
[cite: 4]        "signed_by": user_name,
[cite: 4]        "role": user_role,
[cite: 4]        "timestamp": waktu,
[cite: 4]        "hash": f"DS-P3SRS-{sig_hash}",
[cite: 4]    }

[cite: 4]def catat_log(item, pesan, digital_sig=None):
[cite: 4]    wib = pytz.timezone("Asia/Jakarta")
[cite: 4]    waktu_sekarang = datetime.now(wib).strftime("%d/%m/%Y %H:%M:%S")
[cite: 4]    log_entry = {"waktu": waktu_sekarang, "pesan": pesan}
[cite: 4]    if digital_sig:
[cite: 4]        log_entry["signature"] = digital_sig
[cite: 4]    if "timeline" not in item or not isinstance(item["timeline"], list):
[cite: 4]        item["timeline"] = []
[cite: 4]    item["timeline"].append(log_entry)

[cite: 4]def render_enhanced_timeline(timeline_data):
[cite: 4]    """
[cite: 4]    Merender timeline vertikal modern yang interaktif, bersih, 
[cite: 4]    dilengkapi stempel waktu, aktor, dan penanda visual tanpa risiko terpotong.
[cite: 4]    """
[cite: 4]    timeline_css = """
[cite: 4]    <style>
[cite: 4]    .opb-timeline-container {
[cite: 4]        font-family: 'Inter', sans-serif;
[cite: 4]        padding: 5px 10px;
[cite: 4]    }
[cite: 4]    .opb-tl-item {
[cite: 4]        display: flex;
[cite: 4]        position: relative;
[cite: 4]        padding-bottom: 20px;
[cite: 4]    }
[cite: 4]    .opb-tl-item:last-child {
[cite: 4]        padding-bottom: 0;
[cite: 4]    }
[cite: 4]    .opb-tl-item::before {
[cite: 4]        content: '';
[cite: 4]        position: absolute;
[cite: 4]        left: 14px;
[cite: 4]        top: 30px;
[cite: 4]        bottom: 0;
[cite: 4]        width: 2px;
[cite: 4]        background: #e2e8f0;
[cite: 4]    }
[cite: 4]    .opb-tl-item:last-child::before {
[cite: 4]        display: none;
[cite: 4]    }
[cite: 4]    .opb-tl-icon {
[cite: 4]        position: relative;
[cite: 4]        z-index: 2;
[cite: 4]        width: 30px;
[cite: 4]        height: 30px;
[cite: 4]        border-radius: 50%;
[cite: 4]        display: flex;
[cite: 4]        align-items: center;
[cite: 4]        justify-content: center;
[cite: 4]        font-weight: bold;
[cite: 4]        font-size: 11px;
[cite: 4]        flex-shrink: 0;
[cite: 4]        border: 2px solid #fff;
[cite: 4]        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
[cite: 4]    }
[cite: 4]    .icon-done { background: #10b981; color: white; }
[cite: 4]    .icon-active { background: #f59e0b; color: white; box-shadow: 0 0 10px rgba(245, 158, 11, 0.4); }
    
[cite: 4]    .opb-tl-content {
[cite: 4]        background: #f8fafc;
[cite: 4]        border: 1px solid #e2e8f0;
[cite: 4]        border-radius: 10px;
[cite: 4]        padding: 10px 14px;
[cite: 4]        margin-left: 12px;
[cite: 4]        width: 100%;
[cite: 4]        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
[cite: 4]    }
[cite: 4]    .opb-tl-header {
[cite: 4]        display: flex;
[cite: 4]        justify-content: space-between;
[cite: 4]        align-items: center;
[cite: 4]        margin-bottom: 4px;
[cite: 4]    }
[cite: 4]    .opb-tl-title {
[cite: 4]        font-weight: 700;
[cite: 4]        font-size: 12px;
[cite: 4]        color: #1e293b;
[cite: 4]    }
[cite: 4]    .opb-tl-actor {
[cite: 4]        font-size: 10.5px;
[cite: 4]        font-weight: 600;
[cite: 4]        color: #4338ca;
[cite: 4]        background: #e0e7ff;
[cite: 4]        padding: 1px 6px;
[cite: 4]        border-radius: 4px;
[cite: 4]    }
[cite: 4]    .opb-tl-time {
[cite: 4]        font-size: 10px;
[cite: 4]        color: #64748b;
[cite: 4]        margin-bottom: 4px;
[cite: 4]    }
[cite: 4]    .opb-tl-desc {
[cite: 4]        font-size: 11px;
[cite: 4]        color: #334155;
[cite: 4]        line-height: 1.3;
[cite: 4]    }
[cite: 4]    </style>
[cite: 4]    """

[cite: 4]    if not timeline_data:
[cite: 4]        st.caption("Belum ada riwayat aktivitas.")
[cite: 4]        return

[cite: 4]    formatted_steps = []
[cite: 4]    for i, log_entry in enumerate(timeline_data):
[cite: 4]        if isinstance(log_entry, dict):
[cite: 4]            waktu_log = log_entry.get("waktu", "-")
[cite: 4]            pesan_log = log_entry.get("pesan", "-")
[cite: 4]            sig = log_entry.get("signature", {})
[cite: 4]            actor_log = sig.get("role", "Sistem / User") if sig else "Sistem"
[cite: 4]        else:
[cite: 4]            waktu_log = "-"
[cite: 4]            pesan_log = str(log_entry)
[cite: 4]            actor_log = "Sistem"

[cite: 4]        is_last = (i == len(timeline_data) - 1)
[cite: 4]        formatted_steps.append({
[cite: 4]            "step": i + 1,
[cite: 4]            "title": f"Tahap {i+1}",
[cite: 4]            "actor": actor_log,
[cite: 4]            "time": waktu_log,
[cite: 4]            "desc": pesan_log,
[cite: 4]            "status": "active" if is_last else "done"
[cite: 4]        })

[cite: 4]    html_code = f"{timeline_css}<div class='opb-timeline-container'>"

[cite: 4]    for step in formatted_steps:
[cite: 4]        icon_cls = "icon-active" if step["status"] == "active" else "icon-done"
[cite: 4]        sig_badge_html = ""
[cite: 4]        # Cek jika log entry memiliki signature terlampir
[cite: 4]        if isinstance(timeline_data[step["step"]-1], dict) and timeline_data[step["step"]-1].get("signature"):
[cite: 4]            sig = timeline_data[step["step"]-1].get("signature")
[cite: 4]            sig_badge_html = f"""
[cite: 4]            <br><span class="digital-signature-badge">
[cite: 4]                🔏 Signed by <b>{sig.get('signed_by', '-')}</b> ({sig.get('role', '-')}) | {sig.get('hash', '-')}
[cite: 4]            </span>
[cite: 4]            """

[cite: 4]        html_code += f"""
[cite: 4]        <div class="opb-tl-item">
[cite: 4]            <div class="opb-tl-icon {icon_cls}">{step['step']}</div>
[cite: 4]            <div class="opb-tl-content">
[cite: 4]                <div class="opb-tl-header">
[cite: 4]                    <span class="opb-tl-title">{step['title']}</span>
[cite: 4]                    <span class="opb-tl-actor">👤 {step['actor']}</span>
[cite: 4]                </div>
[cite: 4]                <div class="opb-tl-time">🕒 {step['time']}</div>
[cite: 4]                <div class="opb-tl-desc">{step['desc']}{sig_badge_html}</div>
[cite: 4]            </div>
[cite: 4]        </div>
[cite: 4]        """

[cite: 4]    html_code += "</div>"
    
[cite: 4]    # Hitung tinggi dinamis berdasarkan jumlah tahapan agar pas dan tidak ada scrollbar terpotong
[cite: 4]    dynamic_height = max(130, len(timeline_data) * 115)
[cite: 4]    components.html(html_code, height=dynamic_height, scrolling=False)

[cite: 4]def render_download_buttons(item, key_prefix="dl"):
[cite: 4]    col1, col2, col3 = st.columns([1, 1, 1])
[cite: 4]    with col1:
[cite: 4]        if item.get("file_opb_url"):
[cite: 4]            st.markdown(f"[📥 Download OPB]({item['file_opb_url']})")
[cite: 4]        else:
[cite: 4]            resume_text = f"RESUME DOKUMEN OPB\nNomor: {item.get('nomor_opb', '-')}\nDaftar Barang: {item.get('nama_barang', '-')}\nDivisi: {item.get('divisi','IT')}"
[cite: 4]            st.download_button(
[cite: 4]                label=f"📄 Draft OPB",
[cite: 4]                data=resume_text.encode("utf-8"),
[cite: 4]                file_name=f"{str(item.get('nomor_opb', 'OPB')).replace('/', '_')}.txt",
[cite: 4]                mime="text/plain",
[cite: 4]                key=f"{key_prefix}_opb_txt_{item.get('id', 0)}",
[cite: 4]                use_container_width=True,
[cite: 4]            )

[cite: 4]    with col2:
[cite: 4]        if item.get("file_iom_url"):
[cite: 4]            st.markdown(f"[📥 Download IOM]({item['file_iom_url']})")
[cite: 4]        else:
[cite: 4]            st.caption("ℹ️ IOM Belum Ada")

[cite: 4]    with col3:
[cite: 4]        if item.get("file_bast_url"):
[cite: 4]            st.markdown(f"[📦 Download BAST]({item['file_bast_url']})")
[cite: 4]        else:
[cite: 4]            st.caption("ℹ️ BAST Belum Ada")

[cite: 4]def render_signature_pad(key_id):
[cite: 4]    canvas_html = f"""
[cite: 4]    <div style="border:1px dashed #6366f1; padding:8px; border-radius:12px; background:#f8fafc; text-align:center; max-width:100%;">
[cite: 4]        <label style="font-size:12px; font-weight:bold; color:#3730a3; display:block; margin-bottom:6px;">
[cite: 4]            ✍️ Goreskan Tanda Tangan Digital Anda (Touchscreen Ready):
[cite: 4]        </label>
[cite: 4]        <canvas id="sigCanvas_{key_id}" style="border:1px solid #cbd5e1; border-radius:8px; background:#ffffff; cursor:crosshair; touch-action:none; width:100%; height:120px;"></canvas>
[cite: 4]        <br>
[cite: 4]        <button onclick="clearCanvas_{key_id}()" style="margin-top:6px; background:#f1f5f9; border:1px solid #cbd5e1; padding:4px 12px; border-radius:6px; font-size:11px; cursor:pointer;">
[cite: 4]            🗑️ Bersihkan Canvas
[cite: 4]        </button>
[cite: 4]    </div>
[cite: 4]    <script>
[cite: 4]        var canvas_{key_id} = document.getElementById('sigCanvas_{key_id}');
[cite: 4]        var ctx_{key_id} = canvas_{key_id}.getContext('2d');
[cite: 4]        canvas_{key_id}.width = canvas_{key_id}.offsetWidth;
[cite: 4]        canvas_{key_id}.height = canvas_{key_id}.offsetHeight;
[cite: 4]        var drawing_{key_id} = false;

[cite: 4]        function getPos(e) {{
[cite: 4]            var rect = canvas_{key_id}.getBoundingClientRect();
[cite: 4]            var clientX = e.clientX || (e.touches && e.touches[0].clientX);
[cite: 4]            var clientY = e.clientY || (e.touches && e.touches[0].clientY);
[cite: 4]            return {{ x: clientX - rect.left, y: clientY - rect.top }};
[cite: 4]        }}

[cite: 4]        function startDraw(e) {{ drawing_{key_id} = true; ctx_{key_id}.beginPath(); var pos = getPos(e); ctx_{key_id}.moveTo(pos.x, pos.y); }}
[cite: 4]        function moveDraw(e) {{ if (!drawing_{key_id}) return; var pos = getPos(e); ctx_{key_id}.lineTo(pos.x, pos.y); ctx_{key_id}.strokeStyle = '#1e1b4b'; ctx_{key_id}.lineWidth = 2.5; ctx_{key_id}.stroke(); }}
[cite: 4]        function stopDraw() {{ drawing_{key_id} = false; }}

[cite: 4]        canvas_{key_id}.addEventListener('mousedown', startDraw);
[cite: 4]        canvas_{key_id}.addEventListener('mousemove', moveDraw);
[cite: 4]        canvas_{key_id}.addEventListener('mouseup', stopDraw);
[cite: 4]        canvas_{key_id}.addEventListener('touchstart', function(e){{ startDraw(e); e.preventDefault(); }}, false);
[cite: 4]        canvas_{key_id}.addEventListener('touchmove', function(e){{ moveDraw(e); e.preventDefault(); }}, false);
[cite: 4]        canvas_{key_id}.addEventListener('touchend', stopDraw, false);

[cite: 4]        function clearCanvas_{key_id}() {{
[cite: 4]            ctx_{key_id}.clearRect(0, 0, canvas_{key_id}.width, canvas_{key_id}.height);
[cite: 4]        }}
[cite: 4]    </script>
[cite: 4]    """
[cite: 4]    components.html(canvas_html, height=185)

[cite: 4]def cek_notifikasi_user(role):
[cite: 4]    db = st.session_state["db_opb"]
[cite: 4]    pending_items = []

[cite: 4]    if role == "Purchasing":
[cite: 4]        pending_items = [x for x in db if x.get("status") in ["1. Penawaran Purchasing", "3. Pembuatan IOM (Purchasing)", "6. Serah Terima Barang (Purchasing -> Engineering)", "Revisi BM (OPB)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"] or not x.get("status")]
[cite: 4]    elif role == "BM (Building Manager)":
[cite: 4]        pending_items = [x for x in db if x.get("status") in ["2. Review BM", "5. Approval Akhir (BM & P3SRS)"]]
[cite: 4]    elif role == "Finance":
[cite: 4]        pending_items = [x for x in db if x.get("status") == "4. Review Finance"]
[cite: 4]    elif role == "P3SRS":
[cite: 4]        pending_items = [x for x in db if x.get("status") == "5. Approval Akhir (BM & P3SRS)"]
[cite: 4]    elif role == "Engineering":
[cite: 4]        pending_items = [x for x in db if x.get("status") == "7. Verifikasi Penerimaan Barang (Engineering)"]

[cite: 4]    return pending_items


[cite: 4]# --- 6. INITIALIZATION SESSION STATE ---
[cite: 4]st.session_state["db_opb"] = load_database()

[cite: 4]cookie_manager = stx.CookieManager(key="my_cookie_manager")
[cite: 4]user_cookie = cookie_manager.get("opb_p3srs_user")

[cite: 4]if "logged_in" not in st.session_state:
[cite: 4]    st.session_state["logged_in"] = False
[cite: 4]if "user_info" not in st.session_state:
[cite: 4]    st.session_state["user_info"] = None

[cite: 4]if not st.session_state["logged_in"] and user_cookie:
[cite: 4]    st.session_state["logged_in"] = True
[cite: 4]    st.session_state["user_info"] = user_cookie

[cite: 4]if "notif_shown" not in st.session_state:
[cite: 4]    st.session_state["notif_shown"] = False
[cite: 4]if "target_focus_id" not in st.session_state:
[cite: 4]    st.session_state["target_focus_id"] = None


[cite: 4]# ==================== HALAMAN LOGIN ====================
[cite: 4]if not st.session_state["logged_in"]:
[cite: 4]    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])

[cite: 4]    with col_l2:
[cite: 4]        st.markdown("<br>", unsafe_allow_html=True)
[cite: 4]        st.markdown(
[cite: 4]            """
[cite: 4]            <div style='text-align: center; margin-bottom: 20px;'>
[cite: 4]                <h2 style='color: #1e1b4b; font-weight: 800; margin: 0; font-size: 24px;'>Portal OPB & IOM - P3SRS</h2>
[cite: 4]                <p style='color: #64748b; font-size: 13px; margin-top: 5px;'>Sistem Digitalisasi OPB, IOM & Serah Terima Barang Inter-Divisi</p>
[cite: 4]            </div>
[cite: 4]        """,
[cite: 4]            unsafe_allow_html=True,
[cite: 4]        )

[cite: 4]        with st.form("login_form"):
[cite: 4]            st.markdown("##### 🔑 Silakan Login Akun Divisi")
[cite: 4]            username_input = st.text_input("Username", placeholder="engineering, purchasing, bm...")
[cite: 4]            password_input = st.text_input("Password", type="password", placeholder="Masukkan password...")
[cite: 4]            submit_login = st.form_submit_button("🔒 Masuk ke Portal", type="primary", use_container_width=True)

[cite: 4]            if submit_login:
[cite: 4]                user_data = USERS.get(username_input.lower().strip())
[cite: 4]                if user_data and user_data["password"] == password_input:
[cite: 4]                    st.session_state["logged_in"] = True
[cite: 4]                    st.session_state["user_info"] = user_data
[cite: 4]                    st.session_state["notif_shown"] = False
[cite: 4]                    cookie_manager.set("opb_p3srs_user", user_data, key="set_cookie_login")
[cite: 4]                    st.toast("✅ Login Berhasil!", icon="🎉")
[cite: 4]                    st.rerun()
[cite: 4]                else:
[cite: 4]                    st.error("❌ Username atau Password tidak sesuai!")

[cite: 4]        with st.expander("ℹ️ Daftar Akun Login"):
[cite: 4]            st.markdown("""
[cite: 4]            - **Engineering**: `engineering` / `eng123`
[cite: 4]            - **Purchasing**: `purchasing` / `pur123`
[cite: 4]            - **BM**: `bm` / `bm123`
[cite: 4]            - **Finance**: `finance` / `fin123`
[cite: 4]            - **P3SRS**: `p3srs` / `p3srs123`
[cite: 4]            """)

[cite: 4]else:
[cite: 4]    # ==================== APLIKASI UTAMA ====================
[cite: 4]    user_info = st.session_state["user_info"]
[cite: 4]    role = user_info["role"]

[cite: 4]    pending_tasks = cek_notifikasi_user(role)
[cite: 4]    if pending_tasks and not st.session_state["notif_shown"]:
[cite: 4]        st.toast(f"🔔 **Pemberitahuan:** Ada {len(pending_tasks)} tugas baru!", icon="📩")
[cite: 4]        st.session_state["notif_shown"] = True

[cite: 4]    st.sidebar.markdown(
[cite: 4]        f"""
[cite: 4]        <div class="user-profile-card">
[cite: 4]            <h4 style="margin:0; color:#0f172a; font-size:14px; font-weight:700;">👤 {user_info['name']}</h4>
[cite: 4]            <span class="role-badge">{user_info['role']}</span>
[cite: 4]        </div>
[cite: 4]    """,
[cite: 4]        unsafe_allow_html=True,
[cite: 4]    )

[cite: 4]    if pending_tasks:
[cite: 4]        st.sidebar.warning(f"🔔 **{len(pending_tasks)} Tugas Menunggu**")

[cite: 4]    if st.sidebar.button("🚪 Keluar / Logout", use_container_width=True):
[cite: 4]        st.session_state["logged_in"] = False
[cite: 4]        st.session_state["user_info"] = None
[cite: 4]        st.session_state["notif_shown"] = False
[cite: 4]        st.session_state["target_focus_id"] = None
[cite: 4]        cookie_manager.delete("opb_p3srs_user", key="delete_cookie_logout")
[cite: 4]        st.rerun()

[cite: 4]    st.sidebar.markdown("---")

[cite: 4]    st.markdown(
[cite: 4]        f"""
[cite: 4]        <div class="main-header">
[cite: 4]            <h1>📋 Sistem Pengajuan OPB & IOM - P3SRS</h1>
[cite: 4]            <p>Platform Integrasi OPB, IOM & Digital Signature Handover | Hak Akses: <b>{role}</b></p>
[cite: 4]        </div>
[cite: 4]    """,
[cite: 4]        unsafe_allow_html=True,
[cite: 4]    )

[cite: 4]    if pending_tasks:
[cite: 4]        st.markdown(
[cite: 4]            f"""
[cite: 4]            <div class="notif-box">
[cite: 4]                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
[cite: 4]                    <span style="font-size:20px;">🔔</span>
[cite: 4]                    <span style="font-size: 15px; font-weight: 700;">Notifikasi Tugas Masuk ({len(pending_tasks)} Berkas)</span>
[cite: 4]                </div>
[cite: 4]            </div>
[cite: 4]        """,
[cite: 4]            unsafe_allow_html=True,
[cite: 4]        )

[cite: 4]        btn_cols = st.columns(min(len(pending_tasks), 4))
[cite: 4]        for i, item_task in enumerate(pending_tasks):
[cite: 4]            col_idx = i % 4
[cite: 4]            with btn_cols[col_idx]:
[cite: 4]                if st.button(f"👉 {item_task.get('nomor_opb', 'OPB')}", key=f"quick_btn_{item_task.get('id', i)}", type="primary", use_container_width=True):
[cite: 4]                    st.session_state["target_focus_id"] = item_task.get("id")
[cite: 4]                    components.html('<script>window.parent.document.getElementById("anchor-kelola-opb").scrollIntoView({behavior: "smooth"});</script>', height=0)
[cite: 4]        st.markdown("<br>", unsafe_allow_html=True)

[cite: 4]    # ================= EXECUTIVE DASHBOARD & BUDGET PER DIVISI =================
[cite: 4]    st.markdown("### 📊 Dashboard Monitoring & Budgeting Divisi")

[cite: 4]    TAHAPAN_OPB = [
[cite: 4]        "1. Penawaran Purchasing",
[cite: 4]        "2. Review BM",
[cite: 4]        "3. Pembuatan IOM (Purchasing)",
[cite: 4]        "4. Review Finance",
[cite: 4]        "5. Approval Akhir (BM & P3SRS)",
[cite: 4]        "6. Serah Terima Barang (Purchasing -> Engineering)",
[cite: 4]        "7. Verifikasi Penerimaan Barang (Engineering)",
[cite: 4]        "8. Selesai",
[cite: 4]    ]

[cite: 4]    total_opb = len(st.session_state["db_opb"])
[cite: 4]    budget_summary = calculate_budget_summary(st.session_state["db_opb"])

[cite: 4]    if total_opb > 0:
[cite: 4]        df_opb = pd.DataFrame(st.session_state["db_opb"])
[cite: 4]        if "status" not in df_opb.columns:
[cite: 4]            df_opb["status"] = "1. Penawaran Purchasing"
[cite: 4]        if "harga_estimasi" not in df_opb.columns:
[cite: 4]            df_opb["harga_estimasi"] = 0

[cite: 4]        total_selesai = len(df_opb[df_opb["status"] == "8. Selesai"])
[cite: 4]        total_proses = total_opb - total_selesai
[cite: 4]        total_anggaran = df_opb["harga_estimasi"].fillna(0).sum()

[cite: 4]        m1, m2, m3, m4 = st.columns(4)
[cite: 4]        with m1:
[cite: 4]            st.markdown(f'<div class="kpi-card kpi-blue"><div class="kpi-title">Total Permintaan</div><div class="kpi-value">{total_opb} OPB</div><div class="kpi-sub" style="color:#2563eb;">📂 Seluruh Berkas</div></div>', unsafe_allow_html=True)
[cite: 4]        with m2:
[cite: 4]            st.markdown(f'<div class="kpi-card kpi-amber"><div class="kpi-title">Dalam Process</div><div class="kpi-value" style="color:#d97706;">{total_proses} OPB</div><div class="kpi-sub" style="color:#d97706;">⏳ On Progress</div></div>', unsafe_allow_html=True)
[cite: 4]        with m3:
[cite: 4]            st.markdown(f'<div class="kpi-card kpi-emerald"><div class="kpi-title">Selesai</div><div class="kpi-value" style="color:#059669;">{total_selesai} OPB</div><div class="kpi-sub" style="color:#059669;">✅ Verified</div></div>', unsafe_allow_html=True)
[cite: 4]        with m4:
[cite: 4]            st.markdown(f'<div class="kpi-card kpi-purple"><div class="kpi-title">Total Anggaran Transaksi</div><div class="kpi-value" style="color:#7c3aed; font-size:18px;">Rp {total_anggaran:,.0f}</div><div class="kpi-sub" style="color:#7c3aed;">💰 Realisasi Anggaran</div></div>', unsafe_allow_html=True)

[cite: 4]        st.markdown("<br>", unsafe_allow_html=True)

[cite: 4]        if role != "Engineering":
[cite: 4]            with st.expander("💳 **RINCIAN BUDGET & SISA ANGGARAN PER DIVISI (ALOKASI @ Rp 1 MILIAR)**", expanded=True):
[cite: 4]                b_cols = st.columns(len(budget_summary))
[cite: 4]                for idx, (div_name, b_info) in enumerate(budget_summary.items()):
[cite: 4]                    with b_cols[idx]:
[cite: 4]                        st.markdown(f"**{div_name}**")
[cite: 4]                        st.caption(f"Pagu: Rp {b_info['pagu_awal']:,}")
[cite: 4]                        st.caption(f"Terpakai: Rp {b_info['terpakai']:,}")
[cite: 4]                        sisa_color = "green" if b_info['sisa'] > 0 else "red"
[cite: 4]                        st.markdown(f"<span style='color:{sisa_color}; font-weight:bold; font-size:12px;'>Sisa: Rp {b_info['sisa']:,}</span>", unsafe_allow_html=True)

[cite: 4]        if role in ["Finance", "P3SRS"]:
[cite: 4]            st.markdown("<br>", unsafe_allow_html=True)
[cite: 4]            with st.expander("📊 **RINCIAN MUTASI POTONGAN ANGGARAN & EKSPOR EXCEL (KHUSUS FINANCE & P3SRS)**", expanded=True):
[cite: 4]                items_potongan = [
[cite: 4]                    x for x in st.session_state["db_opb"]
[cite: 4]                    if x.get("status") in [
[cite: 4]                        "6. Serah Terima Barang (Purchasing -> Engineering)",
[cite: 4]                        "7. Verifikasi Penerimaan Barang (Engineering)",
[cite: 4]                        "8. Selesai",
[cite: 4]                    ]
[cite: 4]                ]

[cite: 4]                if items_potongan:
[cite: 4]                    rows = []
[cite: 4]                    for item in items_potongan:
[cite: 4]                        last_date = "-"
[cite: 4]                        if item.get("timeline"):
[cite: 4]                            last_date = item["timeline"][-1].get("waktu", "-")

[cite: 4]                        rows.append({
[cite: 4]                            "No OPB": item.get("nomor_opb", "-"),
[cite: 4]                            "Divisi Pemohon": item.get("divisi", "-"),
[cite: 4]                            "Rincian Barang/Pengajuan": item.get("nama_barang", "-"),
[cite: 4]                            "Vendor": item.get("vendor", "-"),
[cite: 4]                            "Nilai Potongan (Rp)": item.get("harga_estimasi", 0),
[cite: 4]                            "Status": item.get("status", "-"),
[cite: 4]                            "Tanggal Disetujui": last_date
[cite: 4]                        })

[cite: 4]                    df_potongan = pd.DataFrame(rows)

[cite: 4]                    st.dataframe(
[cite: 4]                        df_potongan.style.format({"Nilai Potongan (Rp)": "Rp {:,.0f}"}),
[cite: 4]                        use_container_width=True,
[cite: 4]                        hide_index=True
[cite: 4]                    )

[cite: 4]                    col_exp1, col_exp2 = st.columns([1, 4])
[cite: 4]                    with col_exp1:
[cite: 4]                        excel_data = convert_df_to_excel(df_potongan)
[cite: 4]                        st.download_button(
[cite: 4]                            label="📥 Export Ke Excel (.xlsx)",
[cite: 4]                            data=excel_data,
[cite: 4]                            file_name=f"Laporan_Potongan_Budget_P3SRS_{datetime.now().strftime('%Y%m%d')}.xlsx",
[cite: 4]                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
[cite: 4]                            use_container_width=True,
[cite: 4]                            type="primary"
[cite: 4]                        )
[cite: 4]                    with col_exp2:
[cite: 4]                        csv_data = df_potongan.to_csv(index=False).encode('utf-8')
[cite: 4]                        st.download_button(
[cite: 4]                            label="📄 Export Ke CSV",
[cite: 4]                            data=csv_data,
[cite: 4]                            file_name=f"Laporan_Potongan_Budget_P3SRS_{datetime.now().strftime('%Y%m%d')}.csv",
[cite: 4]                            mime="text/csv",
[cite: 4]                        )
[cite: 4]                else:
[cite: 4]                    st.info("ℹ️ Belum ada pengajuan OPB/IOM yang disetujui (memotong budget).")

[cite: 4]        st.markdown("<br>", unsafe_allow_html=True)

[cite: 4]        col_dash1, col_dash2 = st.columns([1.3, 1])

[cite: 4]        with col_dash1:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.markdown("##### 📌 Progress Live Status & Timeline Berkas")
[cite: 4]            st.markdown("<br>", unsafe_allow_html=True)
[cite: 4]            for idx, item in enumerate(st.session_state["db_opb"]):
[cite: 4]                status_curr = item.get("status") or "1. Penawaran Purchasing"

[cite: 4]                if "Revisi" in str(status_curr):
[cite: 4]                    prog_pct = 25
[cite: 4]                elif status_curr in TAHAPAN_OPB:
[cite: 4]                    step_idx = TAHAPAN_OPB.index(status_curr) + 1
[cite: 4]                    prog_pct = int((step_idx / len(TAHAPAN_OPB)) * 100)
[cite: 4]                else:
[cite: 4]                    prog_pct = 0

[cite: 4]                st.markdown(f"**{item.get('nomor_opb', '-')}** — `{item.get('divisi','IT')}` | Urgensi: `{item.get('urgensi','Normal')}`")
[cite: 4]                c_a, c_b = st.columns([4, 1])
[cite: 4]                with c_a:
[cite: 4]                    st.progress(prog_pct)
[cite: 4]                with c_b:
[cite: 4]                    st.caption(f"**{prog_pct}%**")
                
[cite: 4]                harga_est = item.get('harga_estimasi', 0) or 0
[cite: 4]                st.markdown(f"📦 **Daftar Barang:** {item.get('nama_barang', '-')}")
[cite: 4]                st.caption(f"📍 Status: `{status_curr}` | 💰 Est Biaya: **Rp {harga_est:,}**")

[cite: 4]                render_download_buttons(item, key_prefix=f"dash_{idx}")

[cite: 4]                timeline_list = item.get("timeline", [])
[cite: 4]                with st.expander(f"📜 Timeline & Jejak Verifikasi ({len(timeline_list)} Aktivitas)"):
[cite: 4]                    render_enhanced_timeline(timeline_list)

[cite: 4]                st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]        with col_dash2:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.markdown("##### 📈 Distribusi Berkas per Tahapan")

[cite: 4]            status_counts = df_opb["status"].value_counts().reset_index()
[cite: 4]            status_counts.columns = ["Status Tahapan", "Jumlah OPB"]

[cite: 4]            fig = px.bar(
[cite: 4]                status_counts,
[cite: 4]                x="Jumlah OPB",
[cite: 4]                y="Status Tahapan",
[cite: 4]                orientation="h",
[cite: 4]                color="Jumlah OPB",
[cite: 4]                color_continuous_scale="Purples",
[cite: 4]                text="Jumlah OPB",
[cite: 4]            )
[cite: 4]            fig.update_layout(
[cite: 4]                margin=dict(l=10, r=10, t=10, b=10),
[cite: 4]                height=280,
[cite: 4]                xaxis_title="Jumlah OPB",
[cite: 4]                yaxis_title=None,
[cite: 4]                paper_bgcolor="rgba(0,0,0,0)",
[cite: 4]                plot_bgcolor="rgba(0,0,0,0)",
[cite: 4]                font=dict(family="Inter, sans-serif", size=11, color="#475569"),
[cite: 4]                coloraxis_showscale=False,
[cite: 4]            )
[cite: 4]            st.plotly_chart(fig, use_container_width=True)
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]    else:
[cite: 4]        st.info("💡 **Dashboard Masih Kosong:** Belum ada data pengajuan OPB.")

[cite: 4]    st.markdown("---")
[cite: 4]    st.markdown('<div id="anchor-kelola-opb"></div>', unsafe_allow_html=True)

[cite: 4]    # ==================== MODUL USER PANELS ====================

[cite: 4]    # 1. ROLE ENGINEERING
[cite: 4]    if role == "Engineering":
[cite: 4]        st.header("🔧 Panel Kerja Engineering")
[cite: 4]        tab1, tab2 = st.tabs(["📝 Buat Form OPB Baru", "📦 Verifikasi & Tanda Tangan Penerimaan Barang (BAST)"])

[cite: 4]        with tab1:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.subheader("Pengajuan OPB Baru")

[cite: 4]            divisi_pilihan = st.selectbox("Divisi Pemohon", DIVISI_LIST, key="select_divisi_pemohon")
[cite: 4]            budget_div_info = budget_summary.get(divisi_pilihan, {"sisa": 1_000_000_000})
[cite: 4]            st.info(f"💰 **Sisa Budget Terkini Divisi {divisi_pilihan}:** Rp {budget_div_info['sisa']:,}")

[cite: 4]            next_number = len(st.session_state["db_opb"]) + 1
[cite: 4]            code_div = divisi_pilihan.upper().replace(" ", "")
[cite: 4]            nomor_opb_auto = f"OPB/{code_div}/{next_number:03d}"

[cite: 4]            st.text_input("Nomor OPB (Otomatis)", value=nomor_opb_auto, disabled=True)

[cite: 4]            with st.form(key="form_opb_engineering", clear_on_submit=True):
[cite: 4]                urgensi = st.radio(
[cite: 4]                    "Tingkat Urgensi / Jenis OPB",
[cite: 4]                    options=[
[cite: 4]                        "🔴 Darurat (1x24 Jam)",
[cite: 4]                        "🟠 Prioritas (3x24 Jam)",
[cite: 4]                        "🟢 Medium (5x24 Jam)",
[cite: 4]                        "⚪ Normal (7x24 Jam)"
[cite: 4]                    ],
[cite: 4]                    horizontal=True
[cite: 4]                )
[cite: 4]                nama_barang = st.text_area("Detail Pengajuan Barang", placeholder="Misal: 1 RAM, 2 SSD...")
[cite: 4]                keterangan = st.text_area("Alasan Kebutuhan & Spesifikasi")
[cite: 4]                file_opb = st.file_uploader("Unggah Dokumen Lampiran BA", type=["pdf", "docx", "xlsx"])

[cite: 4]                submit = st.form_submit_button("🚀 Submit & Kirim OPB ke Purchasing", type="primary", use_container_width=True)

[cite: 4]            if submit:
[cite: 4]                if nama_barang:
[cite: 4]                    with st.spinner("Menyimpan berkas..."):
[cite: 4]                        file_url = None
[cite: 4]                        file_name = "-"
[cite: 4]                        if file_opb:
[cite: 4]                            file_url = upload_file_to_supabase(file_opb.getvalue(), file_opb.name, folder="opb")
[cite: 4]                            file_name = file_opb.name

[cite: 4]                        sig_eng = generate_digital_signature("Engineering", user_info["name"], nomor_opb_auto)
[cite: 4]                        data_baru = {
[cite: 4]                            "nomor_opb": nomor_opb_auto,
[cite: 4]                            "divisi": divisi_pilihan,
[cite: 4]                            "urgensi": urgensi,
[cite: 4]                            "nama_barang": nama_barang,
[cite: 4]                            "jumlah": 1,
[cite: 4]                            "keterangan": keterangan,
[cite: 4]                            "file_opb_url": file_url,
[cite: 4]                            "harga_estimasi": 0,
[cite: 4]                            "vendor": "-",
[cite: 4]                            "status": "1. Penawaran Purchasing",
[cite: 4]                            "timeline": [],
[cite: 4]                        }
[cite: 4]                        catat_log(data_baru, f"OPB Dibuat untuk Divisi {divisi_pilihan} oleh {user_info['name']}", digital_sig=sig_eng)
                        
[cite: 4]                        res = save_database(data_baru, is_new=True)
[cite: 4]                        if res:
[cite: 4]                            st.toast("🚀 OPB Berhasil diteruskan ke Purchasing!", icon="✅")
[cite: 4]                            st.rerun()
[cite: 4]                else:
[cite: 4]                    st.warning("Mohon isi Detail Barang terlebih dahulu.")
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]        with tab2:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.subheader("📦 Serah Terima Barang Masuk dari Purchasing")
[cite: 4]            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "7. Verifikasi Penerimaan Barang (Engineering)"]
[cite: 4]            if not items:
[cite: 4]                st.info("Tidak ada barang yang menunggu verifikasi penerimaan.")
[cite: 4]            for item in items:
[cite: 4]                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]                with st.expander(f"📦 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
[cite: 4]                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')}")
[cite: 4]                    render_download_buttons(item, key_prefix="eng_tab2")
[cite: 4]                    render_signature_pad(f"eng_rcv_{item.get('id', 0)}")

[cite: 4]                    if st.button(f"✅ Konfirmasi & Tanda Tangan BAST", type="primary", use_container_width=True):
[cite: 4]                        sig_rcv = generate_digital_signature("Engineering (Penerima)", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                        item["status"] = "8. Selesai"
[cite: 4]                        catat_log(item, f"Barang diterima oleh {user_info['name']}. BAST Ditandatangani.", digital_sig=sig_rcv)
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]    # 2. ROLE PURCHASING
[cite: 4]    elif role == "Purchasing":
[cite: 4]        st.header("🛒 Panel Kerja Purchasing")
[cite: 4]        tab1, tab2, tab3 = st.tabs(["1. Input Penawaran Harga", "2. Buat & Unggah IOM", "3. Serah Terima Barang ke Engineering"])

[cite: 4]        with tab1:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.subheader("OPB Masuk (Perlu Penawaran & Harga Vendor)")
            
[cite: 4]            items = [
[cite: 4]                x for x in st.session_state["db_opb"]
[cite: 4]                if str(x.get("status")).strip() in ["1. Penawaran Purchasing", "Revisi BM (OPB)"]
[cite: 4]                or not x.get("status")
[cite: 4]            ]

[cite: 4]            if not items:
[cite: 4]                st.info("Tidak ada tugas penawaran barang saat ini.")
[cite: 4]            for item in items:
[cite: 4]                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]                item_id = item.get("id", 0)
[cite: 4]                with st.expander(f"📌 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
[cite: 4]                    st.write(f"**Divisi Pemohon:** {item.get('divisi','IT')} | **Urgensi:** {item.get('urgensi','Normal')}")
[cite: 4]                    st.write(f"**Detail:** {item.get('nama_barang', '-')}")
[cite: 4]                    render_download_buttons(item, key_prefix=f"pur_tab1_{item_id}")

[cite: 4]                    st.divider()
[cite: 4]                    with st.form(key=f"form_pur_input_{item_id}"):
[cite: 4]                        vendor_input = st.text_input("Nama Vendor/Pemasok Pilihan", value=item.get("vendor", "-"))
[cite: 4]                        harga_input = st.number_input("Estimasi Total Harga (Rp)", min_value=0, value=int(item.get("harga_estimasi", 0)))

[cite: 4]                        div_item = item.get('divisi', 'IT')
[cite: 4]                        sisa_skrg = budget_summary.get(div_item, {}).get('sisa', 1_000_000_000)
[cite: 4]                        sisa_setelah = sisa_skrg - harga_input
[cite: 4]                        st.caption(f"💡 **Simulasi Budget Divisi {div_item}:** Sisa Awal: Rp {sisa_skrg:,} → **Sisa Setelah Potongan OPB Ini: Rp {sisa_setelah:,}**")

[cite: 4]                        submit_pur = st.form_submit_button("Kirim ke BM untuk Review", type="primary", use_container_width=True)

[cite: 4]                    if submit_pur:
[cite: 4]                        sig_pur = generate_digital_signature("Purchasing", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                        item["vendor"] = vendor_input
[cite: 4]                        item["harga_estimasi"] = int(harga_input)
[cite: 4]                        item["status"] = "2. Review BM"
[cite: 4]                        catat_log(item, f"Purchasing menentukan vendor ({vendor_input}) & harga Rp {harga_input:,}.", digital_sig=sig_pur)
                        
[cite: 4]                        res = save_database(item, is_new=False)
[cite: 4]                        if res is not None:
[cite: 4]                            st.session_state["target_focus_id"] = None
[cite: 4]                            st.toast("📩 Berhasil dikirim ke BM!", icon="✅")
[cite: 4]                            st.rerun()
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]        with tab2:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.subheader("OPB Disetujui BM -> Buat & Upload IOM")
[cite: 4]            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() in ["3. Pembuatan IOM (Purchasing)", "Revisi Finance", "Revisi BM/P3SRS (IOM)"]]
[cite: 4]            if not items:
[cite: 4]                st.info("Tidak ada IOM yang perlu dibuat/direvisi.")
[cite: 4]            for item in items:
[cite: 4]                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]                item_id = item.get("id", 0)
[cite: 4]                with st.expander(f"📑 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
[cite: 4]                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')}")
[cite: 4]                    render_download_buttons(item, key_prefix=f"pur_tab2_{item_id}")

[cite: 4]                    st.divider()
[cite: 4]                    file_iom = st.file_uploader("Unggah Draft Dokumen IOM", type=["pdf", "docx"], key=f"fiom_{item_id}")
[cite: 4]                    if st.button("Kirim Berkas IOM ke Finance", key=f"btn_p2_{item_id}", type="primary", use_container_width=True):
[cite: 4]                        if file_iom:
[cite: 4]                            iom_url = upload_file_to_supabase(file_iom.getvalue(), file_iom.name, folder="iom")
[cite: 4]                            sig_pur_iom = generate_digital_signature("Purchasing (IOM Draft)", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                            item["file_iom_url"] = iom_url
[cite: 4]                            item["status"] = "4. Review Finance"
[cite: 4]                            catat_log(item, "Purchasing mengunggah draft IOM ke Finance.", digital_sig=sig_pur_iom)
[cite: 4]                            save_database(item, is_new=False)
[cite: 4]                            st.session_state["target_focus_id"] = None
[cite: 4]                            st.rerun()
[cite: 4]                        else:
[cite: 4]                            st.warning("Silakan unggah file IOM terlebih dahulu.")
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]        with tab3:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            st.subheader("🤝 Serah Terima Barang & Upload BAST ke Engineering")
[cite: 4]            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() in ["6. Pembelian Barang (Purchasing)", "6. Serah Terima Barang (Purchasing -> Engineering)"]]
[cite: 4]            if not items:
[cite: 4]                st.info("Belum ada barang yang perlu diserahterimakan.")
[cite: 4]            for item in items:
[cite: 4]                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]                item_id = item.get("id", 0)
[cite: 4]                with st.expander(f"💳 {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
[cite: 4]                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')}")
[cite: 4]                    render_download_buttons(item, key_prefix=f"pur_tab3_{item_id}")

[cite: 4]                    st.divider()
[cite: 4]                    file_bast = st.file_uploader("Unggah BAST", type=["pdf", "jpg", "png"], key=f"bast_file_{item_id}")
[cite: 4]                    render_signature_pad(f"pur_bast_{item_id}")

[cite: 4]                    if st.button("🚚 Serahkan Barang & BAST ke Engineering", key=f"btn_p3_{item_id}", type="primary", use_container_width=True):
[cite: 4]                        if file_bast:
[cite: 4]                            item["file_bast_url"] = upload_file_to_supabase(file_bast.getvalue(), file_bast.name, folder="bast")

[cite: 4]                        sig_handover = generate_digital_signature("Purchasing (Penyerah)", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                        item["status"] = "7. Verifikasi Penerimaan Barang (Engineering)"
[cite: 4]                        catat_log(item, f"Purchasing menyerahkan fisik barang & BAST ke Engineering.", digital_sig=sig_handover)
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]    # 3. ROLE BUILDING MANAGER
[cite: 4]    elif role == "BM (Building Manager)":
[cite: 4]        st.header("👔 Panel Building Manager (BM)")
[cite: 4]        tab1, tab2 = st.tabs(["Review OPB (Awal)", "Approval Final IOM"])

[cite: 4]        with tab1:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "2. Review BM"]
[cite: 4]            if not items:
[cite: 4]                st.info("Tidak ada OPB baru menunggu persetujuan.")
[cite: 4]            for item in items:
[cite: 4]                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]                item_id = item.get("id", 0)
[cite: 4]                with st.expander(f"🧐 Review OPB: {item.get('nomor_opb', '-')} - {item.get('nama_barang', '-')}", expanded=is_expanded):
[cite: 4]                    st.write(f"**Divisi:** {item.get('divisi','IT')} | **Vendor:** {item.get('vendor', '-')} | **Estimasi:** Rp {item.get('harga_estimasi', 0):,}")
[cite: 4]                    render_download_buttons(item, key_prefix=f"bm_tab1_{item_id}")

[cite: 4]                    st.divider()
[cite: 4]                    render_signature_pad(f"bm1_sig_{item_id}")
[cite: 4]                    catatan = st.text_input("Catatan / Alasan jika Minta Revisi", key=f"c_bm1_{item_id}")

[cite: 4]                    col1, col2 = st.columns(2)
[cite: 4]                    with col1:
[cite: 4]                        if st.button("✅ Setujui & Tanda Tangan OPB", key=f"app_bm1_{item_id}", type="primary", use_container_width=True):
[cite: 4]                            sig_bm = generate_digital_signature("Building Manager", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                            item["status"] = "3. Pembuatan IOM (Purchasing)"
[cite: 4]                            catat_log(item, "BM menyetujui OPB. Diteruskan ke Purchasing.", digital_sig=sig_bm)
[cite: 4]                            save_database(item, is_new=False)
[cite: 4]                            st.session_state["target_focus_id"] = None
[cite: 4]                            st.rerun()
[cite: 4]                    with col2:
[cite: 4]                        if st.button("❌ Tolak / Minta Revisi", key=f"rej_bm1_{item_id}", use_container_width=True):
[cite: 4]                            item["catatan_bm"] = catatan
[cite: 4]                            item["status"] = "Revisi BM (OPB)"
[cite: 4]                            catat_log(item, f"BM meminta revisi OPB: {catatan}")
[cite: 4]                            save_database(item, is_new=False)
[cite: 4]                            st.session_state["target_focus_id"] = None
[cite: 4]                            st.rerun()
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]        with tab2:
[cite: 4]            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]            items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "5. Approval Akhir (BM & P3SRS)"]
[cite: 4]            if not items:
[cite: 4]                st.info("Tidak ada IOM menunggu persetujuan final.")
[cite: 4]            for item in items:
[cite: 4]                is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]                item_id = item.get("id", 0)
[cite: 4]                with st.expander(f"📑 Approval IOM: {item.get('nomor_opb', '-')}", expanded=is_expanded):
[cite: 4]                    render_download_buttons(item, key_prefix=f"bm_tab2_{item_id}")
[cite: 4]                    render_signature_pad(f"bm2_sig_{item_id}")
[cite: 4]                    if st.button("✅ Approve & Tanda Tangan IOM Final (BM)", key=f"app_bm2_{item_id}", type="primary", use_container_width=True):
[cite: 4]                        sig_bm_iom = generate_digital_signature("Building Manager (IOM Final)", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                        catat_log(item, "BM menyetujui IOM Final.", digital_sig=sig_bm_iom)
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]            st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]    # 4. ROLE FINANCE
[cite: 4]    elif role == "Finance":
[cite: 4]        st.header("💰 Panel Finance & Budgeting")
[cite: 4]        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]        items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "4. Review Finance"]
[cite: 4]        if not items:
[cite: 4]            st.info("Tidak ada IOM yang membutuhkan verifikasi Finance saat ini.")
[cite: 4]        for item in items:
[cite: 4]            is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]            item_id = item.get("id", 0)
[cite: 4]            with st.expander(f"💵 Review IOM: {item.get('nomor_opb', '-')}", expanded=is_expanded):
[cite: 4]                div_item = item.get("divisi", "IT")
[cite: 4]                b_info = budget_summary.get(div_item, {})
[cite: 4]                st.write(f"**Divisi Pemohon:** {div_item} | **Nilai:** Rp {item.get('harga_estimasi', 0):,}")
[cite: 4]                render_download_buttons(item, key_prefix=f"fin_{item_id}")

[cite: 4]                render_signature_pad(f"fin_sig_{item_id}")
[cite: 4]                catatan = st.text_input("Catatan", key=f"c_fin_{item_id}")

[cite: 4]                col1, col2 = st.columns(2)
[cite: 4]                with col1:
[cite: 4]                    if st.button("✅ Verifikasi Budget", key=f"app_fin_{item_id}", type="primary", use_container_width=True):
[cite: 4]                        sig_fin = generate_digital_signature("Finance Officer", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                        item["status"] = "5. Approval Akhir (BM & P3SRS)"
[cite: 4]                        catat_log(item, f"Finance memverifikasi budget Divisi {div_item}.", digital_sig=sig_fin)
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]                with col2:
[cite: 4]                    if st.button("❌ Minta Revisi Budget", key=f"rej_fin_{item_id}", use_container_width=True):
[cite: 4]                        item["catatan_finance"] = catatan
[cite: 4]                        item["status"] = "Revisi Finance"
[cite: 4]                        catat_log(item, f"Finance meminta revisi budget: {catatan}")
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]        st.markdown("</div>", unsafe_allow_html=True)

[cite: 4]    # 5. ROLE P3SRS
[cite: 4]    elif role == "P3SRS":
[cite: 4]        st.header("🏛️ Panel P3SRS (Approval Akhir)")
[cite: 4]        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
[cite: 4]        items = [x for x in st.session_state["db_opb"] if str(x.get("status")).strip() == "5. Approval Akhir (BM & P3SRS)"]
[cite: 4]        if not items:
[cite: 4]            st.info("Tidak ada IOM yang menunggu persetujuan P3SRS.")
[cite: 4]        for item in items:
[cite: 4]            is_expanded = (st.session_state["target_focus_id"] == item.get("id"))
[cite: 4]            item_id = item.get("id", 0)
[cite: 4]            with st.expander(f"⚖️ Persetujuan Final: {item.get('nomor_opb', '-')}", expanded=is_expanded):
[cite: 4]                div_item = item.get("divisi", "IT")
[cite: 4]                harga_nilai = item.get("harga_estimasi", 0)
[cite: 4]                render_download_buttons(item, key_prefix=f"p3srs_{item_id}")

[cite: 4]                render_signature_pad(f"p3srs_sig_{item_id}")
[cite: 4]                catatan = st.text_input("Catatan", key=f"c_p3srs_{item_id}")

[cite: 4]                col1, col2 = st.columns(2)
[cite: 4]                with col1:
[cite: 4]                    if st.button("✅ ACC & Potong Budget Divisi", key=f"app_p3srs_{item_id}", type="primary", use_container_width=True):
[cite: 4]                        sig_p3srs = generate_digital_signature("Pengurus P3SRS", user_info["name"], item.get("nomor_opb", "OPB"))
[cite: 4]                        item["status"] = "6. Serah Terima Barang (Purchasing -> Engineering)"
[cite: 4]                        catat_log(item, f"P3SRS menyetujui IOM Final. Budget Divisi {div_item} terpotong Rp {harga_nilai:,}.", digital_sig=sig_p3srs)
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]                with col2:
[cite: 4]                    if st.button("❌ Minta Revisi", key=f"rej_p3srs_{item_id}", use_container_width=True):
[cite: 4]                        item["catatan_p3srs"] = catatan
[cite: 4]                        item["status"] = "Revisi BM/P3SRS (IOM)"
[cite: 4]                        catat_log(item, f"P3SRS meminta revisi IOM: {catatan}")
[cite: 4]                        save_database(item, is_new=False)
[cite: 4]                        st.session_state["target_focus_id"] = None
[cite: 4]                        st.rerun()
[cite: 4]        st.markdown("</div>", unsafe_allow_html=True)
