import streamlit as st
import pandas as pd
import re
import traceback
import io

st.set_page_config(page_title="仕訳フォーマット自動変換", layout="wide")
st.title("📄 楽楽請求 仕訳フォーマット自動変換ツール")
st.write("会計ソフトから出力した過去仕訳データ(CSV)をアップロードするだけで、楽楽請求の設定フォーマットに変換します！")

uploaded_file = st.file_uploader("1. ここにCSVファイルをドラッグ＆ドロップしてください", type=['csv'])

if uploaded_file is not None:
    st.write(f"2. 「{uploaded_file.name}」 を読み込んでいます...")
    
    df = None
    encodings = ['cp932', 'utf-8', 'utf-8-sig', 'shift_jis']
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=enc)
            st.success(f"文字コード {enc} で読み込み成功！")
            break
        except Exception:
            continue
            
    if df is None:
        st.error("【エラー】CSVファイルの読み込みに失敗しました。")
        st.stop()

    def find_col(keywords):
        for k in keywords:
            for col in df.columns:
                if k == str(col): return col
            for col in df.columns:
                if k in str(col): return col
        return None

    def clean_code(val):
        if pd.isna(val): return ""
        v = str(val).strip()
        if v.endswith('.0'): v = v[:-2]
        if v == 'nan': return ""
        return v

    col_denpyo = find_col(['伝票', 'No', '番号'])
    col_kari_money = find_col(['本体金額', '借方金額', '借金額', '金額(借)', '金額'])
    col_tekiyo = find_col(['摘要', '詳細', 'メモ'])
    
    col_kari_kamoku_name = find_col(['借方勘定科目名', '借方科目', '借科目', '勘定科目(借)'])
    col_torihikisaki_name = find_col(['取引先名', '貸方補助科目名', '貸方補助', '補助科目名'])

    col_torihikisaki_code = find_col(['取引先コード'])
    col_kari_kamoku_code = find_col(['借方勘定科目コード', '借方科目コード'])
    col_kari_hojo_code = find_col(['借方補助科目コード', '借方補助コード'])
    col_kari_bumon_code = find_col(['借方部門コード'])
    col_kari_project_code = find_col(['借方プロジェクトコード', 'プロジェクトコード'])
    col_kari_tax = find_col(['借方消費税区分コード', '借方消費税', '税区分', '税', '消費税'])
    
    col_kashi_kamoku_code = find_col(['貸方勘定科目コード', '貸方科目コード'])
    col_kashi_hojo_code = find_col(['貸方補助科目コード', '貸方補助コード'])
    col_kashi_bumon_code = find_col(['貸方部門コード'])
    col_kashi_project_code = find_col(['貸方プロジェクトコード'])
    col_kashi_tax = find_col(['貸方消費税区分コード', '貸方税区分', '貸方消費税'])
    col_kashi_money = find_col(['本体金額.1', '貸方金額', '貸金額', '金額(貸)']) 

    if not col_denpyo or not col_kari_kamoku_name:
        st.error("【エラー】伝票番号、または借方科目の列が見つかりません。")
        st.stop()

    def replace_month(text):
        if pd.isna(text): return ""
        return re.sub(r'[0-9０-９]{1,2}月', '##__請求月__##', str(text))

    try:
        st.write("3. データを変換・整形しています...")
        grouped = df.groupby(col_denpyo)
        patterns = []
        
        for denpyo, group in grouped:
            first_row = group.iloc[0]
            
            t_code = clean_code(first_row[col_torihikisaki_code]) if col_torihikisaki_code else ""
            t_name = str(first_row[col_torihikisaki_name]).replace('nan', '不明').strip() if col_torihikisaki_name else "不明"
            project_val = clean_code(first_row[col_kari_project_code]) if col_kari_project_code else ""

            kari_kamoku_list = group[col_kari_kamoku_name].dropna().unique().tolist()
            if not kari_kamoku_list: kari_kamoku_list = ["科目不明"]
                
            if len(kari_kamoku_list) == 1:
                pattern_name = f"{t_name}_{kari_kamoku_list[0]}"
            elif len(kari_kamoku_list) == 2:
                pattern_name = f"{t_name}_{kari_kamoku_list[0]}/{kari_kamoku_list[1]}"
            else:
                pattern_name = f"{t_name}_{kari_kamoku_list[0]}ほか"

            lines = []
            for index, row in group.iterrows():
                lines.append({
                    'kari_kamoku': clean_code(row[col_kari_kamoku_code]) if col_kari_kamoku_code else "",
                    'kari_hojo': clean_code(row[col_kari_hojo_code]) if col_kari_hojo_code else "",
                    'kari_bumon': clean_code(row[col_kari_bumon_code]) if col_kari_bumon_code else "",
                    'kari_project': clean_code(row[col_kari_project_code]) if col_kari_project_code else "",
                    'kari_tax': clean_code(row[col_kari_tax]) if col_kari_tax else "",
                    'money_val': clean_code(row[col_kari_money]) if col_kari_money else "",
                    'kashi_kamoku': clean_code(row[col_kashi_kamoku_code]) if col_kashi_kamoku_code else "",
                    'kashi_hojo': clean_code(row[col_kashi_hojo_code]) if col_kashi_hojo_code else "",
                    'kashi_bumon': clean_code(row[col_kashi_bumon_code]) if col_kashi_bumon_code else "",
                    'kashi_project': clean_code(row[col_kashi_project_code]) if col_kashi_project_code else "",
                    'kashi_tax': clean_code(row[col_kashi_tax]) if col_kashi_tax else "",
                    'kashi_money_val': clean_code(row[col_kashi_money]) if col_kashi_money else "",
                    'tekiyo': replace_month(row[col_tekiyo]) if col_tekiyo else ""
                })
                
            patterns.append({'name': pattern_name, 't_code': t_code, 'project': project_val, 'lines': lines})

        unique_patterns = []
        seen = []
        for p in patterns:
            sig = p['name'] + "".join([str(l['kari_kamoku'])+str(l['kashi_kamoku']) for l in p['lines']])
            if sig not in seen:
                seen.append(sig)
                unique_patterns.append(p)

        t_code_totals = {}
        for p in unique_patterns:
            t = p['t_code']
            if t: t_code_totals[t] = t_code_totals.get(t, 0) + 1
            
        t_code_current = {}
        output_rows = []
        
        max_lines = max((len(p['lines']) for p in unique_patterns), default=1)
        
        for p in unique_patterns:
            t = p['t_code']
            if not t:
                t_code_current['EMPTY'] = t_code_current.get('EMPTY', 0) + 1
                pattern_code = f"CODE_{t_code_current['EMPTY']}"
            else:
                t_code_current[t] = t_code_current.get(t, 0) + 1
                if t_code_totals[t] > 1:
                    pattern_code = f"{t}_{chr(64 + t_code_current[t])}"
                else:
                    pattern_code = t
            
            row_1 = {'仕訳パターンコード': pattern_code, '仕訳パターン名': p['name'], '取引先': p['t_code'], 'プロジェクト': p['project'], '部門': '', '仕訳日': ''}
            row_2 = {'仕訳パターンコード': '仕訳の作成方法', '仕訳パターン名': '', '取引先': '', 'プロジェクト': '請求金額(源泉徴収税額控除前)から作成する', '部門': '', '仕訳日': ''}
            row_3 = {'仕訳パターンコード': '金額の設定方法', '仕訳パターン名': '', '取引先': '', 'プロジェクト': '金額を直接入力する', '部門': '', '仕訳日': ''}
            
            for j in range(max_lines):
                suffix = f"_{j+1}"
                
                if j < len(p['lines']):
                    line = p['lines'][j]
                    row_1[f'借方_勘定科目{suffix}'] = line['kari_kamoku']
                    row_1[f'借方_補助科目{suffix}'] = line['kari_hojo']
                    row_1[f'借方_税区分{suffix}'] = line['kari_tax']
                    
                    # ★修正箇所：1行目に「固定で金額を入力」、2行目に「実際の金額」をセット！
                    if len(p['lines']) == 1:
                        row_1[f'借方_金額{suffix}'] = "差額を自動入力"
                        row_2[f'借方_金額{suffix}'] = ""
                    else:
                        row_1[f'借方_金額{suffix}'] = "固定で金額を入力"
                        row_2[f'借方_金額{suffix}'] = line['money_val']
                    row_3[f'借方_金額{suffix}'] = ""
                        
                    row_1[f'借方_部門{suffix}'] = line['kari_bumon']
                    row_1[f'借方_プロジェクト{suffix}'] = line['kari_project']
                    
                    row_1[f'貸方_勘定科目{suffix}'] = line['kashi_kamoku']
                    row_1[f'貸方_補助科目{suffix}'] = line['kashi_hojo']
                    row_1[f'貸方_税区分{suffix}'] = line['kashi_tax']
                    row_1[f'貸方_金額{suffix}'] = line['kashi_money_val']
                    row_2[f'貸方_金額{suffix}'] = ""
                    row_3[f'貸方_金額{suffix}'] = ""
                    row_1[f'貸方_部門{suffix}'] = line['kashi_bumon']
                    row_1[f'貸方_プロジェクト{suffix}'] = line['kashi_project']
                    
                    row_1[f'共通_摘要{suffix}'] = line['tekiyo']
                    
                else:
                    row_1[f'借方_勘定科目{suffix}'] = ""
                    row_1[f'借方_補助科目{suffix}'] = ""
                    row_1[f'借方_税区分{suffix}'] = ""
                    row_1[f'借方_金額{suffix}'] = ""
                    row_2[f'借方_金額{suffix}'] = ""
                    row_3[f'借方_金額{suffix}'] = ""
                    row_1[f'借方_部門{suffix}'] = ""
                    row_1[f'借方_プロジェクト{suffix}'] = ""
                    row_1[f'貸方_勘定科目{suffix}'] = ""
                    row_1[f'貸方_補助科目{suffix}'] = ""
                    row_1[f'貸方_税区分{suffix}'] = ""
                    row_1[f'貸方_金額{suffix}'] = ""
                    row_2[f'貸方_金額{suffix}'] = ""
                    row_3[f'貸方_金額{suffix}'] = ""
                    row_1[f'貸方_部門{suffix}'] = ""
                    row_1[f'貸方_プロジェクト{suffix}'] = ""
                    row_1[f'共通_摘要{suffix}'] = ""
                    
                # 他の行の空欄パディング
                for k in [f'借方_勘定科目{suffix}', f'借方_補助科目{suffix}', f'借方_税区分{suffix}', f'借方_部門{suffix}', f'借方_プロジェクト{suffix}', 
                          f'貸方_勘定科目{suffix}', f'貸方_補助科目{suffix}', f'貸方_税区分{suffix}', f'貸方_部門{suffix}', f'貸方_プロジェクト{suffix}', f'共通_摘要{suffix}']:
                    row_2[k] = ""
                    row_3[k] = ""
                    
            output_rows.extend([row_1, row_2, row_3])
            
        final_df = pd.DataFrame(output_rows)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        output.seek(0)
        
        st.success("✅ 変換が完了しました！下のボタンからダウンロードしてください。")
        st.download_button(
            label="📥 フォーマットをダウンロード",
            data=output,
            file_name='rakuraku_format.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        st.error("【エラー】変換処理中に問題が発生しました。")
        st.text(traceback.format_exc())


