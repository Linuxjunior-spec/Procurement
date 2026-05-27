import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
import subprocess
import platform
import plotly.express as px

# ตั้งค่าหน้าจอโปรแกรม
st.set_page_config(page_title="Procurement Workspace", layout="wide")

# ล็อกที่อยู่โฟลเดอร์หลักในเครื่องคอมพิวเตอร์ของคุณให้ตายตัว (Absolute Path)
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

# --- ฟังก์ชันหน้าต่าง Popup สำหรับเลือกพื้นที่จังหวัดประจำแท็บเปิดใหม่ ---
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
        if "ทุกจังหวัดทั่วประเทศ" in chosen_list:
            result_str = "ทุกจังหวัดทั่วประเทศ"
        else:
            final_display = []
            for region, provinces in THAI_REGIONS.items():
                if region == "ทั่วประเทศ": continue
                region_provs_selected = [p for p in provinces if p in chosen_list]
                if len(region_provs_selected) == len(provinces):
                    final_display.append(f"ทั้งหมดใน{region}")
                else:
                    final_display.extend(region_provs_selected)
            result_str = ", ".join(final_display) if final_display else "ไม่ระบุพื้นที่"
        st.session_state.areas_output_add = result_str
        st.rerun()

# --- ฟังก์ชันหน้าต่าง Popup (Modal Dialog) สำหรับค้นหา/เลือกซัพพลายเออร์ ---
@st.dialog("🔍 ค้นหาและเลือกซัพพลายเออร์")
def select_supplier_popup():
    st.write("พิมพ์คีย์เวิร์ดเพื่อค้นหาคู่ค้า (ระบบจะกรองรายชื่อที่มีตัวอักษรนั้น ๆ ลงมาให้เลือกอัตโนมัติ)")
    if not st.session_state.suppliers_master:
        st.warning("ไม่มีรายชื่อซัพพลายเออร์ในระบบ")
    else:
        sup_choices = [s["name"] for s in st.session_state.suppliers_master]
        chosen_sup = st.selectbox("พิมพ์ค้นหาชื่อบริษัท / ผู้ขาย", sup_choices, help="พิมพ์เพื่อคัดกรองรายชื่อ")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ ยืนยันเปิดดูโปรไฟล์", use_container_width=True):
            st.session_state.selected_supplier_name = chosen_sup
            st.rerun()

# --- ฟังก์ชันหน้าต่าง Popup สำหรับเลือกจังหวัดสืบค้นพื้นที่รับงาน ---
@st.dialog("🎯 ค้นหาและเลือกจังหวัดพิกัดไซต์งาน")
def select_search_province_popup():
    st.write("พิมพ์ชื่อจังหวัดที่คุณต้องการสืบค้น ระบบจะกรองรายชื่อเพื่อคลิกเลือกได้ทันทีครับ")
    flat_provinces_search = []
    for reg_title, prov_names in THAI_REGIONS.items():
        if reg_title != "ทั่วประเทศ":
            flat_provinces_search.extend(prov_names)
    flat_provinces_search.sort()
    
    chosen_search_prov = st.selectbox("พิมพ์ค้นหาชื่อจังหวัด", flat_provinces_search, help="พิมพ์ชื่อจังหวัดเพื่อกรองรายชื่อ")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ ยืนยันเลือกจังหวัดนี้", use_container_width=True):
        st.session_state.selected_search_province = chosen_search_prov
        st.rerun()

