import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time, timedelta
import json
import os
import io
import concurrent.futures

# --- CẤU HÌNH ---
CREDS_FILE = 'credentials.json'
SHEET_ID = '1CZp2eL36miIDZNJPgnhSXkdNoea8nCNGbBkM1jB8d-E'
CONFIG_FILE = 'app_config.json'
DEFAULT_STATUS = ['Created', 'Pending Pick', 'Picking', 'Picked', 'Checking', 'Checked', 'Packing', 'Packed']

st.set_page_config(page_title="Dispatch Pro Dashboard", layout="wide")

st.markdown("""
    <style>
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    section[data-testid="stFileUploadDropzone"] div div span {display:none;}
    </style>
    """, unsafe_allow_html=True)


# ==================== HELPERS ====================

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for k in ["AHM_DAILY", "SDD_DAILY", "SPX_CK_DAILY", "D2H_DAILY"]:
                if k not in data: data[k] = []
            return data
    return {"AHM_DAILY": [], "SDD_DAILY": [], "SPX_CK_DAILY": [], "D2H_DAILY": []}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    st.sidebar.success("✅ Saved!")


# ---- Đọc file: có CACHE để Streamlit không đọc lại file mỗi lần rerun (đây là nguyên
#      nhân chính khiến tool chạy chậm trước đây - mọi lần đổi 1 ô chọn, Streamlit chạy
#      lại toàn bộ script và đọc lại Excel từ đầu) ----
@st.cache_data(show_spinner=False)
def _read_one_file_bytes(file_bytes, file_name):
    try:
        bio = io.BytesIO(file_bytes)
        if file_name.lower().endswith('.csv'):
            return pd.read_csv(bio, encoding='utf-8-sig')
        # Thử engine 'calamine' (Rust, đọc xlsx nhanh hơn nhiều lần so với openpyxl).
        # Nếu chưa cài python-calamine thì tự rơi về engine mặc định, không lỗi.
        try:
            return pd.read_excel(bio, engine="calamine")
        except Exception:
            bio.seek(0)
            return pd.read_excel(bio)
    except Exception as e:
        st.error(f"Lỗi đọc file {file_name}: {e}")
        return None

def smart_read_file(uploaded_file):
    if uploaded_file is None: return None
    return _read_one_file_bytes(uploaded_file.getvalue(), uploaded_file.name)

def read_and_merge_files(uploaded_files):
    """Đọc NHIỀU file song song rồi gộp thành 1 DataFrame lớn duy nhất,
    để lấy tổng số đơn trong tất cả các file nhanh nhất có thể."""
    if not uploaded_files: return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(uploaded_files))) as ex:
        dfs = list(ex.map(smart_read_file, uploaded_files))
    dfs = [d for d in dfs if d is not None and not d.empty]
    if not dfs: return None
    return pd.concat(dfs, ignore_index=True, sort=False)

def prep_create_time(df):
    """Parse + dọn cột Create Time MỘT LẦN duy nhất, để không phải parse lại nhiều lần
    mỗi khi chạy nhiều tool / nhiều COT khác nhau trên cùng 1 file."""
    if df is None: return None
    df = df.copy()
    df['Create Time'] = pd.to_datetime(df['Create Time'], errors='coerce')
    df = df.dropna(subset=['Create Time'])
    return df

def get_time_range_v3(start_str, end_str, ref_date):
    st_obj = datetime.strptime(start_str, "%H:%M:%S").time()
    en_obj = datetime.strptime(end_str, "%H:%M:%S").time()
    start_dt, end_dt = datetime.combine(ref_date, st_obj), datetime.combine(ref_date, en_obj)
    if st_obj >= en_obj: start_dt -= timedelta(days=1)
    return start_dt, end_dt

