import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
import subprocess
import platform
import plotly.express as px

# แก้ไขจุดนี้นะครับพี่ เพิ่ม Image เข้าไปในบรรทัดนี้
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ตั้งค่าหน้าจอโปรแกรม
st.set_page_config(page_title="Procurement Workspace", layout="wide")

# ล็อกที่อยู่โฟลเดอร์หลักเมื่อรันบนคลาวด์ให้อยู่ในตำแหน่งทำงานปัจจุบัน (Relative Path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# กำหนดที่เก็บไฟล์ฐานข้อมูลและโฟลเดอร์เอกสารให้อยู่ด้านใน Procurement-App ทั้งหมด
DB_FILE = os.path.join(BASE_DIR, "rfq_data.json")
USER_FILE = os.path.join(BASE_DIR, "requestors_data.json")
SUP_FILE = os.path.join(BASE_DIR, "suppliers_master.json")
SUP_DOC_DIR = os.path.join(BASE_DIR, "supplier_documents")
STANDALONE_FILE = os.path.join(BASE_DIR, "standalone_prices.json")
ITEM_FILE = os.path.join(BASE_DIR, "item_codes_master.json")
UNIT_FILE = os.path.join(BASE_DIR, "units_master.json")
CATEGORIES_FILE = os.path.join(BASE_DIR, "categories_master.json")
PUR_FILE = os.path.join(BASE_DIR, "pur_proposals.json")  # ฐานข้อมูลใบเสนอราคาขาออกตัวใหม่

if not os.path.exists(SUP_DOC_DIR):
    os.makedirs(SUP_DOC_DIR)

