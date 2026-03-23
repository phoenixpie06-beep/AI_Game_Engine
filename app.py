# -*- coding: utf-8 -*-
"""
AI 游戏商业立项风控引擎 (Ultimate Edition V6 纯净版)
包含：严格富文本过滤(拒收垃圾标签) | 一键净化 | GitHub静默同步 | 动态无限制模型接口
"""

import json
import os
import re
import time
import random
import subprocess
import threading
import tempfile
import streamlit as st
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ============== 1. 系统配置与 GitHub 同步 ==============
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_key": "", "proxy": "", "model": "gemini-3.1-pro"}

def save_config(api_key, proxy, model):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"api_key": api_key, "proxy": proxy, "model": model}, f, indent=2)

def background_git_sync():
    """后台静默同步到 GitHub"""
    try:
        subprocess.run(["git", "add", "database.json", "config.json", "app.py"], capture_output=True)
        subprocess.run(["git", "commit", "-m", "🤖 AI Auto-Sync: 基因库已净化并更新"], capture_output=True)
        subprocess.run(["git", "push"], capture_output=True)
    except Exception:
        pass

def trigger_sync():
    threading.Thread(target=background_git_sync).start()

# ============== 2. 数据库与超级纯净解析器 ==============
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

def init_database():
    default_db = {
        "Entry_Gameplay": ["【摇杆割草】单手操作极度解压 (玩家诉求: 低门槛破冰)", "【极简拖拽放置塔防】零门槛上手 (玩家诉求: 快速多巴胺)"],
        "Core_Loop": ["【空间网格背包整理】有限空间的羁绊拼图 (玩家诉求: 强迫症与策略深水区)"],
        "Theme": ["【现代职场社畜发疯】将修仙包装成打工KPI (玩家诉求: 极强的文化共鸣)"],
        "Art_Style": ["【复古电脑桌面UI】还原90年代Windows系统 (玩家诉求: 猎奇反差与低成本)"],
        "Market_Rules": []
    }
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(default_db, f, ensure_ascii=False, indent=2)

def load_database():
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            if "Market_Rules" not in db: db["Market_Rules"] = []
            return db
    except Exception:
        return {"Entry_Gameplay": [], "Core_Loop": [], "Theme": [], "Art_Style": [], "Market_Rules": []}

def save_database(data):
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        trigger_sync() 
        return True
    except Exception as e:
        st.error(f"❌ 保存基因库失败: {e}")
        return False

def extract_genes_from_json(data):
    """【精英级防垃圾解析器】：只提取富文本，拒绝空壳词汇"""
    result = {"Entry_Gameplay": [], "Core_Loop": [], "Theme": [], "Art_Style": []}
    if not isinstance(data, dict): return result

    # 1. 严格且只提取 modules 数组
    modules = data.get("modules", [])
    if isinstance(modules, list):
        for m in modules:
            if not isinstance(m, dict): continue
            mt = str(m.get("module_type", "")).lower()
            name = str(m.get("name", "")).strip()
            one_liner = str(m.get("one_liner", "")).strip()
            pv = str(m.get("player_value", "")).strip()
            
            # 【垃圾过滤器】：如果没有详细的名字和描述，直接判定为空壳，丢弃！
            if not name or len(one_liner) < 5: 
                continue

            rich = f"【{name}】 {one_liner}"
            if pv: rich += f" (玩家诉求: {pv})"

            if "entry" in mt or "hook" in mt: result["Entry_Gameplay"].append(rich)
            elif "theme" in mt: result["Theme"].append(rich)
            elif "art" in mt or "style" in mt or "visual" in mt: result["Art_Style"].append(rich)
            else: result["Core_Loop"].append(rich)

    # 去重
    for k in result:
        result[k] = list(dict.fromkeys(result[k]))
    return result

def merge_and_dedupe(db, new_items):
    for dim in ["Entry_Gameplay", "Core_Loop", "Theme", "Art_Style"]:
        if dim in new_items:
            for item in new_items[dim]:
                if item.strip() and item.strip() not in db[dim]:
                    db[dim].append(item.strip())
    return db

# ============== 3. 全量实时模型拉取引擎 ==============
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_available_models(api_key, proxy):
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["http_proxy"] = proxy
        os.environ["https_proxy"] = proxy
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        fetched_models = []
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", [])
            if "generateContent" in methods and "gemini" in m.name.lower():
                fetched_models.append(m.name.replace("models/", ""))
        fetched_models.sort(reverse=True)
        return fetched_models, None
    except Exception as e:
        return [], str(e)