# --- ฟังก์ชันหน้าต่าง Popup สำหรับแก้ไขข้อมูลบริษัทซัพพลายเออร์ ---
@st.dialog("📝 แก้ไขข้อมูลซัพพลายเออร์")
def edit_supplier_popup(sup_obj, idx_master):
    st.markdown(f"แก้ไขข้อมูลบริษัท: **{sup_obj['name']}**")
    e_tax = st.text_input("เลขประจำตัวผู้เสียภาษี (Tax ID)", value=sup_obj.get("tax_id", ""))
    e_credit = st.text_input("เครดิตเทอม", value=sup_obj.get("credit", ""))
    e_address = st.text_area("ที่อยู่บริษัท", value=sup_obj.get("address", ""))
    e_info = st.text_area("หมายเหตุทั่วไป / ข้อมูลเพิ่มเติม", value=sup_obj.get("general_info", ""))
    
    st.markdown("**🌍 แก้ไขพื้นที่ที่สามารถรับงานได้:**")
    current_areas_val = sup_obj.get("service_areas", "ไม่ระบุพื้นที่")
    chosen_edit_list = []
    
    with st.expander(f"🗺️ คลิกเพื่อติ๊กเลือกรายภาคหรือรายจังหวัด (ปัจจุบัน: {current_areas_val})"):
        for region, provinces in THAI_REGIONS.items():
            reg_click = st.checkbox(f"เลือกทั้งหมดใน {region}", value=f"ทั้งหมดใน{region}" in current_areas_val or current_areas_val == "ทุกจังหวัดทั่วประเทศ", key=f"edit_reg_{region}")
            if region != "ทั่วประเทศ":
                cols = st.columns(4)
                for idx, prov in enumerate(provinces):
                    col = cols[idx % 4]
                    is_default_checked = reg_click or (prov in current_areas_val)
                    prov_chk = col.checkbox(prov, value=is_default_checked, key=f"edit_prov_{prov}")
                    if prov_chk or reg_click:
                        if prov not in chosen_edit_list: chosen_edit_list.append(prov)
            else:
                if reg_click: chosen_edit_list.append("ทุกจังหวัดทั่วประเทศ")
                
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 บันทึกการแก้ไขข้อมูล", use_container_width=True):
        if "ทุกจังหวัดทั่วประเทศ" in chosen_edit_list:
            result_edit_str = "ทุกจังหวัดทั่วประเทศ"
        else:
            final_edit_display = []
            for region, provinces in THAI_REGIONS.items():
                if region == "ทั่วประเทศ": continue
                region_provs_selected = [p for p in provinces if p in chosen_edit_list]
                if len(region_provs_selected) == len(provinces):
                    final_edit_display.append(f"ทั้งหมดใน{region}")
                else:
                    final_edit_display.extend(region_provs_selected)
            result_edit_str = ", ".join(final_edit_display) if final_edit_display else "ไม่ระบุพื้นที่"
            
        st.session_state.suppliers_master[idx_master]["tax_id"] = e_tax.strip()
        st.session_state.suppliers_master[idx_master]["credit"] = e_credit.strip()
        st.session_state.suppliers_master[idx_master]["address"] = e_address.strip()
        st.session_state.suppliers_master[idx_master]["general_info"] = e_info.strip()
        st.session_state.suppliers_master[idx_master]["service_areas"] = result_edit_str
        
        save_suppliers(st.session_state.suppliers_master)
        st.toast("อัปเดตแก้ไขข้อมูลซัพพลายเออร์เรียบร้อยแล้ว!", icon="✅")
        st.rerun()

# --- ฟังก์ชันหน้าต่าง Popup สำหรับแก้ไขรายชื่อผู้ติดต่อประสานงาน ---
@st.dialog("👥 บริหารจัดการรายชื่อผู้ติดต่อ")
def edit_contacts_popup(sup_obj, idx_master):
    st.markdown(f"แก้ไขรายชื่อเจ้าหน้าที่ของบริษัท: **{sup_obj['name']}**")
    st.caption("สามารถพิมพ์แก้ไขข้อมูล กดลบรายชื่อ หรือกดเพิ่มช่องพนักงานใหม่ได้จากที่นี่")
    st.markdown("---")
    
    updated_items = []
    for i, contact in enumerate(st.session_state.edit_contacts_list):
        st.markdown(f"**👤 ผู้ติดต่อคนที่ {i+1}**")
        ec_c1, ec_c2, ec_c3, ec_c4 = st.columns(4)
        c_name = ec_c1.text_input("ชื่อผู้ติดต่อ", value=contact.get("name", ""), key=f"ec_n_{i}")
        c_phone = ec_c2.text_input("เบอร์โทรศัพท์", value=contact.get("phone", ""), key=f"ec_p_{i}")
        c_email = ec_c3.text_input("Email", value=contact.get("email", ""), key=f"ec_e_{i}")
        c_line = c_c4.text_input("Line ID", value=contact.get("line", ""), key=f"ec_l_{i}")
        
        if st.button("🗑️ ลบผู้ติดต่อคนนี้", key=f"btn_del_ec_{i}"):
            st.session_state.edit_contacts_list.pop(i)
            st.rerun()
            
        updated_items.append({"name": c_name, "phone": c_phone, "email": c_email, "line": c_line})
        
    st.session_state.edit_contacts_list = updated_items
    st.markdown("---")
    
    pop_btn1, pop_btn2 = st.columns(2)
    if pop_btn1.button("➕ เพิ่มช่องผู้ติดต่อคนใหม่", use_container_width=True):
        st.session_state.edit_contacts_list.append({"name": "", "phone": "", "email": "", "line": ""})
        st.rerun()
        
    if pop_btn2.button("💾 บันทึกการเปลี่ยนแปลงรายชื่อทั้งหมด", use_container_width=True):
        cleaned_contacts = [c for c in st.session_state.edit_contacts_list if c.get("name", "").strip() != ""]
        st.session_state.suppliers_master[idx_master]["contacts"] = cleaned_contacts
        save_suppliers(st.session_state.suppliers_master)
        
        if "edit_contacts_list" in st.session_state:
            del st.session_state.edit_contacts_list
        st.toast("อัปเดตบัญชีรายชื่อเจ้าหน้าที่คู่ค้าสำเร็จ!", icon="✅")
        st.rerun()

