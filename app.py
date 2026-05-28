import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
import subprocess
import platform
import plotly.express as px

# นำเข้า Library สำหรับสร้างไฟล์ PDF ภาษาไทยมาตรฐาน
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# [FIXED 1] นำเข้าโมดูลสำหรับจัดการสิทธิ์ Service Account ของ Google Drive ให้ถูกต้องตามหลักสากล
from oauth2client.service_account import ServiceAccountCredentials
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ตั้งค่าหน้าจอโปรแกรม
st.set_page_config(page_title="Procurement Workspace", layout="wide")

# เปลี่ยนตำแหน่งที่เก็บให้ไปอยู่ที่ Drive D หรือโฟลเดอร์ที่ปลอดภัยในเครื่อง 
BASE_DIR = "D:/ProcurementData" [cite: 749]
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR) [cite: 749]

# กำหนดที่เก็บไฟล์ฐานข้อมูลและโฟลเดอร์เอกสารให้อยู่ด้านใน Procurement-App ทั้งหมด 
DB_FILE = os.path.join(BASE_DIR, "rfq_data.json") [cite: 749]
USER_FILE = os.path.join(BASE_DIR, "requestors_data.json") [cite: 749]
SUP_FILE = os.path.join(BASE_DIR, "suppliers_master.json") [cite: 749]
SUP_DOC_DIR = os.path.join(BASE_DIR, "supplier_documents") [cite: 749]
STANDALONE_FILE = os.path.join(BASE_DIR, "standalone_prices.json") [cite: 749]
ITEM_FILE = os.path.join(BASE_DIR, "item_codes_master.json") [cite: 749]
UNIT_FILE = os.path.join(BASE_DIR, "units_master.json") [cite: 749]
CATEGORIES_FILE = os.path.join(BASE_DIR, "categories_master.json") [cite: 749]
PUR_FILE = os.path.join(BASE_DIR, "pur_proposals.json") [cite: 749]

if not os.path.exists(SUP_DOC_DIR):
    os.makedirs(SUP_DOC_DIR) [cite: 750]

# 🎯 [FIXED 2] ปรับแก้ฟังก์ชันเชื่อมต่อ Google Drive อัตโนมัติ โดยครอบเครื่องหมายคำพูดที่ไอดีโฟลเดอร์ให้ถูกต้อง
def upload_to_google_drive(local_file_path, folder_id="1hcqai0lVGsGNdGnH9BBKHgjVnNSlKUbU"):
    try:
        if not os.path.exists(local_file_path):
            return False
        gauth = GoogleAuth()
        gauth.settings['client_config_backend'] = 'settings'
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.join(BASE_DIR, 'credentials.json'), 
            ['https://www.googleapis.com/auth/drive']
        )
        drive = GoogleDrive(gauth)
        
        file_name = os.path.basename(local_file_path)
        drive_file = drive.CreateFile({
            'title': file_name,
            'parents': [{'id': folder_id}]
        })
        drive_file.SetContentFile(local_file_path)
        drive_file.Upload()
        return True
    except Exception as e:
        print(f"Drive Upload Error: {e}")
        return False