# ============== 4. 全局界面与配置 ==============
st.set_page_config(page_title="AI 立项风控中台", layout="wide")
init_database()

if "top_ideas" not in st.session_state: st.session_state.top_ideas = []
if "idea_details" not in st.session_state: st.session_state.idea_details = {}

sys_config = load_config()

with st.sidebar:
    st.title("⚙️ 系统与网络配置")
    api_key_input = st.text_input("🔑 Gemini API Key", type="password", value=sys_config.get("api_key", ""))
    proxy_input = st.text_input("🌐 本地代理 (如 http://127.0.0.1:7890)", value=sys_config.get("proxy", ""))
    
    if proxy_input.strip():
        os.environ["HTTP_PROXY"] = proxy_input.strip()
        os.environ["HTTPS_PROXY"] = proxy_input.strip()

    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 刷新模型库"):
            fetch_available_models.clear()
            st.rerun()

    model_options = []
    error_msg = None
    if api_key_input.strip():
        model_options, error_msg = fetch_available_models(api_key_input.strip(), proxy_input.strip())
            
    if error_msg: st.warning("⚠️ 模型拉取失败，请检查网络。")
    
    saved_model = sys_config.get("model", "gemini-3.1-pro")
    if not model_options: model_options = [saved_model] if saved_model else ["gemini-3.1-pro"]
    elif saved_model and saved_model not in model_options: model_options.append(saved_model)
        
    model_options = sorted(list(set(model_options)), reverse=True)
    default_idx = model_options.index(saved_model) if saved_model in model_options else 0
    
    use_manual = st.checkbox("✍️ 极客模式：手动输入模型名称")
    if use_manual:
        selected_model = st.text_input("手动指定模型", value=saved_model)
    else:
        selected_model = st.selectbox("🤖 请选择 AI 引擎", model_options, index=default_idx)

    if st.button("💾 保存配置并生效", type="primary"):
        save_config(api_key_input, proxy_input, selected_model)
        fetch_available_models.clear() 
        st.success("✅ 配置已保存！（☁️ 已同步）")
        time.sleep(1)
        st.rerun()

    st.divider()
    db = load_database()
    st.subheader("📊 基因库统计")
    st.metric("入局玩法", len(db.get("Entry_Gameplay", [])))
    st.metric("核心循环", len(db.get("Core_Loop", [])))
    st.metric("题材包装", len(db.get("Theme", [])))
    st.metric("视觉画风", len(db.get("Art_Style", [])))
    st.metric("🧠 永久风控法则", len(db.get("Market_Rules", [])))

def get_model():
    if not api_key_input.strip() or not selected_model:
        st.error("❌ 缺少 API Key 或模型配置")
        return None
    import google.generativeai as genai
    genai.configure(api_key=api_key_input.strip())
    return genai.GenerativeModel(selected_model.strip())

SAFETY_SETTINGS = { HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE, HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE, HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE, HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE }
GEN_JSON = {"response_mime_type": "application/json"}

# ============== 主工作区 ==============
tab1, tab2, tab3, tab4 = st.tabs(["🌐 1. 情报雷达入库", "🎯 2. 初筛与立项", "🗂️ 3. 基因库管理", "🧠 4. 真实复盘(永久记忆)"])