# --- ฟังก์ชันสร้างหน้าต่าง Popup สำหรับลงทะเบียนหน่วยนับใหม่ ---
@st.dialog("➕ ลงทะเบียนหน่วยนับมาตรฐานใหม่")
def add_unit_dialog():
    st.write("กรอกชื่อหน่วยนับที่คุณต้องการเพิ่มเข้าสู่ฐานข้อมูลกลาง เช่น กล่อง, ม้วน, โหล, แผ่น")
    new_unit = st.text_input("ชื่อหน่วยนับ (Unit Name)")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 บันทึกหน่วยนับใหม่", use_container_width=True):
        if new_unit:
            new_unit = new_unit.strip()
            if new_unit not in st.session_state.units_list:
                st.session_state.units_list.append(new_unit)
                save_units(st.session_state.units_list)
                st.success(f"บันทึกหน่วยนับ '{new_unit}' เข้าสู่คลังสำเร็จ!")
                st.rerun()
            else: st.warning("หน่วยนับนี้มีอยู่ในคลังระบบเรียบร้อยแล้วครับ")
        else: st.error("กรุณาระบุชื่อหน่วยนับก่อนกดบันทึก")

# --- ฟังก์ชันสร้างหน้าต่าง Popup สำหรับลงทะเบียนหมวดหมู่งานใหม่ ---
@st.dialog("➕ ลงทะเบียนหมวดหมู่งานมาตรฐานใหม่")
def add_category_dialog():
    st.write("กรอกชื่อหมวดหมู่ที่คุณต้องการเพิ่มเข้าสู่ฐานข้อมูลกลาง เช่น งานดิน, งานสถาปัตย์, ระบบสถานีชาร์จ")
    new_cat = st.text_input("ชื่อหมวดหมู่งาน / กลุ่มพัสดุ")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 บันทึกหมวดหมู่ใหม่", use_container_width=True):
        if new_cat:
            new_cat = new_cat.strip()
            if new_cat not in st.session_state.categories_list:
                st.session_state.categories_list.append(new_cat)
                save_categories(st.session_state.categories_list)
                st.success(f"บันทึกหมวดหมู่ '{new_cat}' เข้าสู่คลังสำเร็จ!")
                st.rerun()
            else: st.warning("หมวดหมู่งานนี้มีอยู่ในคลังระบบเรียบร้อยแล้วครับ")
        else: st.error("กรุณาระบุชื่อหมวดหมู่ก่อนกดบันทึก")

# --- ฟังก์ชันสำหรับสั่งเปิดโฟลเดอร์ในเครื่องคอมพิวเตอร์โดยตรง ---
def open_local_folder(folder_path):
    # ปรับให้ปลอดภัยเมื่อรันบนคลาวด์
    if not os.path.isabs(folder_path):
        folder_path = os.path.join(BASE_DIR, folder_path)
        
    if os.path.exists(folder_path):
        try:
            # ตรวจสอบว่ารันบนเครื่องตัวเอง (Local) หรือบน Cloud
            # ถ้าเป็นบนคลาวด์ทั่วไป มักจะไม่มีระบบเปิดโฟลเดอร์เด้งขึ้นมา
            if platform.system() == "Windows": 
                os.startfile(folder_path)
                st.toast(f"📂 เปิดโฟลเดอร์สำเร็จ", icon="✅")
            else:
                # ถ้ารันบนระบบอื่น (เช่น Linux บนคลาวด์) ให้แจ้งเตือนที่อยู่โฟลเดอร์แทนการสั่งเปิด
                st.info(f"📁 ระบบกำลังทำงานอยู่บนเซิร์ฟเวอร์ เส้นทางโฟลเดอร์คือ: {folder_path}")
        except Exception as e: 
            st.info(f"📁 เส้นทางเก็บข้อมูลวัสดุ: {folder_path}")
    else: 
        st.error("❌ ไม่พบโฟลเดอร์นี้ในระบบ")