# คลังข้อมูลพิกัดจังหวัดและภูมิภาคของประเทศไทย
THAI_REGIONS = {
    "ทั่วประเทศ": ["ทุกจังหวัดทั่วประเทศ"],
    "ภาคกลาง / ปริมณฑล": ["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "พระนครศรีอยุธยา", "สระบุรี", "ลพบุรี", "สิงห์บุรี", "อ่างทอง", "ชัยนาท", "อุทัยธานี", "นครสวรรค์"],
    "ภาคเหนือ": ["เชียงใหม่", "เชียงราย", "ลำปาง", "ลำพูน", "แม่ฮ่องสอน", "พะเยา", "แพร่", "น่าน", "อุตรดิตถ์", "พิษณุโลก", "สุโขทัย", "ตาก", "พิจิตร", "กำแพงเพชร", "เพชรบูรณ์"],
    "ภาคอีสาน": ["นครราชสีมา", "ขอนแก่น", "อุดรธานี", "อุบลราชธานี", "บุรีรัมย์", "ศรีสะเกษ", "สุรินทร์", "ร้อยเอ็ด", "ชัยภูมิ", "มหาสารคาม", "กาฬสินธุ์", "สกลนคร", "นครพนม", "เลย", "หนองคาย", "หนองบัวลำภู", "บึงกาฬ", "ยโสธร", "อำนาจเจริญ", "มุกดาหาร"],
    "ภาคตะวันออก": ["ชลบุรี", "ระยอง", "ฉะเชิงเทรา", "จันทบุรี", "ตราด", "ปราจีนบุรี", "สระแก้ว"],
    "ภาคตะวันตก": ["ราชบุรี", "กาญจนบุรี", "เพชรบุรี", "ประจวบคีรีขันธ์"],
    "ภาคใต้": ["ภูเก็ต", "สงขลา", "สุราษฎร์ธานี", "นครศรีธรรมราช", "กระบี่", "พังงา", "ตรัง", "พัทลุง", "ชุมพร", "ระนอง", "สตูล", "ปัตตานี", "ยะลา", "นราธิวาส"]
}

# ฟังก์ชันจัดการระบบจัดการเปิดโฟลเดอร์จำลอง Local
def open_local_folder(folder_path):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        current_os = platform.system()
        if current_os == "Windows":
            os.startfile(folder_path)
        elif current_os == "Darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])
        st.toast(f"เปิดโฟลเดอร์เรียบร้อยแล้ว: {os.path.basename(folder_path)}", icon="📁")
    except Exception as e:
        st.error(f"ไม่สามารถเปิดโฟลเดอร์ได้อัตโนมัติ: {e}")

# ฟังก์ชันจัดการระบบฐานข้อมูล
def load_json_file(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return default_val
    return default_val

def save_json_file(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def save_data(data): save_json_file(DB_FILE, data); upload_to_google_drive(DB_FILE)
def save_requestors(data): save_json_file(USER_FILE, data); upload_to_google_drive(USER_FILE)
def save_suppliers(data): save_json_file(SUP_FILE, data); upload_to_google_drive(SUP_FILE)
def save_standalone_prices(data): save_json_file(STANDALONE_FILE, data); upload_to_google_drive(STANDALONE_FILE)
def save_item_codes(data): save_json_file(ITEM_FILE, data); upload_to_google_drive(ITEM_FILE)
def save_units(data): save_json_file(UNIT_FILE, data); upload_to_google_drive(UNIT_FILE)
def save_categories(data): save_json_file(CATEGORIES_FILE, data); upload_to_google_drive(CATEGORIES_FILE)
def save_pur_proposals(data): save_json_file(PUR_FILE, data); upload_to_google_drive(PUR_FILE)

# โหลดข้อมูลเข้าสู่ตัวแปรระบบ Session State [cite: 753]
if 'rfq_history' not in st.session_state: st.session_state.rfq_history = load_json_file(DB_FILE, []) [cite: 753]
if 'requestors_list' not in st.session_state: st.session_state.requestors_list = load_json_file(USER_FILE, ["คุณสมชาย", "คุณสมหญิง"]) [cite: 753]
if 'suppliers_master' not in st.session_state: st.session_state.suppliers_master = load_json_file(SUP_FILE, []) [cite: 753]
if 'standalone_prices' not in st.session_state: st.session_state.standalone_prices = load_json_file(STANDALONE_FILE, []) [cite: 753]
if 'item_codes_master' not in st.session_state: st.session_state.item_codes_master = load_json_file(ITEM_FILE, []) [cite: 754]
if 'units_list' not in st.session_state: st.session_state.units_list = load_json_file(UNIT_FILE, ["M", "ชุด", "ตัว", "ตร.ม.", "กิโลกรัม", "ท่อน", "ม้วน"]) [cite: 754]
if 'categories_list' not in st.session_state: st.session_state.categories_list = load_json_file(CATEGORIES_FILE, ["สายไฟ", "ท่อร้อยสาย", "อุปกรณ์ไฟฟ้า", "งานระบบ", "ทั่วไป"]) [cite: 754]
if 'pur_proposals' not in st.session_state: st.session_state.pur_proposals = load_json_file(PUR_FILE, []) [cite: 754]

if 'temp_contacts' not in st.session_state: st.session_state.temp_contacts = [{"name": "", "phone": "", "email": "", "line": ""}] [cite: 754]
if 'selected_supplier_name' not in st.session_state: st.session_state.selected_supplier_name = None [cite: 754]
if 'sup_clear_counter' not in st.session_state: st.session_state.sup_clear_counter = 0 [cite: 754]
if 'areas_output_add' not in st.session_state: st.session_state.areas_output_add = "ยังไม่ได้เลือกพื้นที่" [cite: 754]
if 'selected_search_province' not in st.session_state: st.session_state.selected_search_province = None [cite: 754]
if 'current_pur_id' not in st.session_state: st.session_state.current_pur_id = None [cite: 754]

# --- ฟังก์ชันย่อยสำหรับแจ้งเตือนพิกัดจังหวัด/หมวดหมู่/หน่วยนับ (Dialogs) ---
@st.dialog("🌍 เลือกพื้นที่ที่สามารถรับงานได้") [cite: 754]
def select_areas_dialog():
    st.write("เลือกภาค หรือติ๊กเลือกรายจังหวัดตามต้องการ (เสร็จแล้วกดบันทึกด้านล่าง)") [cite: 754]
    chosen_list = [] [cite: 755]
    for region, provinces in THAI_REGIONS.items(): [cite: 755]
        st.markdown(f"**{region}**") [cite: 755]
        reg_click = st.checkbox(f"เลือกทั้งหมดใน {region}", key=f"pop_reg_{region}") [cite: 755]
        if region != "ทั่วประเทศ": [cite: 755]
            cols = st.columns(4) [cite: 755]
            for idx, prov in enumerate(provinces): [cite: 755]
                col = cols[idx % 4] [cite: 755]
                prov_chk = col.checkbox(prov, value=reg_click, key=f"pop_prov_{prov}") [cite: 756]
                if prov_chk or reg_click: [cite: 756]
                    if prov not in chosen_list: chosen_list.append(prov) [cite: 756]
        else: [cite: 756]
            if reg_click: chosen_list.append("ทุกจังหวัดทั่วประเทศ") [cite: 756]
        st.markdown("---") [cite: 756]
    if st.button("💾 ยืนยันการเลือกพื้นที่", use_container_width=True): [cite: 756]
        st.session_state.areas_output_add = "ทุกจังหวัดทั่วประเทศ" if "ทุกจังหวัดทั่วประเทศ" in chosen_list else ", ".join(chosen_list) [cite: 757]
        st.rerun() [cite: 757]

@st.dialog("🔍 ค้นหาและเลือกซัพพลายเออร์") [cite: 757]
def select_supplier_popup():
    sup_choices = [s["name"] for s in st.session_state.suppliers_master] [cite: 757]
    chosen_sup = st.selectbox("พิมพ์ค้นหาชื่อบริษัท / ผู้ขาย", sup_choices) [cite: 757]
    if st.button("✅ ยืนยันเปิดดูโปรไฟล์", use_container_width=True): [cite: 757]
        st.session_state.selected_supplier_name = chosen_sup [cite: 757]
        st.rerun() [cite: 757]

@st.dialog("🎯 ค้นหาและเลือกจังหวัดพิกัดไซต์งาน") [cite: 757]
def select_search_province_popup():
    flat_provinces_search = [] [cite: 757]
    for k, v in THAI_REGIONS.items(): [cite: 757]
        if k != "ทั่วประเทศ": flat_provinces_search.extend(v) [cite: 757]
    flat_provinces_search.sort() [cite: 757]
    chosen_search_prov = st.selectbox("พิมพ์ค้นหาชื่อจังหวัด", flat_provinces_search) [cite: 758]
    if st.button("✅ ยืนยันเลือกจังหวัดนี้", use_container_width=True): [cite: 758]
        st.session_state.selected_search_province = chosen_search_prov [cite: 758]
        st.rerun() [cite: 758]

@st.dialog("📝 แก้ไขข้อมูลซัพพลายเออร์") [cite: 758]
def edit_supplier_popup(sup_obj, idx_master):
    e_tax = st.text_input("เลขประจำตัวผู้เสียภาษี (Tax ID)", value=sup_obj.get("tax_id", "")) [cite: 758]
    e_credit = st.text_input("เครดิตเทอม", value=sup_obj.get("credit", "")) [cite: 758]
    e_address = st.text_area("ที่อยู่บริษัท", value=sup_obj.get("address", "")) [cite: 758]
    e_info = st.text_area("หมายเหตุทั่วไป", value=sup_obj.get("general_info", "")) [cite: 758]
    if st.button("💾 บันทึกการแก้ไขข้อมูล", use_container_width=True): [cite: 758]
        st.session_state.suppliers_master[idx_master].update({"tax_id": e_tax, "credit": e_credit, "address": e_address, "general_info": e_info}) [cite: 758]
        save_suppliers(st.session_state.suppliers_master) [cite: 758]
        st.rerun() [cite: 759]

@st.dialog("👥 บริหารจัดการรายชื่อผู้ติดต่อ") [cite: 759]
def edit_contacts_popup(sup_obj, idx_master):
    updated_items = [] [cite: 759]
    for i, contact in enumerate(st.session_state.edit_contacts_list): [cite: 759]
        ec_c1, ec_c2, ec_c3, ec_c4 = st.columns(4) [cite: 759]
        c_name = ec_c1.text_input("ชื่อ", value=contact.get("name", ""), key=f"ec_n_{i}") [cite: 759]
        c_phone = ec_c2.text_input("เบอร์โทร", value=contact.get("phone", ""), key=f"ec_p_{i}") [cite: 759]
        c_email = ec_c3.text_input("Email", value=contact.get("email", ""), key=f"ec_e_{i}") [cite: 759]
        c_line = ec_c4.text_input("Line ID", value=contact.get("line", ""), key=f"ec_l_{i}") [cite: 759]
        updated_items.append({"name": c_name, "phone": c_phone, "email": c_email, "line": c_line}) [cite: 759]
    if st.button("💾 บันทึกการเปลี่ยนแปลงรายชื่อ", use_container_width=True): [cite: 760]
        st.session_state.suppliers_master[idx_master]["contacts"] = [c for c in updated_items if c["name"].strip()] [cite: 760]
        save_suppliers(st.session_state.suppliers_master) [cite: 760]
        st.rerun() [cite: 760]

@st.dialog("➕ ลงทะเบียนหน่วยนับมาตรฐานใหม่") [cite: 760]
def add_unit_dialog():
    new_unit = st.text_input("ชื่อหน่วยนับ (Unit Name)").strip()
    if st.button("💾 บันทึกหน่วยนับใหม่", use_container_width=True):
        if new_unit and new_unit not in st.session_state.units_list:
            st.session_state.units_list.append(new_unit)
            save_units(st.session_state.units_list)
            st.rerun()

@st.dialog("➕ ลงทะเบียนหมวดหมู่งานมาตรฐานใหม่") [cite: 761]
def add_category_dialog():
    new_cat = st.text_input("ชื่อหมวดหมู่งาน / กลุ่มพัสดุ").strip() [cite: 761]
    if st.button("💾 บันทึกหมวดหมู่ใหม่", use_container_width=True): [cite: 761]
        if new_cat and new_cat not in st.session_state.categories_list: [cite: 761]
            st.session_state.categories_list.append(new_cat) [cite: 761]
            save_categories(st.session_state.categories_list) [cite: 761]
            st.rerun() [cite: 761]

# =========================================================================
# 🧭 ระบบเมนูควบคุมหลักด้านข้าง (Sidebar Navigation)
# =========================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧭 เมนูควบคุมหลัก</h2>", unsafe_allow_html=True) [cite: 761]
    st.markdown("---") [cite: 761]
    main_menu = st.radio( [cite: 762]
        "เลือกหน้าต่างทำงาน:", [cite: 762]
        ["🏠 หน้าหลัก (Dashboard)", "📦 ระบบจัดการ RFQ", "🏢 ข้อมูล Supplier", "📊 BOQ Supplier", "🗂️ บริหาร Item Code", "📝 จัดทำ BOQ เพื่อเสนอ"] [cite: 762]
    ) [cite: 762]
    st.markdown("---") [cite: 762]
    st.caption("ระบบจัดซื้อส่วนตัว v2.2 • 2026") [cite: 762]

# =========================================================================
# 🏠 หน้าหลัก (Dashboard)
# =========================================================================
if main_menu == "🏠 หน้าหลัก (Dashboard)": [cite: 762]
    st.title("ワークスペース • หน้าหลักระบบจัดซื้อ") [cite: 762]
    clock_html = """
    <div style="text-align: center;
    font-family: 'Courier New', Courier, monospace; padding: 20px; background: #1e1e24; border-radius: 12px; border: 1px solid #333;
    margin-bottom: 25px;">
        <div id="live-clock" style="font-size: 55px; font-weight: bold; color: #00ffcc; letter-spacing: 3px;
        text-shadow: 0 0 10px rgba(0,255,204,0.3);">00:00:00</div>
        <div id="live-date" style="font-size: 18px; color: #ffffff; margin-top: 8px;
        font-family: 'Helvetica Neue', Arial, sans-serif;">วันเดือนปี</div>
    </div>
    <script>
        function updateWidgetClock() {
            const now = new Date();
            document.getElementById('live-clock').innerText = now.toLocaleTimeString('th-TH', { hour12: false });
            document.getElementById('live-date').innerText = now.toLocaleDateString('th-TH', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        }
        setInterval(updateWidgetClock, 1000); updateWidgetClock();
    </script>
    """
    components.html(clock_html, height=140) [cite: 767]
    
    total_rfq = len(st.session_state.rfq_history) [cite: 767]
    pending_rfq = sum(1 for x in st.session_state.rfq_history if x.get("status") == "กำลังขอราคา") [cite: 767]
    compared_rfq = sum(1 for x in st.session_state.rfq_history if x.get("status") in ["ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว"]) [cite: 767]
    completed_rfq = sum(1 for x in st.session_state.rfq_history if x.get("status") == "สั่งซื้อเรียบร้อย (PO ออกแล้ว)") [cite: 767]
    total_sups = len(st.session_state.suppliers_master) [cite: 767]
    
    card1, card2, card3, card4, card5 = st.columns(5) [cite: 767]
    card1.metric("RFQ ทั้งหมดในระบบ", f"{total_rfq} ใบ") [cite: 767]
    card2.metric("⏳ อยู่ระหว่างขอราคา", f"{pending_rfq} งาน") [cite: 767]
    card3.metric("📊 ส่งราคา Compare เรียบร้อย", f"{compared_rfq} งาน") [cite: 768]
    card4.metric("✅ ออก PO เรียบร้อย", f"{completed_rfq} งาน") [cite: 768]
    card5.metric("🏢 ซัพพลายเออร์ในคลัง", f"{total_sups} ราย") [cite: 768]

    st.markdown("---") [cite: 768]
    if total_rfq > 0: [cite: 768]
        st.subheader("🍕 กราฟวิเคราะห์สัดส่วนปริมาณงานตามสถานะ") [cite: 768]
        df_rfq = pd.DataFrame(st.session_state.rfq_history) [cite: 768]
        status_counts = df_rfq["status"].value_counts().reset_index() [cite: 768]
        status_counts.columns = ["สถานะงาน", "จำนวนใบงาน"] [cite: 768]
        g_col1, g_col2 = st.columns([3, 2]) [cite: 768]
        with g_col1: [cite: 768]
            fig_pie = px.pie(status_counts, values="จำนวนใบงาน", names="สถานะงาน", hole=0) [cite: 769]
            st.plotly_chart(fig_pie, use_container_width=True) [cite: 769]
        with g_col2: [cite: 769]
            st.markdown("#### 📝 ตารางสรุปตัวเลขสถิติ") [cite: 769]
            st.dataframe(status_counts, use_container_width=True, hide_index=True) [cite: 769]
    else: st.info("💡 ข้อมูลกราฟวิเคราะห์จะปรากฏเมื่อบันทึกใบงาน RFQ") [cite: 769]

# =========================================================================
# 📦 ระบบจัดการ RFQ
# =========================================================================
elif main_menu == "📦 ระบบจัดการ RFQ": [cite: 769]
    st.title("📦 ระบบบริหารจัดการ RFQ") [cite: 769]
    sub_tab0, sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["📋 รายการ RFQ ทั้งหมด", "🆕 เปิด RFQ ใหม่", "📑 อัปเดตสถานะราคา", "📜 ประวัติย้อนหลัง (History)", "👤 จัดการรายชื่อผู้ร้องขอ"]) [cite: 769]
    
    with sub_tab0: [cite: 771]
        st.subheader("📋 ตารางตรวจสอบสถานะงาน RFQ และโฟลเดอร์จัดเก็บข้อมูล") [cite: 771]
        if not st.session_state.rfq_history: st.warning("ยังไม่มีข้อมูล RFQ บันทึกไว้ในระบบ") [cite: 771]
        else: [cite: 771]
            status_filter = st.selectbox("🔍 กรองดูตามสถานะใบงาน:", ["แสดงทั้งหมด", "กำลังขอราคา", "ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว", "สั่งซื้อเรียบร้อย (PO ออกแล้ว)", "ยกเลิกงาน"]) [cite: 771]
            filtered_rfq = st.session_state.rfq_history if status_filter == "แสดงทั้งหมด" else [x for x in st.session_state.rfq_history if x.get("status") == status_filter] [cite: 771]
            st.markdown(f"พบใบงานจัดซื้อทั้งหมด **{len(filtered_rfq)}** รายการ") [cite: 771]
            
            h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5]) [cite: 771]
            h_c1.markdown("**เลขที่ RFQ**") [cite: 771]
            h_c2.markdown("**ชื่อโครงการ / โฟลเดอร์**") [cite: 771]
            h_c3.markdown("**ผู้ร้องขอ**") [cite: 771]
            h_c4.markdown("**กำหนดส่งมอบ**") [cite: 772]
            h_c5.markdown("**สถานะปัจจุบัน**") [cite: 772]
            h_c6.markdown("**เปิดโฟลเดอร์ในคอม**") [cite: 772]
            st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True) [cite: 772]
            
            for idx, item in enumerate(filtered_rfq): [cite: 772]
                r_c1, r_c2, r_c3, r_c4, r_c5, r_c6 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5]) [cite: 772]
                r_c1.write(f"`{item['id']}`") [cite: 773]
                r_c2.write(item.get("project", "ทั่วไป")) [cite: 773]
                r_c3.write(item.get("requestor", "-")) [cite: 773]
                r_c4.write(item.get("deadline", "-")) [cite: 773]
                
                status_text = item.get("status", "กำลังขอราคา") [cite: 774]
                if status_text == "กำลังขอราคา": r_c5.caption(f"⏳ {status_text}") [cite: 774]
                elif status_text == "สั่งซื้อเรียบร้อย (PO ออกแล้ว)": r_c5.write(f"🟢 **{status_text}**") [cite: 774]
                elif status_text == "ยกเลิกงาน": r_c5.caption(f"🔴 {status_text}") [cite: 774]
                else: r_c5.write(f"🔵 {status_text}") [cite: 774]
                
                if r_c6.button("📁 เปิดโฟลเดอร์", key=f"open_direct_f_{item['id']}_{idx}"): [cite: 775]
                    open_local_folder(item.get("folder_name", item["id"])) [cite: 775]

    with sub_tab1: [cite: 775]
        st.subheader("กรอกรายละเอียดเพื่อสร้าง RFQ") [cite: 775]
        current_ym = datetime.now().strftime('%Y%m') [cite: 775]
        prefix = f"RFQ-{current_ym}-" [cite: 775]
        count_current_month = sum(1 for item in st.session_state.rfq_history if item["id"].startswith(prefix)) [cite: 775]
        auto_rfq_id = f"{prefix}{(count_current_month + 1):04d}" [cite: 776]
        
        f_col1, f_col2 = st.columns([2, 1]) [cite: 776]
        with f_col1: [cite: 776]
            with st.form("rfq_form", clear_on_submit=True): [cite: 776]
                rfq_id = st.text_input("เลขที่ RFQ", value=auto_rfq_id) [cite: 776]
                project_name = st.text_input("ชื่อโครงการ (Project Name)", placeholder="เช่น โครงการติดตั้ง EV Charging Station") [cite: 776]
                
                if not st.session_state.requestors_list: [cite: 777]
                    st.error("⚠️ ยังไม่มีรายชื่อผู้ร้องขอในระบบ") [cite: 777]
                    selected_requestor = None [cite: 777]
                else: selected_requestor = st.selectbox("เลือกผู้ร้องขอ", st.session_state.requestors_list) [cite: 777]
                rfq_date = st.date_input("วันที่เปิด RFQ", datetime.now()) [cite: 778]
                details = st.text_area("รายละเอียดงาน / รายการที่ต้องการ") [cite: 778]
                deadline = st.date_input("วันส่งมอบที่ต้องการ", datetime.now()) [cite: 778]
                
                if st.form_submit_button("ส่ง RFQ / บันทึกตั้งค่า"): [cite: 778]
                    if rfq_id and selected_requestor: [cite: 779]
                        clean_rfq = rfq_id.strip() [cite: 779]
                        clean_project = project_name.strip() if project_name else "ทั่วไป" [cite: 779]
                        folder_name = f"{clean_rfq}_{clean_project}_{selected_requestor.strip()}" [cite: 779]
                        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']: folder_name = folder_name.replace(char, "_") [cite: 780]
                        
                        full_folder_path = os.path.join(BASE_DIR, folder_name) [cite: 780]
                        if not os.path.exists(full_folder_path): os.makedirs(full_folder_path) [cite: 781]
                                             
                        new_rfq = { [cite: 781]
                            "id": clean_rfq, "project": clean_project, "requestor": selected_requestor.strip(), [cite: 782]
                            "folder_name": full_folder_path, "date": str(rfq_date), "details": details, "deadline": str(deadline), [cite: 782]
                            "status": "กำลังขอราคา", "suppliers": [], [cite: 782]
                            "history_logs": [f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] สร้าง RFQ ในโฟลเดอร์: {full_folder_path}"] [cite: 783]
                        } [cite: 783]
                        st.session_state.rfq_history.append(new_rfq) [cite: 783]
                        save_data(st.session_state.rfq_history) [cite: 783]
                        st.success(f"บันทึกสำเร็จ!") [cite: 784]
                        st.rerun() [cite: 784]

    with sub_tab2: [cite: 784]
        if not st.session_state.rfq_history: [cite: 784]
            st.warning("ยังไม่มีข้อมูล RFQ ในระบบ กรุณาไปสร้างใบงานที่แท็บเปิด RFQ ใหม่ก่อนครับ") [cite: 784]
        else: [cite: 784]
            rfq_options = [f"{x['id']} [โครงการ: {x.get('project', 'ทั่วไป')}]" for x in st.session_state.rfq_history] [cite: 784]
            selected_display = st.selectbox("เลือกเลขที่ RFQ", rfq_options, key="rfq_select_t2") [cite: 785]
            selected_rfq_id = selected_display.split()[0] [cite: 785]
            current_rfq = next(x for x in st.session_state.rfq_history if x["id"] == selected_rfq_id) [cite: 785]
            target_folder = current_rfq.get("folder_name", selected_rfq_id) [cite: 785]
            if not os.path.isabs(target_folder): target_folder = os.path.join(BASE_DIR, target_folder) [cite: 785]
            
            st.info(f"📂 ที่อยู่โฟลเดอร์งาน: {target_folder}") [cite: 786]
            col_left, col_right = st.columns(2) [cite: 786]
            with col_left: [cite: 786]
                st.markdown("### ➕ บันทึกข้อมูลราคาซัพพลายเออร์") [cite: 786]
                with st.form("price_add_form", clear_on_submit=True): [cite: 786]
                    if not st.session_state.suppliers_master: [cite: 786]
                        st.error("กรุณาเพิ่มชื่อในหน้าข้อมูล Supplier ก่อนครับ") [cite: 787]
                        sup_name = None [cite: 787]
                    else: sup_name = st.selectbox("เลือก Supplier", [s["name"] for s in st.session_state.suppliers_master]) [cite: 787]
                    price = st.number_input("ราคาที่เสนอ (บาท)", min_value=0.0, step=100.0) [cite: 788]
                    terms = st.text_area("เงื่อนไขเพิ่มเติม") [cite: 788]
                    uploaded_file = st.file_uploader("แนบไฟล์ใบเสนอราคา", type=["pdf", "png", "jpg", "jpeg", "xlsx", "xls", "docx"]) [cite: 788]
                    
                    if st.form_submit_button("บันทึกราคาร้านนี้"): [cite: 788]
                        if sup_name: [cite: 789]
                            file_path_saved = "" [cite: 789]
                            if uploaded_file is not None: [cite: 789]
                                if not os.path.exists(target_folder): os.makedirs(target_folder) [cite: 790]
                                clean_filename = f"{sup_name}_{uploaded_file.name}".replace("/", "_").replace("\\", "_") [cite: 790]
                                file_path_saved = os.path.join(target_folder, clean_filename) [cite: 790]
                                with open(file_path_saved, "wb") as f: f.write(uploaded_file.getbuffer()) [cite: 791]
                                         
                            current_rfq["suppliers"].append({ [cite: 791]
                                "name": sup_name, "price": price, "terms": terms, "file_path": file_path_saved, [cite: 792]
                                "date_added": datetime.now().strftime('%Y-%m-%d %H:%M'), "items": [] [cite: 792]
                            }) [cite: 792]
                            current_rfq["history_logs"].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] เพิ่มราคา {sup_name} ยอด {price:,.2f} บาท") [cite: 793]
                            save_data(st.session_state.rfq_history) [cite: 793]
                            st.toast("บันทึกราคาเรียบร้อย!", icon="✅") [cite: 793]
                            st.rerun() [cite: 794]
            with col_right: [cite: 794]
                st.markdown("### ⚙️ เปลี่ยนสถานะใบงาน RFQ") [cite: 794]
                new_status = st.selectbox("สถานะ", ["กำลังขอราคา", "ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว", "สั่งซื้อเรียบร้อย (PO ออกแล้ว)", "ยกเลิกงาน"], index=["กำลังขอราคา", "ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว", "สั่งซื้อเรียบร้อย (PO ออกแล้ว)", "ยกเลิกงาน"].index(current_rfq["status"])) [cite: 794]
                if st.button("อัปเดตสถานะงาน"): [cite: 794]
                    if new_status != current_rfq["status"]: [cite: 795]
                        current_rfq["status"] = new_status [cite: 795]
                        current_rfq["history_logs"].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] เปลี่ยนสถานะเป็น: {new_status}") [cite: 795]
                        save_data(st.session_state.rfq_history) [cite: 795]
                        st.success("อัปเดตสถานะสำเร็จ") [cite: 796]
                        st.rerun() [cite: 796]

            st.markdown("---") [cite: 796]
            st.markdown("### ✏️ บันทึกรายการวัสดุและค่าแรงแยกย่อย (Unit Rate Breakdown)") [cite: 796]
            if not current_rfq.get("suppliers"): st.caption("⚠️ ต้องบันทึกชื่อซัพพลายเออร์และราคาโดยรวมฝั่งด้านบนก่อน") [cite: 796]
            elif not st.session_state.item_codes_master: st.error("⚠️ ยังไม่มีฐานข้อมูลวัสดุกลาง") [cite: 797]
            else: [cite: 797]
                sup_list_rfq = [s["name"] for s in current_rfq["suppliers"]] [cite: 797]
                selected_input_sup = st.selectbox("เลือกซัพพลายเออร์เพื่อบันทึกราคาแยกชิ้นงาน:", sup_list_rfq) [cite: 797]
                target_sup_obj = next(s for s in current_rfq["suppliers"] if s["name"] == selected_input_sup) [cite: 797]
                
                with st.form("unit_rate_input_form", clear_on_submit=True): [cite: 798]
                    item_choices = [f"[{i['code']}] {i['item_name']}" for i in st.session_state.item_codes_master] [cite: 798]
                    selected_item_display = st.selectbox("เลือกรายการวัสดุ (Item Code Center)", item_choices) [cite: 798]
                    target_code = selected_item_display.split("]")[0].replace("[", "") [cite: 798]
                    item_master_obj = next(i for i in st.session_state.item_codes_master if i["code"] == target_code) [cite: 799]
                    
                    st.caption(f"💡 หมวดหมู่: `{item_master_obj['category']}` | หน่วย: `{item_master_obj['unit']}`") [cite: 799]
                    it_col1, it_col2 = st.columns(2) [cite: 800]
                    i_mat_rate = it_col1.number_input("ราคาวัสดุหน่วย (บาท)", min_value=0.0, step=1.0) [cite: 800]
                    i_lab_rate = it_col2.number_input("ค่าแรงต่อหน่วย (บาท)", min_value=0.0, step=1.0) [cite: 800]
                    
                    if st.form_submit_button("➕ บันทึกรายการวัสดุนี้เข้าใบเสนอราคา"): [cite: 801]
                        if "items" not in target_sup_obj: target_sup_obj["items"] = [] [cite: 801]
                        target_sup_obj["items"].append({ [cite: 801]
                            "item_code": item_master_obj["code"], "category": item_master_obj["category"], [cite: 802]
                            "item_name": item_master_obj["item_name"], "unit": item_master_obj["unit"], [cite: 802]
                            "material_rate": i_mat_rate, "labor_rate": i_lab_rate, "total_rate": i_mat_rate + i_lab_rate, [cite: 802]
                            "date_updated": datetime.now().strftime('%d/%m/%Y') [cite: 802]
                        }) [cite: 803]
                        save_data(st.session_state.rfq_history) [cite: 803]
                        st.toast(f"บันทึกข้อมูลสำเร็จ!", icon="✅") [cite: 803]
                        st.rerun() [cite: 803]
                                 
                if target_sup_obj.get("items"): [cite: 804]
                    df_sup_items = pd.DataFrame(target_sup_obj["items"])[["item_code", "category", "item_name", "unit", "material_rate", "labor_rate", "total_rate", "date_updated"]] [cite: 804]
                    df_sup_items.columns = ["รหัสสินค้า", "หมวดหมู่", "รายการวัสดุ", "หน่วย", "ราคาวัสดุ/หน่วย", "ค่าแรง/หน่วย", "ราคารวมต่อหน่วย", "วันที่บันทึก"] [cite: 804]
                    st.dataframe(df_sup_items, use_container_width=True, hide_index=True) [cite: 805]

            st.markdown("---") [cite: 805]
            st.markdown("### 📊 ตารางเปรียบเทียบราคา ณ ปัจจุบัน") [cite: 805]
            if current_rfq["suppliers"]: [cite: 805]
                h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2, 1.5, 3, 1.5, 1.5]) [cite: 805]
                h_col1.markdown("**ชื่อร้านค้า**") [cite: 806]
                h_col2.markdown("**ราคาเสนอโดยรวม (บาท)**") [cite: 806]
                h_col3.markdown("**เงื่อนไขเพิ่มเติม**") [cite: 806]
                h_col4.markdown("**วันที่บันทึก**") [cite: 806]
                h_col5.markdown("**ไฟล์ใบเสนอราคา**") [cite: 806]
                st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True) [cite: 806]
                for idx, s in enumerate(current_rfq["suppliers"]): [cite: 807]
                    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([2, 1.5, 3, 1.5, 1.5]) [cite: 807]
                    r_col1.write(s["name"]) [cite: 807]
                    r_col2.write(f"{s['price']:,.2f}") [cite: 807]
                    r_col3.write(s["terms"] if s["terms"] else "-") [cite: 808]
                    r_col4.write(s["date_added"].split()[0]) [cite: 808]
                    
                    f_path = s.get("file_path", "") [cite: 808]
                    if f_path and not os.path.isabs(f_path): f_path = os.path.join(BASE_DIR, f_path) [cite: 808]
                    if f_path and os.path.exists(f_path): [cite: 809]
                        with open(f_path, "rb") as file_data: [cite: 809]
                            r_col5.download_button(label="📁 เปิด/ดาวน์โหลด", data=file_data.read(), file_name=os.path.basename(f_path), key=f"btn_dl_tab2_{selected_rfq_id}_{idx}") [cite: 809]
                    else: r_col5.caption("❌ ไม่มีไฟล์แนบ") [cite: 810]

    with sub_tab3: [cite: 810]
        if not st.session_state.rfq_history: st.warning("ยังไม่มีข้อมูล") [cite: 810]
        else: [cite: 810]
            for item in st.session_state.rfq_history: [cite: 810]
                with st.expander(f"📋 {item['id']} [โครงการ: {item.get('project', 'ทั่วไป')}] - Status: {item['status']}"): [cite: 810]
                    st.write(f"**รายละเอียดงาน:** {item['details']}") [cite: 810]
                    st.write(f"**ผู้ร้องขอ:** {item['requestor']} | **กำหนดส่งมอบ:** {item['deadline']}") [cite: 811]
                    st.markdown("**Timeline Log:**") [cite: 812]
                    for log in item.get("history_logs", []): st.text(log) [cite: 812]

    with sub_tab4: [cite: 812]
        st.markdown("### 👤 ระบบบริหารและจัดการรายชื่อผู้ร้องขอโครงการ") [cite: 812]
        u_col1, u_col2 = st.columns(2) [cite: 812]
        with u_col1: [cite: 812]
            st.markdown("#### **➕ บันทึกรายชื่อผู้ร้องขอใหม่**") [cite: 812]
            new_name = st.text_input("ชื่อ-นามสกุล ของเจ้าหน้าที่คนใหม่", key="tab4_add_user_input") [cite: 813]
            if st.button("💾 บันทึกรายชื่อเข้าสู่ระบบ", key="tab4_save_user_btn"): [cite: 813]
                if new_name: [cite: 813]
                    clean_name = new_name.strip() [cite: 813]
                    if clean_name not in st.session_state.requestors_list: [cite: 813]
                        st.session_state.requestors_list.append(clean_name) [cite: 814]
                        save_requestors(st.session_state.requestors_list) [cite: 814]
                        st.success(f"บันทึกสำเร็จ") [cite: 814]
                        st.rerun() [cite: 814]
                    else: st.warning("รายชื่อนี้มีอยู่ในระบบแล้ว") [cite: 815]
        with u_col2: [cite: 815]
            st.markdown("#### **❌ ลบรายชื่อออกจากฐานข้อมูล**") [cite: 815]
            if not st.session_state.requestors_list: st.caption("ไม่มีรายชื่อให้จัดการ") [cite: 815]
            else: [cite: 815]
                name_to_delete = st.selectbox("เลือกรายชื่อที่ต้องการคัดออก", st.session_state.requestors_list, key="tab4_del_user_select") [cite: 815]
                if st.button("🗑️ ยืนยันการลบชื่อนี้ออกจากคลัง", key="tab4_del_user_btn"): [cite: 815]
                    is_name_used = any(rfq.get("requestor") == name_to_delete for rfq in st.session_state.rfq_history) [cite: 816]
                    if is_name_used: st.error(f"❌ ไม่สามารถลบรายชื่อได้ เนื่องจากเคยนำไปเปิดใบงาน RFQ แล้ว") [cite: 816]
                    else: [cite: 816]
                        st.session_state.requestors_list.remove(name_to_delete) [cite: 816]
                        save_requestors(st.session_state.requestors_list) [cite: 817]
                        st.success(f"ลบเรียบร้อย") [cite: 817]
                        st.rerun() [cite: 817]

