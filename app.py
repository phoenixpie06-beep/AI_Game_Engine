# -*- coding: utf-8 -*-
"""
AI 游戏商业立项风控引擎
支持高维富文本基因库 | 深度 JSON 导入 + 智能雷达扫描
"""

import json
import os
import re
import time
import random
import streamlit as st
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ============== 1. 数据源初始化 ==============
def init_database():
    """启动时检查 database.json，不存在则创建四个维度的初始数组"""
    default_db = {
        "Entry_Gameplay": [
            "单手摇杆走位自动割草", "极简拖拽放置塔防", "屏幕物理连线消除", "场景滑动寻找违和感"
        ],
        "Core_Loop": [
            "局外空间网格背包整理", "自动化产线运转与物流", "环境生理数值干预战斗", "局内技能变异与双人反应"
        ],
        "Theme": [
            "现代职场社畜发疯修仙", "微缩办公桌奇观", "极端深海高压生存", "反差童话朋克"
        ],
        "Art_Style": [
            "复古高保真像素", "黑白单色手绘", "90年代老电脑桌面UI", "冷色调工业赛博"
        ]
    }
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
    if not os.path.exists(db_path):
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(default_db, f, ensure_ascii=False, indent=2)
    return db_path


def load_database(db_path):
    """安全加载 database.json"""
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
        st.error(f"❌ 加载基因库失败: {e}")
        return {"Entry_Gameplay": [], "Core_Loop": [], "Theme": [], "Art_Style": []}


def save_database(db_path, data):
    """安全保存 database.json"""
    try:
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except (IOError, TypeError) as e:
        st.error(f"❌ 保存基因库失败: {e}")
        return False


def merge_and_dedupe(db, new_items):
    """将新词条追加到数据库，严格去重"""
    for dim in ["Entry_Gameplay", "Core_Loop", "Theme", "Art_Style"]:
        if dim not in db:
            db[dim] = []
        if dim in new_items and isinstance(new_items[dim], list):
            for item in new_items[dim]:
                if isinstance(item, str) and item.strip() and item.strip() not in db[dim]:
                    db[dim].append(item.strip())
    return db


def parse_json_clean(raw_text):
    """解析 JSON，正则清理 markdown 标记，支持对象 {} 和数组 []"""
    if not raw_text or not isinstance(raw_text, str):
        return None
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()
    # 尝试提取：先整体，再数组（Tab2），再对象（Tab1）
    arr_match = re.search(r"\[[\s\S]*\]", text)
    obj_match = re.search(r"\{[\s\S]*\}", text)
    for candidate in [text, arr_match.group(0) if arr_match else None, obj_match.group(0) if obj_match else None]:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def modules_to_db_items(modules):
    """
    将 modules 数组转换为四个维度的富文本词条，按 module_type 路由。
    富文本格式：【{name}】 {one_liner} (玩家诉求: {player_value})
    """
    result = {
        "Entry_Gameplay": [],
        "Core_Loop": [],
        "Theme": [],
        "Art_Style": [],
    }
    if not isinstance(modules, list):
        return result
    for m in modules:
        if not isinstance(m, dict):
            continue
        mt = (m.get("module_type") or "").lower()
        name = m.get("name") or ""
        one_liner = m.get("one_liner") or ""
        player_value = m.get("player_value") or ""
        if not name and not one_liner:
            continue
        if player_value:
            rich = f"【{name}】 {one_liner} (玩家诉求: {player_value})".strip()
        else:
            rich = f"【{name}】 {one_liner}".strip()
        if not rich:
            continue
        if "entry" in mt:
            result["Entry_Gameplay"].append(rich)
        elif "core_loop" in mt or "mechanic" in mt or "meta_system" in mt:
            result["Core_Loop"].append(rich)
        elif "theme" in mt:
            result["Theme"].append(rich)
        elif "art" in mt:
            result["Art_Style"].append(rich)
    return result


# ============== 2. 全局界面 ==============
st.set_page_config(page_title="AI 立项风控引擎", layout="wide")

if "top_ideas" not in st.session_state:
    st.session_state.top_ideas = []
if "idea_details" not in st.session_state:
    st.session_state.idea_details = {}

db_path = init_database()
db = load_database(db_path)