def process_logic(df, tool_type, cots=None, date_start=None, date_end=None, d2h_mapping_list=None, extra_status=None):
    """
    df: DataFrame đã qua prep_create_time() (Create Time đã là datetime, đã dropna NaT).
    date_start, date_end: khoảng ngày người dùng chọn -> sẽ LẶP QUA TỪNG NGÀY trong
    khoảng này để tính khung giờ COT cho từng ngày, không bị sót đơn của các ngày khác
    (bản cũ chỉ lấy ngày Create Time lớn nhất làm mốc nên các ngày khác bị tính sai/sót).
    """
    if df is None or not cots: return None
    df_proc = df
    current_master_status = DEFAULT_STATUS + (extra_status if extra_status else [])

    if "D2H" in tool_type:
        if d2h_mapping_list:
            df_proc = df_proc[df_proc['LM Tracking No'].astype(str).isin(d2h_mapping_list)]
        else:
            return None
    elif "Ahamove" in tool_type:
        df_proc = df_proc[df_proc['New 3PL'].isin(["Ahamove - Trong Ngày", "Ahamove SBS - Trong Ngày"])]
    elif "SPX_CK" in tool_type:
        df_proc = df_proc[df_proc['New 3PL'].isin(["SPX - Hàng Cồng Kềnh"])]
    elif "SDD" in tool_type:
        df_proc = df_proc[df_proc['New 3PL'].isin(["SPX Express SBS - Trong Ngày"])]
    else:
        return None

    if df_proc.empty: return None

    if date_start and date_end:
        df_proc = df_proc[(df_proc['Create Time'] >= datetime.combine(date_start, time.min)) &
                           (df_proc['Create Time'] <= datetime.combine(date_end, time.max))]
        if df_proc.empty: return None
        n_days = (date_end - date_start).days + 1
        all_dates = [date_start + timedelta(days=i) for i in range(n_days)]
    else:
        all_dates = sorted(set(df_proc['Create Time'].dt.date))

    header = []
    for cot in cots: header.extend(["Status", cot['name']])
    final_table = [header]

    # Tối ưu: với mỗi COT, gộp mask của TẤT CẢ các ngày rồi groupby 1 LẦN theo Status,
    # thay vì lọc lại toàn bộ dataframe cho từng status x từng COT như bản cũ (chậm hơn nhiều).
    qty_map = {}
    for cot in cots:
        mask = pd.Series(False, index=df_proc.index)
        for d in all_dates:
            st_t, en_t = get_time_range_v3(cot['start'], cot['end'], d)
            mask = mask | ((df_proc['Create Time'] >= st_t) & (df_proc['Create Time'] <= en_t))
        sub = df_proc[mask]
        qty_map[cot['name']] = {} if sub.empty else sub.groupby('Status')['LM Tracking No'].nunique().to_dict()

    for s in current_master_status:
        row = []
        for cot in cots:
            row.extend([s, int(qty_map[cot['name']].get(s, 0))])
        final_table.append(row)

    # TOTAL = tổng đúng các dòng status đang hiển thị ở trên (không cộng thêm các status khác
    # như Cancelled/Delivered... mà bản cũ vô tình tính luôn vào tổng).
    total_row = []
    for cot in cots:
        total_qty = sum(qty_map[cot['name']].get(s, 0) for s in current_master_status)
        total_row.extend(["TOTAL", int(total_qty)])
    final_table.append(total_row)
    return final_table

def process_d2h_report(df_to, df_total):
    if df_to is None or df_total is None: return None
    df_to = df_to.copy(); df_total = df_total.copy()
    df_to['SPX Tracking Number'] = df_to['SPX Tracking Number'].astype(str).str.strip()
    df_total['Order ID'] = df_total['Order ID'].astype(str).str.strip()
    all_hubs = df_total[['Destination Station']].drop_duplicates().rename(columns={'Destination Station': 'Hub'}).sort_values('Hub')
    plan_qty = df_total.groupby('Destination Station')['Order ID'].nunique().reset_index().rename(columns={'Order ID':'Plan', 'Destination Station':'Hub'})
    to_list = df_to['SPX Tracking Number'].unique()
    act_counts = df_to.groupby('Receiver Name')['SPX Tracking Number'].nunique().reset_index().rename(columns={'SPX Tracking Number':'Qty', 'Receiver Name':'Hub'})
    df_wrong = df_total[~df_total['Order ID'].isin(to_list)]
    wrong_counts = df_wrong.groupby('Destination Station')['Order ID'].nunique().reset_index().rename(columns={'Order ID':'Qty', 'Destination Station':'Hub'})

    def build_sub_table(counts_df, title):
        merge_df = pd.merge(pd.merge(all_hubs, counts_df, on='Hub', how='left'), plan_qty, on='Hub', how='left').fillna(0)
        merge_df['%'] = (merge_df['Qty']/merge_df['Plan']*100).fillna(0).round(2).astype(str) + '%'
        data = [[title, "", ""]] + [["Hub", "Qty", "Percentage"]] + merge_df[['Hub', 'Qty', '%']].values.tolist()
        tq, tp = merge_df['Qty'].sum(), merge_df['Plan'].sum()
        data.append(["TOTAL", int(tq), f"{(tq/tp*100):.2f}%" if tp>0 else "0%"])
        return data

    res = build_sub_table(act_counts, "Overview Direct to Hub (Đúng luồng)")
    res.extend([["", "", ""]] + build_sub_table(wrong_counts, "Overview đơn sai luồng"))
    return res