# =========================================================================
# 🏢 ข้อมูล Supplier
# =========================================================================
elif main_menu == "🏢 ข้อมูล Supplier": [cite: 817]
    st.title("🏢 ระบบฐานข้อมูลทะเบียน Supplier สำคัญ") [cite: 817]
    s_tab1, s_tab2, s_tab3 = st.tabs(["➕ เพิ่ม Supplier ใหม่", "🔍 ดูข้อมูลซัพพลายเออร์", "📍 ค้นหาตามพื้นที่รับงาน"]) [cite: 817]
    
    with s_tab1: [cite: 818]
        st.markdown("### ➕ เพิ่มข้อมูล Supplier และอัปโหลดหลักฐาน") [cite: 818]
        s_name = st.text_input("ชื่อซัพพลายเออร์ / ชื่อบริษัท", key=f"add_s_name_{st.session_state.sup_clear_counter}") [cite: 818]
        s_tax = st.text_input("เลขประจำตัวผู้เสียภาษี (Tax ID)", key=f"add_s_tax_{st.session_state.sup_clear_counter}") [cite: 818]
        
        st.markdown("**🌍 พื้นที่ที่สามารถรับงานได้:**") [cite: 818]
        st.info(st.session_state.areas_output_add) [cite: 818]
        if st.button("🗺️ เปิดหน้าต่างเลือกพื้นที่รับงาน (Popup)", key=f"btn_pop_areas_add_{st.session_state.sup_clear_counter}", icon="🌍"): [cite: 818]
            select_areas_dialog() [cite: 818]
             
        s_address = st.text_area("ที่อยู่บริษัท", key=f"add_s_address_{st.session_state.sup_clear_counter}") [cite: 819]
        s_credit = st.text_input("เครดิตเทอม", key=f"add_s_credit_{st.session_state.sup_clear_counter}") [cite: 819]
        s_info = st.text_area("หมายเหตุทั่วไป", key=f"add_s_info_{st.session_state.sup_clear_counter}") [cite: 819]
        
        st.markdown("#### 📄 เอกสารนิติบุคคลคู่ค้าสำคัญ") [cite: 819]
        file_pp20 = st.file_uploader("อัปโหลดไฟล์ ภ.พ.20", type=["pdf", "png", "jpg", "jpeg"], key=f"add_file_pp20_{st.session_state.sup_clear_counter}") [cite: 819]
        file_cert = st.file_uploader("อัปโหลดไฟล์ หนังสือรับรองบริษัท", type=["pdf", "png", "jpg", "jpeg"], key=f"add_file_cert_{st.session_state.sup_clear_counter}") [cite: 819]
        file_bb = st.file_uploader("อัปโหลดไฟล์ หน้าสมุกบัญชีธนาคาร (Book Bank)", type=["pdf", "png", "jpg", "jpeg"], key=f"add_file_bb_{st.session_state.sup_clear_counter}") [cite: 820]
        
        st.markdown("#### 👥 บุคคลผู้ติดต่อประสานงาน") [cite: 820]
        updated_contacts = [] [cite: 820]
        for i, contact in enumerate(st.session_state.temp_contacts): [cite: 820]
            st.markdown(f"**ผู้ติดต่อคนที่ {i+1}**") [cite: 820]
            c_c1, c_c2, c_c3, c_c4 = st.columns(4) [cite: 820]
            c_name = c_c1.text_input("ชื่อ", value=contact["name"], key=f"s_cn_{i}_{st.session_state.sup_clear_counter}") [cite: 820]
            c_phone = c_c2.text_input("เบอร์โทร", value=contact["phone"], key=f"s_cp_{i}_{st.session_state.sup_clear_counter}") [cite: 821]
            c_email = c_c3.text_input("Email", value=contact["email"], key=f"s_ce_{i}_{st.session_state.sup_clear_counter}") [cite: 821]
            c_line = c_c4.text_input("Line ID", value=contact["line"], key=f"s_cl_{i}_{st.session_state.sup_clear_counter}") [cite: 821]
            updated_contacts.append({"name": c_name, "phone": c_phone, "email": c_email, "line": c_line}) [cite: 821]
        st.session_state.temp_contacts = updated_contacts [cite: 821]
        
        if st.button("➕ เพิ่มรายชื่อผู้ติดต่ออีกคน"): [cite: 821]
            st.session_state.temp_contacts.append({"name": "", "phone": "", "email": "", "line": ""}) [cite: 822]
            st.rerun() [cite: 822]
            
        if st.button("💾 บันทึกข้อมูลขึ้นคลัง Supplier ถาวร"): [cite: 822]
            if s_name: [cite: 822]
                s_name = s_name.strip() [cite: 822]
                if any(x["name"] == s_name for x in st.session_state.suppliers_master): [cite: 822]
                    st.error("ชื่อซัพพลายเออร์รายนี้มีอยู่ในคลังแล้ว") [cite: 823]
                else: [cite: 823]
                    clean_dir = s_name [cite: 823]
                    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']: clean_dir = clean_dir.replace(char, "_") [cite: 823]
                    specific_folder = os.path.join(SUP_DOC_DIR, clean_dir) [cite: 824]
                    if not os.path.exists(specific_folder): os.makedirs(specific_folder) [cite: 824]
                    
                    p_pp20, p_cert, p_bb = "", "", "" [cite: 824]
                    if file_pp20: [cite: 825]
                        p_pp20 = os.path.join(specific_folder, f"ภพ20_{file_pp20.name}") [cite: 825]
                        with open(p_pp20, "wb") as f: f.write(file_pp20.getbuffer()) [cite: 825]
                    if file_cert: [cite: 825]
                        p_cert = os.path.join(specific_folder, f"หนังสือรับรอง_{file_cert.name}") [cite: 826]
                        with open(p_cert, "wb") as f: f.write(file_cert.getbuffer()) [cite: 826]
                    if file_bb: [cite: 826]
                        p_bb = os.path.join(specific_folder, f"บุ๊คแบงก์_{file_bb.name}") [cite: 826]
                        with open(p_bb, "wb") as f: f.write(file_bb.getbuffer()) [cite: 827]
                        
                    st.session_state.suppliers_master.append({ [cite: 827]
                        "name": s_name, "tax_id": s_tax, "address": s_address, "credit": s_credit, [cite: 827]
                        "service_areas": st.session_state.areas_output_add, "general_info": s_info, [cite: 828]
                        "pp20_path": p_pp20, "cert_path": p_cert, "bb_path": p_bb, [cite: 828]
                        "contacts": st.session_state.temp_contacts [cite: 828]
                    }) [cite: 828]
                    save_suppliers(st.session_state.suppliers_master) [cite: 829]
                    
                    st.session_state.sup_clear_counter += 1 [cite: 829]
                    st.session_state.areas_output_add = "ยังไม่ได้เลือกพื้นที่" [cite: 829]
                    st.session_state.temp_contacts = [{"name": "", "phone": "", "email": "", "line": ""}] [cite: 830]
                    st.success("บันทึกข้อมูลเข้าคลังและล้างหน้าฟอร์มเรียบร้อยแล้ว!") [cite: 830]
                    st.rerun() [cite: 830]
            else: st.error("กรุณากรอกชื่อบริษัทซัพพลายเออร์") [cite: 830]

    with s_tab2: [cite: 830]
        st.markdown("### 🔍 ศูนย์ประวัติและฐานข้อมูลข้อมูลซัพพลายเออร์ฉบับเต็ม") [cite: 830]
        col_pop1, col_pop2 = st.columns([2, 3]) [cite: 830]
        with col_pop1: [cite: 830]
            if st.button("🏢 คลิกเพื่อเลือกซัพพลายเออร์ (POPUP ค้นหา)", use_container_width=True, icon="🔍"): [cite: 831]
                select_supplier_popup() [cite: 831]
                
        if not st.session_state.selected_supplier_name: [cite: 831]
            st.info("💡 กรุณากดปุ่มด้านบนเพื่อเลือกซัพพลายเออร์ที่ต้องการเปิดดูข้อมูลโปรไฟล์ครับ") [cite: 831]
        else: [cite: 831]
            sup_name_target = st.session_state.selected_supplier_name [cite: 831]
            if not any(x["name"] == sup_name_target for x in st.session_state.suppliers_master): [cite: 832]
                st.session_state.selected_supplier_name = None [cite: 832]
                st.warning("ไม่พบข้อมูลซัพพลายเออร์ที่เลือก") [cite: 832]
            else: [cite: 832]
                sup = next(x for x in st.session_state.suppliers_master if x["name"] == sup_name_target) [cite: 832]
                idx_master = st.session_state.suppliers_master.index(sup) [cite: 833]
                
                st.markdown("---") [cite: 833]
                v_col1, v_col2 = st.columns([3, 2]) [cite: 833]
                with v_col1: [cite: 833]
                    st.markdown(f"## 🏢 {sup['name']}") [cite: 833]
                    st.write(f"**🔢 เลขประจำตัวผู้เสียภาษี (Tax ID):** {sup.get('tax_id','-')}") [cite: 834]
                    st.write(f"**⏳ ข้อตกลงเครดิตเทอม:** {sup.get('credit','-')}") [cite: 834]
                    st.write(f"**🌍 พื้นที่ที่สามารถรับงานได้:** {sup.get('service_areas','-')}") [cite: 834]
                    st.write(f"**📍 ที่อยู่สำนักงาน/โรงงาน:**\n{sup.get('address','-')}") [cite: 834]
                    st.write(f"**📝 ข้อมูลทั่วไป / หมายเหตุประกอบ:**\n{sup.get('general_info','-')}") [cite: 835]
                    
                    st.markdown("<br>", unsafe_allow_html=True) [cite: 835]
                    btn_c1, btn_c2 = st.columns(2) [cite: 835]
                    if btn_c1.button("📝 แก้ไขข้อมูลพื้นฐานซัพพลายเออร์", use_container_width=True, key=f"edit_sup_act_{idx_master}"): [cite: 835]
                        edit_supplier_popup(sup, idx_master) [cite: 836]
                        
                    if btn_c2.button(f"🗑️ ลบข้อมูล Supplier นี้ออกจากระบบ", use_container_width=True, key=f"del_master_view_{idx_master}"): [cite: 836]
                        for p_k in ["pp20_path", "cert_path", "bb_path"]: [cite: 836]
                            p_v = sup.get(p_k, "") [cite: 837]
                            if p_v and not os.path.isabs(p_v): p_v = os.path.join(BASE_DIR, p_v) [cite: 837]
                            if p_v and os.path.exists(p_v): [cite: 837]
                                try: os.remove(p_v) [cite: 838]
                                except: pass [cite: 838]
                        st.session_state.suppliers_master.remove(sup) [cite: 838]
                        save_suppliers(st.session_state.suppliers_master) [cite: 839]
                        st.session_state.selected_supplier_name = None [cite: 839]
                        st.success(f"ลบข้อมูลเรียบร้อย") [cite: 839]
                        st.rerun() [cite: 839]
                                 
                with v_col2: [cite: 839]
                    st.markdown("### 📂 คลังเอกสารนิติบุคคลแนบ") [cite: 840]
                    paths = {"pp": sup.get("pp20_path", ""), "cert": sup.get("cert_path", ""), "bb": sup.get("bb_path", "")} [cite: 840]
                    for k, v in paths.items(): [cite: 841]
                        if v and not os.path.isabs(v): paths[k] = os.path.join(BASE_DIR, v) [cite: 841]
                    
                    if paths["pp"] and os.path.exists(paths["pp"]): [cite: 841]
                        with open(paths["pp"], "rb") as f: st.download_button("📄 เปิดเอกสาร ภ.พ.20", f.read(), file_name=os.path.basename(paths["pp"]), key=f"view_pp_{idx_master}") [cite: 842]
                    else: st.caption("❌ ไม่มีเอกสาร ภ.พ.20 แนบไว้") [cite: 842]
                    if paths["cert"] and os.path.exists(paths["cert"]): [cite: 842]
                        with open(paths["cert"], "rb") as f: st.download_button("📄 เปิดหนังสือรับรองบริษัท", f.read(), file_name=os.path.basename(paths["cert"]), key=f"view_cert_{idx_master}") [cite: 842]
                    else: st.caption("❌ ไม่มีเอกสารหนังสือรับรองบริษัทแนบไว้") [cite: 843]
                    if paths["bb"] and os.path.exists(paths["bb"]): [cite: 843]
                        with open(paths["bb"], "rb") as f: st.download_button("📄 เปิดหน้าสมุดบัญชี (Book Bank)", f.read(), file_name=os.path.basename(paths["bb"]), key=f"view_bb_{idx_master}") [cite: 843]
                    else: st.caption("❌ ไม่มีเอกสาร Book Bank แนบไว้") [cite: 844]
                
                st.markdown("---") [cite: 844]
                c_head1, c_head2 = st.columns([4, 1]) [cite: 844]
                c_head1.markdown("#### 👥 บัญชีรายชื่อเจ้าหน้าที่/ผู้ติดต่อประจำบริษัท") [cite: 844]
                
                if c_head2.button("📝 แก้ไขรายชื่อผู้ติดต่อ", use_container_width=True, key=f"trigger_edit_contacts_{idx_master}"): [cite: 845]
                    st.session_state.edit_contacts_list = json.loads(json.dumps(sup.get("contacts", []))) [cite: 845]
                    if not st.session_state.edit_contacts_list: [cite: 845]
                        st.session_state.edit_contacts_list = [{"name": "", "phone": "", "email": "", "line": ""}] [cite: 845]
                    edit_contacts_popup(sup, idx_master) [cite: 846]
                
                if not sup.get("contacts") or not any(c.get("name") for c in sup["contacts"]): [cite: 846]
                    st.caption("ไม่ได้บันทึกรายชื่อผู้ติดต่อสำหรับซัพพลายเออร์รายนี้") [cite: 846]
                else: [cite: 846]
                    valid_contacts = [c for c in sup["contacts"] if c.get("name")] [cite: 847]
                    df_contacts = pd.DataFrame(valid_contacts) [cite: 847]
                    df_contacts = df_contacts[["name", "phone", "email", "line"]] [cite: 847]
                    df_contacts.columns = ["ชื่อผู้ติดต่อ", "เบอร์โทรศัพท์", "อีเมล (Email)", "Line ID"] [cite: 847]
                    st.dataframe(df_contacts, use_container_width=True, hide_index=True) [cite: 848]

    with s_tab3: [cite: 848]
        st.markdown("### 🗺️ ค้นหาตรวจสอบรายชื่อซัพพลายเออร์ตามพิกัดพื้นที่ปฏิบัติงาน") [cite: 848]
        st.caption("คลิกเพื่อเลือกหรือพิมพ์เสิร์ชรายจังหวัด ตัวระบบจะคัดกรองคู่ค้าจัดซื้อที่สามารถไปวิ่งหน้างานจุดพิกัดนั้นขึ้นมาสรุปให้ทันที") [cite: 848]
        
        if not st.session_state.suppliers_master: [cite: 848]
            st.warning("⚠️ ปัจจุบันไม่มีข้อมูลซัพพลายเออร์ในระบบคลังคู่ค้า กรุณาลงทะเบียนข้อมูลที่แท็บแรกก่อนครับ") [cite: 848]
        else: [cite: 848]
            col_pop_prov1, col_pop_prov2 = st.columns([2, 3]) [cite: 848]
            with col_pop_prov1: [cite: 849]
                if st.button("🎯 คลิกเพื่อเลือกจังหวัดไซต์งาน (POPUP ค้นหา)", use_container_width=True, icon="🎯"): [cite: 849]
                    select_search_province_popup() [cite: 849]
            
            if not st.session_state.get('selected_search_province'): [cite: 849]
                st.info("💡 กรุณากดปุ่มด้านบนเพื่อเปิดหน้าต่างเสิร์ชค้นหาและคลิกพิกัดจังหวัดที่ต้องการตรวจสอบครับ") [cite: 849]
            else: [cite: 849]
                target_search_prov = st.session_state.selected_search_province [cite: 850]
                st.markdown(f"### 📍 เขตพื้นที่สืบค้นไซต์งาน: **{target_search_prov}**") [cite: 850]
                
                belonging_reg_name = "" [cite: 850]
                for reg_k, provinces_list in THAI_REGIONS.items(): [cite: 850]
                    if target_search_prov in provinces_list: [cite: 851]
                        belonging_reg_name = reg_k [cite: 851]
                        break [cite: 851]
                
                matched_area_sups = [] [cite: 851]
                for s in st.session_state.suppliers_master: [cite: 852]
                    sup_areas = s.get("service_areas", "") [cite: 852]
                    if sup_areas == "ทุกจังหวัดทั่วประเทศ": [cite: 852]
                        matched_area_sups.append(s) [cite: 852]
                    elif target_search_prov in sup_areas: [cite: 853]
                        matched_area_sups.append(s) [cite: 853]
                    elif belonging_reg_name and f"ทั้งหมดใน{belonging_reg_name}" in sup_areas: [cite: 853]
                        matched_area_sups.append(s) [cite: 853]
                        
                st.markdown(f"พบซัพพลายเออร์ที่รองรับงานพิกัดเขตนี้ทั้งหมด **{len(matched_area_sups)}** บริษัท") [cite: 854]
                st.markdown("<hr style='margin:5px 0px 15px 0px;'>", unsafe_allow_html=True) [cite: 854]
                
                if not matched_area_sups: [cite: 854]
                    st.caption(f"❌ ปัจจุบันยังไม่มีข้อมูลบริษัทใดลงทะเบียนบริการครอบคลุมเขตพื้นที่จังหวัด {target_search_prov}") [cite: 855]
                else: [cite: 855]
                    display_area_data = [] [cite: 855]
                    for s in matched_area_sups: [cite: 855]
                        main_contact_person = "-" [cite: 855]
                        if s.get("contacts") and s["contacts"][0].get("name"): [cite: 856]
                            main_contact_person = f"{s['contacts'][0]['name']} ({s['contacts'][0].get('phone', '-')})" [cite: 856]
                                             
                        display_area_data.append({ [cite: 857]
                            "ชื่อบริษัท / ผู้ขาย": s["name"], [cite: 857]
                            "เลขประจำตัวผู้เสียภาษี (Tax ID)": s.get("tax_id", "-"), [cite: 857]
                            "ข้อตกลงเครดิตเทอม": s.get("credit", "-"), [cite: 858]
                            "ผู้ติดต่อหลักคนแรก": main_contact_person, [cite: 858]
                            "ขอบเขตพื้นที่บริการทั้งหมดที่บันทึก": s.get("service_areas", "-") [cite: 858]
                        }) [cite: 858]
                        
                    df_area_report = pd.DataFrame(display_area_data) [cite: 859]
                    st.dataframe(df_area_report, use_container_width=True, hide_index=True) [cite: 859]