# ============== 侧边栏 ==============
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = st.text_input("Gemini API Key", type="password", placeholder="请输入您的 API Key")

    proxy_url = st.text_input(
        "🔌 本地网络代理 (国内用户防超时必填)",
        value="",
        placeholder="例如 http://127.0.0.1:7890",
        help="例如 Clash 默认填 http://127.0.0.1:7890，v2ray 填 http://127.0.0.1:10808。不填则直连。"
    )
    if proxy_url and proxy_url.strip():
        p = proxy_url.strip()
        os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = p
        os.environ["http_proxy"] = os.environ["https_proxy"] = p
        st.success("✅ 全局代理已挂载，引擎已打通外网！")

    model_names = []
    if api_key and api_key.strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key.strip())
            for m in genai.list_models():
                methods = getattr(m, "supported_generation_methods", None) or []
                name = getattr(m, "name", None) or ""
                if "generateContent" in methods and "gemini" in name.lower():
                    model_names.append(name)
        except Exception:
            st.error("API Key 无效或网络连接失败")

    model_options = model_names if model_names else ["（暂无可用模型）"]
    selected_model = st.selectbox("🤖 请选择 AI 引擎", model_options, key="model_select")

    st.divider()
    st.subheader("📊 基因库统计")
    for dim, label in [("Entry_Gameplay", "入局玩法"), ("Core_Loop", "核心循环"), ("Theme", "题材"), ("Art_Style", "画风")]:
        st.metric(label, len(db.get(dim, [])))


def validate_api_key():
    if not api_key or not api_key.strip():
        st.error("❌ 请先在侧边栏输入 Gemini API Key")
        return False
    return True


def get_gemini_model(api_key_str, model_name_str):
    if not model_name_str or "暂无可用" in model_name_str:
        st.error("❌ 请先在侧边栏选择有效的 AI 引擎")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key_str.strip())
        return genai.GenerativeModel(model_name_str)
    except Exception as e:
        st.error(f"❌ Gemini 初始化失败: {e}")
        return None


def safe_extract_json(text):
    """从模型返回中提取 JSON（用于 Tab 2 数组格式）"""
    parsed = parse_json_clean(text)
    if parsed is None and text:
        st.error("❌ JSON 解析失败")
    return parsed


# 通用安全设置与 JSON 模式
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
GEN_CONFIG_JSON = {"response_mime_type": "application/json"}

# ============== 主界面 Tab ==============
tab1, tab2, tab3 = st.tabs(["🌐 1. 深度情报雷达", "🎯 2. 智能初筛与立项", "🗂️ 3. 基因库管理"])