# ==================== SIDEBAR ====================
config = load_config()

with st.sidebar:
    st.header("⚙️ Setting COT")
    for k, lbl in {"AHM_DAILY":"AHAMOVE", "SDD_DAILY":"SPX_SDD", "SPX_CK_DAILY":"SPX_CK", "D2H_DAILY":"D2H Hub"}.items():
        st.subheader(f"📍 {lbl}")
        for i, cot in enumerate(config[k]):
            with st.expander(cot['name']):
                cot['name'] = st.text_input("Tên", value=cot['name'], key=f"n_{k}_{i}")
                s = st.time_input("Start", value=datetime.strptime(cot['start'], "%H:%M:%S").time(), key=f"s_{k}_{i}")
                e = st.time_input("End", value=datetime.strptime(cot['end'], "%H:%M:%S").time(), key=f"e_{k}_{i}")
                cot['start'], cot['end'] = s.strftime("%H:%M:%S"), e.strftime("%H:%M:%S")
                if st.button("🗑️", key=f"del_{k}_{i}"): config[k].pop(i); save_config(config); st.rerun()
        if st.button(f"➕ {lbl}", key=f"add_{k}"): config[k].append({"name":"New","start":"00:00:00","end":"23:59:59"}); save_config(config); st.rerun()

    st.markdown("---")
    if st.button("💾 Save Config"):
        save_config(config)


# ==================== MAIN: DAILY REPORT ====================
st.title("🚚 Dispatch Pro Dashboard")
st.subheader("📊 Daily Report")

c1, c2, c3 = st.columns(3)
with c1:
    f_out = st.file_uploader("📂 Outbound Files (chọn nhiều file sẽ tự gộp)", type=['xlsx', 'csv'],
                              accept_multiple_files=True, key="out_files")
with c2:
    f_to_files = st.file_uploader("✅ Total xuất (File TO) — chọn nhiều file được", type=['xlsx', 'csv'],
                                   accept_multiple_files=True, key="to_files")
with c3:
    f_total_files = st.file_uploader("🎯 Total D2H (File Plan) — chọn nhiều file được", type=['xlsx', 'csv'],
                                      accept_multiple_files=True, key="total_files")

st.divider()

# --- Khoảng ngày lọc cho Daily Report ---
# QUAN TRỌNG: lịch chọn ngày dùng ngày hiện tại làm mốc, KHÔNG đọc file trước để lấy
# min/max như bản cũ -> tránh bị "treo" / không tương tác được khi file Excel rất lớn.
# Việc đọc file thật sẽ chỉ diễn ra khi bấm nút "CHẠY TẤT CẢ" ở dưới, và khi đó tool sẽ
# tự lấy GIAO giữa khoảng lịch đã chọn và khoảng ngày thực tế có trong file.
st.subheader("📅 Date Range")
today = datetime.now().date()
dr = st.date_input(
    "Date Range", value=(today, today), key="report_date_range", label_visibility="collapsed"
)
if isinstance(dr, (list, tuple)) and len(dr) == 2:
    date_start, date_end = dr
elif dr:
    date_start = date_end = dr
else:
    date_start, date_end = None, None

st.divider()
extra_st = []
chk1, chk2 = st.columns(2)
with chk1:
    if st.checkbox("🚚 Bao gồm Shipping"): extra_st.append("Shipping")
with chk2:
    if st.checkbox("📦 Bao gồm Outbound"): extra_st.append("Outbound")

st.divider()
t_col, o_col = st.columns(2)
with t_col:
    tools = st.multiselect("🛠 List Tool", ["Ahamove Daily", "Ahamove Event", "SDD Daily", "SDD Event", "SPX_CK Daily", "SPX_CK Event", "D2H Daily", "Report D2H Đối Soát"])
with o_col:
    opts = [f"AHM - {c['name']}" for c in config['AHM_DAILY']] + [f"SDD - {c['name']}" for c in config['SDD_DAILY']] + \
           [f"CK - {c['name']}" for c in config['SPX_CK_DAILY']] + [f"D2H - {c['name']}" for c in config['D2H_DAILY']]
    selected_ov = st.multiselect("📊 Chọn COT vào Overview", opts)