# =========================================================================
# 📊 BOQ Supplier
# =========================================================================
elif main_menu == "📊 BOQ Supplier": [cite: 859]
    st.title("📊 BOQ Supplier • ศูนย์วิเคราะห์เปรียบเทียบและสืบค้นราคา") [cite: 859]
    boq_tab1, boq_tab2, boq_tab3 = st.tabs(["📈 เปรียบเทียบใบเสนอราคาประจำโครงการ", "🔍 ค้นหาประวัติ Unit Rate / Item", "➕ บันทึกราคาตรงเข้าคลัง (ไม่อ้างอิง RFQ)"]) [cite: 859]
    
    with boq_tab1: [cite: 860]
        if not st.session_state.rfq_history: st.warning("ยังไม่มีข้อมูล RFQ ในระบบ") [cite: 860]
        else: [cite: 860]
            rfq_options = [f"{x['id']} [โครงการ: {x.get('project', 'ทั่วไป')}]" for x in st.session_state.rfq_history] [cite: 860]
            selected_display = st.selectbox("เลือกหมายเลข RFQ เพื่อเปิดดูตารางเปรียบเทียบราคา BOQ", rfq_options, key="boq_rfq_select") [cite: 860]
            selected_rfq_id = selected_display.split()[0] [cite: 860]
            current_rfq = next(x for x in st.session_state.rfq_history if x["id"] == selected_rfq_id) [cite: 861]
            
            st.info(f"📋 **หัวข้อใบงาน:** {current_rfq['details']} | **ผู้ร้องขอ:** {current_rfq['requestor']} | **สถานะ:** {current_rfq['status']}") [cite: 862]
            st.markdown("### 📈 ตารางเปรียบเทียบราคาเสนอจากทุก Supplier") [cite: 862]
            
            if not current_rfq.get("suppliers"): st.caption("เคสนี้ยังไม่มีข้อมูลการเสนอราคาจากซัพพลายเออร์บันทึกไว้") [cite: 862]
            else: [cite: 862]
                sorted_sups = sorted(current_rfq["suppliers"], key=lambda x: x["price"]) [cite: 862]
                h_c1, h_c2, h_c3, h_c4, h_c5 = st.columns([2, 1.5, 3, 1.5, 1.5]) [cite: 863]
                h_c1.markdown("**ชื่อร้านค้า/ซัพพลายเออร์**") [cite: 863]
                h_c2.markdown("**ราคารวมสุทธิ (บาท)**") [cite: 863]
                h_c3.markdown("**เงื่อนไข / เครดิตเทอม**") [cite: 863]
                h_c4.markdown("**วันที่บันทึกราคานี้**") [cite: 863]
                h_c5.markdown("**เปิดเอกสารแนบ**") [cite: 863]
                st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True) [cite: 864]
                
                for idx, s in enumerate(sorted_sups): [cite: 864]
                    r_c1, r_c2, r_c3, r_c4, r_c5 = st.columns([2, 1.5, 3, 1.5, 1.5]) [cite: 864]
                    if idx == 0 and len(sorted_sups) > 1: r_c1.write(f"🥇 **{s['name']}** (ราคาดีที่สุด)") [cite: 865]
                    else: r_c1.write(s["name"]) [cite: 865]
                    r_c2.write(f"{s['price']:,.2f}") [cite: 865]
                    r_c3.write(s["terms"] if s["terms"] else "-") [cite: 865]
                    r_c4.write(s["date_added"]) [cite: 865]
                                     
                    f_p = s.get("file_path", "") [cite: 866]
                    if f_p and not os.path.isabs(f_p): f_p = os.path.join(BASE_DIR, f_p) [cite: 866]
                    if f_p and os.path.exists(f_p): [cite: 867]
                        with open(f_p, "rb") as f: r_c5.download_button(label="📁 เปิดดูไฟล์ใบเสนอราคา", data=f.read(), file_name=os.path.basename(f_p), key=f"dl_boq_view_{idx}") [cite: 867]
                    else: r_c5.caption("❌ ไม่มีไฟล์แนบ") [cite: 867]

    with boq_tab2: [cite: 867]
        st.markdown("### 🔍 ค้นหาและบริหารจัดการประวัติราคาวัสดุ-ค่าแรงแยกรายการ") [cite: 867]
        st.caption("💡 พี่สามารถติ๊กถูกหน้าข้อที่ต้องการ (เลือกได้ทีละ 1 ข้อ) เพื่อเปิดเครื่องมือแก้ไขข้อมูลทั่วไป/เปลี่ยนซัพพลายเออร์ หรือกดลบรายการนั้นออกครับ") [cite: 867]
        
        search_lay1, search_lay2 = st.columns([4, 1]) [cite: 868]
        search_query = search_lay1.text_input("ค้นหาประวัติราคา", placeholder="พิมพ์ชื่อรายการวัสดุ หมวดหมู่ หรือชื่อร้านค้า เช่น CV 1C-150sq.mm", label_visibility="collapsed") [cite: 868]
        
        flat_records = [] [cite: 868]
        for rfq_idx, rfq in enumerate(st.session_state.rfq_history): [cite: 868]
            for sup_idx, sup in enumerate(rfq.get("suppliers", [])): [cite: 868]
                for item_idx, item in enumerate(sup.get("items", [])): [cite: 868]
                    flat_records.append({ [cite: 869]
                        "source_type": "rfq", [cite: 869]
                        "rfq_id": rfq["id"], [cite: 869]
                        "sup_name": sup["name"], [cite: 869]
                        "item_code": item.get("item_code", ""), [cite: 870]
                        "index_keys": (rfq_idx, sup_idx, item_idx), [cite: 870]
                        "หมวดหมู่": item.get("category", "ทั่วไป"), [cite: 870]
                        "รายการวัสดุ": item.get("item_name", "-"), [cite: 871]
                        "ชื่อบริษัท/ผู้ขาย": sup["name"], [cite: 871]
                        "หน่วย": item.get("unit", "-"), [cite: 871]
                        "ราคาวัสดุ / หน่วย (บาท)": float(item.get("material_rate", 0.0)), [cite: 871]
                        "ค่าแรง/หน่วย (บาท)": float(item.get("labor_rate", 0.0)), [cite: 872]
                        "ราคารวมต่อหน่วย (บาท)": float(item.get("total_rate", 0.0)), [cite: 872]
                        "วันที่อัปเดตราคา": item.get("date_updated", "-"), [cite: 872]
                        "อ้างอิงแหล่งข้อมูล": f"RFQ: {rfq['id']}" [cite: 872]
                    }) [cite: 872]
                    
        for sa_idx, item in enumerate(st.session_state.standalone_prices): [cite: 873]
            flat_records.append({ [cite: 873]
                "source_type": "standalone", [cite: 873]
                "index_keys": sa_idx, [cite: 873]
                "หมวดหมู่": item.get("category", "ทั่วไป"), [cite: 874]
                "รายการวัสดุ": item.get("item_name", "-"), [cite: 874]
                "ชื่อบริษัท/ผู้ขาย": item.get("supplier_name", "-"), [cite: 874]
                "หน่วย": item.get("unit", "-"), [cite: 874]
                "ราคาวัสดุ / หน่วย (บาท)": float(item.get("material_rate", 0.0)), [cite: 874]
                "ค่าแรง/หน่วย (บาท)": float(item.get("labor_rate", 0.0)), [cite: 875]
                "ราคารวมต่อหน่วย (บาท)": float(item.get("total_rate", 0.0)), [cite: 875]
                "วันที่อัปเดตราคา": item.get("date_updated", "-"), [cite: 875]
                "อ้างอิงแหล่งข้อมูล": "Standalone (คลังตรง)" [cite: 875]
            }) [cite: 875]
            
        if not flat_records: [cite: 875]
            st.info("💡 ปัจจุบันยังไม่มีข้อมูลรายการวัสดุแยกย่อยในคลังระบบ") [cite: 876]
        else: [cite: 876]
            if search_query: [cite: 876]
                q = search_query.strip().lower() [cite: 876]
                filtered_records = [r for r in flat_records if q in r["รายการวัสดุ"].lower() or q in r["หมวดหมู่"].lower() or q in r["ชื่อบริษัท/ผู้ขาย"].lower()] [cite: 876]
            else: [cite: 876]
                filtered_records = flat_records [cite: 877]
                
            st.markdown(f"พบรายการราคาวัสดุทั้งหมด **{len(filtered_records)}** รายการ") [cite: 877]
            
            if filtered_records: [cite: 877]
                df_history = pd.DataFrame(filtered_records) [cite: 877]
                df_history.insert(0, "เลือกรายการ 🎯", False) [cite: 878]
                
                show_cols = ["เลือกรายการ 🎯", "หมวดหมู่", "รายการวัสดุ", "ชื่อบริษัท/ผู้ขาย", "หน่วย", "ราคาวัสดุ / หน่วย (บาท)", "ค่าแรง/หน่วย (บาท)", "ราคารวมต่อหน่วย (บาท)", "วันที่อัปเดตราคา", "อ้างอิงแหล่งข้อมูล"] [cite: 878]
                                 
                edited_df = st.data_editor( [cite: 879]
                    df_history[show_cols], [cite: 879]
                    use_container_width=True, [cite: 879]
                    hide_index=True, [cite: 879]
                    column_config={ [cite: 879]
                        "เลือกรายการ 🎯": st.column_config.CheckboxColumn(required=True), [cite: 880]
                        "หมวดหมู่": st.column_config.TextColumn(disabled=True), [cite: 880]
                        "รายการวัสดุ": st.column_config.TextColumn(disabled=True), [cite: 880]
                        "ชื่อบริษัท/ผู้ขาย": st.column_config.TextColumn(disabled=True), [cite: 880]
                        "หน่วย": st.column_config.TextColumn(disabled=True), [cite: 881]
                        "ราคาวัสดุ / หน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True), [cite: 881]
                        "ค่าแรง/หน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True), [cite: 881]
                        "ราคารวมต่อหน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True), [cite: 881]
                        "วันที่อัปเดตราคา": st.column_config.TextColumn(disabled=True), [cite: 882]
                        "อ้างอิงแหล่งข้อมูล": st.column_config.TextColumn(disabled=True) [cite: 882]
                    } [cite: 882]
                ) [cite: 882]
                
                checked_rows = edited_df[edited_df["เลือกรายการ 🎯"] == True] [cite: 883]
                
                if len(checked_rows) > 1: [cite: 883]
                    st.warning("⚠️ พี่ติ๊กเลือกพร้อมกันหลายข้อเกินไปครับ กรุณาเลือกติ๊กถูกแค่ 'ข้อเดียว' ที่ต้องการจัดการครับ") [cite: 883]
                elif len(checked_rows) == 1: [cite: 883]
                    st.markdown("---") [cite: 884]
                    target_idx = checked_rows.index[0] [cite: 884]
                    target_row = filtered_records[target_idx] [cite: 884]
                    
                    st.markdown(f"### ⚙️ เครื่องมือจัดการ: *{target_row['รายการวัสดุ']}*") [cite: 884]
                                 
                    if st.session_state.suppliers_master: [cite: 885]
                        master_sups = [s["name"] for s in st.session_state.suppliers_master] [cite: 885]
                        if target_row["ชื่อบริษัท/ผู้ขาย"] not in master_sups: [cite: 886]
                            master_sups.append(target_row["ชื่อบริษัท/ผู้ขาย"]) [cite: 886]
                        current_sup_idx = master_sups.index(target_row["ชื่อบริษัท/ผู้ขาย"]) [cite: 886]
                    else: [cite: 886]
                        master_sups = [target_row["ชื่อบริษัท/ผู้ขาย"]] [cite: 887]
                        current_sup_idx = 0 [cite: 887]
                    
                    with st.form("edit_single_record_form", clear_on_submit=False): [cite: 887]
                        col_e1, col_e2 = st.columns(2) [cite: 888]
                        with col_e1: [cite: 888]
                            edit_sup = st.selectbox("📝 แก้ไข/เปลี่ยนชื่อผู้ขาย (Supplier)", master_sups, index=current_sup_idx) [cite: 888]
                            edit_cat = st.selectbox("แก้ไขหมวดหมู่งาน", st.session_state.categories_list, index=st.session_state.categories_list.index(target_row["หมวดหมู่"]) if target_row["หมวดหมู่"] in st.session_state.categories_list else 0) [cite: 888]
                            edit_name = st.text_input("แก้ไขรายการวัสดุ / รายละเอียดพัสดุ", value=target_row["รายการวัสดุ"]) [cite: 889]
                        
                        with col_e2: [cite: 889]
                            edit_unit = st.selectbox("แก้ไขหน่วยนับพัสดุ", st.session_state.units_list, index=st.session_state.units_list.index(target_row["หน่วย"]) if target_row["หน่วย"] in st.session_state.units_list else 0) [cite: 890]
                            edit_mat = st.number_input("แก้ไขราคาวัสดุ/หน่วย (บาท)", min_value=0.0, value=target_row["ราคาวัสดุ / หน่วย (บาท)"], format="%.2f", step=1.0) [cite: 890]
                            edit_lab = st.number_input("แก้ไขค่าแรงต่อหน่วย (บาท)", min_value=0.0, value=target_row["ค่าแรง/หน่วย (บาท)"], format="%.2f", step=1.0) [cite: 890]
                        
                        st.markdown("<br>", unsafe_allow_html=True) [cite: 891]
                        btn_space1, btn_space2 = st.columns([3, 1]) [cite: 891]
                                                 
                        if btn_space1.form_submit_button("💾 บันทึกการแก้ไขข้อมูลทั้งหมดของรายการนี้", use_container_width=True): [cite: 892]
                            if target_row["source_type"] == "rfq": [cite: 892]
                                r_idx, s_idx, i_idx = target_row["index_keys"] [cite: 893]
                                st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["name"] = edit_sup [cite: 893]
                                item_ptr = st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"][i_idx] [cite: 893]
                                item_ptr["category"] = edit_cat [cite: 894]
                                item_ptr["item_name"] = edit_name [cite: 894]
                                item_ptr["unit"] = edit_unit [cite: 894]
                                item_ptr["material_rate"] = edit_mat [cite: 895]
                                item_ptr["labor_rate"] = edit_lab [cite: 895]
                                item_ptr["total_rate"] = edit_mat + edit_lab [cite: 895]
                                item_ptr["date_updated"] = datetime.now().strftime('%d/%m/%Y') [cite: 896]
                                
                            elif target_row["source_type"] == "standalone": [cite: 896]
                                sa_idx = target_row["index_keys"] [cite: 897]
                                item_ptr = st.session_state.standalone_prices[sa_idx] [cite: 897]
                                item_ptr["supplier_name"] = edit_sup [cite: 897]
                                item_ptr["category"] = edit_cat [cite: 898]
                                item_ptr["item_name"] = edit_name [cite: 898]
                                item_ptr["unit"] = edit_unit [cite: 898]
                                item_ptr["material_rate"] = edit_mat [cite: 899]
                                item_ptr["labor_rate"] = edit_lab [cite: 899]
                                item_ptr["total_rate"] = edit_mat + edit_lab [cite: 899]
                                item_ptr["date_updated"] = datetime.now().strftime('%d/%m/%Y') [cite: 900]
                                
                            save_data(st.session_state.rfq_history) [cite: 900]
                            save_standalone_prices(st.session_state.standalone_prices) [cite: 901]
                            st.toast("อัปเดตข้อมูลและราคาพัสดุสำเร็จเรียบร้อย!", icon="✅") [cite: 901]
                            st.rerun() [cite: 901]
                            
                        if btn_space2.form_submit_button("🗑️ ลบรายการนี้ออก", use_container_width=True, type="primary"): [cite: 902]
                            if target_row["source_type"] == "rfq": [cite: 902]
                                r_idx, s_idx, i_idx = target_row["index_keys"] [cite: 902]
                                st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"].pop(i_idx) [cite: 903]
                            elif target_row["source_type"] == "standalone": [cite: 903]
                                sa_idx = target_row["index_keys"] [cite: 903]
                                st.session_state.standalone_prices.pop(sa_idx) [cite: 904]
                                
                            save_data(st.session_state.rfq_history) [cite: 904]
                            save_standalone_prices(st.session_state.standalone_prices) [cite: 905]
                            st.toast("ลบรายการประวัติราคาเรียบร้อยแล้ว!", icon="🗑️") [cite: 905]
                            st.rerun() [cite: 905]

    with boq_tab3: [cite: 905]
        st.markdown("### ➕ บันทึกข้อมูลวัสดุตรงเข้าคลังราคา (ไม่อ้างอิงใบงาน RFQ)") [cite: 905]
        if not st.session_state.item_codes_master: st.error("⚠️ ยังไม่มีฐานข้อมูลวัสดุกลาง") [cite: 906]
        else: [cite: 906]
            form_layout_c1, form_layout_c2 = st.columns([2, 1]) [cite: 906]
            with form_layout_c1: [cite: 906]
                with st.form("standalone_input_form", clear_on_submit=True): [cite: 906]
                    if not st.session_state.suppliers_master: [cite: 906]
                        st.error("⚠️ ยังไม่มีรายชื่อ Supplier ในระบบ") [cite: 907]
                        selected_sup_name = None [cite: 907]
                    else: selected_sup_name = st.selectbox("ชื่อบริษัท / ผู้ขาย", [s["name"] for s in st.session_state.suppliers_master]) [cite: 907]
                    
                    item_choices_boq = [f"[{i['code']}] {i['item_name']}" for i in st.session_state.item_codes_master] [cite: 908]
                    selected_item_boq = st.selectbox("เลือกรายการวัสดุ (Item Code Center)", item_choices_boq) [cite: 908]
                    target_code_boq = selected_item_boq.split("]")[0].replace("[", "") [cite: 908]
                    item_master_boq_obj = next(i for i in st.session_state.item_codes_master if i["code"] == target_code_boq) [cite: 908]
                    
                    st.caption(f"💡 หมวดหมู่: `{item_master_boq_obj['category']}` | หน่วย: `{item_master_boq_obj['unit']}`") [cite: 909]
                    st_mat_rate = st.number_input("ราคาวัสดุหน่วย (บาท)", min_value=0.0, step=0.01, format="%.2f") [cite: 910]
                    st_lab_rate = st.number_input("ค่าแรงต่อหน่วย (บาท)", min_value=0.0, step=0.01, format="%.2f") [cite: 910]
                    st_date = st.date_input("วันที่ได้รับราคา", datetime.now()) [cite: 910]
                    
                    st.markdown("<br>", unsafe_allow_html=True) [cite: 911]
                    if st.form_submit_button("🟩 บันทึกข้อมูลเข้าคลังราคา"): [cite: 911]
                        if selected_sup_name: [cite: 911]
                            date_str = st_date.strftime('%d/%m/%Y') if hasattr(st_date, 'strftime') else str(st_date) [cite: 912]
                            st.session_state.standalone_prices.append({ [cite: 912]
                                "item_code": item_master_boq_obj["code"], "category": item_master_boq_obj["category"], [cite: 912]
                                "item_name": item_master_boq_obj["item_name"], "supplier_name": selected_sup_name, [cite: 913]
                                "unit": item_master_boq_obj["unit"], "material_rate": st_mat_rate, "labor_rate": st_lab_rate, [cite: 913]
                                "total_rate": st_mat_rate + st_lab_rate, "date_updated": date_str [cite: 914]
                            }) [cite: 914]
                            save_standalone_prices(st.session_state.standalone_prices) [cite: 914]
                            st.success(f"💾 จัดเก็บเรียบร้อย!") [cite: 914]
                            st.rerun() [cite: 915]

