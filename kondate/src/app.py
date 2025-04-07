import streamlit as st
import pandas as pd
from menu_updater import update_menu_with_desserts, update_menu_with_reordering, get_nutritionist_response, preview_reordering, reorder_with_llm, generate_weekly_menu, create_order_sheets
import tempfile
import os
from pathlib import Path
import datetime
import io

# プロジェクトのルートディレクトリを取得
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

# ページ設定
st.set_page_config(
    page_title="給食AI自動生成システム",
    page_icon="🍰",
    layout="wide"
)

# アプリタイトル
st.title("給食AI自動生成システム 🍰")

# アプリ概要説明
st.write("""
## 使い方
1. Excelファイル（input_menu.xlsx）をアップロードしてください
2. 「通常出力」ボタン：デザート追加と栄養計算を行います
3. 「献立並び替え」ボタン：選択した戦略に基づいて献立を並び替えます
4. 処理が完了すると、更新されたファイルが自動で開かれます
""")

# タブを作成して機能を分ける
tab1, tab2, tab3 = st.tabs(["既存献立の管理", "一週間献立の自動生成", "発注書作成"])

with tab1:
    # 既存の機能（ファイルアップロード、デザート追加、並び替え）
    uploaded_file = st.file_uploader("メニューファイルを選択してください", type=['xlsx'], key="menu_file")

    # ファイルがアップロードされた場合の処理
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("通常出力", key="normal_output"):
                with st.spinner("デザート追加と栄養計算を実行中..."):
                    try:
                        # 一時ファイルとして保存
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_input:
                            tmp_input.write(uploaded_file.getvalue())
                            input_path = tmp_input.name

                        # 出力用の一時ファイル名を生成
                        output_path = str(Path(input_path).with_name('updated_menu.xlsx'))
                        
                        # メニュー更新処理を実行
                        update_menu_with_desserts(input_path, output_path)

                        # 一時入力ファイルを削除
                        os.unlink(input_path)

                        # 完了メッセージ
                        st.success("処理が完了しました！ファイルが自動で開かれます。")

                    except Exception as e:
                        st.error(f"エラーが発生しました: {str(e)}")
        
        with col2:
            # 並び替え基本戦略のプルダウン
            reorder_options = [
                "栄養バランス優先並び替え", 
                "ランダム並び替え",
                "曜日指定並び替え"
            ]
            reorder_selection = st.selectbox(
                "並び替えタイプを選択してください:",
                reorder_options
            )
            
            # 曜日指定が選択された場合、曜日とジャンルの追加選択肢を表示
            if reorder_selection == "曜日指定並び替え":
                col_weekday, col_genre = st.columns(2)
                
                with col_weekday:
                    weekday_options = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
                    selected_weekday = st.selectbox("曜日を選択:", weekday_options)
                
                with col_genre:
                    genre_options = [
                        "麺類", "中華料理", "魚料理", "肉料理", "和食", "洋食", 
                        "丼物", "揚げ物", "シチュー", "カレー"
                    ]
                    selected_genre = st.selectbox("ジャンルを選択:", genre_options)
            else:
                # UI構成のためにダミー変数を設定
                selected_weekday = None
                selected_genre = None
            
            if st.button("並び替えプレビュー"):
                if not uploaded_file:
                    st.error("ファイルをアップロードしてください。")
                else:
                    try:
                        # 一時ファイルとして保存
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_input:
                            tmp_input.write(uploaded_file.getvalue())
                            input_path = tmp_input.name

                        # プレビュー生成パラメータ
                        params = {
                            "reorder_type": reorder_selection
                        }
                        
                        if reorder_selection == "曜日指定並び替え":
                            params["target_weekday"] = selected_weekday
                            params["target_genre"] = selected_genre
                        
                        # プレビュー生成
                        preview_df, menu_details, reorder_rationale = preview_reordering(input_path, **params)
                        
                        # セッションステートに保存
                        st.session_state.preview_df = preview_df
                        st.session_state.menu_details = menu_details
                        st.session_state.reorder_rationale = reorder_rationale
                        st.session_state.reorder_params = params
                        st.session_state.input_path = input_path
                        
                        # プレビュー表示
                        st.subheader("並び替え後のメニュー表")
                        st.dataframe(preview_df, use_container_width=True)
                        
                        # 並び替え理由の表示
                        st.write("#### AIによる並び替え判断の説明")
                        st.info(reorder_rationale)
                        
                        # メッセージとボタンを横に配置
                        col_message, col_button = st.columns([2, 1])
                        
                        with col_message:
                            st.success("並び替えプレビューを生成しました。確定して保存する場合は右のボタンをクリックしてください。")
                        
                        with col_button:
                            if st.button("確定して保存", key="confirm_reorder"):
                                with st.spinner("ファイルを保存しています..."):
                                    # 出力用の一時ファイル名を生成
                                    output_path = str(Path(input_path).with_name('reordered_menu.xlsx'))
                                    
                                    # 並び替え更新処理を実行
                                    update_menu_with_reordering(
                                        input_path, 
                                        output_path, 
                                        reorder_selection,
                                        selected_weekday,
                                        selected_genre
                                    )
                                    
                                    # 完了メッセージ
                                    st.success("並び替えが完了しました！ファイルが自動で開かれます。")
                        
                        # メニュー詳細表示
                        with st.expander("メニューの詳細を表示"):
                            st.write("#### 日付ごとのメニュー内容")
                            
                            # 日付ごとに折りたたみ可能なセクションで表示
                            for date, meals in menu_details.items():
                                with st.expander(f"{date}"):
                                    for meal_type, dishes in meals.items():
                                        st.write(f"**{meal_type}**")
                                        for dish in dishes:
                                            st.write(f"- {dish}")
                    except Exception as e:
                        st.error(f"プレビュー生成中にエラーが発生しました: {str(e)}")
                        if 'input_path' in vars() and os.path.exists(input_path):
                            os.unlink(input_path)