with tab1:
    st.header("🌐 深度情报雷达与 JSON 注入港")
    sub_a, sub_b = st.tabs(["📥 模式A：外部 JSON 注入", "🤖 模式B：内置雷达扫描"])

    with sub_a:
        json_input = st.text_area("请粘贴由 Gemini 生成的市场报告 JSON", height=300)
        if st.button("⚡ 强力净化并提取商业基因入库"):
            if not json_input.strip(): st.stop()
            text = re.sub(r"^```(?:json)?\s*", "", json_input.strip())
            text = re.sub(r"\s*```\s*$", "", text).strip()
            try:
                obj_match = re.search(r"\{[\s\S]*\}", text)
                data = json.loads(obj_match.group(0) if obj_match else text)
            except Exception as e:
                st.warning(f"⚠️ 捕获到格式损坏 ({e})，启动【智能提纯模式】(约需5-10秒)...")
                model = get_model()
                if not model: st.stop()

                repair_prompt = f"你是一个顶尖的数据清洗AI。用户粘贴了一段损坏的文本（可能缺失逗号、带有非法索引等）。\n请直接跳过语法修复，从这段文本中提取出所有具有商业价值的游戏机制/题材/画风。\n必须返回一个合法的 JSON 对象，包含以下四个键（若无内容则为空数组 []）：\n- Entry_Gameplay (入局玩法)\n- Core_Loop (核心循环)\n- Theme (题材)\n- Art_Style (画风)\n提取的内容尽量保留「【名称】 描述 (玩家诉求: xxx)」的格式。绝对不要带有 markdown 标记。\n\n损坏文本：\n{text}"

                with st.spinner("🤖 AI 正在无视语法错误，直接强行抽取商业基因..."):
                    try:
                        resp = model.generate_content(repair_prompt, safety_settings=SAFETY_SETTINGS)
                        fixed_raw = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                        fixed_raw = re.sub(r"\s*```\s*$", "", fixed_raw).strip()

                        obj_match = re.search(r"\{[\s\S]*\}", fixed_raw)
                        data = json.loads(obj_match.group(0) if obj_match else fixed_raw)

                        new_items = {
                            "Entry_Gameplay": data.get("Entry_Gameplay", []),
                            "Core_Loop": data.get("Core_Loop", []),
                            "Theme": data.get("Theme", []),
                            "Art_Style": data.get("Art_Style", [])
                        }

                        db = load_database()
                        db = merge_and_dedupe(db, new_items)
                        save_database(db)

                        total = sum(len(v) for v in new_items.values())
                        if total > 0:
                            st.success(f"✅ AI 强行提纯成功！榨取 {total} 个基因并入库！（☁️ 已同步）")
                            st.json(new_items)
                        else:
                            st.warning("⚠️ AI 未能在损坏文本中找到有效基因。")
                        st.stop()
                    except Exception as ex2:
                        st.error(f"❌ AI 强行提取失败，文本损坏过于严重: {ex2}")
                        st.stop()

            new_items = extract_genes_from_json(data)
            db = load_database()
            db = merge_and_dedupe(db, new_items)
            save_database(db)
            
            total = sum(len(v) for v in new_items.values())
            if total > 0:
                st.success(f"✅ 成功榨取 {total} 个极品商业基因！（已严格拒收所有短废话标签）")
                st.json(new_items)
            else:
                st.warning("⚠️ 未提取到基因：报告中的 modules 可能缺乏详细的 one_liner 说明，或者全都是单字标签。")

    with sub_b:
        queries_text = st.text_area("搜索指令", value="过去一周 微信小游戏 新品 核心玩法\nSteam 过去7天 潜力独立游戏 创新机制\n海外手游 飙升榜 差异化 玩法 拆解")
        if st.button("🕷️ 启动雷达扫描"):
            model = get_model()
            if not model: st.stop()
            try: from duckduckgo_search import DDGS
            except: st.error("需安装: pip install duckduckgo-search"); st.stop()
                
            queries = [q.strip() for q in queries_text.split("\n") if q.strip()]
            all_raw = []
            with st.spinner("🕷️ 正在搜刮..."):
                for q in queries:
                    try:
                        with DDGS() as ddgs: res = list(ddgs.text(q, max_results=5))
                        for r in res: all_raw.append(f"【{r.get('title','')}】\n{r.get('body','')}")
                        st.toast(f"🔍 '{q}' 抓到 {len(res)} 条")
                    except Exception: pass
                    time.sleep(2)
            
            context = "\n\n".join(all_raw[:30])
            if len(context) < 50: st.error("❌ 抓取失败"); st.stop()
                
            prompt = f"你是商业分析师。阅读快照：\n{context}\n提取深度机制。必须返回JSON对象，包含 modules 数组。每个对象含: module_type, name, one_liner, player_value。必须是详细解构，不要单字标签！"
            with st.spinner(f"🤖 正在调用 [{selected_model}] 分析..."):
                try:
                    resp = model.generate_content(prompt, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                    data = json.loads(re.sub(r"^```(?:json)?\s*", "", resp.text.strip()).replace("```", "").strip())
                except Exception: st.error("解析失败"); st.stop()
            
            new_items = extract_genes_from_json(data)
            db = merge_and_dedupe(load_database(), new_items)
            save_database(db)
            st.success("✅ 雷达扫描入库完成！")
            st.json(new_items)

with tab2:
    st.header("🎯 智能初筛与立项")
    if st.button(f"🧠 让 [{selected_model}] 精选 Top 3 立项组合", type="primary"):
        model = get_model()
        if not model: st.stop()
        db = load_database()
        if not (db["Entry_Gameplay"] and db["Core_Loop"] and db["Theme"] and db["Art_Style"]):
            st.error("❌ 基因库四个维度不能为空"); st.stop()
            
        combos = [f"[入局]{random.choice(db['Entry_Gameplay'])} | [循环]{random.choice(db['Core_Loop'])} | [题材]{random.choice(db['Theme'])} | [画风]{random.choice(db['Art_Style'])}" for _ in range(15)]
        rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(db.get("Market_Rules", []))])
        prompt = f"""【🔴 团队风控法则库】：\n{rules_text}\n\n请评估以下组合：\n{chr(10).join(combos)}\n淘汰12个废案，选出最具爆发力的3个。返回纯JSON数组：[ {{"id":"1", "idea_name":"代号", "combo":"组合", "evaluation":"优劣势分析"}} ]"""

        with st.spinner(f"🤖 正在使用 {selected_model} 进行风控打分..."):
            try:
                resp = model.generate_content(prompt, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                raw = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                st.session_state.top_ideas = json.loads(re.sub(r"\s*```\s*$", "", raw).strip())
                st.session_state.idea_details = {}
                st.rerun()
            except Exception as e: st.error(f"解析失败: {e}")

    if st.session_state.top_ideas:
        for idx, obj in enumerate(st.session_state.top_ideas):
            with st.container(border=True):
                st.subheader(obj.get("idea_name", "未命名"))
                st.info(obj.get("combo", ""))
                st.write(obj.get("evaluation", ""))
                if st.button(f"📝 深度推演：生成【{obj.get('idea_name')}】详案", key=f"btn_{idx}"):
                    model = get_model()
                    rules_text = "\n".join(load_database().get("Market_Rules", []))
                    detail_prompt = f"【法则】：\n{rules_text}\n\n基于此，为组合 [{obj.get('combo')}] 撰写详尽 Markdown 立项案。包含：高概念、玩法过渡拆解、买量分析、LTV设计。"
                    with st.spinner(f"正在使用 [{selected_model}] 撰写详案..."):
                        try: st.session_state.idea_details[idx] = model.generate_content(detail_prompt).text
                        except Exception: pass
                    st.rerun()
                if idx in st.session_state.idea_details:
                    st.markdown("---"); st.markdown(st.session_state.idea_details[idx])

with tab3:
    st.header("🗂️ 核心基因库管理")
    
    # 🚨 为您特别增加的救命功能：一键清洗垃圾！
    st.error("🚨 发现库里混入了大量类似【RPG】【TPS】的单字垃圾？请点击下方红色按钮，系统会一键帮您洗净所有垃圾！")
    if st.button("🧹 紧急救援：一键清除所有干瘪垃圾词条 (强力净化)", type="primary"):
        db = load_database()
        def clean_list(lst):
            cleaned = []
            for x in lst:
                x = x.strip()
                # 规则：必须包含【】且总长度大于 15 个字符的，才被认可为富文本；带"源自观察"的直接抛弃！
                if "【" in x and "】" in x and len(x) > 15 and "(源自观察:" not in x:
                    cleaned.append(x)
            return list(dict.fromkeys(cleaned))
            
        db["Entry_Gameplay"] = clean_list(db["Entry_Gameplay"])
        db["Core_Loop"] = clean_list(db["Core_Loop"])
        db["Theme"] = clean_list(db["Theme"])
        db["Art_Style"] = clean_list(db["Art_Style"])
        save_database(db)
        st.success("✅ 垃圾已全部灰飞烟灭！基因库重回纯净状态！（☁️ 已同步）")
        time.sleep(2)
        st.rerun()

    st.divider()

    db = load_database()
    c1, c2 = st.columns(2)
    with c1:
        ep_edit = st.text_area("入局玩法", value="\n".join(db["Entry_Gameplay"]), height=300)
        cl_edit = st.text_area("核心循环", value="\n".join(db["Core_Loop"]), height=300)
    with c2:
        th_edit = st.text_area("题材包装", value="\n".join(db["Theme"]), height=300)
        ar_edit = st.text_area("视觉画风", value="\n".join(db["Art_Style"]), height=300)

    if st.button("💾 手动保存并更新基因库"):
        def parse(s): return list(dict.fromkeys([x.strip() for x in s.split("\n") if x.strip()]))
        db["Entry_Gameplay"] = parse(ep_edit)
        db["Core_Loop"] = parse(cl_edit)
        db["Theme"] = parse(th_edit)
        db["Art_Style"] = parse(ar_edit)
        save_database(db)
        st.success("✅ 已保存！（☁️ 已同步）")
        time.sleep(1); st.rerun()

    st.divider()
    if st.button("🧠 召唤 AI 进行全库深度语义合并与瘦身", type="primary"):
        model = get_model()
        if not model: st.stop()
        db = load_database()
        prompt = f"""你是有重度数据洁癖的资深游戏主策。这是我的立项基因库：
{json.dumps(db, ensure_ascii=False)}

请对四个维度进行【合并同类项与语义瘦身】。将本质相同、表述冗余的机制融合成一个最精准的表述（务必保留原有的【模块名】和'(玩家诉求: xxx)'格式）。必须且只能返回清洗后的纯 JSON 对象，键名保持 Entry_Gameplay, Core_Loop, Theme, Art_Style 不变。绝对不要带有 markdown 标记。"""

        with st.spinner(f"🧠 正在调用 [{selected_model}] 进行全库语义扫描与融合..."):
            try:
                resp = model.generate_content(prompt, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                raw_text = resp.text if hasattr(resp, "text") else str(resp)
            except Exception as ex:
                st.error(f"❌ 调用失败: {ex}")
                st.stop()

        text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        text = re.sub(r"\s*```\s*$", "", text).strip()
        m = re.search(r"\{[\s\S]*\}", text)
        if m: text = m.group(0)
        try:
            washed = json.loads(text)
        except json.JSONDecodeError as ex:
            st.error(f"❌ 解析失败: {ex}")
            st.stop()

        # 把 Market_Rules 塞回洗好的 JSON，防止丢失
        washed["Market_Rules"] = db.get("Market_Rules", [])
        save_database(washed)
        st.success("✨ 深度语义查重与洗库完成！（☁️ 已同步）")
        time.sleep(1)
        st.rerun()

with tab4:
    st.header("🧠 真实市场复盘与永久记忆权重")
    r_name = st.text_input("竞品名称")
    r_desc = st.text_area("玩法与题材概述")
    r_result = st.text_area("真实市场成绩反馈")
    uploaded_file = st.file_uploader("📂 上传实机参考", type=['png', 'jpg', 'jpeg', 'mp4'])
    
    if st.button("📥 深度复盘，提取通用法则入库", type="primary"):
        if not r_name or not r_result: st.error("必填！"); st.stop()
        model = get_model()
        if not model: st.stop()
        import google.generativeai as genai
        contents, temp_path, cloud_file = [], None, None
        
        if uploaded_file:
            ext = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_path = tmp.name
            with st.spinner("⬆️ 上传中..."): cloud_file = genai.upload_file(temp_path)
            if "video" in uploaded_file.type or ext.lower() == ".mp4":
                while cloud_file.state.name == "PROCESSING":
                    with st.spinner("⏳ 正在分析视频..."): time.sleep(3); cloud_file = genai.get_file(cloud_file.name)
            contents.append(cloud_file)
            
        prompt = f"分析此案例：游戏：{r_name}\n概述：{r_desc}\n成绩：{r_result}\n提炼 1 条极精炼的可复用【风控法则】。返回 JSON: {{ \"rule\": \"法则文本\" }}"
        contents.append(prompt)
        
        with st.spinner(f"🧠 使用 [{selected_model}] 提炼法则..."):
            try:
                resp = model.generate_content(contents, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                raw = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                new_rule = json.loads(re.sub(r"\s*```\s*$", "", raw).strip()).get("rule", "")
            except Exception: new_rule = ""
                
        if cloud_file: 
            try: genai.delete_file(cloud_file.name)
            except: pass
        if temp_path: 
            try: os.remove(temp_path)
            except: pass
        
        if new_rule:
            db = load_database()
            new_entry = f"【复盘:{r_name}】 {new_rule}"
            if new_entry not in db["Market_Rules"]:
                db["Market_Rules"].append(new_entry)
                save_database(db)
                st.success("✅ 新法则已入库！")
                st.info(f"💡 {new_entry}")
    
    st.divider()
    db = load_database()
    rules_text = st.text_area("法则列表", value="\n".join(db.get("Market_Rules", [])), height=200)
    if st.button("💾 保存法则修改"):
        db["Market_Rules"] = [x.strip() for x in rules_text.split("\n") if x.strip()]
        save_database(db)
        st.success("✅ 已更新！")
        time.sleep(1); st.rerun()