# =========================================================================
# 🗂️ บริหาร Item Code
# =========================================================================
elif main_menu == "🗂️ บริหาร Item Code": [cite: 915]
    st.title("🗂️ ศูนย์บริหารคลังฐานข้อมูลสินค้าและรหัสสินค้ากลาง (Item Code Master)") [cite: 915]
    item_tab1, item_tab2 = st.tabs(["➕ เพิ่ม Item Code มาตรฐานใหม่", "📋 ทำเนียบสืบค้นตรวจสอบรหัสทั้งหมด"]) [cite: 915]
    
    with item_tab1: [cite: 915]
        st.markdown("### ➕ เพิ่มพัสดุและรหัสสินค้าใหม่เข้าสู่ระบบ") [cite: 915]
        
        cat_lay1, cat_lay2 = st.columns([5, 1]) [cite: 915]
        with cat_lay1: [cite: 916]
            i_cat = st.selectbox( [cite: 916]
                "1. เลือกหมวดหมู่งาน / กลุ่มวัสดุ ก่อนเป็นอันดับแรก", [cite: 917]
                st.session_state.categories_list, [cite: 917]
                help="💡 สามารถพิมพ์ชื่อเพื่อเสิร์ชหาหมวดหมู่เดิมด่วนได้ทันทีครับ" [cite: 917]
            ) [cite: 917]
        with cat_lay2: [cite: 917]
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True) [cite: 917]
            if st.button("➕ ลงทะเบียนหมวดหมู่", use_container_width=True, help="เปิดหน้าต่างลงทะเบียนเพิ่มกลุ่มงานชิ้นใหม่"): [cite: 917]
                add_category_dialog() [cite: 918]
                
        if i_cat: [cite: 918]
            prefix_char = i_cat[0] [cite: 918]
            prefix = f"{prefix_char}-" [cite: 918]
            
            max_seq = 0 [cite: 918]
            for item in st.session_state.item_codes_master: [cite: 919]
                code_str = item.get("code", "") [cite: 919]
                if code_str.startswith(prefix): [cite: 919]
                    try: [cite: 919]
                        current_num = int(code_str.split("-")[1]) [cite: 919]
                        if current_num > max_seq: [cite: 920]
                            max_seq = current_num [cite: 920]
                    except (IndexError, ValueError): [cite: 920]
                        pass [cite: 920]
            
            next_itm_seq = max_seq + 1 [cite: 921]
            auto_itm_code = f"{prefix}{next_itm_seq:04d}" [cite: 921]
        else: [cite: 921]
            auto_itm_code = "ITM-0001" [cite: 921]
            
        st.markdown("---") [cite: 921]
        st.markdown("##### 📝 รายละเอียดรหัสสินค้าใหม่") [cite: 921]
        
        i_code = st.text_input("รหัสสินค้า (Item Code)", value=auto_itm_code) [cite: 922]
        i_name = st.text_input("2. รายการวัสดุ / รายละเอียดพัสดุ (Item Description)", placeholder="เช่น CV 1C-150sq.mm (1Core) 0.6/1KV") [cite: 923]
        
        u_lay1, u_lay2 = st.columns([5, 1]) [cite: 923]
        with u_lay1: [cite: 923]
            i_unit = st.selectbox("3. หน่วยนับพัสดุ (Unit)", st.session_state.units_list) [cite: 923]
        with u_lay2: [cite: 923]
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True) [cite: 923]
            if st.button("➕ ลงทะเบียนหน่วย", use_container_width=True, help="เปิดหน้าต่างลงทะเบียนเพิ่มหน่วยนับชิ้นใหม่"): [cite: 923]
                add_unit_dialog() [cite: 924]
                
        st.markdown("<br>", unsafe_allow_html=True) [cite: 924]
        
        if st.button("💾 บันทึกรหัสพัสดุนี้เข้าคลังมาสเตอร์", use_container_width=True, type="primary"): [cite: 924]
            if i_code and i_name: [cite: 924]
                i_code = i_code.strip() [cite: 924]
                i_name = i_name.strip() [cite: 925]
                
                if any(x["code"] == i_code for x in st.session_state.item_codes_master): [cite: 925]
                    st.error(f"❌ ไม่สามารถบันทึกได้ เนื่องจากรหัสสินค้า '{i_code}' มีอยู่ในระบบแล้ว") [cite: 925]
                else: [cite: 925]
                    st.session_state.item_codes_master.append({ [cite: 926]
                        "code": i_code, [cite: 926]
                        "category": i_cat, [cite: 926]
                        "item_name": i_name, [cite: 926]
                        "unit": i_unit [cite: 927]
                    }) [cite: 927]
                    save_item_codes(st.session_state.item_codes_master) [cite: 927]
                    st.toast(f"✅ บันทึกรหัสสินค้า {i_code} เข้าสารบบกลางเรียบร้อย!", icon="🎉") [cite: 927]
                    st.rerun() [cite: 927]
            else: [cite: 927]
                st.error("❌ กรุณากรอกรหัสสินค้าและรายละเอียดพัสดุให้ครบถ้วนก่อนกดบันทึก") [cite: 928]

    with item_tab2: [cite: 928]
        if not st.session_state.item_codes_master: [cite: 928]
            st.info("💡 ปัจจุบันยังไม่มีข้อมูลวัสดุในคลัง") [cite: 928]
        else: [cite: 928]
            df_items_master = pd.DataFrame(st.session_state.item_codes_master) [cite: 928]
            df_display = df_items_master[["code", "category", "item_name", "unit"]] [cite: 928]
            df_display.columns = ["รหัสสินค้า (Item Code)", "หมวดหมู่พัสดุ", "รายการวัสดุ / รายละเอียด", "หน่วยนับ (Unit)"] [cite: 929]
            st.dataframe(df_display, use_container_width=True, hide_index=True) [cite: 929]
            
            st.markdown("---") [cite: 929]
            item_list_del = [f"[{i['code']}] {i['item_name']}" for i in st.session_state.item_codes_master] [cite: 929]
            selected_item_del_display = st.selectbox("เลือกรหัสพัสดุที่ต้องการคัดออก:", item_list_del) [cite: 929]
            
            if st.button("🗑️ ยืนยันการลบรหัสสินค้าออกจากคลังหลัก"): [cite: 930]
                target_del_code = selected_item_del_display.split("]")[0].replace("[", "") [cite: 930]
                is_item_used_rfq = any(item.get("item_code") == target_del_code for rfq in st.session_state.rfq_history for sup in rfq.get("suppliers", []) for item in sup.get("items", [])) [cite: 930]
                is_item_used_standalone = any(x.get("item_code") == target_del_code for x in st.session_state.standalone_prices) [cite: 930]
                                 
                if is_item_used_rfq or is_item_used_standalone: [cite: 931]
                    st.error("❌ ไม่สามารถลบได้ เนื่องจากรหัสนี้ถูกนำไปใช้งานบันทึกราคาในประวัติจัดซื้อแล้ว") [cite: 931]
                else: [cite: 931]
                    item_to_remove = next(i for i in st.session_state.item_codes_master if i["code"] == target_del_code) [cite: 932]
                    st.session_state.item_codes_master.remove(item_to_remove) [cite: 932]
                    save_item_codes(st.session_state.item_codes_master) [cite: 932]
                    st.success(f"ลบรหัสสินค้าเรียบร้อย") [cite: 932]
                    st.rerun() [cite: 932]