# --- ฟังก์ชันจัดการระบบฐานข้อมูล ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_requestors():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return ["คุณสมชาย", "คุณสมหญิง"]
    return ["คุณสมชาย", "คุณสมหญิง"]

def save_requestors(requestors_list):
    with open(USER_FILE, "w", encoding="utf-8") as f: json.dump(requestors_list, f, ensure_ascii=False, indent=4)

def load_suppliers():
    if os.path.exists(SUP_FILE):
        try:
            with open(SUP_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_suppliers(suppliers_list):
    with open(SUP_FILE, "w", encoding="utf-8") as f: json.dump(suppliers_list, f, ensure_ascii=False, indent=4)

def load_standalone_prices():
    if os.path.exists(STANDALONE_FILE):
        try:
            with open(STANDALONE_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_standalone_prices(prices_list):
    with open(STANDALONE_FILE, "w", encoding="utf-8") as f: json.dump(prices_list, f, ensure_ascii=False, indent=4)

def load_item_codes():
    if os.path.exists(ITEM_FILE):
        try:
            with open(ITEM_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_item_codes(items_list):
    with open(ITEM_FILE, "w", encoding="utf-8") as f: json.dump(items_list, f, ensure_ascii=False, indent=4)

def load_units():
    if os.path.exists(UNIT_FILE):
        try:
            with open(UNIT_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return ["M", "ชุด", "ตัว", "ตร.ม.", "กิโลกรัม", "ท่อน", "ม้วน"]
    return ["M", "ชุด", "ตัว", "ตร.ม.", "กิโลกรัม", "ท่อน", "ม้วน"]

def save_units(units_list):
    with open(UNIT_FILE, "w", encoding="utf-8") as f: json.dump(units_list, f, ensure_ascii=False, indent=4)

def load_categories():
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return ["สายไฟ", "ท่อร้อยสาย", "อุปกรณ์ไฟฟ้า", "งานระบบ", "ทั่วไป"]
    return ["สายไฟ", "ท่อร้อยสาย", "อุปกรณ์ไฟฟ้า", "งานระบบ", "ทั่วไป"]

def save_categories(categories_list):
    with open(CATEGORIES_FILE, "w", encoding="utf-8") as f: json.dump(categories_list, f, ensure_ascii=False, indent=4)

# โหลดข้อมูลเข้าสู่ตัวแปรระบบ
if 'rfq_history' not in st.session_state: st.session_state.rfq_history = load_data()
if 'requestors_list' not in st.session_state: st.session_state.requestors_list = load_requestors()
if 'suppliers_master' not in st.session_state: st.session_state.suppliers_master = load_suppliers()
if 'standalone_prices' not in st.session_state: st.session_state.standalone_prices = load_standalone_prices()
if 'item_codes_master' not in st.session_state: st.session_state.item_codes_master = load_item_codes()
if 'units_list' not in st.session_state: st.session_state.units_list = load_units()
if 'categories_list' not in st.session_state: st.session_state.categories_list = load_categories()
if 'temp_contacts' not in st.session_state: st.session_state.temp_contacts = [{"name": "", "phone": "", "email": "", "line": ""}]
if 'selected_supplier_name' not in st.session_state: st.session_state.selected_supplier_name = None
if 'sup_clear_counter' not in st.session_state: st.session_state.sup_clear_counter = 0
if 'areas_output_add' not in st.session_state: st.session_state.areas_output_add = "ยังไม่ได้เลือกพื้นที่"
if 'selected_search_province' not in st.session_state: st.session_state.selected_search_province = None

# =========================================================================
# 🧭 ระบบเมนูควบคุมหลักด้านข้าง (Sidebar Navigation)
# =========================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧭 เมนูควบคุมหลัก</h2>", unsafe_allow_html=True)
    st.markdown("---")
    main_menu = st.radio(
        "เลือกหน้าต่างทำงาน:",
        ["🏠 หน้าหลัก (Dashboard)", "📦 ระบบจัดการ RFQ", "🏢 ข้อมูล Supplier", "📊 BOQ Supplier", "🗂️ บริหาร Item Code"]
    )
    st.markdown("---")
    st.caption("ระบบจัดซื้อส่วนตัว v2.2 • 2026")

# =========================================================================
# 🏠 หน้าหลัก (Dashboard)
# =========================================================================
if main_menu == "🏠 หน้าหลัก (Dashboard)":
    st.title("ワークスペース • หน้าหลักระบบจัดซื้อ")
    
    clock_html = """
    <div style="text-align: center; font-family: 'Courier New', Courier, monospace; padding: 20px; background: #1e1e24; border-radius: 12px; border: 1px solid #333; margin-bottom: 25px;">
        <div id="live-clock" style="font-size: 55px; font-weight: bold; color: #00ffcc; letter-spacing: 3px; text-shadow: 0 0 10px rgba(0,255,204,0.3);">00:00:00</div>
        <div id="live-date" style="font-size: 18px; color: #ffffff; margin-top: 8px; font-family: 'Helvetica Neue', Arial, sans-serif;">วันเดือนปี</div>
    </div>
    <script>
        function updateWidgetClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('th-TH', { hour12: false });
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            const dateStr = now.toLocaleDateString('th-TH', options);
            document.getElementById('live-clock').innerText = timeStr;
            document.getElementById('live-date').innerText = dateStr;
        }
        setInterval(updateWidgetClock, 1000);
        updateWidgetClock();
    </script>
    """
    components.html(clock_html, height=140)
    
    st.subheader("📊 สรุปภาพรวมสถานะงานจัดซื้อ")
    
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
        st.subheader("🍕 กราฟวิเคราะห์สัดส่วนปริมาณงานตามสถานะ (RFQ Status Breakdown)")
        df_rfq = pd.DataFrame(st.session_state.rfq_history)
        status_counts = df_rfq["status"].value_counts().reset_index()
        status_counts.columns = ["สถานะงาน", "จำนวนใบงาน"]
        
        g_col1, g_col2 = st.columns([3, 2])
        with g_col1:
            fig_pie = px.pie(status_counts, values="จำนวนใบงาน", names="สถานะงาน", hole=0)
            fig_pie.update_traces(
                textposition='inside', textinfo='value+percent', insidetextorientation='horizontal',
                hovertemplate="<b>%{label}</b><br>ปริมาณ: %{value} ใบงาน<br>คิดเป็นสัดส่วน: %{percent}<extra></extra>"
            )
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02))
            st.plotly_chart(fig_pie, use_container_width=True)
        with g_col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("#### 📝 ตารางสรุปตัวเลขสถิติ")
            st.dataframe(status_counts, use_container_width=True, hide_index=True)
    else: st.info("💡 ข้อมูลกราฟวิเคราะห์ 2D-Pie จะปรากฏขึ้นที่นี่โดยอัตโนมัติ ทันทีที่คุณเริ่มบันทึกใบงาน RFQ ครับ")

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

    # --- แท็บย่อย 2: อัปเดตราคา (ดักจับ Error กรณีคลังจัดซื้อยังว่างสะอาดเรียบร้อย) ---
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
                        with open(f_path, "rb") as f: r_col5.download_button(label="📁 เปิด/ดาวน์โหลด", data=f.read(), file_name=os.path.basename(f_path), key=f"btn_dl_tab2_{selected_rfq_id}_{idx}")
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
        st.markdown("### 🔍 ค้นหาและบริหารจัดการประวัติราคาวัสดุ-ค่าแรงแยกรายการ (Single Selection)")
        st.caption("💡 พี่สามารถดับเบิ้ลคลิกแก้ไขราคาบนตารางได้โดยตรง หรือเลือกหมายเลขข้อด้านล่างเพื่อกดลบ/แก้ไขข้อมูลทั่วไป")
        
        search_lay1, search_lay2 = st.columns([4, 1])
        search_query = search_lay1.text_input("ค้นหาประวัติราคา", placeholder="พิมพ์ชื่อรายการวัสดุ หมวดหมู่ หรือชื่อร้านค้า เช่น CV 1C-150sq.mm", label_visibility="collapsed")
        
        # --- 1. รวบรวมข้อมูลจากทั้ง 2 แหล่ง (RFQ History และ Standalone Prices) ---
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
            # ทำการกรองข้อมูลตาม Keyword
            if search_query:
                q = search_query.strip().lower()
                filtered_records = [r for r in flat_records if q in r["รายการวัสดุ"].lower() or q in r["หมวดหมู่"].lower() or q in r["ชื่อบริษัท/ผู้ขาย"].lower()]
            else:
                filtered_records = flat_records
                
            st.markdown(f"พบรายการราคาวัสดุทั้งหมด **{len(filtered_records)}** รายการ")
            
            if filtered_records:
                # แปลงเป็น DataFrame และใส่เลขข้อ (No.) นำหน้าตารางชัดๆ
                df_history = pd.DataFrame(filtered_records)
                df_history.insert(0, "ลำดับที่ (No.)", range(1, len(df_history) + 1))
                
                show_cols = ["ลำดับที่ (No.)", "หมวดหมู่", "รายการวัสดุ", "ชื่อบริษัท/ผู้ขาย", "หน่วย", "ราคาวัสดุ / หน่วย (บาท)", "ค่าแรง/หน่วย (บาท)", "ราคารวมต่อหน่วย (บาท)", "วันที่อัปเดตราคา", "อ้างอิงแหล่งข้อมูล"]
                
                # --- 2. ตารางแสดงผลปรับปรุงราคาพร้อมลูกน้ำ (ล็อกคอลัมน์ตัวอักษรไว้ให้พิมพ์แก้มือด้านล่างแทน) ---
                edited_df = st.data_editor(
                    df_history[show_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ลำดับที่ (No.)": st.column_config.NumberColumn(format="%d", disabled=True),
                        "หมวดหมู่": st.column_config.TextColumn(disabled=True),
                        "รายการวัสดุ": st.column_config.TextColumn(disabled=True),
                        "ชื่อบริษัท/ผู้ขาย": st.column_config.TextColumn(disabled=True),
                        "หน่วย": st.column_config.TextColumn(disabled=True),
                        "อ้างอิงแหล่งข้อมูล": st.column_config.TextColumn(disabled=True),
                        "ราคาวัสดุ / หน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", min_value=0.0),
                        "ค่าแรง/หน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", min_value=0.0),
                        "ราคารวมต่อหน่วย (บาท)": st.column_config.NumberColumn(format="%,.2f", disabled=True)
                    }
                )
                
                st.markdown("---")
                
                # --- 3. ส่วนควบคุมชิ้นงานแบบเจาะจงเลือกได้แค่ 1 ข้อ (Single Selection) ---
                st.markdown("##### ⚙️ เครื่องมือจัดการรายการพัสดุแบบเจาะจงชิ้น")
                
                select_options = [f"ข้อที่ {i}: {r['รายการวัสดุ']} [{r['ชื่อบริษัท/ผู้ขาย']}]" for i, r in zip(df_history["ลำดับที่ (No.)"], filtered_records)]
                chosen_target = st.selectbox("เลือกรายการลำดับข้อที่พี่ต้องการสั่งการสำหรับแก้ไขหรือลบ:", select_options)
                
                if chosen_target:
                    # ถอดหา Index ตัวจริงของแถวที่เลือกมาใช้งาน
                    chosen_no = int(chosen_target.split(":")[0].replace("ข้อที่ ", ""))
                    target_row = filtered_records[chosen_no - 1]
                    
                    act_col1, act_col2 = st.columns([1, 1])
                    
                    # ➕ ฟีเจอร์เพิ่มเติม: เพิ่มหน้าต่างขยายปุ่มแก้ไขชื่อข้อความทั่วไป (หมวดหมู่, รายการ, หน่วย)
                    with act_col1:
                        with st.expander("📝 คลิกเพื่อเปิดหน้าต่างแก้ไขข้อมูลข้อความพัสดุ"):
                            edit_cat = st.selectbox("แก้ไขหมวดหมู่", st.session_state.categories_list, index=st.session_state.categories_list.index(target_row["หมวดหมู่"]) if target_row["หมวดหมู่"] in st.session_state.categories_list else 0)
                            edit_name = st.text_input("แก้ไขรายการวัสดุ / รายละเอียด", value=target_row["รายการวัสดุ"])
                            edit_unit = st.selectbox("แก้ไขหน่วยนับ", st.session_state.units_list, index=st.session_state.units_list.index(target_row["หน่วย"]) if target_row["หน่วย"] in st.session_state.units_list else 0)
                            
                            if st.button("💾 ยืนยันบันทึกการแก้ไขข้อความ", use_container_width=True, type="primary"):
                                if target_row["source_type"] == "rfq":
                                    r_idx, s_idx, i_idx = target_row["index_keys"]
                                    item_ptr = st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"][i_idx]
                                    item_ptr["category"] = edit_cat
                                    item_ptr["item_name"] = edit_name
                                    item_ptr["unit"] = edit_unit
                                    item_ptr["date_updated"] = datetime.now().strftime('%d/%m/%Y')
                                elif target_row["source_type"] == "standalone":
                                    sa_idx = target_row["index_keys"]
                                    item_ptr = st.session_state.standalone_prices[sa_idx]
                                    item_ptr["category"] = edit_cat
                                    item_ptr["item_name"] = edit_name
                                    item_ptr["unit"] = edit_unit
                                    item_ptr["date_updated"] = datetime.now().strftime('%d/%m/%Y')
                                    
                                save_data(st.session_state.rfq_history)
                                save_standalone_prices(st.session_state.standalone_prices)
                                st.toast("แก้ไขข้อมูลข้อความพัสดุสำเร็จแล้ว!", icon="✅")
                                st.rerun()
                                
                    # 🗑️ ฟีเจอร์ลบรายการที่เลือกทีละ 1 ข้ออย่างปลอดภัย
                    with act_col2:
                        st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
                        if st.button(f"🗑️ สั่งลบข้อมูล {chosen_target.split(':')[0]} นี้ออกจากคลังถาวร", type="primary", use_container_width=True):
                            if target_row["source_type"] == "rfq":
                                r_idx, s_idx, i_idx = target_row["index_keys"]
                                st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"].pop(i_idx)
                            elif target_row["source_type"] == "standalone":
                                sa_idx = target_row["index_keys"]
                                st.session_state.standalone_prices.pop(sa_idx)
                                
                            save_data(st.session_state.rfq_history)
                            save_standalone_prices(st.session_state.standalone_prices)
                            st.toast("ลบข้อมูลประวัติราคาที่เลือกออกเรียบร้อยแล้ว!", icon="🗑️")
                            st.rerun()

                # --- 4. ปุ่มกลางสำหรับตรวจสอบตัวเลขราคาที่ดับเบิ้ลคลิกแก้ไขในตาราง ---
                mat_changed = (edited_df["ราคาวัสดุ / หน่วย (บาท)"] != df_history["ราคาวัสดุ / หน่วย (บาท)"])
                lab_changed = (edited_df["ค่าแรง/หน่วย (บาท)"] != df_history["ค่าแรง/หน่วย (บาท)"])
                
                if mat_changed.any() or lab_changed.any():
                    st.markdown("---")
                    if st.button("💾 ตรวจพบการแก้ไขตัวเลขราคาบนตาราง • กดคลิกตรงนี้เพื่อบันทึกราคาทั้งหมด", use_container_width=True):
                        for idx in range(len(edited_df)):
                            new_mat = float(edited_df.iloc[idx]["ราคาวัสดุ / หน่วย (บาท)"])
                            new_lab = float(edited_df.iloc[idx]["ค่าแรง/หน่วย (บาท)"])
                            orig_row = filtered_records[idx]
                            
                            if orig_row["source_type"] == "rfq":
                                r_idx, s_idx, i_idx = orig_row["index_keys"]
                                target_item = st.session_state.rfq_history[r_idx]["suppliers"][s_idx]["items"][i_idx]
                                target_item["material_rate"] = new_mat
                                target_item["labor_rate"] = new_lab
                                target_item["total_rate"] = new_mat + new_lab
                                target_item["date_updated"] = datetime.now().strftime('%d/%m/%Y')
                            elif orig_row["source_type"] == "standalone":
                                sa_idx = orig_row["index_keys"]
                                target_item = st.session_state.standalone_prices[sa_idx]
                                target_item["material_rate"] = new_mat
                                target_item["labor_rate"] = new_lab
                                target_item["total_rate"] = new_mat + new_lab
                                target_item["date_updated"] = datetime.now().strftime('%d/%m/%Y')
                                
                        save_data(st.session_state.rfq_history)
                        save_standalone_prices(st.session_state.standalone_prices)
                        st.toast("อัปเดตแก้ไขตัวเลขราคาบนตารางสำเร็จ!", icon="✅")
                        st.rerun()