# ============== Tab 1: 深度情报雷达 ==============
with tab1:
    st.header("🌐 深度情报雷达与 JSON 注入港")
    sub_a, sub_b = st.tabs(["📥 模式A：外部高维 JSON 直接注入", "🤖 模式B：内置雷达智能扫描"])

    # ---------- 模式A：外部 JSON 注入 ----------
    with sub_a:
        st.caption("粘贴由 Gemini 生成的带有 modules 数组的深度 JSON 报告")
        json_input = st.text_area(
            "请粘贴由 Gemini 生成的带有 modules 数组的深度 JSON 报告",
            height=400,
            placeholder='{"modules": [{"module_type": "entry_hook", "name": "xxx", "one_liner": "xxx", "player_value": "xxx"}, ...]}'
        )
        if st.button("⚡ 解析 JSON 提取高维商业基因并入库"):
            if not json_input or not json_input.strip():
                st.error("❌ 请输入 JSON 内容")
                st.stop()

            # Step 1: 清理 markdown 标记
            text = json_input.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
            text = text.strip()

            data = None
            # Step 2: 先尝试原生 json.loads
            try:
                obj_match = re.search(r"\{[\s\S]*\}", text)
                candidate = obj_match.group(0) if obj_match else text
                data = json.loads(candidate)
            except (json.JSONDecodeError, AttributeError) as e:
                # Step 3: 解析失败 → 启动 AI 自动纠错
                st.warning("⚠️ 检测到输入文本存在 JSON 语法错误（如未转义的双引号）。正在呼叫 AI 启动自动修复与提纯...")

                if not validate_api_key():
                    st.error("❌ 请输入 API Key 以便启用 AI 修复功能")
                    st.stop()

                model = get_gemini_model(api_key, selected_model)
                if not model:
                    st.stop()

                repair_prompt = f"""你是一个 JSON 修复与数据清洗专家。以下是一段损坏的 JSON 文本，我只需要里面 `modules` 数组的数据。请修复语法错误（如未转义的双引号、多余逗号等），并提取出所有的模块。
必须且只能返回一个合法的 JSON 对象，包含一个 `modules` 数组（数组内包含对象，对象键名为 module_type, name, one_liner, player_value）。
绝对不要包含 markdown 标记（如 ```json）。

损坏的文本如下：
{text}"""

                with st.spinner("🤖 AI 正在修复 JSON 语法..."):
                    try:
                        resp = model.generate_content(
                            repair_prompt,
                            generation_config=GEN_CONFIG_JSON,
                            safety_settings=SAFETY_SETTINGS,
                        )
                        raw_fixed = resp.text if hasattr(resp, "text") else str(resp)
                    except Exception as ex:
                        st.error(f"❌ AI 修复调用失败: {ex}")
                        st.stop()

                # 正则剔除 markdown 后再次解析
                raw_fixed = re.sub(r"^```(?:json)?\s*", "", raw_fixed)
                raw_fixed = re.sub(r"\s*```\s*$", "", raw_fixed).strip()
                obj_match = re.search(r"\{[\s\S]*\}", raw_fixed)
                candidate = obj_match.group(0) if obj_match else raw_fixed
                try:
                    data = json.loads(candidate)
                except json.JSONDecodeError as ex2:
                    st.error(f"❌ AI 修复后仍无法解析 JSON。详细错误: {ex2}")
                    st.code(raw_fixed)
                    st.stop()

            if data is None:
                st.error("❌ 解析失败")
                st.stop()

            modules = data.get("modules")
            if not isinstance(modules, list):
                st.error("❌ 未找到 modules 数组，请确保 JSON 中包含 modules 键")
                st.stop()

            new_items = modules_to_db_items(modules)
            total = sum(len(v) for v in new_items.values())
            if total == 0:
                st.warning("⚠️ 未解析出任何有效模块，请检查 module_type 取值（entry/core_loop/mechanic/meta_system/theme/art）")
                st.stop()

            db = load_database(db_path)
            db = merge_and_dedupe(db, new_items)
            if save_database(db_path, db):
                st.success("✅ 高维商业基因已入库")
                st.json(new_items)

    # ---------- 模式B：内置雷达 ----------
    with sub_b:
        default_queries = """过去一周 微信小游戏 新品 核心玩法
Steam 过去7天 潜力独立游戏 创新机制
海外手游 飙升榜 差异化 玩法 拆解"""
        queries_text = st.text_area("搜索指令（每行一条）", value=default_queries, height=120)
        num_per_query = st.slider("每个指令抓取数量", 1, 15, 5)

        if st.button("🕷️ 启动雷达：搜刮情报并提取高维基因"):
            if not validate_api_key():
                st.stop()
            queries = [q.strip() for q in queries_text.strip().split("\n") if q.strip()]
            if not queries:
                st.error("❌ 请至少输入一条搜索指令")
                st.stop()

            try:
                from duckduckgo_search import DDGS
            except ImportError:
                st.error("❌ 请安装 duckduckgo_search: pip install duckduckgo-search")
                st.stop()

            all_raw = []
            with st.spinner("🕷️ 正在抓取..."):
                for q in queries:
                    try:
                        with DDGS() as ddgs:
                            results = list(ddgs.text(q, max_results=num_per_query))
                        for r in results:
                            t = getattr(r, "title", "") or ""
                            b = getattr(r, "body", "") or getattr(r, "snippet", "") or ""
                            all_raw.append(f"【{t}】\n{b}")
                        st.toast(f"🔍 '{q}' 抓取到 {len(results)} 条")
                    except Exception as ex:
                        st.warning(f"⚠️ 搜索「{q}」失败：{ex}")
                        time.sleep(2)
                        continue
                    time.sleep(2)

            if not all_raw:
                st.error("❌ 未抓取到任何情报")
                st.stop()

            search_context = "\n\n---\n\n".join(all_raw[:50])
            if len(search_context) < 50:
                st.error("❌ 抓取彻底失败：网络超时或被拦截")
                st.stop()

            st.info(f"✅ 共 {len(search_context)} 字符，正在喂给 AI...")
            with st.expander("👀 原始网页快照"):
                st.write(search_context)

            current_db = load_database(db_path)
            current_db_str = json.dumps(current_db, ensure_ascii=False, indent=2)

            prompt = f"""你是顶尖游戏商业分析师。阅读以下搜索引擎抓取的最新情报快照：

【情报开始】
{search_context}
【情报结束】

请挖掘潜力新品和差异化玩法。提取最具商业价值的底层机制。注意与现有基因库做语义去重：

【现有基因库】
{current_db_str}

你必须返回一个合法的 JSON 对象，包含一个 `modules` 数组。每个对象必须包含：
- module_type（只能是: entry_hook, core_loop, theme, art_style 之一）
- name（模块精炼名称）
- one_liner（一句话核心机制拆解）
- player_value（该机制满足了玩家什么心理诉求或商业错位点）

绝对不要包含 markdown 标记。未提取到则 modules 为空数组 []。"""

            model = get_gemini_model(api_key, selected_model)
            if not model:
                st.stop()

            with st.spinner("🤖 AI 正在提取高维基因..."):
                try:
                    resp = model.generate_content(prompt, generation_config=GEN_CONFIG_JSON, safety_settings=SAFETY_SETTINGS)
                    raw_text = resp.text if hasattr(resp, "text") else str(resp)
                except Exception as ex:
                    st.error(f"❌ Gemini 调用失败: {ex}")
                    st.stop()

            data = parse_json_clean(raw_text)
            if data is None:
                st.error("🚨 解析失败，原始回复：")
                st.code(raw_text)
                st.stop()

            modules = data.get("modules") or []
            with st.expander("🤖 [Debug] 原始 JSON"):
                st.code(raw_text, language="json")

            if not isinstance(modules, list):
                st.warning("⚠️ 未找到 modules 数组")
                st.stop()

            new_items = modules_to_db_items(modules)
            total = sum(len(v) for v in new_items.values())
            if total == 0:
                st.warning("⚠️ 未提取到有效增量，建议调整搜索词")
                st.stop()

            db = load_database(db_path)
            db = merge_and_dedupe(db, new_items)
            if save_database(db_path, db):
                st.success("🤖 AI 已完成深度语义查重，提取出以下【全新增量】变异基因：")
                st.json(new_items)