# =========================================================================
# 📝 จัดทำ BOQ เพื่อเสนอ (แยกหมวดหมู่และส่งซิงก์ Google Drive อัตโนมัติ)
# =========================================================================
elif main_menu == "📝 จัดทำ BOQ เพื่อเสนอ": [cite: 932]
    st.title("📝 ระบบจัดทำใบเสนอราคาและประมาณการ BOQ ขาออก") [cite: 933]
    
    pur_tab1, pur_tab2 = st.tabs(["📋 ทะเบียนใบเสนอราคา (PUR)", "➕ สร้างเอกสารเสนอราคาโครงการใหม่"]) [cite: 933]
    
    with pur_tab1: [cite: 933]
        st.subheader("📋 ประวัติรายการเสนองานและประมาณการราคาขาออกทั้งหมด") [cite: 933]
        if not st.session_state.pur_proposals: [cite: 933]
            st.info("💡 ปัจจุบันยังไม่มีการสร้างเอกสารเสนอราคา PUR ในคลังระบบ") [cite: 933]
        else: [cite: 933]
            summary_pur_data = [] [cite: 933]
            for proposal in st.session_state.pur_proposals: [cite: 934]
                total_proposal_price = sum(float(item.get("total_price", 0.0)) for item in proposal.get("items", [])) [cite: 934]
                summary_pur_data.append({ [cite: 934]
                    "เลขที่ใบเสนอราคา": proposal["id"], [cite: 934]
                    "ชื่อโครงการ / ไไซต์งาน": proposal.get("project_name", "-"), [cite: 934]
                    "ชื่อลูกค้า / บริษัท": proposal.get("client_name", "-"), [cite: 935]
                    "ผู้ร้องขอโครงการ": proposal.get("requestor", "-"), [cite: 935]
                    "วันที่ออกเอกสาร": proposal.get("date", "-"), [cite: 935]
                    "จำนวนรายการวัสดุ": len(proposal.get("items", [])), [cite: 935]
                    "มูลค่ารวมสุทธิ (บาท)": total_proposal_price [cite: 936]
                }) [cite: 936]
            
            df_pur_report = pd.DataFrame(summary_pur_data) [cite: 936]
            st.dataframe(df_pur_report, use_container_width=True, hide_index=True, column_config={"มูลค่ารวมสุทธิ (บาท)": st.column_config.NumberColumn(format="%,.2f")}) [cite: 936]
            
            st.markdown("---") [cite: 936]
            st.markdown("##### 🎯 เลือกเอกสารเพื่อลงรายละเอียดพัสดุรายชิ้นงาน หรือพิมพ์เอกสาร PDF") [cite: 937]
            pur_options = [f"{p['id']} | โครงการ: {p['project_name']}" for p in st.session_state.pur_proposals] [cite: 938]
            selected_pur_option = st.selectbox("เลือกเลขที่เอกสาร PUR ที่ต้องการจัดการ:", pur_options) [cite: 938]
            
            if selected_pur_option: [cite: 938]
                target_pur_id = selected_pur_option.split(" | ")[0] [cite: 938]
                curr_pur_obj = next(p for p in st.session_state.pur_proposals if p["id"] == target_pur_id) [cite: 938]
                
                st.info(f"📁 **กำลังจัดการเอกสาร:** {curr_pur_obj['id']} | **โครงการ:** {curr_pur_obj['project_name']} | **ลูกค้า:** {curr_pur_obj['client_name']} | **ผู้ร้องขอ:** {curr_pur_obj.get('requestor', '-')}") [cite: 939]
                
                st.markdown("#### ➕ เพิ่มรายการวัสดุและคำนวณราคาลงใน BOQ เสนอราคา") [cite: 939]
                
                if not st.session_state.item_codes_master: [cite: 940]
                    st.error("⚠️ ต้องไปลงทะเบียนไอเทมที่หน้า 'บริหาร Item Code' ก่อนครับ") [cite: 940]
                else: [cite: 940]
                    item_choices = [f"[{i['code']}] {i['item_name']} ({i['unit']})" for i in st.session_state.item_codes_master] [cite: 941]
                    sel_item_choice = st.selectbox("ดึงรายการจากรหัสพัสดุกลาง:", item_choices) [cite: 941]
                    
                    item_code_extracted = sel_item_choice.split("]")[0].replace("[", "") [cite: 941]
                    master_item_ptr = next(i for i in st.session_state.item_codes_master if i["code"] == item_code_extracted) [cite: 941]
                    
                    col_l1, col_l2, col_l3 = st.columns(3) [cite: 942]
                    with col_l1: [cite: 942]
                        input_qty = st.number_input("ระบุจำนวน (Quantity)", min_value=0.0, step=1.0, value=1.0) [cite: 943]
                    with col_l2: [cite: 943]
                        input_mat_rate = st.number_input("ระบุราคาวัสดุเสนอขาย / หน่วย (บาท)", min_value=0.0, step=10.0, value=0.0) [cite: 943]
                    with col_l3: [cite: 943]
                        input_lab_rate = st.number_input("ระบุค่าแรงเสนอขาย / หน่วย (บาท)", min_value=0.0, step=10.0, value=0.0) [cite: 944]
                    
                    col_l4, col_l5 = st.columns(2) [cite: 944]
                    with col_l4: [cite: 945]
                        input_brand = st.text_input("ยี่ห้อ / รุ่น (Brand / Model)", placeholder="เช่น BCC, ABB, Link, N/A") [cite: 945]
                    with col_l5: [cite: 945]
                        input_remark = st.text_input("หมายเหตุ (Remark)", placeholder="เช่น ระบุข้อมูลเพิ่มเติมเฉพาะแถวนี้") [cite: 946]
                        
                    if st.button("➕ กดเพื่อเพิ่มลำดับวัสดุรายการนี้เข้า BOQ", use_container_width=True, type="primary"): [cite: 946]
                        unit_rate_total = input_mat_rate + input_lab_rate [cite: 946]
                        line_total_price = unit_rate_total * input_qty [cite: 947]
                        
                        if "items" not in curr_pur_obj: [cite: 947]
                            curr_pur_obj["items"] = [] [cite: 947]
                            
                        curr_pur_obj["items"].append({ [cite: 948]
                            "item_code": master_item_ptr["code"], [cite: 949]
                            "item_name": master_item_ptr["item_name"], [cite: 949]
                            "unit": master_item_ptr["unit"], [cite: 949]
                            "qty": input_qty, [cite: 949]
                            "material_rate": input_mat_rate, [cite: 950]
                            "labor_rate": input_lab_rate, [cite: 950]
                            "unit_rate_total": unit_rate_total, [cite: 950]
                            "total_price": line_total_price, [cite: 951]
                            "brand": input_brand.strip() if input_brand else "-", [cite: 951]
                            "remark": input_remark.strip() if input_remark else "" [cite: 951]
                        }) [cite: 952]
                        save_pur_proposals(st.session_state.pur_proposals) [cite: 952]
                        st.toast("เพิ่มรายการพัสดุเข้า BOQ สำเร็จ!", icon="✅") [cite: 952]
                        st.rerun() [cite: 952]
                        
                # --- ตารางรายละเอียดวัสดุในใบเสนอราคาปัจจุบัน พร้อมไอคอนจัดการ ---
                if curr_pur_obj.get("items"): [cite: 953]
                    st.markdown("##### 📊 ตารางรายละเอียดวัสดุในใบเสนอราคาปัจจุบัน") [cite: 953]
                    
                    h_cols = st.columns([0.6, 1.2, 3.2, 0.8, 1.0, 1.3, 1.3, 1.5, 1.2]) [cite: 954]
                    h_cols[0].markdown("**ลำดับ**") [cite: 954]
                    h_cols[1].markdown("**รหัสวัสดุ**") [cite: 954]
                    h_cols[2].markdown("**รายละเอียดวัสดุ**") [cite: 955]
                    h_cols[3].markdown("**หน่วย**") [cite: 955]
                    h_cols[4].markdown("**จำนวน**") [cite: 955]
                    h_cols[5].markdown("**ราคา/หน่วย**") [cite: 955]
                    h_cols[6].markdown("**ค่าแรง/หน่วย**") [cite: 955]
                    h_cols[7].markdown("**ยอดรวมสุทธิ**") [cite: 956]
                    h_cols[8].markdown("**จัดการ**") [cite: 956]
                    st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True) [cite: 956]
                    
                    for i, it in enumerate(curr_pur_obj["items"]): [cite: 957]
                        r_cols = st.columns([0.6, 1.2, 3.2, 0.8, 1.0, 1.3, 1.3, 1.5, 1.2]) [cite: 957]
                        
                        unit_rate_total = float(it.get("material_rate", 0.0)) + float(it.get("labor_rate", 0.0)) [cite: 958]
                        line_total = unit_rate_total * float(it.get("qty", 0.0)) [cite: 958]
                        
                        r_cols[0].write(f"{i+1}") [cite: 959]
                        r_cols[1].write(f"`{it.get('item_code', '-')}`") [cite: 959]
                        
                        item_display_name = it.get('item_name', '-') [cite: 960]
                        if it.get('brand') and it['brand'] != "-": [cite: 960]
                            item_display_name += f" ({it['brand']})" [cite: 961]
                        r_cols[2].write(item_display_name) [cite: 961]
                        
                        r_cols[3].write(f"{it.get('unit', '-')}") [cite: 962]
                        r_cols[4].write(f"{it.get('qty', 0.0):,.0f}") [cite: 962]
                        r_cols[5].write(f"{it.get('material_rate', 0.0):,.2f}") [cite: 962]
                        r_cols[6].write(f"{it.get('labor_rate', 0.0):,.2f}") [cite: 962]
                        r_cols[7].write(f"**{line_total:,.2f}**") [cite: 963]
                        
                        btn_col1, btn_col2 = r_cols[8].columns(2) [cite: 963]
                        
                        if btn_col1.button("✏️", key=f"edit_pur_item_{curr_pur_obj['id']}_{i}", help="แก้ไขรายการนี้"): [cite: 964]
                            @st.dialog(f"✏️ แก้ไขข้อมูลลำดับที่ {i+1}") [cite: 965]
                            def edit_pur_item_dialog(item_idx, item_data):
                                edit_q = st.number_input("แก้ไขจำนวน (Qty)", min_value=0.0, value=float(item_data.get("qty", 1.0)), step=1.0) [cite: 965]
                                edit_m = st.number_input("แก้ไขราคาวัสดุ / หน่วย", min_value=0.0, value=float(item_data.get("material_rate", 0.0)), step=10.0) [cite: 966]
                                edit_l = st.number_input("แก้ไขค่าแรง / หน่วย", min_value=0.0, value=float(item_data.get("labor_rate", 0.0)), step=10.0) [cite: 966]
                                edit_b = st.text_input("แก้ไขยี่ห้อ / รุ่น", value=item_data.get("brand", "-")) [cite: 966]
                                edit_r = st.text_input("แก้ไขหมายเหตุ (Remark)", value=item_data.get("remark", "")) [cite: 967]
                                
                                if st.button("💾 บันทึกการแก้ไขชิ้นนี้", use_container_width=True): [cite: 967]
                                    item_data["qty"] = edit_q [cite: 968]
                                    item_data["material_rate"] = edit_m [cite: 968]
                                    item_data["labor_rate"] = edit_l [cite: 969]
                                    item_data["unit_rate_total"] = edit_m + edit_l [cite: 969]
                                    item_data["total_price"] = (edit_m + edit_l) * edit_q [cite: 969]
                                    item_data["brand"] = edit_b.strip() if edit_b else "-" [cite: 970]
                                    item_data["remark"] = edit_r.strip() [cite: 970]
                                    
                                    save_pur_proposals(st.session_state.pur_proposals) [cite: 971]
                                    st.toast("แก้ไขรายการสำเร็จ!", icon="✅") [cite: 971]
                                    st.rerun() [cite: 972]
                            edit_pur_item_dialog(i, it) [cite: 972]

                        if btn_col2.button("🗑️", key=f"del_pur_item_{curr_pur_obj['id']}_{i}", help="ลบรายการนี้ออก"): [cite: 973]
                            curr_pur_obj["items"].pop(i) [cite: 973]
                            save_pur_proposals(st.session_state.pur_proposals) [cite: 973]
                            st.toast("ลบรายการออกจากตารางเรียบร้อย!", icon="🗑️") [cite: 974]
                            st.rerun() [cite: 974]
                            
                    st.markdown("---") [cite: 974]
                    # [FIXED 3] ลบอักขระแปลกปลอม `` และคำนวณสรุปยอดสุทธิหลักให้ทำงานได้แม่นยำ
                    grand_total_boq = sum(float(item.get("total_price", 0.0)) for item in curr_pur_obj["items"]) [cite: 975]
                    st.markdown(f"<h3 style='text-align: right; color:#00ffcc;'>💰 ยอดรวมมูลค่าเอกสารทั้งสิ้น: {grand_total_boq:,.2f} บาท</h3>", unsafe_allow_html=True) [cite: 975]
                    
                    # --- ฟังก์ชันเขียนไฟล์และดาวน์โหลด PDF ใบขอสอบราคา ---
                    pdf_filename = f"Request_for_Quotation_{curr_pur_obj['id']}.pdf" [cite: 976]
                    pdf_path = os.path.join(BASE_DIR, pdf_filename) [cite: 976]
                    
                    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=25, bottomMargin=25) [cite: 977]
                    story = [] [cite: 977]
                    
                    try:
                        font_file_path = os.path.join(BASE_DIR, 'DB Heavent v3.2.2.ttf') [cite: 978]
                        pdfmetrics.registerFont(TTFont('DBHeavent', font_file_path)) [cite: 979]
                        
                        title_style = ParagraphStyle('TitleStyle', fontName='DBHeavent', fontSize=24, leading=26, alignment=1) [cite: 979]
                        text_style = ParagraphStyle('TextStyle', fontName='DBHeavent', fontSize=13, leading=16) [cite: 979]
                        text_bold = ParagraphStyle('TextBold', fontName='DBHeavent', fontSize=13, leading=16) [cite: 980]
                        header_style = ParagraphStyle('HeaderStyle', fontName='DBHeavent', fontSize=12, leading=14, alignment=1) [cite: 980]
                        cat_style = ParagraphStyle('CatStyle', fontName='DBHeavent', fontSize=13, leading=15, alignment=0, textColor=colors.HexColor("#003311")) [cite: 980]
                        footer_style = ParagraphStyle('FooterStyle', fontName='DBHeavent', fontSize=13, leading=15, alignment=1) [cite: 981]
                        font_to_use = 'DBHeavent' [cite: 981]
                    except Exception as e:
                        title_style = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=18, alignment=1) [cite: 982]
                        text_style = ParagraphStyle('TextStyle', fontName='Helvetica', fontSize=10, leading=12) [cite: 982]
                        text_bold = ParagraphStyle('TextBold', fontName='Helvetica-Bold', fontSize=10, leading=12) [cite: 982]
                        header_style = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=9, alignment=1) [cite: 983]
                        cat_style = ParagraphStyle('CatStyle', fontName='Helvetica-Bold', fontSize=10, alignment=0) [cite: 983]
                        footer_style = ParagraphStyle('FooterStyle', fontName='Helvetica', fontSize=10, alignment=1) [cite: 983]
                        font_to_use = 'Helvetica' [cite: 983]

                    # ส่วนที่ 1: Header โลโก้บริษัท [cite: 984]
                    logo_path = os.path.join(BASE_DIR, 'SHARGE.png') [cite: 984]
                    if os.path.exists(logo_path): [cite: 984]
                        logo_img = Image(logo_path, width=120, height=38) [cite: 985]
                        logo_cell = logo_img [cite: 985]
                    else: [cite: 985]
                        logo_cell = Paragraph("<b>SHARGE</b>", title_style) [cite: 986]
                        
                    top_header_data = [[logo_cell, Paragraph("<b>ใบขอสอบราคา</b>", title_style), ""]] [cite: 986]
                    top_header_table = Table(top_header_data, colWidths=[150, 245, 140]) [cite: 987]
                    top_header_table.setStyle(TableStyle([ [cite: 987]
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), [cite: 987]
                        ('ALIGN', (1,0), (1,0), 'CENTER'), [cite: 987]
                        ('BOTTOMPADDING', (0,0), (-1,-1), 10), [cite: 988]
                    ])) [cite: 988]
                    story.append(top_header_table) [cite: 988]

                    # ส่วนที่ 2: บล็อกข้อมูลโครงการ [cite: 989]
                    requestor_name = curr_pur_obj.get('requestor', '-') [cite: 811]
                    client_company = curr_pur_obj.get('client_name', '-') [cite: 935]
                    project_title = curr_pur_obj.get('project_name', '-') [cite: 934]
                    doc_date = curr_pur_obj.get('date', '-') [cite: 935]

                    left_block_text = f"<b>บริษัทที่เสนอ :</b> {client_company}<br/><b>โครงการ :</b> {project_title}<br/><b>ผู้ร้องขอโครงการ :</b> {requestor_name}" [cite: 990]
                    right_block_text = f"<b>วันที่ request :</b> {doc_date}<br/><b>เลขที่ ร้องขอ :</b> {curr_pur_obj['id']}<br/><b>RFQ Ref :</b> -" [cite: 991]

                    address_block_data = [ [cite: 992]
                        [Paragraph("<b>บริษัทที่เสนอ</b>", text_bold), "", Paragraph("", text_bold), ""], [cite: 992]
                        [Paragraph(left_block_text, text_style), "", Paragraph(right_block_text, text_style), ""] [cite: 992]
                    ] [cite: 992]
                    
                    address_table = Table(address_block_data, colWidths=[250, 15, 260, 10]) [cite: 993]
                    address_table.setStyle(TableStyle([ [cite: 993]
                        ('SPAN', (0,0), (1,0)), ('SPAN', (2,0), (3,0)), ('SPAN', (0,1), (1,1)), ('SPAN', (2,1), (3,1)), [cite: 993]
                        ('BACKGROUND', (0,0), (3,0), colors.HexColor("#EAEAEA")), [cite: 994]
                        ('BOX', (0,0), (1,1), 1, colors.HexColor("#CCCCCC")), ('BOX', (2,0), (3,1), 1, colors.HexColor("#CCCCCC")), [cite: 994]
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), [cite: 994]
                        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6), [cite: 995]
                        ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8), [cite: 995]
                    ])) [cite: 995]
                    story.append(address_table) [cite: 995]
                    story.append(Spacer(1, 15)) [cite: 995]

                    # ส่วนที่ 3: ตารางรายการพัสดุสินค้าจัดซื้อ (7 คอลัมน์สมบูรณ์แบบ) [cite: 996]
                    table_data = [[ [cite: 996]
                        Paragraph("<b>ลำดับ</b>", header_style), [cite: 997]
                        Paragraph("<b>รหัสสินค้า</b>", header_style), [cite: 997]
                        Paragraph("<b>รายการสินค้า</b>", header_style), [cite: 997]
                        Paragraph("<b>จำนวน</b>", header_style), [cite: 997]
                        Paragraph("<b>Unit</b>", header_style), [cite: 998]
                        Paragraph("<b>ราคา/หน่วย</b>", header_style), [cite: 998]
                        Paragraph("<b>จำนวนเงินรวม</b>", header_style) [cite: 998]
                    ]] [cite: 998]

                    table_styles_list = [ [cite: 999]
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#D9D9D9")), [cite: 999]
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#999999")), [cite: 999]
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), [cite: 999]
                        ('ALIGN', (0,0), (-1,0), 'CENTER'), [cite: 1000]
                        ('TOPPADDING', (0,0), (-1,0), 6), [cite: 1000]
                        ('BOTTOMPADDING', (0,0), (-1,0), 6), [cite: 1000]
                    ] [cite: 1000]

                    items_list = curr_pur_obj.get("items", []) [cite: 1001]
                    categories_in_doc = [] [cite: 1001]
                    for it in items_list: [cite: 1001]
                        cat_name = it.get("category") [cite: 1002]
                        if not cat_name: [cite: 1002]
                            match_master = next((m for m in st.session_state.item_codes_master if m["code"] == it["item_code"]), None) [cite: 1003]
                            cat_name = match_master["category"] if match_master else "ทั่วไป" [cite: 1003]
                        if cat_name not in categories_in_doc: [cite: 1003]
                            categories_in_doc.append(cat_name) [cite: 1004]

                    current_row_idx = 1 [cite: 1004]

                    for cat in categories_in_doc: [cite: 1004]
                        cat_items = [] [cite: 1005]
                        for it in items_list: [cite: 1005]
                            cat_name = it.get("category") or next((m["category"] for m in st.session_state.item_codes_master if m["code"] == it["item_code"]), "ทั่วไป") [cite: 1005]
                            if cat_name == cat: [cite: 1006]
                                cat_items.append(it) [cite: 1006]
                                
                        cat_row = [Paragraph(f"<b>{cat}</b>", cat_style), "", "", "", "", "", ""] [cite: 1007]
                        table_data.append(cat_row) [cite: 1007]
                        
                        table_styles_list.append(('SPAN', (0, current_row_idx), (-1, current_row_idx))) [cite: 1008]
                        table_styles_list.append(('BACKGROUND', (0, current_row_idx), (-1, current_row_idx), colors.HexColor("#C2EABD"))) [cite: 1008]
                        table_styles_list.append(('TOPPADDING', (0, current_row_idx), (-1, current_row_idx), 5)) [cite: 1009]
                        table_styles_list.append(('BOTTOMPADDING', (0, current_row_idx), (-1, current_row_idx), 5)) [cite: 1009]
                        current_row_idx += 1 [cite: 1009]
                        
                        for item_no, it in enumerate(cat_items, 1): [cite: 1010]
                            display_name = it['item_name'] [cite: 1010]
                            if it.get('brand') and it['brand'] != "-": [cite: 1011]
                                display_name += f" ({it['brand']})" [cite: 1011]
                                
                            no_p = Paragraph(str(item_no), text_style) [cite: 1012]
                            code_p = Paragraph(it.get('item_code', '-'), text_style) [cite: 1012]
                            desc_p = Paragraph(display_name, text_style) [cite: 1012]
                            qty_p = Paragraph(f"{it['qty']:,.0f}", text_style) [cite: 1013]
                            unit_p = Paragraph(it.get('unit', '-'), text_style) [cite: 1013]
                            
                            unit_rate = float(it.get("unit_rate_total", it.get("material_rate", 0.0) + it.get("labor_rate", 0.0))) [cite: 1014]
                            total_line_price = unit_rate * float(it["qty"]) [cite: 1014]
                            
                            rate_p = Paragraph(f"{unit_rate:,.2f}", text_style) [cite: 1014]
                            amount_p = Paragraph(f"{total_line_price:,.2f}", text_style) [cite: 1015]
                            
                            table_data.append([no_p, code_p, desc_p, qty_p, unit_p, rate_p, amount_p]) [cite: 1015]
                            
                            table_styles_list.append(('ALIGN', (0, current_row_idx), (1, current_row_idx), 'CENTER')) [cite: 1016]
                            table_styles_list.append(('ALIGN', (2, current_row_idx), (2, current_row_idx), 'LEFT')) [cite: 1017]
                            table_styles_list.append(('ALIGN', (3, current_row_idx), (4, current_row_idx), 'CENTER')) [cite: 1017]
                            table_styles_list.append(('ALIGN', (5, current_row_idx), (6, current_row_idx), 'RIGHT')) [cite: 1017]
                            table_styles_list.append(('TOPPADDING', (0, current_row_idx), (-1, current_row_idx), 5)) [cite: 1018]
                            table_styles_list.append(('BOTTOMPADDING', (0, current_row_idx), (-1, current_row_idx), 5)) [cite: 1018]
                            current_row_idx += 1 [cite: 1018]

                    # ส่วนที่ 4: ตารางสรุปมูลค่ารวมเงินสุทธิ [cite: 1019]
                    # [FIXED 4] แก้ไขจุดบกพรณ์ SPAN และ ซ่อนเส้นฝั่งซ้ายล่างอย่างสมบูรณ์แบบสไตล์ SHARGE
                    table_data.append(["", "", "", "", "", Paragraph("<b>裁量合計 / มูลค่ารวมทั้งสิ้น</b>", text_bold), Paragraph(f"<b>{grand_total_boq:,.2f}</b>", text_bold)])
                    
                    table_styles_list.append(('SPAN', (0, current_row_idx), (4, current_row_idx))) [cite: 1020]
                    table_styles_list.append(('BACKGROUND', (5, current_row_idx), (6, current_row_idx), colors.HexColor("#EAEAEA"))) [cite: 1020]
                    table_styles_list.append(('ALIGN', (5, current_row_idx), (5, current_row_idx), 'LEFT')) [cite: 1021]
                    table_styles_list.append(('ALIGN', (6, current_row_idx), (6, current_row_idx), 'RIGHT')) [cite: 1021]
                    table_styles_list.append(('TOPPADDING', (0, current_row_idx), (-1, current_row_idx), 6)) [cite: 1021]
                    table_styles_list.append(('BOTTOMPADDING', (0, current_row_idx), (-1, current_row_idx), 6)) [cite: 1021]
                    
                    table_styles_list.append(('LINEBEFORE', (0, current_row_idx), (0, current_row_idx), 0, colors.white)) [cite: 1022]
                    table_styles_list.append(('LINEBELOW', (0, current_row_idx), (4, current_row_idx), 0, colors.white)) [cite: 1022]
                    current_row_idx += 1 [cite: 1023]
                    
                    pdf_table = Table(table_data, colWidths=[40, 65, 185, 40, 35, 85, 85]) [cite: 1023]
                    pdf_table.setStyle(TableStyle(table_styles_list)) [cite: 1024]
                    story.append(pdf_table) [cite: 1024]
                    story.append(Spacer(1, 40)) [cite: 1024]

                    # ส่วนที่ 5: บล็อกลงนามลายเซ็นท้ายเล่ม [cite: 1024]
                    signature_data = [ [cite: 1025]
                        ["(......................................................)", "", "(......................................................)"], [cite: 1025]
                        [Paragraph("<b>(ผู้อนุมัติ)</b>", footer_style), "", Paragraph("<b>(ผู้เสนอราคา)</b>", footer_style)], [cite: 1025]
                        ["", "", Paragraph("<b>SHARGE</b>", footer_style)], [cite: 1026]
                        ["", "", Paragraph("<b>(Procurement Department)</b>", footer_style)] [cite: 1026]
                    ] [cite: 1026]
                    signature_table = Table(signature_data, colWidths=[230, 75, 230]) [cite: 1026]
                    signature_table.setStyle(TableStyle([ [cite: 1027]
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'), [cite: 1027]
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), [cite: 1027]
                        ('TOPPADDING', (0,0), (-1,-1), 1), [cite: 1027]
                        ('BOTTOMPADDING', (0,0), (-1,-1), 1), [cite: 1028]
                    ])) [cite: 1028]
                    story.append(signature_table) [cite: 1028]

                    doc.build(story) [cite: 1029]
                    upload_to_google_drive(pdf_path) # ส่งเข้า Google Drive ทั่วถึงอัตโนมัติ [cite: 1029]
                    
                    with open(pdf_path, "rb") as pdf_file: [cite: 1029]
                        st.download_button(
                            label="🖨️ ดาวน์โหลดใบเสนอราคาประมาณการรวมเป็นไฟล์ PDF", [cite: 1030]
                            data=pdf_file.read(), [cite: 1030]
                            file_name=pdf_filename, [cite: 1031]
                            mime="application/pdf", [cite: 1031]
                            use_container_width=True [cite: 1031]
                        )
                    
                    if st.button("🗑️ ลบเอกสารใบเสนอราคา PUR นี้ออกจากประวัติคลังข้อมูลทั้งหมด", type="primary"): [cite: 1032]
                        st.session_state.pur_proposals.remove(curr_pur_obj) [cite: 1032]
                        save_pur_proposals(st.session_state.pur_proposals) [cite: 1033]
                        st.success("ลบโปรเจกต์เสนอราคาเรียบร้อย") [cite: 1033]
                        st.rerun() [cite: 1033]

    with pur_tab2: [cite: 1033]
        st.subheader("🆕 บันทึกสร้างโปรเจกต์เอกสารเสนอราคา (ขาออก) ใบใหม่") [cite: 1033]
        curr_year_short = datetime.now().strftime('%y') [cite: 1033]
        curr_month = datetime.now().strftime('%m') [cite: 1034]
        pur_prefix = f"PUR-{curr_year_short}{curr_month}" [cite: 1034]
        
        count_pur_month = sum(1 for p in st.session_state.pur_proposals if p["id"].startswith(pur_prefix)) [cite: 1034]
        auto_pur_id = f"{pur_prefix}{(count_pur_month + 1):04d}" [cite: 1034]
        
        with st.form("create_pur_proposal_form", clear_on_submit=True): [cite: 1034]
            new_pur_id = st.text_input("เลขที่ใบเสนอราคาอัตโนมัติ (PUR ID)", value=auto_pur_id) [cite: 1034]
            new_pur_project = st.text_input("ชื่อโครงการประมาณการเสนอราคา", placeholder="เช่น งานปรับปรุงสถานีชาร์จไฟรถยนต์ EV แผนกโรงงาน") [cite: 1035]
            new_pur_client = st.text_input("ชื่อลูกค้า / บริษัทผู้ว่าจ้าง", placeholder="เช่น บริษัท ควอด อิเลคทริค จำกัด") [cite: 1035]
            
            if not st.session_state.requestors_list: [cite: 1035]
                st.error("⚠️ ยังไม่มีรายชื่อผู้ร้องขอในระบบ กรุณาเพิ่มรายชื่อในระบบจัดการ RFQ ก่อน") [cite: 1036]
                selected_pur_requestor = None [cite: 1036]
            else: [cite: 1036]
                selected_pur_requestor = st.selectbox("เลือกผู้ร้องขอโครงการ (ดึงข้อมูลกลาง)", st.session_state.requestors_list) [cite: 1036]
                
            new_pur_date = st.date_input("วันที่ลงเอกสารออกเสนอราคา", datetime.now()) [cite: 1036]
            
            st.markdown("<br>", unsafe_allow_html=True) [cite: 1037]
            if st.form_submit_button("💾 เปิดเล่ม / บันทึกตั้งต้นเอกสารโปรเจกต์นี้"): [cite: 1037]
                if new_pur_id and new_pur_project and new_pur_client and selected_pur_requestor: [cite: 1037]
                    st.session_state.pur_proposals.append({ [cite: 1037]
                        "id": new_pur_id.strip(), [cite: 1037]
                        "project_name": new_pur_project.strip(), [cite: 1038]
                        "client_name": new_pur_client.strip(), [cite: 1038]
                        "requestor": selected_pur_requestor.strip(), [cite: 1038]
                        "date": new_pur_date.strftime('%d/%m/%Y'), [cite: 1038]
                        "items": [] [cite: 1039]
                    }) [cite: 1039]
                    save_pur_proposals(st.session_state.pur_proposals) [cite: 1039]
                    st.toast(f"🎉 เปิดเอกสารประมาณการเลขที่ {new_pur_id} เข้าสู่คลังเสนอราคาขาออกสำเร็จ!", icon="✅") [cite: 1039]
                    st.rerun() [cite: 1040]
                else: [cite: 1040]
                    st.error("❌ กรุณากรอกรหัสเอกสาร ชื่อโครงการ ชื่อบริษัทผู้ว่าจ้าง และผู้ร้องขอให้ครบถ้วนก่อนส่ง") [cite: 1040]