# คลังข้อมูลพิกัดจังหวัดและภูมิภาคของประเทศไทยสำหรับใช้ติ๊กเลือกพื้นที่รับงาน
THAI_REGIONS = {
    "ทั่วประเทศ": ["ทุกจังหวัดทั่วประเทศ"],
    "ภาคกลาง / ปริมณฑล": ["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "พระนครศรีอยุธยา", "สระบุรี", "ลพบุรี", "สิงห์บุรี", "อ่างทอง", "ชัยนาท", "อุทัยธานี", "นครสวรรค์"],
    "ภาคเหนือ": ["เชียงใหม่", "เชียงราย", "ลำปาง", "ลำพูน", "แม่ฮ่องสอน", "พะเยา", "แพร่", "น่าน", "อุตรดิตถ์", "พิษณุโลก", "สุโขทัย", "ตาก", "พิจิตร", "กำแพงเพชร", "เพชรบูรณ์"],
    "ภาคอีสาน": ["นครราชสีมา", "ขอนแก่น", "อุดรธานี", "อุบลราชธานี", "บุรีรัมย์", "ศรีสะเกษ", "สุรินทร์", "ร้อยเอ็ด", "ชัยภูมิ", "มหาสารคาม", "กาฬสินธุ์", "สกลนคร", "นครพนม", "เลย", "หนองคาย", "หนองบัวลำภู", "บึงกาฬ", "ยโสธร", "อำนาจเจริญ", "มุกดาหาร"],
    "ภาคตะวันออก": ["ชลบุรี", "ระยอง", "ฉะเชิงเทรา", "จันทบุรี", "ตราด", "ปราจีนบุรี", "สระแก้ว"],
    "ภาคตะวันตก": ["ราชบุรี", "กาญจนบุรี", "เพชรบุรี", "ประจวบคีรีขันธ์"],
    "ภาคใต้": ["ภูเก็ต", "สงขลา", "สุราษฎร์ธานี", "นครศรีธรรมราช", "กระบี่", "พังงา", "ตรัง", "พัทลุง", "ชุมพร", "ระนอง", "สตูล", "ปัตตานี", "ยะลา", "นราธิวาส"]
}

# --- [ADD] ฟังก์ชันสำหรับสั่งเปิดโฟลเดอร์ในเครื่องคอมพิวเตอร์แบบ Local ---
def open_local_folder(folder_path):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        current_os = platform.system()
        if current_os == "Windows":
            os.startfile(folder_path)
        elif current_os == "Darwin":  # macOS
            subprocess.Popen(["open", folder_path])
        else:  # Linux
            subprocess.Popen(["xdg-open", folder_path])
        st.toast(f"เปิดโฟลเดอร์เรียบร้อยแล้ว: {os.path.basename(folder_path)}", icon="📁")
    except Exception as e:
        st.error(f"ไม่สามารถเปิดโฟลเดอร์ได้อัตโนมัติ: {e}\nที่อยู่โฟลเดอร์คือ: {folder_path}")

# ฟังก์ชันจัดการระบบฐานข้อมูล
def load_json_file(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return default_val
    return default_val

def save_json_file(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# โหลดฟังก์ชันย่อยด่วน
def save_data(data): save_json_file(DB_FILE, data)
def save_requestors(data): save_json_file(USER_FILE, data)
def save_suppliers(data): save_json_file(SUP_FILE, data)
def save_standalone_prices(data): save_json_file(STANDALONE_FILE, data)
def save_item_codes(data): save_json_file(ITEM_FILE, data)
def save_units(data): save_json_file(UNIT_FILE, data)
def save_categories(data): save_json_file(CATEGORIES_FILE, data)
def save_pur_proposals(data): save_json_file(PUR_FILE, data)

# โหลดข้อมูลเข้าสู่ตัวแปรระบบ Session State
if 'rfq_history' not in st.session_state: st.session_state.rfq_history = load_json_file(DB_FILE, [])
if 'requestors_list' not in st.session_state: st.session_state.requestors_list = load_json_file(USER_FILE, ["คุณสมชาย", "คุณสมหญิง"])
if 'suppliers_master' not in st.session_state: st.session_state.suppliers_master = load_json_file(SUP_FILE, [])
if 'standalone_prices' not in st.session_state: st.session_state.standalone_prices = load_json_file(STANDALONE_FILE, [])
if 'item_codes_master' not in st.session_state: st.session_state.item_codes_master = load_json_file(ITEM_FILE, [])
if 'units_list' not in st.session_state: st.session_state.units_list = load_json_file(UNIT_FILE, ["M", "ชุด", "ตัว", "ตร.ม.", "กิโลกรัม", "ท่อน", "ม้วน"])
if 'categories_list' not in st.session_state: st.session_state.categories_list = load_json_file(CATEGORIES_FILE, ["สายไฟ", "ท่อร้อยสาย", "อุปกรณ์ไฟฟ้า", "งานระบบ", "ทั่วไป"])
if 'pur_proposals' not in st.session_state: st.session_state.pur_proposals = load_json_file(PUR_FILE, [])

if 'temp_contacts' not in st.session_state: st.session_state.temp_contacts = [{"name": "", "phone": "", "email": "", "line": ""}]
if 'selected_supplier_name' not in st.session_state: st.session_state.selected_supplier_name = None
if 'sup_clear_counter' not in st.session_state: st.session_state.sup_clear_counter = 0
if 'areas_output_add' not in st.session_state: st.session_state.areas_output_add = "ยังไม่ได้เลือกพื้นที่"
if 'selected_search_province' not in st.session_state: st.session_state.selected_search_province = None
if 'current_pur_id' not in st.session_state: st.session_state.current_pur_id = None

# --- ฟังก์ชันย่อยสำหรับแจ้งเตือนพิกัดจังหวัด/หมวดหมู่/หน่วยนับ (Dialogs) ---
@st.dialog("🌍 เลือกพื้นที่ที่สามารถรับงานได้")
def select_areas_dialog():
    st.write("เลือกภาค หรือติ๊กเลือกรายจังหวัดตามต้องการ (เสร็จแล้วกดบันทึกด้านล่าง)")
    chosen_list = []
    for region, provinces in THAI_REGIONS.items():
        st.markdown(f"**{region}**")
        reg_click = st.checkbox(f"เลือกทั้งหมดใน {region}", key=f"pop_reg_{region}")
        if region != "ทั่วประเทศ":
            cols = st.columns(4)
            for idx, prov in enumerate(provinces):
                col = cols[idx % 4]
                prov_chk = col.checkbox(prov, value=reg_click, key=f"pop_prov_{prov}")
                if prov_chk or reg_click:
                    if prov not in chosen_list: chosen_list.append(prov)
        else:
            if reg_click: chosen_list.append("ทุกจังหวัดทั่วประเทศ")
        st.markdown("---")
    if st.button("💾 ยืนยันการเลือกพื้นที่", use_container_width=True):
        st.session_state.areas_output_add = "ทุกจังหวัดทั่วประเทศ" if "ทุกจังหวัดทั่วประเทศ" in chosen_list else ", ".join(chosen_list)
        st.rerun()

@st.dialog("🔍 ค้นหาและเลือกซัพพลายเออร์")
def select_supplier_popup():
    sup_choices = [s["name"] for s in st.session_state.suppliers_master]
    chosen_sup = st.selectbox("พิมพ์ค้นหาชื่อบริษัท / ผู้ขาย", sup_choices)
    if st.button("✅ ยืนยันเปิดดูโปรไฟล์", use_container_width=True):
        st.session_state.selected_supplier_name = chosen_sup
        st.rerun()

@st.dialog("🎯 ค้นหาและเลือกจังหวัดพิกัดไซต์งาน")
def select_search_province_popup():
    flat_provinces_search = []
    for k, v in THAI_REGIONS.items():
        if k != "ทั่วประเทศ": flat_provinces_search.extend(v)
    flat_provinces_search.sort()
    chosen_search_prov = st.selectbox("พิมพ์ค้นหาชื่อจังหวัด", flat_provinces_search)
    if st.button("✅ ยืนยันเลือกจังหวัดนี้", use_container_width=True):
        st.session_state.selected_search_province = chosen_search_prov
        st.rerun()

@st.dialog("📝 แก้ไขข้อมูลซัพพลายเออร์")
def edit_supplier_popup(sup_obj, idx_master):
    e_tax = st.text_input("เลขประจำตัวผู้เสียภาษี (Tax ID)", value=sup_obj.get("tax_id", ""))
    e_credit = st.text_input("เครดิตเทอม", value=sup_obj.get("credit", ""))
    e_address = st.text_area("ที่อยู่บริษัท", value=sup_obj.get("address", ""))
    e_info = st.text_area("หมายเหตุทั่วไป", value=sup_obj.get("general_info", ""))
    if st.button("💾 บันทึกการแก้ไขข้อมูล", use_container_width=True):
        st.session_state.suppliers_master[idx_master].update({"tax_id": e_tax, "credit": e_credit, "address": e_address, "general_info": e_info})
        save_suppliers(st.session_state.suppliers_master)
        st.rerun()

@st.dialog("👥 บริหารจัดการรายชื่อผู้ติดต่อ")
def edit_contacts_popup(sup_obj, idx_master):
    updated_items = []
    for i, contact in enumerate(st.session_state.edit_contacts_list):
        ec_c1, ec_c2, ec_c3, ec_c4 = st.columns(4)
        c_name = ec_c1.text_input("ชื่อ", value=contact.get("name", ""), key=f"ec_n_{i}")
        c_phone = ec_c2.text_input("เบอร์โทร", value=contact.get("phone", ""), key=f"ec_p_{i}")
        c_email = ec_c3.text_input("Email", value=contact.get("email", ""), key=f"ec_e_{i}")
        c_line = ec_c4.text_input("Line ID", value=contact.get("line", ""), key=f"ec_l_{i}")
        updated_items.append({"name": c_name, "phone": c_phone, "email": c_email, "line": c_line})
    if st.button("💾 บันทึกการเปลี่ยนแปลงรายชื่อ", use_container_width=True):
        st.session_state.suppliers_master[idx_master]["contacts"] = [c for c in updated_items if c["name"].strip()]
        save_suppliers(st.session_state.suppliers_master)
        st.rerun()

@st.dialog("➕ ลงทะเบียนหน่วยนับมาตรฐานใหม่")
def add_unit_dialog():
    new_unit = st.text_input("ชื่อหน่วยนับ (Unit Name)").strip()
    if st.button("💾 บันทึกหน่วยนับใหม่", use_container_width=True):
        if new_unit and new_unit not in st.session_state.units_list:
            st.session_state.units_list.append(new_unit)
            save_units(st.session_state.units_list)
            st.rerun()

@st.dialog("➕ ลงทะเบียนหมวดหมู่งานมาตรฐานใหม่")
def add_category_dialog():
    new_cat = st.text_input("ชื่อหมวดหมู่งาน / กลุ่มพัสดุ").strip()
    if st.button("💾 บันทึกหมวดหมู่ใหม่", use_container_width=True):
        if new_cat and new_cat not in st.session_state.categories_list:
            st.session_state.categories_list.append(new_cat)
            save_categories(st.session_state.categories_list)  # [FIXED] ย้ายเข้ามาในบล็อกเงื่อนไขให้ถูกต้อง
            st.rerun()

# =========================================================================
# 🧭 ระบบเมนูควบคุมหลักด้านข้าง (Sidebar Navigation)
# =========================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧭 เมนูควบคุมหลัก</h2>", unsafe_allow_html=True)
    st.markdown("---")
    main_menu = st.radio(
        "เลือกหน้าต่างทำงาน:",
        ["🏠 หน้าหลัก (Dashboard)", "📦 ระบบจัดการ RFQ", "🏢 ข้อมูล Supplier", "📊 BOQ Supplier", "🗂️ บริหาร Item Code", "📝 จัดทำ BOQ เพื่อเสนอ"]
    )
    st.markdown("---")
    st.caption("ระบบจัดซื้อส่วนตัว v2.2 • 2026")

# =========================================================================
# 🏠 หน้าหลัก (Dashboard)
# =========================================================================
if main_menu == "🏠 หน้าหลัก (Dashboard)":
    st.title("ワークスペース • หน้าหลักระบบจัดซื้อ")
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
    components.html(clock_html, height=140)
    
    total_rfq = len(st.session_state.rfq_history)
    pending_rfq = sum(1 for x in st.session_state.rfq_history if x.get("status") == "กำลังขอราคา")
    compared_rfq = sum(1 for x in st.session_state.rfq_history if x.get("status") in ["ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว"])
    completed_rfq = sum(1 for x in st.session_state.rfq_history if x.get("status") == "สั่งซื้อเรียบร้อย (PO ออกแล้ว)")
    total_sups = len(st.session_state.suppliers_master)
    
    card1, card2, card3, card4, card5 = st.columns(5)
    card1.metric("RFQ ทั้งหมดในระบบ", f"{total_rfq} ใบ")
    card2.metric("⏳ อยู่ระหว่างขอราคา", f"{pending_rfq} งาน")
    card3.metric("📊 ส่งราคา Compare เรียบร้อย", f"{compared_rfq} งาน")
    card4.metric("✅ ออก PO เรียบร้อย", f"{completed_rfq} งาน")
    card5.metric("🏢 ซัพพลายเออร์ในคลัง", f"{total_sups} ราย")

    st.markdown("---")
    if total_rfq > 0:
        st.subheader("🍕 กราฟวิเคราะห์สัดส่วนปริมาณงานตามสถานะ")
        df_rfq = pd.DataFrame(st.session_state.rfq_history)
        status_counts = df_rfq["status"].value_counts().reset_index()
        status_counts.columns = ["สถานะงาน", "จำนวนใบงาน"]
        g_col1, g_col2 = st.columns([3, 2])
        with g_col1:
            fig_pie = px.pie(status_counts, values="จำนวนใบงาน", names="สถานะงาน", hole=0)
            st.plotly_chart(fig_pie, use_container_width=True)
        with g_col2:
            st.markdown("#### 📝 ตารางสรุปตัวเลขสถิติ")
            st.dataframe(status_counts, use_container_width=True, hide_index=True)
    else: st.info("💡 ข้อมูลกราฟวิเคราะห์จะปรากฏเมื่อบันทึกใบงาน RFQ")

# =========================================================================
# 📦 ระบบจัดการ RFQ
# =========================================================================
elif main_menu == "📦 ระบบจัดการ RFQ":
    st.title("📦 ระบบบริหารจัดการ RFQ")
    sub_tab0, sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["📋 รายการ RFQ ทั้งหมด", "🆕 เปิด RFQ ใหม่", "📑 อัปเดตสถานะราคา", "📜 ประวัติย้อนหลัง (History)", "👤 จัดการรายชื่อผู้ร้องขอ"])
    
    with sub_tab0:
        st.subheader("📋 ตารางตรวจสอบสถานะงาน RFQ และโฟลเดอร์จัดเก็บข้อมูล")
        if not st.session_state.rfq_history: st.warning("ยังไม่มีข้อมูล RFQ บันทึกไว้ในระบบ")
        else:
            status_filter = st.selectbox("🔍 กรองดูตามสถานะใบงาน:", ["แสดงทั้งหมด", "กำลังขอราคา", "ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว", "สั่งซื้อเรียบร้อย (PO ออกแล้ว)", "ยกเลิกงาน"])
            filtered_rfq = st.session_state.rfq_history if status_filter == "แสดงทั้งหมด" else [x for x in st.session_state.rfq_history if x.get("status") == status_filter]
            st.markdown(f"พบใบงานจัดซื้อทั้งหมด **{len(filtered_rfq)}** รายการ")
            
            h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5])
            h_c1.markdown("**เลขที่ RFQ**")
            h_c2.markdown("**ชื่อโครงการ / โฟลเดอร์**")
            h_c3.markdown("**ผู้ร้องขอ**")
            h_c4.markdown("**กำหนดส่งมอบ**")
            h_c5.markdown("**สถานะปัจจุบัน**")
            h_c6.markdown("**เปิดโฟลเดอร์ในคอม**")
            st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True)
            
            for idx, item in enumerate(filtered_rfq):
                r_c1, r_c2, r_c3, r_c4, r_c5, r_c6 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5])
                r_c1.write(f"`{item['id']}`")
                r_c2.write(item.get("project", "ทั่วไป"))
                r_c3.write(item.get("requestor", "-"))
                r_c4.write(item.get("deadline", "-"))
                
                status_text = item.get("status", "กำลังขอราคา")
                if status_text == "กำลังขอราคา": r_c5.caption(f"⏳ {status_text}")
                elif status_text == "สั่งซื้อเรียบร้อย (PO ออกแล้ว)": r_c5.write(f"🟢 **{status_text}**")
                elif status_text == "ยกเลิกงาน": r_c5.caption(f"🔴 {status_text}")
                else: r_c5.write(f"🔵 {status_text}")
                
                if r_c6.button("📁 เปิดโฟลเดอร์", key=f"open_direct_f_{item['id']}_{idx}"):
                    open_local_folder(item.get("folder_name", item["id"]))

    with sub_tab1:
        st.subheader("กรอกรายละเอียดเพื่อสร้าง RFQ")
        current_ym = datetime.now().strftime('%Y%m')
        prefix = f"RFQ-{current_ym}-"
        count_current_month = sum(1 for item in st.session_state.rfq_history if item["id"].startswith(prefix))
        
        auto_rfq_id = f"{prefix}{(count_current_month + 1):04d}"
        
        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            with st.form("rfq_form", clear_on_submit=True):
                rfq_id = st.text_input("เลขที่ RFQ", value=auto_rfq_id)
                project_name = st.text_input("ชื่อโครงการ (Project Name)", placeholder="เช่น โครงการติดตั้ง EV Charging Station")
                
                if not st.session_state.requestors_list:
                    st.error("⚠️ ยังไม่มีรายชื่อผู้ร้องขอในระบบ")
                    selected_requestor = None
                else: selected_requestor = st.selectbox("เลือกผู้ร้องขอ", st.session_state.requestors_list)
                rfq_date = st.date_input("วันที่เปิด RFQ", datetime.now())
                details = st.text_area("รายละเอียดงาน / รายการที่ต้องการ")
                deadline = st.date_input("วันส่งมอบที่ต้องการ", datetime.now())
                
                if st.form_submit_button("ส่ง RFQ / บันทึกตั้งค่า"):
                    if rfq_id and selected_requestor:
                        clean_rfq = rfq_id.strip()
                        clean_project = project_name.strip() if project_name else "ทั่วไป"
                        folder_name = f"{clean_rfq}_{clean_project}_{selected_requestor.strip()}"
                        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']: folder_name = folder_name.replace(char, "_")
                        
                        full_folder_path = os.path.join(BASE_DIR, folder_name)
                        if not os.path.exists(full_folder_path): os.makedirs(full_folder_path)
                                             
                        new_rfq = {
                            "id": clean_rfq, "project": clean_project, "requestor": selected_requestor.strip(),
                            "folder_name": full_folder_path, "date": str(rfq_date), "details": details, "deadline": str(deadline),
                            "status": "กำลังขอราคา", "suppliers": [],
                            "history_logs": [f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] สร้าง RFQ ในโฟลเดอร์: {full_folder_path}"]
                        }
                        st.session_state.rfq_history.append(new_rfq)
                        save_data(st.session_state.rfq_history)
                        st.success(f"บันทึกสำเร็จ!")
                        st.rerun()

    with sub_tab2:
        if not st.session_state.rfq_history:
            st.warning("ยังไม่มีข้อมูล RFQ ในระบบ กรุณาไปสร้างใบงานที่แท็บเปิด RFQ ใหม่ก่อนครับ")
        else:
            rfq_options = [f"{x['id']} [โครงการ: {x.get('project', 'ทั่วไป')}]" for x in st.session_state.rfq_history]
            selected_display = st.selectbox("เลือกเลขที่ RFQ", rfq_options, key="rfq_select_t2")
            selected_rfq_id = selected_display.split()[0]
            current_rfq = next(x for x in st.session_state.rfq_history if x["id"] == selected_rfq_id)
            target_folder = current_rfq.get("folder_name", selected_rfq_id)
            if not os.path.isabs(target_folder): target_folder = os.path.join(BASE_DIR, target_folder)
            
            st.info(f"📂 ที่อยู่โฟลเดอร์งาน: {target_folder}")
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("### ➕ บันทึกข้อมูลราคาซัพพลายเออร์")
                with st.form("price_add_form", clear_on_submit=True):
                    if not st.session_state.suppliers_master:
                        st.error("กรุณาเพิ่มชื่อในหน้าข้อมูล Supplier ก่อนครับ")
                        sup_name = None
                    else: sup_name = st.selectbox("เลือก Supplier", [s["name"] for s in st.session_state.suppliers_master])
                    price = st.number_input("ราคาที่เสนอ (บาท)", min_value=0.0, step=100.0)
                    terms = st.text_area("เงื่อนไขเพิ่มเติม")
                    uploaded_file = st.file_uploader("แนบไฟล์ใบเสนอราคา", type=["pdf", "png", "jpg", "jpeg", "xlsx", "xls", "docx"])
                    
                    if st.form_submit_button("บันทึกราคาร้านนี้"):
                        if sup_name:
                            file_path_saved = ""
                            if uploaded_file is not None:
                                if not os.path.exists(target_folder): os.makedirs(target_folder)
                                clean_filename = f"{sup_name}_{uploaded_file.name}".replace("/", "_").replace("\\", "_")
                                file_path_saved = os.path.join(target_folder, clean_filename)
                                with open(file_path_saved, "wb") as f: f.write(uploaded_file.getbuffer())
                                         
                            current_rfq["suppliers"].append({
                                "name": sup_name, "price": price, "terms": terms, "file_path": file_path_saved,
                                "date_added": datetime.now().strftime('%Y-%m-%d %H:%M'), "items": []
                            })
                            current_rfq["history_logs"].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] เพิ่มราคา {sup_name} ยอด {price:,.2f} บาท")
                            save_data(st.session_state.rfq_history)
                            st.toast("บันทึกราคาเรียบร้อย!", icon="✅")
                            st.rerun()
            with col_right:
                st.markdown("### ⚙️ เปลี่ยนสถานะใบงาน RFQ")
                new_status = st.selectbox("สถานะ", ["กำลังขอราคา", "ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว", "สั่งซื้อเรียบร้อย (PO ออกแล้ว)", "ยกเลิกงาน"], index=["กำลังขอราคา", "ได้ใบเสนอราคาครบแล้ว", "ส่งอนุมัติแล้ว", "สั่งซื้อเรียบร้อย (PO ออกแล้ว)", "ยกเลิกงาน"].index(current_rfq["status"]))
                if st.button("อัปเดตสถานะงาน"):
                    if new_status != current_rfq["status"]:
                        current_rfq["status"] = new_status
                        current_rfq["history_logs"].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] เปลี่ยนสถานะเป็น: {new_status}")
                        save_data(st.session_state.rfq_history)
                        st.success("อัปเดตสถานะสำเร็จ")
                        st.rerun()

            st.markdown("---")
            st.markdown("### ✏️ บันทึกรายการวัสดุและค่าแรงแยกย่อย (Unit Rate Breakdown)")
            if not current_rfq.get("suppliers"): st.caption("⚠️ ต้องบันทึกชื่อซัพพลายเออร์และราคาโดยรวมฝั่งด้านบนก่อน")
            elif not st.session_state.item_codes_master: st.error("⚠️ ยังไม่มีฐานข้อมูลวัสดุกลาง")
            else:
                sup_list_rfq = [s["name"] for s in current_rfq["suppliers"]]
                selected_input_sup = st.selectbox("เลือกซัพพลายเออร์เพื่อบันทึกราคาแยกชิ้นงาน:", sup_list_rfq)
                target_sup_obj = next(s for s in current_rfq["suppliers"] if s["name"] == selected_input_sup)
                
                with st.form("unit_rate_input_form", clear_on_submit=True):
                    item_choices = [f"[{i['code']}] {i['item_name']}" for i in st.session_state.item_codes_master]
                    selected_item_display = st.selectbox("เลือกรายการวัสดุ (Item Code Center)", item_choices)
                    target_code = selected_item_display.split("]")[0].replace("[", "")
                    item_master_obj = next(i for i in st.session_state.item_codes_master if i["code"] == target_code)
                    
                    st.caption(f"💡 หมวดหมู่: `{item_master_obj['category']}` | หน่วย: `{item_master_obj['unit']}`")
                    it_col1, it_col2 = st.columns(2)
                    i_mat_rate = it_col1.number_input("ราคาวัสดุหน่วย (บาท)", min_value=0.0, step=1.0)
                    i_lab_rate = it_col2.number_input("ค่าแรงต่อหน่วย (บาท)", min_value=0.0, step=1.0)
                    
                    if st.form_submit_button("➕ บันทึกรายการวัสดุนี้เข้าใบเสนอราคา"):
                        if "items" not in target_sup_obj: target_sup_obj["items"] = []
                        target_sup_obj["items"].append({
                            "item_code": item_master_obj["code"], "category": item_master_obj["category"],
                            "item_name": item_master_obj["item_name"], "unit": item_master_obj["unit"],
                            "material_rate": i_mat_rate, "labor_rate": i_lab_rate, "total_rate": i_mat_rate + i_lab_rate,
                            "date_updated": datetime.now().strftime('%d/%m/%Y')
                        })
                        save_data(st.session_state.rfq_history)
                        st.toast(f"บันทึกข้อมูลสำเร็จ!", icon="✅")
                        st.rerun()
                                 
                if target_sup_obj.get("items"):
                    df_sup_items = pd.DataFrame(target_sup_obj["items"])[["item_code", "category", "item_name", "unit", "material_rate", "labor_rate", "total_rate", "date_updated"]]
                    df_sup_items.columns = ["รหัสสินค้า", "หมวดหมู่", "รายการวัสดุ", "หน่วย", "ราคาวัสดุ/หน่วย", "ค่าแรง/หน่วย", "ราคารวมต่อหน่วย", "วันที่บันทึก"]
                    st.dataframe(df_sup_items, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 📊 ตารางเปรียบเทียบราคา ณ ปัจจุบัน")
            if current_rfq["suppliers"]:
                h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2, 1.5, 3, 1.5, 1.5])
                h_col1.markdown("**ชื่อร้านค้า**")
                h_col2.markdown("**ราคาเสนอโดยรวม (บาท)**")
                h_col3.markdown("**เงื่อนไขเพิ่มเติม**")
                h_col4.markdown("**วันที่บันทึก**")
                h_col5.markdown("**ไฟล์ใบเสนอราคา**")
                st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True)
                for idx, s in enumerate(current_rfq["suppliers"]):
                    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([2, 1.5, 3, 1.5, 1.5])
                    r_col1.write(s["name"])
                    r_col2.write(f"{s['price']:,.2f}")
                    r_col3.write(s["terms"] if s["terms"] else "-")
                    r_col4.write(s["date_added"].split()[0])
                    
                    f_path = s.get("file_path", "")
                    if f_path and not os.path.isabs(f_path): f_path = os.path.join(BASE_DIR, f_path)
                    if f_path and os.path.exists(f_path):
                        with open(f_path, "rb") as file_data:
                            r_col5.download_button(label="📁 เปิด/ดาวน์โหลด", data=file_data.read(), file_name=os.path.basename(f_path), key=f"btn_dl_tab2_{selected_rfq_id}_{idx}")
                    else: r_col5.caption("❌ ไม่มีไฟล์แนบ")

    with sub_tab3:
        if not st.session_state.rfq_history: st.warning("ยังไม่มีข้อมูล")
        else:
            for item in st.session_state.rfq_history:
                with st.expander(f"📋 {item['id']} [โครงการ: {item.get('project', 'ทั่วไป')}] - Status: {item['status']}"):
                    st.write(f"**รายละเอียดงาน:** {item['details']}")
                    st.write(f"**ผู้ร้องขอ:** {item['requestor']} | **กำหนดส่งมอบ:** {item['deadline']}")
                    st.markdown("**Timeline Log:**")
                    for log in item.get("history_logs", []): st.text(log)

    with sub_tab4:
        st.markdown("### 👤 ระบบบริหารและจัดการรายชื่อผู้ร้องขอโครงการ")
        u_col1, u_col2 = st.columns(2)
        with u_col1:
            st.markdown("#### **➕ บันทึกรายชื่อผู้ร้องขอใหม่**")
            new_name = st.text_input("ชื่อ-นามสกุล ของเจ้าหน้าที่คนใหม่", key="tab4_add_user_input")
            if st.button("💾 บันทึกรายชื่อเข้าสู่ระบบ", key="tab4_save_user_btn"):
                if new_name:
                    clean_name = new_name.strip()
                    if clean_name not in st.session_state.requestors_list:
                        st.session_state.requestors_list.append(clean_name)
                        save_requestors(st.session_state.requestors_list)
                        st.success(f"บันทึกสำเร็จ")
                        st.rerun()
                    else: st.warning("รายชื่อนี้มีอยู่ในระบบแล้ว")
        with u_col2:
            st.markdown("#### **❌ ลบรายชื่อออกจากฐานข้อมูล**")
            if not st.session_state.requestors_list: st.caption("ไม่มีรายชื่อให้จัดการ")
            else:
                name_to_delete = st.selectbox("เลือกรายชื่อที่ต้องการคัดออก", st.session_state.requestors_list, key="tab4_del_user_select")
                if st.button("🗑️ ยืนยันการลบชื่อนี้ออกจากคลัง", key="tab4_del_user_btn"):
                    is_name_used = any(rfq.get("requestor") == name_to_delete for rfq in st.session_state.rfq_history)
                    if is_name_used: st.error(f"❌ ไม่สามารถลบรายชื่อได้ เนื่องจากเคยนำไปเปิดใบงาน RFQ แล้ว")
                    else:
                        st.session_state.requestors_list.remove(name_to_delete)
                        save_requestors(st.session_state.requestors_list)
                        st.success(f"ลบเรียบร้อย")
                        st.rerun()