# ============== Tab 2: 智能初筛与立项 ==============
with tab2:
    st.header("🎯 智能初筛与立项")

    st.subheader("第一步：后台海选初筛")
    if st.button("🧠 让 AI 在后台推演 10 次，精选 Top 3"):
        if not validate_api_key():
            st.stop()
        db = load_database(db_path)
        ep = db.get("Entry_Gameplay", [])
        cl = db.get("Core_Loop", [])
        th = db.get("Theme", [])
        ar = db.get("Art_Style", [])
        if not (ep and cl and th and ar):
            st.error("❌ 基因库至少每个维度需有 1 个词条")
            st.stop()

        combos_raw = set()
        for _ in range(30):
            c = f"[入局]{random.choice(ep)} + [循环]{random.choice(cl)} + [题材]{random.choice(th)} + [画风]{random.choice(ar)}"
            combos_raw.add(c)
            if len(combos_raw) >= 10:
                break
        combos_list = list(combos_raw)[:10]

        prompt = f"""我随机生成了 10 个立项组合（每个模块都带有详细的商业机制与玩家诉求解释）：

{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(combos_list))}

请作为风控专家，仔细阅读这些深度解释，淘汰掉 7 个生硬缝合的废案（特别是入局与核心循环过渡不平滑的）。挑选出【最具商业爆发力或错位竞争潜力】的 3 个组合。
返回 JSON 数组格式：[ {{"id": "唯一ID", "idea_name": "项目代号", "combo": "组合的核心名称简述", "evaluation": "150字内的商业初判，说明优劣势、错位机会及过渡是否平滑"}} ]。绝对不要带有 ```json 等 markdown 标记。"""

        model = get_gemini_model(api_key, selected_model)
        if not model:
            st.stop()

        with st.spinner("🤖 AI 正在推演..."):
            try:
                resp = model.generate_content(prompt, generation_config=GEN_CONFIG_JSON, safety_settings=SAFETY_SETTINGS)
                raw = resp.text if hasattr(resp, "text") else str(resp)
            except Exception as ex:
                st.error(f"❌ 调用失败: {ex}")
                st.stop()

        parsed = safe_extract_json(raw)
        if parsed is None:
            st.stop()
        if not isinstance(parsed, list) or len(parsed) < 1:
            st.error("❌ 返回格式不符合预期")
            st.stop()

        st.session_state.top_ideas = parsed[:3]
        st.session_state.idea_details = {}
        st.success("✅ 已精选 Top 3")
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()

    st.subheader("第二步：展示摘要与按需生成详情")
    if st.session_state.top_ideas:
        for idx, obj in enumerate(st.session_state.top_ideas):
            idea_id = obj.get("id") or f"idea_{idx+1}"
            idea_name = obj.get("idea_name", "未命名")
            combo = obj.get("combo", "")
            evaluation = obj.get("evaluation", "")

            with st.container(border=True):
                st.subheader(idea_name)
                st.info(f"组合：{combo}")
                st.write("**初判评价**：", evaluation)

                if st.button(f"📝 深度推演：生成【{idea_name}】详细立项企划案", key=f"detail_{idea_id}"):
                    if not validate_api_key():
                        st.stop()
                    model = get_gemini_model(api_key, selected_model)
                    if not model:
                        st.stop()

                    detail_prompt = f"""系统选定了这个潜力组合：{combo}。
该组合中的每个模块都带有【详细机制解释与玩家诉求】。请撰写极其详尽的 Markdown 商业立项企划案，必须结合这些深度信息。包含：
1. 一句话高概念
2. 玩法拆解与【平滑过渡设计】（说明从入局到核心循环的平滑过渡）
3. CPI 吸量潜力与错位竞争红利
4. 商业化深度 LTV 设计
5. 研发可行性与自传播属性"""

                    with st.spinner(f"🤖 正在生成【{idea_name}】企划案..."):
                        try:
                            resp = model.generate_content(detail_prompt)
                            md_text = resp.text if hasattr(resp, "text") else str(resp)
                            st.session_state.idea_details[idea_id] = md_text
                        except Exception as ex:
                            st.error(f"❌ 生成失败: {ex}")
                            st.stop()
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()

                if idea_id in st.session_state.idea_details:
                    st.markdown("---")
                    st.markdown("### 📄 详细立项企划案")
                    st.markdown(st.session_state.idea_details[idea_id])
    else:
        st.info("👆 请先点击上方按钮精选 Top 3")