# =========================================================================
# 🗂️ บริหาร Item Code (เวอร์ชันมาตรฐานจัดซื้อ: เก็บเฉพาะข้อมูลสารบบวัสดุกลาง ไม่เก็บราคา)
# =========================================================================
elif main_menu == "🗂️ บริหาร Item Code":
    st.title("🗂️ ศูนย์บริหารคลังฐานข้อมูลสินค้าและรหัสสินค้ากลาง (Item Code Master)")
    item_tab1, item_tab2 = st.tabs(["➕ เพิ่ม Item Code มาตรฐานใหม่", "📋 ทำเนียบสืบค้นตรวจสอบรหัสทั้งหมด"])
    
    with item_tab1:
        st.markdown("### ➕ เพิ่มพัสดุและรหัสสินค้าใหม่เข้าสู่ระบบ")
        
        # 1. ส่วนเลือกหมวดหมู่ (อยู่นอก Form เพื่อใช้สลับแล้วให้ระบบ Rerun เจนรหัสใหม่ทันที)
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
                
        # --- ตรรกะคำนวณรหัสสินค้าอัตโนมัติ (Prefix Character Matching) ---
        if i_cat:
            prefix_char = i_cat[0]  # ดึงตัวอักษรตัวแรกสุด เช่น "สายไฟ" -> "ส"
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
            auto_itm_code = f"{prefix}{next_itm_seq:04d}"  # เช่น ส-0001
        else:
            auto_itm_code = "ITM-0001"
            
        st.markdown("---")
        
        # 2. ส่วนกรอกข้อมูลเนื้อหาพัสดุ (ถอดส่วนช่องกรอกราคาวัสดุ/ค่าแรงออกเรียบร้อยแล้ว)
        st.markdown("##### 📝 รายละเอียดรหัสสินค้าใหม่")
        
        # ช่องแสดงรหัสสินค้า (ล็อกค่าอัปเดตอัตโนมัติ แต่ยังพิมพ์แก้ไขมือได้)
        i_code = st.text_input("รหัสสินค้า (Item Code)", value=auto_itm_code)
        
        # ช่องกรอกชื่อวัสดุ
        i_name = st.text_input("2. รายการวัสดุ / รายละเอียดพัสดุ (Item Description)", placeholder="เช่น CV 1C-150sq.mm (1Core) 0.6/1KV")
        
        # แถวเลือกหน่วยนับ และ ปุ่มเพิ่มหน่วยนับกลาง
        u_lay1, u_lay2 = st.columns([5, 1])
        with u_lay1: 
            i_unit = st.selectbox("3. หน่วยนับพัสดุ (Unit)", st.session_state.units_list)
        with u_lay2:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ ลงทะเบียนหน่วย", use_container_width=True, help="เปิดหน้าต่างลงทะเบียนเพิ่มหน่วยนับชิ้นใหม่"): 
                add_unit_dialog()
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ปุ่มบันทึกข้อมูลหลัก
        if st.button("💾 บันทึกรหัสพัสดุนี้เข้าคลังมาสเตอร์", use_container_width=True, type="primary"):
            if i_code and i_name:
                i_code = i_code.strip()
                i_name = i_name.strip()
                
                # ตรวจสอบเพื่อป้องกันการบันทึกรหัสซ้ำ
                if any(x["code"] == i_code for x in st.session_state.item_codes_master): 
                    st.error(f"❌ ไม่สามารถบันทึกได้ เนื่องจากรหัสสินค้า '{i_code}' มีอยู่ในระบบแล้ว")
                else:
                    # บันทึกเฉพาะโครงสร้างข้อมูลวัสดุหลักตามมาตรฐานจัดซื้อ
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
            # ปรับตารางทำเนียบรหัสสินค้าให้คลีน แสดงเฉพาะข้อมูลคุณลักษณะพัสดุ ไม่ปนเรื่องราคา
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