# =========================================================================
# 🏢 ข้อมูล Supplier
# =========================================================================
elif main_menu == "🏢 ข้อมูล Supplier":
    st.title("🏢 ระบบฐานข้อมูลทะเบียน Supplier สำคัญ")
    s_tab1, s_tab2, s_tab3 = st.tabs(["➕ เพิ่ม Supplier ใหม่", "🔍 ดูข้อมูลซัพพลายเออร์", "📍 ค้นหาตามพื้นที่รับงาน"])
    
    with s_tab1:
        st.markdown("### ➕ เพิ่มข้อมูล Supplier และอัปโหลดหลักฐาน")
        s_name = st.text_input("ชื่อซัพพลายเออร์ / ชื่อบริษัท", key=f"add_s_name_{st.session_state.sup_clear_counter}")
        s_tax = st.text_input("เลขประจำตัวผู้เสียภาษี (Tax ID)", key=f"add_s_tax_{st.session_state.sup_clear_counter}")
        
        st.markdown("**🌍 พื้นที่ที่สามารถรับงานได้:**")
        st.info(st.session_state.areas_output_add)
        if st.button("🗺️ เปิดหน้าต่างเลือกพื้นที่รับงาน (Popup)", key=f"btn_pop_areas_add_{st.session_state.sup_clear_counter}", icon="🌍"):
            select_areas_dialog()
             
        s_address = st.text_area("ที่อยู่บริษัท", key=f"add_s_address_{st.session_state.sup_clear_counter}")
        s_credit = st.text_input("เครดิตเทอม", key=f"add_s_credit_{st.session_state.sup_clear_counter}")
        s_info = st.text_area("หมายเหตุทั่วไป", key=f"add_s_info_{st.session_state.sup_clear_counter}")
        
        st.markdown("#### 📄 เอกสารนิติบุคคลคู่ค้าสำคัญ")
        file_pp20 = st.file_uploader("อัปโหลดไฟล์ ภ.พ.20", type=["pdf", "png", "jpg", "jpeg"], key=f"add_file_pp20_{st.session_state.sup_clear_counter}")
        file_cert = st.file_uploader("อัปโหลดไฟล์ หนังสือรับรองบริษัท", type=["pdf", "png", "jpg", "jpeg"], key=f"add_file_cert_{st.session_state.sup_clear_counter}")
        file_bb = st.file_uploader("อัปโหลดไฟล์ หน้าสมุกบัญชีธนาคาร (Book Bank)", type=["pdf", "png", "jpg", "jpeg"], key=f"add_file_bb_{st.session_state.sup_clear_counter}")
        
        st.markdown("#### 👥 บุคคลผู้ติดต่อประสานงาน")
        updated_contacts = []
        for i, contact in enumerate(st.session_state.temp_contacts):
            st.markdown(f"**ผู้ติดต่อคนที่ {i+1}**")
            c_c1, c_c2, c_c3, c_c4 = st.columns(4)
            c_name = c_c1.text_input("ชื่อ", value=contact["name"], key=f"s_cn_{i}_{st.session_state.sup_clear_counter}")
            c_phone = c_c2.text_input("เบอร์โทร", value=contact["phone"], key=f"s_cp_{i}_{st.session_state.sup_clear_counter}")
            c_email = c_c3.text_input("Email", value=contact["email"], key=f"s_ce_{i}_{st.session_state.sup_clear_counter}")
            c_line = c_c4.text_input("Line ID", value=contact["line"], key=f"s_cl_{i}_{st.session_state.sup_clear_counter}")
            updated_contacts.append({"name": c_name, "phone": c_phone, "email": c_email, "line": c_line})
        st.session_state.temp_contacts = updated_contacts
        
        if st.button("➕ เพิ่มรายชื่อผู้ติดต่ออีกคน"):
            st.session_state.temp_contacts.append({"name": "", "phone": "", "email": "", "line": ""})
            st.rerun()
            
        if st.button("💾 บันทึกข้อมูลขึ้นคลัง Supplier ถาวร"):
            if s_name:
                s_name = s_name.strip()
                if any(x["name"] == s_name for x in st.session_state.suppliers_master):
                    st.error("ชื่อซัพพลายเออร์รายนี้มีอยู่ในคลังแล้ว")
                else:
                    clean_dir = s_name
                    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']: clean_dir = clean_dir.replace(char, "_")
                    specific_folder = os.path.join(SUP_DOC_DIR, clean_dir)
                    if not os.path.exists(specific_folder): os.makedirs(specific_folder)
                    
                    p_pp20, p_cert, p_bb = "", "", ""
                    if file_pp20:
                        p_pp20 = os.path.join(specific_folder, f"ภพ20_{file_pp20.name}")
                        with open(p_pp20, "wb") as f: f.write(file_pp20.getbuffer())
                    if file_cert:
                        p_cert = os.path.join(specific_folder, f"หนังสือรับรอง_{file_cert.name}")
                        with open(p_cert, "wb") as f: f.write(file_cert.getbuffer())
                    if file_bb:
                        p_bb = os.path.join(specific_folder, f"บุ๊คแบงก์_{file_bb.name}")
                        with open(p_bb, "wb") as f: f.write(file_bb.getbuffer())
                        
                    st.session_state.suppliers_master.append({
                        "name": s_name, "tax_id": s_tax, "address": s_address, "credit": s_credit, 
                        "service_areas": st.session_state.areas_output_add, "general_info": s_info, 
                        "pp20_path": p_pp20, "cert_path": p_cert, "bb_path": p_bb, 
                        "contacts": st.session_state.temp_contacts
                    })
                    save_suppliers(st.session_state.suppliers_master)
                    
                    st.session_state.sup_clear_counter += 1
                    st.session_state.areas_output_add = "ยังไม่ได้เลือกพื้นที่"
                    st.session_state.temp_contacts = [{"name": "", "phone": "", "email": "", "line": ""}]
                    st.success("บันทึกข้อมูลเข้าคลังและล้างหน้าฟอร์มเรียบร้อยแล้ว!")
                    st.rerun()
            else: st.error("กรุณากรอกชื่อบริษัทซัพพลายเออร์")

    with s_tab2:
        st.markdown("### 🔍 ศูนย์ประวัติและฐานข้อมูลข้อมูลซัพพลายเออร์ฉบับเต็ม")
        col_pop1, col_pop2 = st.columns([2, 3])
        with col_pop1:
            if st.button("🏢 คลิกเพื่อเลือกซัพพลายเออร์ (POPUP ค้นหา)", use_container_width=True, icon="🔍"):
                select_supplier_popup()
                
        if not st.session_state.selected_supplier_name:
            st.info("💡 กรุณากดปุ่มด้านบนเพื่อเลือกซัพพลายเออร์ที่ต้องการเปิดดูข้อมูลโปรไฟล์ครับ")
        else:
            sup_name_target = st.session_state.selected_supplier_name
            if not any(x["name"] == sup_name_target for x in st.session_state.suppliers_master):
                st.session_state.selected_supplier_name = None
                st.warning("ไม่พบข้อมูลซัพพลายเออร์ที่เลือก")
            else:
                sup = next(x for x in st.session_state.suppliers_master if x["name"] == sup_name_target)
                idx_master = st.session_state.suppliers_master.index(sup)
                
                st.markdown("---")
                v_col1, v_col2 = st.columns([3, 2])
                with v_col1:
                    st.markdown(f"## 🏢 {sup['name']}")
                    st.write(f"**🔢 เลขประจำตัวผู้เสียภาษี (Tax ID):** {sup.get('tax_id','-')}")
                    st.write(f"**⏳ ข้อตกลงเครดิตเทอม:** {sup.get('credit','-')}")
                    st.write(f"**🌍 พื้นที่ที่สามารถรับงานได้:** {sup.get('service_areas','-')}")
                    st.write(f"**📍 ที่อยู่สำนักงาน/โรงงาน:**\n{sup.get('address','-')}")
                    st.write(f"**📝 ข้อมูลทั่วไป / หมายเหตุประกอบ:**\n{sup.get('general_info','-')}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    btn_c1, btn_c2 = st.columns(2)
                    if btn_c1.button("📝 แก้ไขข้อมูลพื้นฐานซัพพลายเออร์", use_container_width=True, key=f"edit_sup_act_{idx_master}"):
                        edit_supplier_popup(sup, idx_master)
                        
                    if btn_c2.button(f"🗑️ ลบข้อมูล Supplier นี้ออกจากระบบ", use_container_width=True, key=f"del_master_view_{idx_master}"):
                        for p_k in ["pp20_path", "cert_path", "bb_path"]:
                            p_v = sup.get(p_k, "")
                            if p_v and not os.path.isabs(p_v): p_v = os.path.join(BASE_DIR, p_v)
                            if p_v and os.path.exists(p_v):
                                try: os.remove(p_v)
                                except: pass
                        st.session_state.suppliers_master.remove(sup)
                        save_suppliers(st.session_state.suppliers_master)
                        st.session_state.selected_supplier_name = None
                        st.success(f"ลบข้อมูลเรียบร้อย")
                        st.rerun()
                                 
                with v_col2:
                    st.markdown("### 📂 คลังเอกสารนิติบุคคลแนบ")
                    paths = {"pp": sup.get("pp20_path", ""), "cert": sup.get("cert_path", ""), "bb": sup.get("bb_path", "")}
                    for k, v in paths.items():
                        if v and not os.path.isabs(v): paths[k] = os.path.join(BASE_DIR, v)
                    
                    if paths["pp"] and os.path.exists(paths["pp"]):
                        with open(paths["pp"], "rb") as f: st.download_button("📄 เปิดเอกสาร ภ.พ.20", f.read(), file_name=os.path.basename(paths["pp"]), key=f"view_pp_{idx_master}")
                    else: st.caption("❌ ไม่มีเอกสาร ภ.พ.20 แนบไว้")
                    if paths["cert"] and os.path.exists(paths["cert"]):
                        with open(paths["cert"], "rb") as f: st.download_button("📄 เปิดหนังสือรับรองบริษัท", f.read(), file_name=os.path.basename(paths["cert"]), key=f"view_cert_{idx_master}")
                    else: st.caption("❌ ไม่มีเอกสารหนังสือรับรองบริษัทแนบไว้")
                    if paths["bb"] and os.path.exists(paths["bb"]):
                        with open(paths["bb"], "rb") as f: st.download_button("📄 เปิดหน้าสมุดบัญชี (Book Bank)", f.read(), file_name=os.path.basename(paths["bb"]), key=f"view_bb_{idx_master}")
                    else: st.caption("❌ ไม่มีเอกสาร Book Bank แนบไว้")
                
                st.markdown("---")
                c_head1, c_head2 = st.columns([4, 1])
                c_head1.markdown("#### 👥 บัญชีรายชื่อเจ้าหน้าที่/ผู้ติดต่อประจำบริษัท")
                
                if c_head2.button("📝 แก้ไขรายชื่อผู้ติดต่อ", use_container_width=True, key=f"trigger_edit_contacts_{idx_master}"):
                    st.session_state.edit_contacts_list = json.loads(json.dumps(sup.get("contacts", [])))
                    if not st.session_state.edit_contacts_list:
                        st.session_state.edit_contacts_list = [{"name": "", "phone": "", "email": "", "line": ""}]
                    edit_contacts_popup(sup, idx_master)
                
                if not sup.get("contacts") or not any(c.get("name") for c in sup["contacts"]):
                    st.caption("ไม่ได้บันทึกรายชื่อผู้ติดต่อสำหรับซัพพลายเออร์รายนี้")
                else:
                    valid_contacts = [c for c in sup["contacts"] if c.get("name")]
                    df_contacts = pd.DataFrame(valid_contacts)
                    df_contacts = df_contacts[["name", "phone", "email", "line"]]
                    df_contacts.columns = ["ชื่อผู้ติดต่อ", "เบอร์โทรศัพท์", "อีเมล (Email)", "Line ID"]
                    st.dataframe(df_contacts, use_container_width=True, hide_index=True)

    with s_tab3:
        st.markdown("### 🗺️ ค้นหาตรวจสอบรายชื่อซัพพลายเออร์ตามพิกัดพื้นที่ปฏิบัติงาน")
        st.caption("คลิกเพื่อเลือกหรือพิมพ์เสิร์ชรายจังหวัด ตัวระบบจะคัดกรองคู่ค้าจัดซื้อที่สามารถไปวิ่งหน้างานจุดพิกัดนั้นขึ้นมาสรุปให้ทันที")
        
        if not st.session_state.suppliers_master:
            st.warning("⚠️ ปัจจุบันไม่มีข้อมูลซัพพลายเออร์ในระบบคลังคู่ค้า กรุณาลงทะเบียนข้อมูลที่แท็บแรกก่อนครับ")
        else:
            col_pop_prov1, col_pop_prov2 = st.columns([2, 3])
            with col_pop_prov1:
                if st.button("🎯 คลิกเพื่อเลือกจังหวัดไซต์งาน (POPUP ค้นหา)", use_container_width=True, icon="🎯"):
                    select_search_province_popup()
            
            if not st.session_state.get('selected_search_province'):
                st.info("💡 กรุณากดปุ่มด้านบนเพื่อเปิดหน้าต่างเสิร์ชค้นหาและคลิกพิกัดจังหวัดที่ต้องการตรวจสอบครับ")
            else:
                target_search_prov = st.session_state.selected_search_province
                st.markdown(f"### 📍 เขตพื้นที่สืบค้นไซต์งาน: **{target_search_prov}**")
                
                belonging_reg_name = ""
                for reg_k, provinces_list in THAI_REGIONS.items():
                    if target_search_prov in provinces_list:
                        belonging_reg_name = reg_k
                        break
                
                matched_area_sups = []
                for s in st.session_state.suppliers_master:
                    sup_areas = s.get("service_areas", "")
                    if sup_areas == "ทุกจังหวัดทั่วประเทศ":
                        matched_area_sups.append(s)
                    elif target_search_prov in sup_areas:
                        matched_area_sups.append(s)
                    elif belonging_reg_name and f"ทั้งหมดใน{belonging_reg_name}" in sup_areas:
                        matched_area_sups.append(s)
                        
                st.markdown(f"พบซัพพลายเออร์ที่รองรับงานพิกัดเขตนี้ทั้งหมด **{len(matched_area_sups)}** บริษัท")
                st.markdown("<hr style='margin:5px 0px 15px 0px;'>", unsafe_allow_html=True)
                
                if not matched_area_sups:
                    st.caption(f"❌ ปัจจุบันยังไม่มีข้อมูลบริษัทใดลงทะเบียนบริการครอบคลุมเขตพื้นที่จังหวัด {target_search_prov}")
                else:
                    display_area_data = []
                    for s in matched_area_sups:
                        main_contact_person = "-"
                        if s.get("contacts") and s["contacts"][0].get("name"):
                            main_contact_person = f"{s['contacts'][0]['name']} ({s['contacts'][0].get('phone', '-')})"
                                             
                        display_area_data.append({
                            "ชื่อบริษัท / ผู้ขาย": s["name"],
                            "เลขประจำตัวผู้เสียภาษี (Tax ID)": s.get("tax_id", "-"),
                            "ข้อตกลงเครดิตเทอม": s.get("credit", "-"),
                            "ผู้ติดต่อหลักคนแรก": main_contact_person,
                            "ขอบเขตพื้นที่บริการทั้งหมดที่บันทึก": s.get("service_areas", "-")
                        })
                        
                    df_area_report = pd.DataFrame(display_area_data)
                    st.dataframe(df_area_report, use_container_width=True, hide_index=True)

# =========================================================================
# 📊 BOQ Supplier
# =========================================================================
elif main_menu == "📊 BOQ Supplier":
    st.title("📊 BOQ Supplier • ศูนย์วิเคราะห์เปรียบเทียบและสืบค้นราคา")
    boq_tab1, boq_tab2, boq_tab3 = st.tabs(["📈 เปรียบเทียบใบเสนอราคาประจำโครงการ", "🔍 ค้นหาประวัติ Unit Rate / Item", "➕ บันทึกราคาตรงเข้าคลัง (ไม่อ้างอิง RFQ)"])
    
    with boq_tab1:
        if not st.session_state.rfq_history: st.warning("ยังไม่มีข้อมูล RFQ ในระบบ")
        else:
            rfq_options = [f"{x['id']} [โครงการ: {x.get('project', 'ทั่วไป')}]" for x in st.session_state.rfq_history]
            selected_display = st.selectbox("เลือกหมายเลข RFQ เพื่อเปิดดูตารางเปรียบเทียบราคา BOQ", rfq_options, key="boq_rfq_select")
            selected_rfq_id = selected_display.split()[0]
            current_rfq = next(x for x in st.session_state.rfq_history if x["id"] == selected_rfq_id)
            
            st.info(f"📋 **หัวข้อใบงาน:** {current_rfq['details']} | **ผู้ร้องขอ:** {current_rfq['requestor']} | **สถานะ:** {current_rfq['status']}")
            st.markdown("### 📈 ตารางเปรียบเทียบราคาเสนอจากทุก Supplier")
            
            if not current_rfq.get("suppliers"): st.caption("เคสนี้ยังไม่มีข้อมูลการเสนอราคาจากซัพพลายเออร์บันทึกไว้")
            else:
                sorted_sups = sorted(current_rfq["suppliers"], key=lambda x: x["price"])
                h_c1, h_c2, h_c3, h_c4, h_c5 = st.columns([2, 1.5, 3, 1.5, 1.5])
                h_c1.markdown("**ชื่อร้านค้า/ซัพพลายเออร์**")
                h_c2.markdown("**ราคารวมสุทธิ (บาท)**")
                h_c3.markdown("**เงื่อนไข / เครดิตเทอม**")
                h_c4.markdown("**วันที่บันทึกราคานี้**")
                h_c5.markdown("**เปิดเอกสารแนบ**")
                st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True)
                
                for idx, s in enumerate(sorted_sups):
                    r_c1, r_c2, r_c3, r_c4, r_c5 = st.columns([2, 1.5, 3, 1.5, 1.5])
                    if idx == 0 and len(sorted_sups) > 1: r_c1.write(f"🥇 **{s['name']}** (ราคาดีที่สุด)")
                    else: r_c1.write(s["name"])
                    r_c2.write(f"{s['price']:,.2f}")
                    r_c3.write(s["terms"] if s["terms"] else "-")
                    r_c4.write(s["date_added"])
                                     
                    f_p = s.get("file_path", "")
                    if f_p and not os.path.isabs(f_p): f_p = os.path.join(BASE_DIR, f_p)
                    if f_p and os.path.exists(f_p):
                        with open(f_p, "rb") as f: r_c5.download_button(label="📁 เปิดดูไฟล์ใบเสนอราคา", data=f.read(), file_name=os.path.basename(f_p), key=f"dl_boq_view_{idx}")
                    else: r_c5.caption("❌ ไม่มีไฟล์แนบ")

    with boq_tab2:
        st.markdown("### 🔍 ค้นหาและบริหารจัดการประวัติราคาวัสดุ-ค่าแรงแยกรายการ")
        st.caption("💡 พี่สามารถติ๊กถูกหน้าข้อที่ต้องการ (เลือกได้ทีละ 1 ข้อ) เพื่อเปิดเครื่องมือแก้ไขข้อมูลทั่วไป/เปลี่ยนซัพพลายเออร์ หรือกดลบรายการนั้นออกครับ")
        
        search_lay1, search_lay2 = st.columns([4, 1])
        search_query = search_lay1.text_input("ค้นหาประวัติราคา", placeholder="พิมพ์ชื่อรายการวัสดุ หมวดหมู่ หรือชื่อร้านค้า เช่น CV 1C-150sq.mm", label_visibility="collapsed")
        
        flat_records = []
        # ดึงจากระบบ RFQ
        for rfq_idx, rfq in enumerate(st.session_state.rfq_history):
            for sup_idx, sup in enumerate(rfq.get("suppliers", [])):
                for item_idx, item in enumerate(sup.get("items", [])):
                    flat_records.append({
                        "source_type": "rfq",
                        "rfq_id": rfq["id"],
                        "sup_name": sup["name"],
                        "item_code": item.get("item_code", ""),
                        "index_keys": (rfq_idx, sup_idx, item_idx),
                        "หมวดหมู่": item.get("category", "ทั่วไป"),
                        "รายการวัสดุ": item.get("item_name", "-"),
                        "ชื่อบริษัท/ผู้ขาย": sup["name"],
                        "หน่วย": item.get("unit", "-"),
                        "ราคาวัสดุ / หน่วย (บาท)": float(item.get("material_rate", 0.0)),
                        "ค่าแรง/หน่วย (บาท)": float(item.get("labor_rate", 0.0)),
                        "ราคารวมต่อหน่วย (บาท)": float(item.get("total_rate", 0.0)),
                        "วันที่อัปเดตราคา": item.get("date_updated", "-"),
                        "อ้างอิงแหล่งข้อมูล": f"RFQ: {rfq['id']}"
                    })
                    
        # ดึงจากระบบราคาตรง (Standalone)
        for sa_idx, item in enumerate(st.session_state.standalone_prices):
            flat_records.append({
                "source_type": "standalone",
                "index_keys": sa_idx,
                "หมวดหมู่": item.get("category", "ทั่วไป"),
                "รายการวัสดุ": item.get("item_name", "-"),
                "ชื่อบริษัท/ผู้ขาย": item.get("supplier_name", "-"),
                "หน่วย": item.get("unit", "-"),
                "ราคาวัสดุ / หน่วย (บาท)": float(item.get("material_rate", 0.0)),
                "ค่าแรง/หน่วย (บาท)": float(item.get("labor_rate", 0.0)),
                "ราคารวมต่อหน่วย (บาท)": float(item.get("total_rate", 0.0)),
                "วันที่อัปเดตราคา": item.get("date_updated", "-"),
                "อ้างอิงแหล่งข้อมูล": "Standalone (คลังตรง)"
            })
            
        if not flat_records:
            st.info("💡 ปัจจุบันยังไม่มีข้อมูลรายการวัสดุแยกย่อยในคลังระบบ")
        else:
            if search_query:
                q = search_query.strip().lower()
                filtered_records = [r for r in flat_records if q in r["รายการวัสดุ"].lower() or q in r["หมวดหมู่"].lower() or q in r["ชื่อบริษัท/ผู้ขาย"].lower()]
            else:
                filtered_records = flat_records
                
            st.markdown(f"พบรายการราคาวัสดุทั้งหมด **{len(filtered_records)}** รายการ")
            
            if filtered_records:
                df_history = pd.DataFrame(filtered_records)
                df_history.insert(0, "เลือกรายการ 🎯", False)
                
                show_cols = ["เลือกรายการ 🎯", "หมวดหมู่", "รายการวัสดุ", "ชื่อบริษัท/ผู้ขาย", "หน่วย", "ราคาวัสดุ / หน่วย (บาท)", "ค่าแรง/หน่วย (บาท)", "ราคารวมต่อหน่วย (บาท)", "วันที่อัปเดตราคา", "อ้างอิงแหล่งข้อมูล"]
                                 
                edited_df = st.data_editor(
                    df_history[show_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "เลือกรายการ 🎯": st.column_config.CheckboxColumn(required=True),
                        "หมวดหมู่": st.column_config.TextColumn(disabled=True),
                        "รายการวัสดุ": st.column_config.TextColumn(disabled=True),
                        "ชื่อบริษัท/ผู้ขาย": st.column_config.TextColumn(disabled=True),
                        "หน่วย": st.column_config.TextColumn(disabled=True),
                        "ราคาวัสดุ / หน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True),
                        "ค่าแรง/หน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True),
                        "ราคารวมต่อหน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True),
                        "วันที่อัปเดตราคา": st.column_config.TextColumn(disabled=True),
                        "อ้างอิงแหล่งข้อมูล": st.column_config.TextColumn(disabled=True)
                    }
                )
                
                checked_rows = edited_df[edited_df["เลือกรายการ 🎯"] == True]
                
                if len(checked_rows) > 1:
                    st.warning("⚠️ พี่ติ๊กเลือกพร้อมกันหลายข้อเกินไปครับ กรุณาเลือกติ๊กถูกแค่ 'ข้อเดียว' ที่ต้องการจัดการครับ")
                elif len(checked_rows) == 1:
                    st.markdown("---")
                    target_idx = checked_rows.index[0]
                    target_row = filtered_records[target_idx]
                    
                    st.markdown(f"### ⚙️ เครื่องมือจัดการ: *{target_row['รายการวัสดุ']}*")
                                 
                    if st.session_state.suppliers_master:
                        master_sups = [s["name"] for s in st.session_state.suppliers_master]
                        if target_row["ชื่อบริษัท/ผู้ขาย"] not in master_sups:
                            master_sups.append(target_row["ชื่อบริษัท/ผู้ขาย"])
                        current_sup_idx = master_sups.index(target_row["ชื่อบริษัท/ผู้ขาย"])
                    else:
                        master_sups = [target_row["ชื่อบริษัท/ผู้ขาย"]]
                        current_sup_idx = 0
                    
                    with st.form("edit_single_record_form", clear_on_submit=False):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            edit_sup = st.selectbox("📝 แก้ไข/เปลี่ยนชื่อผู้ขาย (Supplier)", master_sups, index=current_sup_idx)
                            edit_cat = st.selectbox("แก้ไขหมวดหมู่งาน", st.session_state.categories_list, index=st.session_state.categories_list.index(target_row["หมวดหมู่"]) if target_row["หมวดหมู่"] in st.session_state.categories_list else 0)
                            edit_name = st.text_input("แก้ไขรายการวัสดุ / รายละเอียดพัสดุ", value=target_row["รายการวัสดุ"])
                        
                        with col_e2:
                            edit_unit = st.selectbox("แก้ไขหน่วยนับพัสดุ", st.session_state.units_list, index=st.session_state.units_list.index(target_row["หน่วย"]) if target_row["หน่วย"] in st.session_state.units_list else 0)
                            edit_mat = st.number_input("แก้ไขราคาวัสดุ/หน่วย (บาท)", min_value=0.0, value=target_row["ราคาวัสดุ / หน่วย (บาท)"], format="%.2f", step=1.0)
                            edit_lab = st.number_input("แก้ไขค่าแรงต่อหน่วย (บาท)", min_value=0.0, value=target_row["ค่าแรง/หน่วย (บาท)"], format="%.2f", step=1.0)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        btn_space1, btn_space2 = st.columns([3, 1])
                                                 
                        if btn_space1.form_submit_button("💾 บันทึกการแก้ไขข้อมูลทั้งหมดของรายการนี้", use_container_width=True):
                            if target_row["source_type"] == "rfq":
                                r_idx, s_idx, i_idx = target_row["index_keys"]
                                st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["name"] = edit_sup
                                item_ptr = st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"][i_idx]
                                item_ptr["category"] = edit_cat
                                item_ptr["item_name"] = edit_name
                                item_ptr["unit"] = edit_unit
                                item_ptr["material_rate"] = edit_mat
                                item_ptr["labor_rate"] = edit_lab
                                item_ptr["total_rate"] = edit_mat + edit_lab
                                item_ptr["date_updated"] = datetime.now().strftime('%d/%m/%Y')
                                
                            elif target_row["source_type"] == "standalone":
                                sa_idx = target_row["index_keys"]
                                item_ptr = st.session_state.standalone_prices[sa_idx]
                                item_ptr["supplier_name"] = edit_sup
                                item_ptr["category"] = edit_cat
                                item_ptr["item_name"] = edit_name
                                item_ptr["unit"] = edit_unit
                                item_ptr["material_rate"] = edit_mat
                                item_ptr["labor_rate"] = edit_lab
                                item_ptr["total_rate"] = edit_mat + edit_lab
                                item_ptr["date_updated"] = datetime.now().strftime('%d/%m/%Y')
                                
                            save_data(st.session_state.rfq_history)
                            save_standalone_prices(st.session_state.standalone_prices)
                            st.toast("อัปเดตข้อมูลและราคาพัสดุสำเร็จเรียบร้อย!", icon="✅")
                            st.rerun()
                            
                        if btn_space2.form_submit_button("🗑️ ลบรายการนี้ออก", use_container_width=True, type="primary"):
                            if target_row["source_type"] == "rfq":
                                r_idx, s_idx, i_idx = target_row["index_keys"]
                                st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"].pop(i_idx)
                            elif target_row["source_type"] == "standalone":
                                sa_idx = target_row["index_keys"]
                                st.session_state.standalone_prices.pop(sa_idx)
                                
                            save_data(st.session_state.rfq_history)
                            save_standalone_prices(st.session_state.standalone_prices)
                            st.toast("ลบรายการประวัติราคาเรียบร้อยแล้ว!", icon="🗑️")
                            st.rerun()

    with boq_tab3:
        st.markdown("### ➕ บันทึกข้อมูลวัสดุตรงเข้าคลังราคา (ไม่อ้างอิงใบงาน RFQ)")
        if not st.session_state.item_codes_master: st.error("⚠️ ยังไม่มีฐานข้อมูลวัสดุกลาง")
        else:
            form_layout_c1, form_layout_c2 = st.columns([2, 1])
            with form_layout_c1:
                with st.form("standalone_input_form", clear_on_submit=True):
                    if not st.session_state.suppliers_master:
                        st.error("⚠️ ยังไม่มีรายชื่อ Supplier ในระบบ")
                        selected_sup_name = None
                    else: selected_sup_name = st.selectbox("ชื่อบริษัท / ผู้ขาย", [s["name"] for s in st.session_state.suppliers_master])
                    
                    item_choices_boq = [f"[{i['code']}] {i['item_name']}" for i in st.session_state.item_codes_master]
                    selected_item_boq = st.selectbox("เลือกรายการวัสดุ (Item Code Center)", item_choices_boq)
                    target_code_boq = selected_item_boq.split("]")[0].replace("[", "")
                    item_master_boq_obj = next(i for i in st.session_state.item_codes_master if i["code"] == target_code_boq)
                    
                    st.caption(f"💡 หมวดหมู่: `{item_master_boq_obj['category']}` | หน่วย: `{item_master_boq_obj['unit']}`")
                    st_mat_rate = st.number_input("ราคาวัสดุหน่วย (บาท)", min_value=0.0, step=0.01, format="%.2f")
                    st_lab_rate = st.number_input("ค่าแรงต่อหน่วย (บาท)", min_value=0.0, step=0.01, format="%.2f")
                    st_date = st.date_input("วันที่ได้รับราคา", datetime.now())
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("🟩 บันทึกข้อมูลเข้าคลังราคา"):
                        if selected_sup_name:
                            # [FIXED] แปลงฟอร์แมตวันที่ที่ดึงจาก date_input ให้เป็น string ที่เซฟลง JSON ได้อย่างปลอดภัย
                            date_str = st_date.strftime('%d/%m/%Y') if hasattr(st_date, 'strftime') else str(st_date)
                            st.session_state.standalone_prices.append({
                                "item_code": item_master_boq_obj["code"], "category": item_master_boq_obj["category"],
                                "item_name": item_master_boq_obj["item_name"], "supplier_name": selected_sup_name,
                                "unit": item_master_boq_obj["unit"], "material_rate": st_mat_rate, "labor_rate": st_lab_rate,
                                "total_rate": st_mat_rate + st_lab_rate, "date_updated": date_str
                            })
                            save_standalone_prices(st.session_state.standalone_prices)
                            st.success(f"💾 จัดเก็บเรียบร้อย!")
                            st.rerun()