# ============== Tab 3: 基因库管理 ==============
with tab3:
    st.header("🗂️ 核心基因库管理")
    db = load_database(db_path)
    ep_val = "\n".join(db.get("Entry_Gameplay", []))
    cl_val = "\n".join(db.get("Core_Loop", []))
    th_val = "\n".join(db.get("Theme", []))
    ar_val = "\n".join(db.get("Art_Style", []))

    c1, c2 = st.columns(2)
    with c1:
        ep_edit = st.text_area("Entry_Gameplay（入局玩法）", value=ep_val, height=400)
        cl_edit = st.text_area("Core_Loop（核心循环）", value=cl_val, height=400)
    with c2:
        th_edit = st.text_area("Theme（题材）", value=th_val, height=400)
        ar_edit = st.text_area("Art_Style（画风）", value=ar_val, height=400)

    if st.button("💾 保存并更新基因库"):
        def parse_lines(s):
            return list(dict.fromkeys([x.strip() for x in s.split("\n") if x.strip()]))

        new_db = {
            "Entry_Gameplay": parse_lines(ep_edit),
            "Core_Loop": parse_lines(cl_edit),
            "Theme": parse_lines(th_edit),
            "Art_Style": parse_lines(ar_edit),
        }
        if save_database(db_path, new_db):
            st.success("✅ 基因库已保存")
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()

    st.divider()
    if st.button("🧹 召唤 AI 进行全库深度语义合并与瘦身", type="primary"):
        if not validate_api_key():
            st.stop()
        model = get_gemini_model(api_key, selected_model)
        if not model:
            st.stop()
        current_db = load_database(db_path)
        current_db_str = json.dumps(current_db, ensure_ascii=False, indent=2)
        wash_prompt = f"""你是有重度数据洁癖的资深游戏主策。这是我目前庞大且可能充满冗余的立项基因库（词条可能带【】括号和玩家诉求说明）：
{current_db_str}

请对四个维度进行【合并同类项与语义瘦身】。将本质相同的机制融合成一个最精准、最专业的表述（可保留【】与玩家诉求格式）。保留真正独立的概念。
必须且只能返回清洗后的纯 JSON 对象，键名保持 Entry_Gameplay, Core_Loop, Theme, Art_Style 不变。"""

        with st.spinner("🧠 AI 正在语义扫描与融合..."):
            try:
                resp = model.generate_content(wash_prompt, generation_config=GEN_CONFIG_JSON, safety_settings=SAFETY_SETTINGS)
                raw_text = resp.text if hasattr(resp, "text") else str(resp)
            except Exception as ex:
                st.error(f"❌ 洗库失败: {ex}")
                st.stop()

        try:
            washed_db = json.loads(raw_text)
        except json.JSONDecodeError:
            st.error("🚨 解析失败，原始回复：")
            st.code(raw_text)
            st.stop()

        if save_database(db_path, washed_db):
            st.success("✨ 洗库完成！")
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