with tab2:
    st.header("🍽️ 一週間の献立自動生成")
    st.write("AIを活用して、シルバー向け給食の献立を自動生成します。予算は一食200〜300円（デザート込み）で設定されています。")
    
    # 献立設定オプション
    col1, col2 = st.columns(2)
    
    with col1:
        # 対象期間の設定
        start_date = st.date_input(
            "献立開始日",
            datetime.date.today() + datetime.timedelta(days=1),
            format="YYYY/MM/DD"
        )
        
        # 期間選択（週数）
        weeks_options = [1, 2, 3, 4]
        selected_weeks = st.selectbox(
            "生成する週数",
            weeks_options,
            format_func=lambda x: f"{x}週間（{x*7}日分）"
        )
        
        # 食事形式の選択
        meal_pattern = st.selectbox(
            "食事のパターン",
            ["一日3食（朝・昼・夕）", "一日2食（朝・夕）", "一日2食（昼・夕）"]
        )
    
    with col2:
        # 人数の選択
        person_count = st.number_input(
            "何人分の献立を準備しますか？",
            min_value=1,
            max_value=100,
            value=20,
            step=1,
            help="調理する人数を指定してください。食材量が人数分に計算されます。"
        )
        
        # 献立のテーマ/好みの選択
        cuisine_preference = st.selectbox(
            "献立の傾向",
            ["バランス重視", "和食中心", "洋食中心", "中華中心", "和洋折衷", "季節の食材重視", "低塩分", "高タンパク質"]
        )
        
        # 特別な配慮
        special_considerations = st.multiselect(
            "特別な配慮",
            ["噛みやすさ重視", "消化に優しい", "塩分控えめ", "糖質控えめ", "季節感重視"]
        )
    
    # 週間献立生成ボタン
    generate_button_text = f"{selected_weeks}週間の献立を生成"
    if st.button(generate_button_text, type="primary"):
        with st.spinner("献立を考案中です..."):
            try:
                # 生成パラメータの設定
                days = selected_weeks * 7
                params = {
                    "start_date": start_date,
                    "meal_pattern": meal_pattern,
                    "cuisine_preference": cuisine_preference,
                    "special_considerations": special_considerations,
                    "budget_per_meal": "200〜300円",
                    "person_count": person_count
                }
                
                # 献立生成関数を呼び出し
                weekly_menu = generate_weekly_menu(days, params)
                
                if "error" in weekly_menu:
                    st.error(weekly_menu["error"])
                else:
                    # 献立表示
                    st.success(f"{selected_weeks}週間分（{days}日分）の献立の生成が完了しました！")
                    
                    # 各週ごとのタブ
                    week_tabs = st.tabs([f"第{i+1}週" for i in range(selected_weeks)])
                    
                    # Excel出力用のデータを週ごとに作成
                    all_excel_data = []
                    
                    # 週ごとに処理
                    for week_idx in range(selected_weeks):
                        with week_tabs[week_idx]:
                            # 日付タブの作成（各週7日分）
                            start_day_idx = week_idx * 7
                            end_day_idx = start_day_idx + 7
                            week_dates = [(start_date + datetime.timedelta(days=i)) for i in range(start_day_idx, end_day_idx)]
                            
                            day_tabs = st.tabs([f"{date.strftime('%m/%d')}（{['月', '火', '水', '木', '金', '土', '日'][date.weekday()]}）" for date in week_dates])
                            
                            # 週ごとのExcelデータ構造
                            week_excel_data = {
                                "日付": [],
                                "食事区分": [],
                                "メニュー区分": [],
                                "料理名": [],
                                "1人分量": [],
                                f"{person_count}人分量": []
                            }
                            
                            # 各日の処理
                            for day_idx, day_date in enumerate(week_dates):
                                date_key = day_date.strftime("%Y-%m-%d")
                                date_display = day_date.strftime("%m月%d日")
                                
                                # 日付タブの内容を表示
                                with day_tabs[day_idx]:
                                    day_menu = weekly_menu.get(date_key, {})
                                    
                                    # 献立の表示
                                    if day_menu:
                                        # メニューと食材情報を表示
                                        meals = day_menu.get("meals", {})
                                        ingredients = day_menu.get("ingredients", {})
                                        
                                        st.subheader("本日の献立")
                                        for meal_type in ["朝食", "昼食", "夕食"]:
                                            if meal_type in meals:
                                                st.write(f"### {meal_type}")
                                                
                                                # メニュー項目と食材情報を表で表示
                                                meal_items = meals[meal_type]
                                                meal_ingredients = ingredients.get(meal_type, {})
                                                
                                                for idx, item_name in enumerate(meal_items):
                                                    st.write(f"**{item_name}**")
                                                    
                                                    # Excel用データに追加
                                                    # 日付, 食事区分, メニュー区分, 料理名, 1人分量, 全体量
                                                    week_excel_data["日付"].append(date_display)
                                                    week_excel_data["食事区分"].append(meal_type)
                                                    
                                                    # メニュー区分を決定（順番に応じて）
                                                    menu_category = ""
                                                    if idx == 0:
                                                        menu_category = "主食"
                                                    elif idx == 1:
                                                        menu_category = "主菜"
                                                    elif idx == 2:
                                                        menu_category = "副菜"
                                                    elif idx == 3:
                                                        menu_category = "汁物"
                                                    elif idx == 4:
                                                        menu_category = "デザート"
                                                    else:
                                                        menu_category = "その他"
                                                    
                                                    week_excel_data["メニュー区分"].append(menu_category)
                                                    week_excel_data["料理名"].append(item_name)
                                                    
                                                    # 食材情報があれば表示
                                                    if item_name in meal_ingredients:
                                                        ingredient_info = meal_ingredients[item_name]
                                                        
                                                        # データフレームで食材情報を表示
                                                        ingredients_data = {
                                                            "食材名": [],
                                                            "1人分量": [],
                                                            f"{person_count}人分量": []
                                                        }
                                                        
                                                        for ingredient, amount in ingredient_info.items():
                                                            ingredients_data["食材名"].append(ingredient)
                                                            ingredients_data["1人分量"].append(amount)
                                                            
                                                            # 人数分の計算
                                                            try:
                                                                # 数値部分と単位を分離
                                                                import re
                                                                match = re.match(r"([\d.]+)(\D+)", amount)
                                                                if match:
                                                                    value, unit = match.groups()
                                                                    total = float(value) * person_count
                                                                    total_amount = f"{total}{unit}"
                                                                else:
                                                                    total_amount = f"{amount}×{person_count}"
                                                            except:
                                                                total_amount = f"{amount}×{person_count}"
                                                                
                                                            ingredients_data[f"{person_count}人分量"].append(total_amount)
                                                        
                                                        # 食材テーブルを表示
                                                        st.table(pd.DataFrame(ingredients_data))
                                                        
                                                        # Excel用データに追加（食材ごとに1行ずつではなく、メニュー項目ごとに1行）
                                                        # 一人分と全体分の量をメインの表に追加
                                                        one_person = ", ".join([f"{ing}: {amt}" for ing, amt in ingredient_info.items()])
                                                        all_persons = ", ".join([f"{ing}: {amt}×{person_count}" for ing, amt in ingredient_info.items()])
                                                        
                                                        week_excel_data["1人分量"].append(one_person)
                                                        week_excel_data[f"{person_count}人分量"].append(all_persons)
                                                    else:
                                                        # 食材情報がない場合は空欄
                                                        week_excel_data["1人分量"].append("")
                                                        week_excel_data[f"{person_count}人分量"].append("")
                                        
                                        # 栄養情報も表示
                                        st.write("### 栄養情報")
                                        nutrition = day_menu.get("nutrition", {})
                                        nutrition_data = {
                                            "栄養素": list(nutrition.keys()),
                                            "1人分": list(nutrition.values()),
                                            f"{person_count}人分": [f"{value}×{person_count}" for value in nutrition.values()]
                                        }
                                        st.table(pd.DataFrame(nutrition_data))
                                    else:
                                        st.write("この日の献立情報はありません")
                            
                            # 週ごとのデータをリストに追加
                            all_excel_data.append(pd.DataFrame(week_excel_data))
                    
                    # 全てのデータを結合
                    final_excel_df = pd.concat(all_excel_data, ignore_index=True)
                    
                    # エクスポートオプション
                    st.write(f"### 献立のエクスポート ({selected_weeks}週間分)")
                    
                    # Excelファイルの作成
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        final_excel_df.to_excel(writer, sheet_name='献立表', index=False)
                        
                        # シートの書式設定
                        workbook = writer.book
                        worksheet = writer.sheets['献立表']
                        
                        # 列幅の調整
                        for i, col in enumerate(final_excel_df.columns):
                            max_len = max(
                                final_excel_df[col].astype(str).map(len).max(),
                                len(str(col))
                            ) + 2
                            # Excelの列は0から始まるのではなく、AからZ、その後AA...と続く
                            column_letter = chr(65 + i) if i < 26 else chr(64 + i // 26) + chr(65 + i % 26)
                            worksheet.column_dimensions[column_letter].width = min(max_len, 50)  # 最大幅を50に制限
                    
                    # ダウンロードボタン
                    if st.download_button(
                        label=f"{selected_weeks}週間分の献立をExcelでダウンロード",
                        data=output.getvalue(),
                        file_name=f"menu_{selected_weeks}w_{start_date.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ):
                        st.balloons()

            except Exception as e:
                st.error(f"献立生成中にエラーが発生しました: {str(e)}")
                import traceback
                st.error(traceback.format_exc())

# サイドバーの機能説明
st.sidebar.write("""
### 機能説明
- 既存のメニューにデザートを自動追加
- 栄養バランスを考慮
- 彩りの良い食材を使用
- 予算内で実現可能なメニュー

### 並び替え機能
- 栄養バランス優先：栄養価が均等に分配されるよう最適化
- ランダム並び替え：メニューをランダムに並び替え
- 曜日指定並び替え：特定の曜日に特定のジャンルの料理が来るよう調整
  （例：月曜日に麺類、水曜日に魚料理など）
- 同じ系統の料理が続かないよう調整
- 週ごとのメニューの多様性を確保

### 一週間献立自動生成
- AIによる献立の完全自動生成
- 高齢者施設向けの栄養バランス考慮
- 予算制約内（200〜300円/食）での実現性
- 様々な食事パターンや好みに対応
""")

# 区切り線で明確に分離
st.markdown("---")

def render_nutritionist_chat():
    """栄養士チャット機能を表示する独立した関数"""
    st.header("👩‍⚕️ 栄養士に質問してみましょう")
    st.write("献立内容や栄養バランスについて、プロの栄養士に質問できます。")
    
    # チャット履歴の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "こんにちは！栄養士の山田です。献立や栄養に関するご質問があればお気軽にどうぞ。"}
        ]
    
    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 応答生成中フラグの初期化
    if "generating_response" not in st.session_state:
        st.session_state.generating_response = False
    
    # 応答生成中の表示
    if st.session_state.generating_response:
        with st.chat_message("assistant"):
            with st.container():
                st.write("回答を生成中です...")
                st.spinner()
    
    # 日本語入力用のカスタムUI
    st.write("※日本語入力時はShift+Enterで改行、送信は専用ボタンを使用")
    
    # カスタムCSS
    st.markdown("""
    <style>
    .chat-button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .generating-response {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #555;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 入力とボタンを横に並べるためのコンテナ
    col1, col2 = st.columns([5, 1])
    
    # テキストエリア入力（日本語対応）
    with col1:
        if "user_input" not in st.session_state:
            st.session_state.user_input = ""
        
        user_input = st.text_area(
            "質問を入力してください...",
            key="user_input",
            height=80,
            placeholder="ここに質問を入力してください。Shift+Enterで改行できます。",
            label_visibility="collapsed",
            disabled=st.session_state.generating_response  # 応答生成中は入力を無効化
        )
    
    # 送信処理関数
    def send_message():
        if st.session_state.user_input and st.session_state.user_input.strip():
            # 応答生成中フラグをセット
            st.session_state.generating_response = True
            
            # 入力内容を保持
            user_message = st.session_state.user_input
            
            # 入力フィールドをクリア
            st.session_state.user_input = ""
            
            # ユーザーメッセージを追加
            st.session_state.messages.append({"role": "user", "content": user_message})
            
            # 直ちに再描画して質問を表示
            st.experimental_rerun()
    
    # 応答を生成する関数（別のところで呼び出す）
    def generate_response():
        if st.session_state.generating_response:
            # 最後のユーザーメッセージを取得
            user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
            if user_messages:
                last_user_message = user_messages[-1]["content"]
                
                # 応答を生成
                response = get_nutritionist_response(last_user_message, st.session_state.messages)
                
                # 応答をチャット履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # 応答生成完了フラグをリセット
                st.session_state.generating_response = False
                
                # 再描画
                st.experimental_rerun()
    
    # 送信ボタン
    with col2:
        st.write("")  # 位置調整用の空白
        st.write("")  # 位置調整用の空白
        send_button = st.button(
            "送信", 
            on_click=send_message, 
            type="primary",
            disabled=st.session_state.generating_response  # 応答生成中は送信ボタンを無効化
        )
    
    # 応答生成処理を実行（送信後の状態の場合）
    if st.session_state.generating_response:
        generate_response()

# 栄養士チャットを下部にのみ表示
render_nutritionist_chat()

with tab3:
    st.header("発注書作成")
    st.write("献立表からまとめて発注書を作成します。各日の食材をまとめて1ヶ月分の発注書を生成します。")
    
    # ファイルアップロード
    order_file = st.file_uploader("メニューファイルを選択してください", type=['xlsx'], key="order_file")
    
    if order_file is not None:
        try:
            # 送り先選択プルダウン
            destination = st.selectbox(
                "発注書の送り先を選択してください",
                ["宝成", "豊中"],
                key="order_destination"
            )
            
            # 人数の入力
            person_count = st.number_input("何人分の発注書を作成しますか？", min_value=1, max_value=1000, value=45, step=1)
            
            # 一時ファイルとしてExcelを保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_input:
                tmp_input.write(order_file.getvalue())
                input_path = tmp_input.name
            
            # 読み込んだExcelの内容を表示
            menu_df = pd.read_excel(input_path)
            
            if st.button("発注書を作成", key="create_order"):
                with st.spinner("発注書を作成中..."):
                    try:
                        # 実際の発注書生成関数を呼び出し
                        output_path = str(Path(input_path).with_name('order_sheet.xlsx'))
                        
                        # 発注書作成関数を呼び出し - 送り先情報も渡す
                        create_order_sheets(input_path, output_path, person_count, destination)
                        
                        # 発注書をダウンロード可能にする
                        with open(output_path, 'rb') as f:
                            excel_data = f.read()
                        
                        # 一時ファイルの削除
                        os.unlink(input_path)
                        os.unlink(output_path)
                        
                        # ダウンロードボタン
                        st.success("発注書の作成が完了しました！")
                        st.download_button(
                            label="発注書をダウンロード",
                            data=excel_data,
                            file_name="order_sheet.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"発注書作成中にエラーが発生しました: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
        except Exception as e:
            st.error(f"ファイル読み込み中にエラーが発生しました: {str(e)}") 