# =========================================================================
# 🗂️ บริหาร Item Code
# =========================================================================
elif main_menu == "🗂️ บริหาร Item Code":
    st.title("🗂️ ศูนย์บริหารคลังฐานข้อมูลสินค้าและรหัสสินค้ากลาง (Item Code Master)")
    item_tab1, item_tab2 = st.tabs(["➕ เพิ่ม Item Code มาตรฐานใหม่", "📋 ทำเนียบสืบค้นตรวจสอบรหัสทั้งหมด"])
    
    with item_tab1:
        st.markdown("### ➕ เพิ่มพัสดุและรหัสสินค้าใหม่เข้าสู่ระบบ")
        
        cat_lay1, cat_lay2 = st.columns([5, 1])
        with cat_lay1:
            i_cat = st.selectbox(
                "1. เลือกหมวดหมู่งาน / กลุ่มวัสดุ ก่อนเป็นอันดับแรก", 
                st.session_state.categories_list, 
                help="💡 สามารถพิมพ์ชื่อเพื่อเสิร์ชหาหมวดหมู่เดิมด่วนได้ทันทีครับ"
            )
        with cat_lay2:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ ลงทะเบียนหมวดหมู่", use_container_width=True, help="เปิดหน้าต่างลงทะเบียนเพิ่มกลุ่มงานชิ้นใหม่"):
                add_category_dialog()
                
        if i_cat:
            prefix_char = i_cat[0]
            prefix = f"{prefix_char}-"
            
            max_seq = 0
            for item in st.session_state.item_codes_master:
                code_str = item.get("code", "")
                if code_str.startswith(prefix):
                    try:
                        current_num = int(code_str.split("-")[1])
                        if current_num > max_seq:
                            max_seq = current_num
                    except (IndexError, ValueError):
                        pass
            
            next_itm_seq = max_seq + 1
            auto_itm_code = f"{prefix}{next_itm_seq:04d}"
        else:
            auto_itm_code = "ITM-0001"
            
        st.markdown("---")
        st.markdown("##### 📝 รายละเอียดรหัสสินค้าใหม่")
        
        i_code = st.text_input("รหัสสินค้า (Item Code)", value=auto_itm_code)
        i_name = st.text_input("2. รายการวัสดุ / รายละเอียดพัสดุ (Item Description)", placeholder="เช่น CV 1C-150sq.mm (1Core) 0.6/1KV")
        
        u_lay1, u_lay2 = st.columns([5, 1])
        with u_lay1: 
            i_unit = st.selectbox("3. หน่วยนับพัสดุ (Unit)", st.session_state.units_list)
        with u_lay2:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ ลงทะเบียนหน่วย", use_container_width=True, help="เปิดหน้าต่างลงทะเบียนเพิ่มหน่วยนับชิ้นใหม่"): 
                add_unit_dialog()
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 บันทึกรหัสพัสดุนี้เข้าคลังมาสเตอร์", use_container_width=True, type="primary"):
            if i_code and i_name:
                i_code = i_code.strip()
                i_name = i_name.strip()
                
                if any(x["code"] == i_code for x in st.session_state.item_codes_master): 
                    st.error(f"❌ ไม่สามารถบันทึกได้ เนื่องจากรหัสสินค้า '{i_code}' มีอยู่ในระบบแล้ว")
                else:
                    st.session_state.item_codes_master.append({
                        "code": i_code, 
                        "category": i_cat, 
                        "item_name": i_name, 
                        "unit": i_unit
                    })
                    save_item_codes(st.session_state.item_codes_master)
                    st.toast(f"✅ บันทึกรหัสสินค้า {i_code} เข้าสารบบกลางเรียบร้อย!", icon="🎉")
                    st.rerun()
            else:
                st.error("❌ กรุณากรอกรหัสสินค้าและรายละเอียดพัสดุให้ครบถ้วนก่อนกดบันทึก")

    with item_tab2:
        if not st.session_state.item_codes_master: 
            st.info("💡 ปัจจุบันยังไม่มีข้อมูลวัสดุในคลัง")
        else:
            df_items_master = pd.DataFrame(st.session_state.item_codes_master)
            df_display = df_items_master[["code", "category", "item_name", "unit"]]
            df_display.columns = ["รหัสสินค้า (Item Code)", "หมวดหมู่พัสดุ", "รายการวัสดุ / รายละเอียด", "หน่วยนับ (Unit)"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            item_list_del = [f"[{i['code']}] {i['item_name']}" for i in st.session_state.item_codes_master]
            selected_item_del_display = st.selectbox("เลือกรหัสพัสดุที่ต้องการคัดออก:", item_list_del)
            
            if st.button("🗑️ ยืนยันการลบรหัสสินค้าออกจากคลังหลัก"):
                target_del_code = selected_item_del_display.split("]")[0].replace("[", "")
                is_item_used_rfq = any(item.get("item_code") == target_del_code for rfq in st.session_state.rfq_history for sup in rfq.get("suppliers", []) for item in sup.get("items", []))
                is_item_used_standalone = any(x.get("item_code") == target_del_code for x in st.session_state.standalone_prices)
                         
                if is_item_used_rfq or is_item_used_standalone: 
                    st.error("❌ ไม่สามารถลบได้ เนื่องจากรหัสนี้ถูกนำไปใช้งานบันทึกราคาในประวัติจัดซื้อแล้ว")
                else:
                    item_to_remove = next(i for i in st.session_state.item_codes_master if i["code"] == target_del_code)
                    st.session_state.item_codes_master.remove(item_to_remove)
                    save_item_codes(st.session_state.item_codes_master)
                    st.success(f"ลบรหัสสินค้าเรียบร้อย")
                    st.rerun()

# =========================================================================
# 📝 จัดทำ BOQ เพื่อเสนอ (ปรับปรุงดึงข้อมูลผู้ร้องขอร่วมกับระบบ RFQ และอัปเดต PDF)
# =========================================================================
elif main_menu == "📝 จัดทำ BOQ เพื่อเสนอ":
    st.title("📝 ระบบจัดทำใบเสนอราคาและประมาณการ BOQ ขาออก")
    
    pur_tab1, pur_tab2 = st.tabs(["📋 ทะเบียนใบเสนอราคา (PUR)", "➕ สร้างเอกสารเสนอราคาโครงการใหม่"])
    
    with pur_tab1:
        st.subheader("📋 ประวัติรายการเสนองานและประมาณการราคาขาออกทั้งหมด")
        if not st.session_state.pur_proposals:
            st.info("💡 ปัจจุบันยังไม่มีการสร้างเอกสารเสนอราคา PUR ในคลังระบบ")
        else:
            # ตารางสรุปภาพรวมหน้ารวม
            summary_pur_data = []
            for proposal in st.session_state.pur_proposals:
                total_proposal_price = sum(float(item.get("total_price", 0.0)) for item in proposal.get("items", []))
                summary_pur_data.append({
                    "เลขที่ใบเสนอราคา": proposal["id"],
                    "ชื่อโครงการ / ไไซต์งาน": proposal.get("project_name", "-"),
                    "ชื่อลูกค้า / บริษัท": proposal.get("client_name", "-"),
                    "ผู้ร้องขอโครงการ": proposal.get("requestor", "-"),  # เพิ่มการแสดงผลในตารางสรุป
                    "วันที่ออกเอกสาร": proposal.get("date", "-"),
                    "จำนวนรายการวัสดุ": len(proposal.get("items", [])),
                    "มูลค่ารวมสุทธิ (บาท)": total_proposal_price
                })
            
            df_pur_report = pd.DataFrame(summary_pur_data)
            st.dataframe(df_pur_report, use_container_width=True, hide_index=True, column_config={"มูลค่ารวมสุทธิ (บาท)": st.column_config.NumberColumn(format="%,.2f")})
            
            st.markdown("---")
            st.markdown("##### 🎯 เลือกเอกสารเพื่อลงรายละเอียดพัสดุรายชิ้นงาน หรือพิมพ์เอกสาร PDF")
            pur_options = [f"{p['id']} | โครงการ: {p['project_name']}" for p in st.session_state.pur_proposals]
            selected_pur_option = st.selectbox("เลือกเลขที่เอกสาร PUR ที่ต้องการจัดการ:", pur_options)
            
            if selected_pur_option:
                target_pur_id = selected_pur_option.split(" | ")[0]
                curr_pur_obj = next(p for p in st.session_state.pur_proposals if p["id"] == target_pur_id)
                
                st.info(f"📁 **กำลังจัดการเอกสาร:** {curr_pur_obj['id']} | **โครงการ:** {curr_pur_obj['project_name']} | **ลูกค้า:** {curr_pur_obj['client_name']} | **ผู้ร้องขอ:** {curr_pur_obj.get('requestor', '-')}")
                
                # --- ส่วนลงรายละเอียด Line Items แยกย่อยภายในโครงการ (เพิ่มช่อง ยี่ห้อ และ Remark) ---
                st.markdown("#### ➕ เพิ่มรายการวัสดุและคำนวณราคาลงใน BOQ เสนอราคา")
                
                if not st.session_state.item_codes_master:
                    st.error("⚠️ ต้องไปลงทะเบียนไอเทมที่หน้า 'บริหาร Item Code' ก่อนครับ")
                else:
                    item_choices = [f"[{i['code']}] {i['item_name']} ({i['unit']})" for i in st.session_state.item_codes_master]
                    sel_item_choice = st.selectbox("ดึงรายการจากรหัสพัสดุกลาง:", item_choices)
                    
                    item_code_extracted = sel_item_choice.split("]")[0].replace("[", "")
                    master_item_ptr = next(i for i in st.session_state.item_codes_master if i["code"] == item_code_extracted)
                    
                    # บรรทัดที่ 1: กรอก จำนวน, ราคาวัสดุ, ค่าแรง
                    col_l1, col_l2, col_l3 = st.columns(3)
                    with col_l1:
                        input_qty = st.number_input("ระบุจำนวน (Quantity)", min_value=0.0, step=1.0, value=1.0)
                    with col_l2:
                        input_mat_rate = st.number_input("ระบุราคาวัสดุเสนอขาย / หน่วย (บาท)", min_value=0.0, step=10.0, value=0.0)
                    with col_l3:
                        input_lab_rate = st.number_input("ระบุค่าแรงเสนอขาย / หน่วย (บาท)", min_value=0.0, step=10.0, value=0.0)
                    
                    # [ADD] บรรทัดที่ 2: เพิ่มช่องสำหรับกรอก ยี่ห้อ/รุ่น และ Remark (หมายเหตุ) บนหน้าเว็บ
                    col_l4, col_l5 = st.columns(2)
                    with col_l4:
                        input_brand = st.text_input("ยี่ห้อ / รุ่น (Brand / Model)", placeholder="เช่น BCC, ABB, Link, N/A")
                    with col_l5:
                        input_remark = st.text_input("หมายเหตุ (Remark)", placeholder="เช่น ระบุข้อมูลเพิ่มเติมเฉพาะแถวนี้")
                        
                    if st.button("➕ กดเพื่อเพิ่มลำดับวัสดุรายการนี้เข้า BOQ", use_container_width=True, type="primary"):
                        unit_rate_total = input_mat_rate + input_lab_rate
                        line_total_price = unit_rate_total * input_qty
                        
                        if "items" not in curr_pur_obj:
                            curr_pur_obj["items"] = []
                            
                        # [UPDATED] บันทึกค่า ยี่ห้อ และ Remark ร่วมลงฐานข้อมูล JSON ของใบเสนอราคานั้น ๆ
                        curr_pur_obj["items"].append({
                            "item_code": master_item_ptr["code"],
                            "item_name": master_item_ptr["item_name"],
                            "unit": master_item_ptr["unit"],
                            "qty": input_qty,
                            "material_rate": input_mat_rate,
                            "labor_rate": input_lab_rate,
                            "unit_rate_total": unit_rate_total,
                            "total_price": line_total_price,
                            "brand": input_brand.strip() if input_brand else "-",   # บันทึกยี่ห้อ (ถ้าว่างจะใส่ขีดให้)
                            "remark": input_remark.strip() if input_remark else ""  # บันทึกหมายเหตุ
                        })
                        save_pur_proposals(st.session_state.pur_proposals)
                        st.toast("เพิ่มรายการพัสดุเข้า BOQ สำเร็จ!", icon="✅")
                        st.rerun()
                        
                # --- ตารางรายละเอียดวัสดุในใบเสนอราคาปัจจุบัน พร้อมไอคอนจัดการ ---
                if curr_pur_obj.get("items"):
                    st.markdown("##### 📊 ตารางรายละเอียดวัสดุในใบเสนอราคาปัจจุบัน") # [cite: 201]
                    
                    # หัวข้อตารางแสดงผลบนหน้าเว็บ
                    h_cols = st.columns([0.6, 1.2, 3.2, 0.8, 1.0, 1.3, 1.3, 1.5, 1.2]) # [cite: 202]
                    h_cols[0].markdown("**ลำดับ**") # [cite: 202]
                    h_cols[1].markdown("**รหัสวัสดุ**") # [cite: 202]
                    h_cols[2].markdown("**รายละเอียดวัสดุ**") # [cite: 202]
                    h_cols[3].markdown("**หน่วย**") # [cite: 202]
                    h_cols[4].markdown("**จำนวน**") # [cite: 202]
                    h_cols[5].markdown("**ราคา/หน่วย**") # [cite: 202]
                    h_cols[6].markdown("**ค่าแรง/หน่วย**") # [cite: 202]
                    h_cols[7].markdown("**ยอดรวมสุทธิ**") # [cite: 202]
                    h_cols[8].markdown("**จัดการ**")
                    st.markdown("<hr style='margin:0px 0px 10px 0px;'>", unsafe_allow_html=True)
                    
                    # วนลูปแสดงผลรายการวัสดุทีละบรรทัดพร้อมปุ่มกดไอคอน
                    for i, it in enumerate(curr_pur_obj["items"]): # [cite: 212]
                        r_cols = st.columns([0.6, 1.2, 3.2, 0.8, 1.0, 1.3, 1.3, 1.5, 1.2])
                        
                        # คำนวณราคาสุทธิของแถว
                        unit_rate_total = float(it.get("material_rate", 0.0)) + float(it.get("labor_rate", 0.0)) # [cite: 195]
                        line_total = unit_rate_total * float(it.get("qty", 0.0)) # [cite: 195]
                        
                        # หยอดข้อมูลลงคอลลัมน์
                        r_cols[0].write(f"{i+1}") # [cite: 213]
                        r_cols[1].write(f"`{it.get('item_code', '-')}`") # [cite: 213]
                        
                        # แสดงชื่อสินค้าพ่วงยี่ห้อ (ถ้ามีกรอกไว้)
                        item_display_name = it.get('item_name', '-') # [cite: 213]
                        if it.get('brand') and it['brand'] != "-":
                            item_display_name += f" ({it['brand']})"
                        r_cols[2].write(item_display_name)
                        
                        r_cols[3].write(f"{it.get('unit', '-')}") # [cite: 213]
                        r_cols[4].write(f"{it.get('qty', 0.0):,.0f}") # [cite: 213]
                        r_cols[5].write(f"{it.get('material_rate', 0.0):,.2f}") # [cite: 202]
                        r_cols[6].write(f"{it.get('labor_rate', 0.0):,.2f}") # [cite: 202]
                        r_cols[7].write(f"**{line_total:,.2f}**")
                        
                        # ฝังไอคอนปุ่มจัดการ ✏️ และ 🗑️ ไว้ท้ายแถวของแต่ละไอเทม
                        btn_col1, btn_col2 = r_cols[8].columns(2)
                        
                        # 1. ปุ่มไอคอนแก้ไข (✏️) เปิด Dialog ขึ้นมาแก้ไขเฉพาะชิ้น
                        if btn_col1.button("✏️", key=f"edit_pur_item_{curr_pur_obj['id']}_{i}", help="แก้ไขรายการนี้"):
                            @st.dialog(f"✏️ แก้ไขข้อมูลลำดับที่ {i+1}")
                            def edit_pur_item_dialog(item_idx, item_data):
                                edit_q = st.number_input("แก้ไขจำนวน (Qty)", min_value=0.0, value=float(item_data.get("qty", 1.0)), step=1.0)
                                edit_m = st.number_input("แก้ไขราคาวัสดุ / หน่วย", min_value=0.0, value=float(item_data.get("material_rate", 0.0)), step=10.0)
                                edit_l = st.number_input("แก้ไขค่าแรง / หน่วย", min_value=0.0, value=float(item_data.get("labor_rate", 0.0)), step=10.0)
                                edit_b = st.text_input("แก้ไขยี่ห้อ / รุ่น", value=item_data.get("brand", "-"))
                                edit_r = st.text_input("แก้ไขหมายเหตุ (Remark)", value=item_data.get("remark", ""))
                                
                                if st.button("💾 บันทึกการแก้ไขชิ้นนี้", use_container_width=True):
                                    item_data["qty"] = edit_q
                                    item_data["material_rate"] = edit_m
                                    item_data["labor_rate"] = edit_l
                                    item_data["unit_rate_total"] = edit_m + edit_l
                                    item_data["total_price"] = (edit_m + edit_l) * edit_q
                                    item_data["brand"] = edit_b.strip() if edit_b else "-"
                                    item_data["remark"] = edit_r.strip()
                                    
                                    save_pur_proposals(st.session_state.pur_proposals)
                                    st.toast("แก้ไขรายการสำเร็จ!", icon="✅")
                                    st.rerun()
                            
                            edit_pur_item_dialog(i, it)

                        # 2. ปุ่มไอคอนลบ (🗑️) สั่งดึงออกจากลิสต์แถวทันที
                        if btn_col2.button("🗑️", key=f"del_pur_item_{curr_pur_obj['id']}_{i}", help="ลบรายการนี้ออก"):
                            curr_pur_obj["items"].pop(i)
                            save_pur_proposals(st.session_state.pur_proposals)
                            st.toast("ลบรายการออกจากตารางเรียบร้อย!", icon="🗑️")
                            st.rerun()
                            
                    st.markdown("---")
                    # [FIXED] แก้ไขไวยากรณ์การดึงค่าไอเทมวนลูปให้ถูกต้องเรียบร้อย ไม่เกิด NameError ตัวแปรลอย
                    st.markdown("---")
                    grand_total_boq = sum(float(item.get("total_price", 0.0)) for item in curr_pur_obj["items"])
                    st.markdown(f"<h3 style='text-align: right; color:#00ffcc;'>💰 ยอดรวมมูลค่าเอกสารทั้งสิ้น: {grand_total_boq:,.2f} บาท</h3>", unsafe_allow_html=True)
                    
                    # --- ฟังก์ชันเขียนไฟล์และดาวน์โหลด PDF ขาออกตามรูปแบบ "ใบขอสอบราคา" ---
                    pdf_filename = f"Request_for_Quotation_{curr_pur_obj['id']}.pdf"
                    pdf_path = os.path.join(BASE_DIR, pdf_filename)
                    
                    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=25, bottomMargin=25)
                    story = []
                    
                    try:
                        font_file_path = os.path.join(BASE_DIR, 'DB Heavent v3.2.2.ttf')
                        pdfmetrics.registerFont(TTFont('DBHeavent', font_file_path))
                        
                        title_style = ParagraphStyle('TitleStyle', fontName='DBHeavent', fontSize=24, leading=26, alignment=1)
                        text_style = ParagraphStyle('TextStyle', fontName='DBHeavent', fontSize=13, leading=16)
                        text_bold = ParagraphStyle('TextBold', fontName='DBHeavent', fontSize=13, leading=16)
                        header_style = ParagraphStyle('HeaderStyle', fontName='DBHeavent', fontSize=12, leading=14, alignment=1)
                        footer_style = ParagraphStyle('FooterStyle', fontName='DBHeavent', fontSize=13, leading=15, alignment=1)
                        font_to_use = 'DBHeavent'
                    except Exception as e:
                        title_style = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=18, alignment=1)
                        text_style = ParagraphStyle('TextStyle', fontName='Helvetica', fontSize=10, leading=12)
                        text_bold = ParagraphStyle('TextBold', fontName='Helvetica-Bold', fontSize=10, leading=12)
                        header_style = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=9, alignment=1)
                        footer_style = ParagraphStyle('FooterStyle', fontName='Helvetica', fontSize=10, alignment=1)
                        font_to_use = 'Helvetica'

                    # 1. Header โลโก้บริษัท
                    logo_path = os.path.join(BASE_DIR, 'SHARGE.png')
                    if os.path.exists(logo_path):
                        logo_img = Image(logo_path, width=120, height=38)
                        logo_cell = logo_img
                    else:
                        logo_cell = Paragraph("<b>SHARGE</b>", title_style)
                        
                    top_header_data = [[logo_cell, Paragraph("<b>ใบขอสอบราคา</b>", title_style), ""]]
                    top_header_table = Table(top_header_data, colWidths=[150, 245, 140])
                    top_header_table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('ALIGN', (1,0), (1,0), 'CENTER'),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                    ]))
                    story.append(top_header_table)

                    # 2. บล็อกข้อมูลโครงการ
                    requestor_name = curr_pur_obj.get('requestor', '-')
                    client_company = curr_pur_obj.get('client_name', '-')
                    project_title = curr_pur_obj.get('project_name', '-')
                    doc_date = curr_pur_obj.get('date', '-')

                    left_block_text = f"<b>บริษัทที่เสนอ :</b> {client_company}<br/><b>โครงการ :</b> {project_title}<br/><b>ผู้ร้องขอโครงการ :</b> {requestor_name}"
                    right_block_text = f"<b>วันที่ request :</b> {doc_date}<br/><b>เลขที่ ร้องขอ :</b> {curr_pur_obj['id']}<br/><b>RFQ Ref :</b> -"

                    address_block_data = [
                        [Paragraph("<b>บริษัทที่เสนอ</b>", text_bold), "", Paragraph("", text_bold), ""], 
                        [Paragraph(left_block_text, text_style), "", Paragraph(right_block_text, text_style), ""]
                    ]
                    
                    address_table = Table(address_block_data, colWidths=[250, 15, 260, 10])
                    address_table.setStyle(TableStyle([
                        ('SPAN', (0,0), (1,0)), ('SPAN', (2,0), (3,0)), ('SPAN', (0,1), (1,1)), ('SPAN', (2,1), (3,1)), 
                        ('BACKGROUND', (0,0), (3,0), colors.HexColor("#EAEAEA")), 
                        ('BOX', (0,0), (1,1), 1, colors.HexColor("#CCCCCC")), ('BOX', (2,0), (3,1), 1, colors.HexColor("#CCCCCC")),    
                        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
                    ]))
                    story.append(address_table)
                    story.append(Spacer(1, 15))

                    # 3. โครงสร้างตารางเนื้อหาพัสดุในไฟล์ PDF (7 คอลัมน์ มีช่อง Unit ครบถ้วน)
                    table_data = [[
                        Paragraph("<b>ลำดับ</b>", header_style),
                        Paragraph("<b>รหัสสินค้า</b>", header_style),
                        Paragraph("<b>รายการสินค้า</b>", header_style),
                        Paragraph("<b>จำนวน</b>", header_style),
                        Paragraph("<b>Unit</b>", header_style),
                        Paragraph("<b>ราคา/หน่วย</b>", header_style),
                        Paragraph("<b>จำนวนเงินรวม</b>", header_style)
                    ]]
                    
                    table_styles_list = [
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#D9D9D9")),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#999999")),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ]
                    
                    current_row_idx = 1
                    for i, it in enumerate(curr_pur_obj["items"]):
                        display_name = it['item_name']
                        if it.get('brand') and it['brand'] != "-":
                            display_name += f" ({it['brand']})"
                            
                        unit_rate = float(it.get("unit_rate_total", it.get("material_rate", 0.0) + it.get("labor_rate", 0.0)))
                        total_line_price = unit_rate * float(it["qty"])
                        
                        table_data.append([
                            Paragraph(str(i+1), text_style),
                            Paragraph(it.get("item_code", "-"), text_style),
                            Paragraph(display_name, text_style),
                            Paragraph(f"{it['qty']:,.0f}", text_style),
                            Paragraph(it.get('unit', '-'), text_style),
                            Paragraph(f"{unit_rate:,.2f}", text_style),
                            Paragraph(f"{total_line_price:,.2f}", text_style)
                        ])
                        table_styles_list.append(('ALIGN', (0, current_row_idx), (1, current_row_idx), 'CENTER'))
                        table_styles_list.append(('ALIGN', (2, current_row_idx), (2, current_row_idx), 'LEFT'))
                        table_styles_list.append(('ALIGN', (3, current_row_idx), (4, current_row_idx), 'CENTER'))
                        table_styles_list.append(('ALIGN', (5, current_row_idx), (6, current_row_idx), 'RIGHT'))
                        current_row_idx += 1
                        
                    # เพิ่มแถวสรุปผลรวมท้ายตาราง (ขยาย SPAN ครอบคลุม 5 คอลัมน์แรกเพื่อให้ฝั่งซ้ายล่างตารางโล่งสะอาด)
                    table_data.append(["", "", "", "", "", Paragraph("<b>มูลค่ารวมทั้งสิ้น</b>", text_bold), Paragraph(f"<b>{grand_total_boq:,.2f}</b>", text_bold)])
                    table_styles_list.append(('SPAN', (0, current_row_idx), (4, current_row_idx)))
                    table_styles_list.append(('BACKGROUND', (5, current_row_idx), (6, current_row_idx), colors.HexColor("#EAEAEA")))
                    table_styles_list.append(('ALIGN', (5, current_row_idx), (5, current_row_idx), 'LEFT'))
                    table_styles_list.append(('ALIGN', (6, current_row_idx), (6, current_row_idx), 'RIGHT'))
                    table_styles_list.append(('LINEBEFORE', (0, current_row_idx), (0, current_row_idx), 0, colors.white))
                    table_styles_list.append(('LINEBELOW', (0, current_row_idx), (4, current_row_idx), 0, colors.white))
                    current_row_idx += 1
                    
                    # กำหนดความกว้างตารางรวม 535 พอดีหน้า A4 คำว่า "ลำดับ" ไม่ตกหล่นแน่นอน
                    pdf_table = Table(table_data, colWidths=[40, 65, 185, 40, 35, 85, 85])
                    pdf_table.setStyle(TableStyle(table_styles_list))
                    story.append(pdf_table)
                    story.append(Spacer(1, 40))

                    # 4. ช่องเซ็นชื่อผู้อนุมัติ / ผู้เสนอราคา
                    signature_data = [
                        ["(......................................................)", "", "(......................................................)"],
                        [Paragraph("<b>(ผู้อนุมัติ)</b>", footer_style), "", Paragraph("<b>(ผู้เสนอราคา)</b>", footer_style)],
                        ["", "", Paragraph("<b>SHARGE</b>", footer_style)],
                        ["", "", Paragraph("<b>(Procurement Department)</b>", footer_style)]
                    ]
                    signature_table = Table(signature_data, colWidths=[230, 75, 230])
                    signature_table.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('TOPPADDING', (0,0), (-1,-1), 1), ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                    ]))
                    story.append(signature_table)
                    doc.build(story)
                    
                    # ปุ่มดาวน์โหลดเอกสาร PDF ขาออกไปใช้งานพริ้นต์จริง
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="🖨️ ดาวน์โหลดใบเสนอราคาประมาณการรวมเป็นไฟล์ PDF",
                            data=pdf_file.read(),
                            file_name=pdf_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    # ปุ่มกดล้างหรือลบใบงาน PUR ชิ้นนี้ออกจากประวัติคลังข้อมูล
                    if st.button("🗑️ ลบเอกสารใบเสนอราคา PUR นี้ออกจากประวัติคลังข้อมูลทั้งหมด", type="primary"):
                        st.session_state.pur_proposals.remove(curr_pur_obj)
                        save_pur_proposals(st.session_state.pur_proposals)
                        st.success("ลบโปรเจกต์เสนอราคาเรียบร้อย")
                        st.rerun()

    with pur_tab2:
        st.subheader("🆕 บันทึกสร้างโปรเจกต์เอกสารเสนอราคา (ขาออก) ใบใหม่")
        
        curr_year_short = datetime.now().strftime('%y') 
        curr_month = datetime.now().strftime('%m')      
        pur_prefix = f"PUR-{curr_year_short}{curr_month}" 
        
        # นับจำนวนใบเสนอราคาในเดือนนี้ที่มีอยู่แล้วเพื่อรันตัวเลขต่อกัน
        count_pur_month = sum(1 for p in st.session_state.pur_proposals if p["id"].startswith(pur_prefix))
        auto_pur_id = f"{pur_prefix}{(count_pur_month + 1):04d}" 
        
        with st.form("create_pur_proposal_form", clear_on_submit=True):
            new_pur_id = st.text_input("เลขที่ใบเสนอราคาอัตโนมัติ (PUR ID)", value=auto_pur_id)
            new_pur_project = st.text_input("ชื่อโครงการประมาณการเสนอราคา", placeholder="เช่น งานปรับปรุงสถานีชาร์จไฟรถยนต์ EV แผนกโรงงาน")
            new_pur_client = st.text_input("ชื่อลูกค้า / บริษัทผู้ว่าจ้าง", placeholder="เช่น บริษัท ควอด อิเลคทริค จำกัด")
            
            # --- [ADD] ดึงชุดข้อมูลรายชื่อผู้ร้องขอแบบเดียวกับหน้าระบบจัดการ RFQ มาใช้งานร่วมกัน ---
            if not st.session_state.requestors_list:
                st.error("⚠️ ยังไม่มีรายชื่อผู้ร้องขอในระบบ กรุณาเพิ่มรายชื่อในระบบจัดการ RFQ ก่อน")
                selected_pur_requestor = None
            else:
                selected_pur_requestor = st.selectbox("เลือกผู้ร้องขอโครงการ (ดึงข้อมูลกลาง)", st.session_state.requestors_list)
                
            new_pur_date = st.date_input("วันที่ลงเอกสารออกเสนอราคา", datetime.now())
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 เปิดเล่ม / บันทึกตั้งต้นเอกสารโปรเจกต์นี้"):
                if new_pur_id and new_pur_project and new_pur_client and selected_pur_requestor:
                    st.session_state.pur_proposals.append({
                        "id": new_pur_id.strip(),
                        "project_name": new_pur_project.strip(),
                        "client_name": new_pur_client.strip(),
                        "requestor": selected_pur_requestor.strip(),  # บันทึกรายชื่อผู้ร้องขอลงฐานข้อมูล PUR
                        "date": new_pur_date.strftime('%d/%m/%Y'),
                        "items": []
                    })
                    save_pur_proposals(st.session_state.pur_proposals)
                    st.toast(f"🎉 เปิดเอกสารประมาณการเลขที่ {new_pur_id} เข้าสู่คลังเสนอราคาขาออกสำเร็จ!", icon="✅")
                    st.rerun()
                else:
                    st.error("❌ กรุณากรอกรหัสเอกสาร ชื่อโครงการ ชื่อบริษัทผู้ว่าจ้าง และผู้ร้องขอให้ครบถ้วนก่อนส่ง")