if st.button("🚀 CHẠY TẤT CẢ", key="run_report"):
    try:
        with st.spinner("📦 Đang đọc & gộp file..."):
            df_out_raw = read_and_merge_files(f_out)
            df_out = prep_create_time(df_out_raw)
            df_to_val = read_and_merge_files(f_to_files)
            df_tot_val = read_and_merge_files(f_total_files)
        mapping_ids = df_tot_val['Order ID'].astype(str).unique().tolist() if df_tot_val is not None else None

        if df_out_raw is not None:
            st.caption(f"📦 Đã gộp **{len(f_out)} file** → tổng **{len(df_out_raw):,} dòng**, "
                       f"**{df_out_raw['LM Tracking No'].nunique():,} tracking** duy nhất.")

        # --- Lấy GIAO giữa khoảng lịch đã chọn và khoảng ngày thực tế có trong file ---
        # - File hẹp hơn lịch -> lọc theo file.
        # - File rộng hơn lịch -> lọc theo lịch.
        eff_start, eff_end = date_start, date_end
        date_range_empty = False
        if df_out is not None and not df_out.empty and date_start and date_end:
            file_min, file_max = df_out['Create Time'].min().date(), df_out['Create Time'].max().date()
            eff_start, eff_end = max(date_start, file_min), min(date_end, file_max)
            if eff_start > eff_end:
                date_range_empty = True
                st.warning(f"⚠️ Khoảng ngày đã chọn (**{date_start} → {date_end}**) không trùng với dữ liệu "
                           f"thực tế trong file Outbound (**{file_min} → {file_max}**). Không có dữ liệu để lọc cho các tool dùng file Outbound.")
            else:
                st.info(f"📅 Đang lọc theo khoảng ngày: **{eff_start} → {eff_end}** "
                        f"(giao giữa lịch đã chọn **{date_start} → {date_end}** và dữ liệu thực tế trong file **{file_min} → {file_max}**)")

        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        ss = gspread.authorize(creds).open_by_key(SHEET_ID)

        for t in tools:
            if t == "Report D2H Đối Soát":
                data = process_d2h_report(df_to_val, df_tot_val)
                if data:
                    ws = ss.worksheet("Report D2H") if "Report D2H" in [w.title for w in ss.worksheets()] else ss.add_worksheet("Report D2H", 500, 20)
                    ws.clear(); ws.update(values=data, range_name='A1'); st.write("✅ Report D2H: Done")
            else:
                if df_out is None or date_range_empty: continue
                tool_key = "Ahamove" if "Ahamove" in t else "SPX_CK" if "SPX_CK" in t else "D2H" if "D2H" in t else "SDD"
                conf = config['AHM_DAILY'] if "Ahamove" in t else config['SPX_CK_DAILY'] if "SPX_CK" in t else config['D2H_DAILY'] if "D2H" in t else config['SDD_DAILY']

                data = process_logic(df_out, tool_key, cots=conf, date_start=eff_start, date_end=eff_end,
                                      d2h_mapping_list=mapping_ids, extra_status=extra_st)
                if data:
                    s_name = "Direct to Hub" if "D2H" in t else t
                    ws = ss.worksheet(s_name) if s_name in [w.title for w in ss.worksheets()] else ss.add_worksheet(s_name, 100, 20)
                    ws.clear(); ws.update(values=data, range_name='A1'); st.write(f"✅ {t}: Done")

        if selected_ov and df_out is not None and not date_range_empty:
            ov_table = []
            for item in selected_ov:
                pre, c_name = item.split(" - ", 1)
                k = 'AHM_DAILY' if pre == "AHM" else 'SPX_CK_DAILY' if pre == "CK" else 'D2H_DAILY' if pre == "D2H" else 'SDD_DAILY'
                t_type = "Ahamove" if pre == "AHM" else "SPX_CK" if pre == "CK" else "D2H" if pre == "D2H" else "SDD"
                c_cfg = next((c for c in config[k] if c['name'] == c_name), None)
                if c_cfg:
                    res = process_logic(df_out, t_type, cots=[c_cfg], date_start=eff_start, date_end=eff_end,
                                         d2h_mapping_list=mapping_ids, extra_status=extra_st)
                    if res:
                        if not ov_table:
                            ov_table = [[r[0], r[1]] for r in res]
                        else:
                            for idx, row in enumerate(res): ov_table[idx].append(row[1])
            if ov_table:
                ws_ov = ss.worksheet("Overview AHM - SDD") if "Overview AHM - SDD" in [w.title for w in ss.worksheets()] else ss.add_worksheet("Overview AHM - SDD", 100, 50)
                ws_ov.clear(); ws_ov.update(values=ov_table, range_name='A1'); st.write("✅ Overview: Done")
        st.balloons()
    except Exception as e:
        st.error(f"Error: {e}")
