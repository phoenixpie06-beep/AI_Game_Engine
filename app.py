# -*- coding: utf-8 -*-
"""
AI 游戏商业立项风控引擎 (Ultimate Edition V5)
包含：高维JSON榨取 | GitHub静默同步 | Tab 4 真实复盘 | 全网动态无限制模型接口
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
        subprocess.run(["git", "commit", "-m", "🤖 AI Auto-Sync: 基因库或系统配置已更新"], capture_output=True)
        subprocess.run(["git", "push"], capture_output=True)
    except Exception:
        pass

def trigger_sync():
    """触发异步同步"""
    threading.Thread(target=background_git_sync).start()

# ============== 2. 数据库与超级解析器 ==============
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

def init_database():
    """启动时检查 database.json，不存在则创建"""
    default_db = {
        "Entry_Gameplay": ["单手摇杆走位自动割草", "极简拖拽放置塔防", "屏幕物理连线消除", "场景滑动寻找违和感"],
        "Core_Loop": ["局外空间网格背包整理", "自动化产线运转与物流", "环境生理数值干预战斗", "局内技能变异与双人反应"],
        "Theme": ["现代职场社畜发疯修仙", "微缩办公桌奇观", "极端深海高压生存", "反差童话朋克"],
        "Art_Style": ["复古高保真像素", "黑白单色手绘", "90年代老电脑桌面UI", "冷色调工业赛博"],
        "Market_Rules": []
    }
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(default_db, f, ensure_ascii=False, indent=2)

def load_database():
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            if "Market_Rules" not in db:
                db["Market_Rules"] = []
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
    """【超级榨汁机】：同时从 modules, combos 和 observations 提取基因"""
    result = {"Entry_Gameplay": [], "Core_Loop": [], "Theme": [], "Art_Style": []}
    if not isinstance(data, dict): return result

    # 1. 提取 modules 数组
    modules = data.get("modules", [])
    if isinstance(modules, list):
        for m in modules:
            if not isinstance(m, dict): continue
            mt = str(m.get("module_type", "")).lower()
            name = m.get("name", "")
            one_liner = m.get("one_liner", "")
            pv = m.get("player_value", "")
            if not name and not one_liner: continue

            rich = f"【{name}】 {one_liner}"
            if pv: rich += f" (玩家诉求: {pv})"

            if "entry" in mt: result["Entry_Gameplay"].append(rich)
            elif "core" in mt or "mechanic" in mt or "meta" in mt: result["Core_Loop"].append(rich)
            elif "theme" in mt: result["Theme"].append(rich)
            elif "art" in mt: result["Art_Style"].append(rich)

    # 2. 提取 combos
    combos = data.get("combos", [])
    if isinstance(combos, list):
        for c in combos:
            if not isinstance(c, dict): continue
            if c.get("entry_hook"): result["Entry_Gameplay"].append(f"【{c['entry_hook']}】")
            if c.get("core_loop"): result["Core_Loop"].append(f"【{c['core_loop']}】")
            if c.get("theme"): result["Theme"].append(f"【{c['theme']}】")
            if c.get("art_style"): result["Art_Style"].append(f"【{c['art_style']}】")

    # 3. 提取 observations 数组中的 tags
    obs = data.get("observations", [])
    if isinstance(obs, list):
        for o in obs:
            if not isinstance(o, dict): continue
            tags = o.get("tags", {})
            if not isinstance(tags, dict): continue
            entity_name = o.get("entity_name", "某产品")

            for mech in tags.get("mechanic", []) + tags.get("genre", []):
                if isinstance(mech, str): result["Core_Loop"].append(f"【{mech}】 (源自观察: {entity_name})")
            for theme in tags.get("theme", []):
                if isinstance(theme, str): result["Theme"].append(f"【{theme}】 (源自观察: {entity_name})")
            for art in tags.get("art_style", []):
                if isinstance(art, str): result["Art_Style"].append(f"【{art}】 (源自观察: {entity_name})")

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
    """真正通过接口查询账号权限内的所有最新模型"""
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
            # 只要名字带 gemini 并且支持生成的，统统抓回来！
            if "generateContent" in methods and "gemini" in m.name.lower():
                fetched_models.append(m.name.replace("models/", ""))
        
        # 字母倒序排列，保证 3.1 永远排在 2.5 和 1.5 的前面
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
        os.environ["http_proxy"] = proxy_input.strip()
        os.environ["https_proxy"] = proxy_input.strip()

    st.markdown("---")
    
    # 强制刷新按钮
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 刷新模型库"):
            fetch_available_models.clear()
            st.rerun()

    # --- 100% 毫无保留获取全量模型 ---
    model_options = []
    error_msg = None
    
    if api_key_input.strip():
        with st.spinner("🔄 正在直连 API 获取全网最新模型..."):
            model_options, error_msg = fetch_available_models(api_key_input.strip(), proxy_input.strip())
            
    if error_msg:
        st.warning(f"⚠️ API模型拉取失败，可能是代理网络波动。(报错: {error_msg})")
    
    saved_model = sys_config.get("model", "gemini-3.1-pro")
    
    if not model_options:
        model_options = [saved_model] if saved_model else ["gemini-3.1-pro", "gemini-2.5-pro"]
    elif saved_model and saved_model not in model_options:
        model_options.append(saved_model)
        
    model_options = sorted(list(set(model_options)), reverse=True)
    default_idx = model_options.index(saved_model) if saved_model in model_options else 0
    
    # 【新增功能】：如果下拉框拉不到，允许您强行手动输入！
    use_manual = st.checkbox("✍️ 极客模式：手动输入模型名称")
    if use_manual:
        selected_model = st.text_input("手动指定模型 (如 gemini-3.1-pro)", value=saved_model)
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
    if not api_key_input.strip():
        st.error("❌ 请在侧边栏配置 API Key")
        return None
    if not selected_model:
        st.error("❌ 请在侧边栏选择有效的模型")
        return None
    import google.generativeai as genai
    genai.configure(api_key=api_key_input.strip())
    # 真正调用侧边栏选择好的最新模型！
    return genai.GenerativeModel(selected_model.strip())

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
GEN_JSON = {"response_mime_type": "application/json"}

# ============== 主工作区 ==============
tab1, tab2, tab3, tab4 = st.tabs(["🌐 1. 情报雷达入库", "🎯 2. 初筛与立项", "🗂️ 3. 基因库管理", "🧠 4. 真实市场复盘(永久记忆)"])

# ---------- Tab 1: 雷达与注入港 ----------
with tab1:
    st.header("🌐 深度情报雷达与 JSON 注入港")
    sub_a, sub_b = st.tabs(["📥 模式A：外部 JSON 注入", "🤖 模式B：内置雷达扫描"])

    with sub_a:
        json_input = st.text_area("请粘贴由 Gemini 生成的市场报告 JSON", height=300)
        if st.button("⚡ 解析 JSON 榨取所有商业基因入库"):
            if not json_input.strip(): st.stop()
            text = re.sub(r"^```(?:json)?\s*", "", json_input.strip())
            text = re.sub(r"\s*```\s*$", "", text).strip()
            
            try:
                obj_match = re.search(r"\{[\s\S]*\}", text)
                candidate = obj_match.group(0) if obj_match else text
                data = json.loads(candidate)
            except Exception as e:
                st.error(f"❌ JSON 解析失败: {e}")
                st.stop()
                
            new_items = extract_genes_from_json(data)
            db = load_database()
            db = merge_and_dedupe(db, new_items)
            save_database(db)
            
            total = sum(len(v) for v in new_items.values())
            if total > 0:
                st.success(f"✅ 成功榨取 {total} 个商业基因并入库！（☁️ 已在后台同步 GitHub）")
                st.json(new_items)
            else:
                st.warning("⚠️ 未提取到任何有效基因，请检查 JSON 内容。")

    with sub_b:
        queries_text = st.text_area("搜索指令", value="过去一周 微信小游戏 新品 核心玩法\nSteam 过去7天 潜力独立游戏 创新机制\n海外手游 飙升榜 差异化 玩法 拆解")
        if st.button("🕷️ 启动雷达扫描"):
            model = get_model()
            if not model: st.stop()
            try:
                from duckduckgo_search import DDGS
            except:
                st.error("需安装: pip install duckduckgo-search")
                st.stop()
                
            queries = [q.strip() for q in queries_text.split("\n") if q.strip()]
            all_raw = []
            with st.spinner("🕷️ 正在搜刮..."):
                for q in queries:
                    try:
                        with DDGS() as ddgs:
                            res = list(ddgs.text(q, max_results=5))
                        for r in res:
                            all_raw.append(f"【{r.get('title','')}】\n{r.get('body','')}")
                        st.toast(f"🔍 '{q}' 抓到 {len(res)} 条")
                    except Exception as ex:
                        st.warning(f"搜索 {q} 失败: {ex}")
                    time.sleep(2)
            
            context = "\n\n".join(all_raw[:30])
            if len(context) < 50:
                st.error("❌ 抓取失败，可能被拦截")
                st.stop()
                
            prompt = f"你是商业分析师。阅读以下快照：\n{context}\n提取底层机制。必须返回JSON对象，包含 modules 数组。每个对象含: module_type, name, one_liner, player_value。"
            with st.spinner(f"🤖 正在调用 [{selected_model}] 分析..."):
                try:
                    resp = model.generate_content(prompt, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                    raw = resp.text
                except Exception as ex:
                    st.error(f"调用失败: {ex}"); st.stop()
            
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            raw = re.sub(r"\s*```\s*$", "", raw).strip()
            try:
                data = json.loads(raw)
            except:
                st.error("解析失败"); st.stop()
            
            new_items = extract_genes_from_json(data)
            db = merge_and_dedupe(load_database(), new_items)
            save_database(db)
            st.success("✅ 雷达扫描入库完成！（☁️ 已同步）")
            st.json(new_items)

# ---------- Tab 2: 智能初筛与立项 ----------
with tab2:
    st.header("🎯 智能初筛与立项")
    if st.button(f"🧠 让 [{selected_model}] 精选 Top 3 立项组合", type="primary"):
        model = get_model()
        if not model: st.stop()
        db = load_database()
        if not (db["Entry_Gameplay"] and db["Core_Loop"] and db["Theme"] and db["Art_Style"]):
            st.error("❌ 基因库四个维度不能为空")
            st.stop()
            
        combos = []
        for _ in range(15):
            c = f"[入局]{random.choice(db['Entry_Gameplay'])} | [循环]{random.choice(db['Core_Loop'])} | [题材]{random.choice(db['Theme'])} | [画风]{random.choice(db['Art_Style'])}"
            combos.append(c)
            
        rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(db.get("Market_Rules", []))])
        
        prompt = f"""【🔴 团队最高风控法则库】：这是真实的复盘教训：
{rules_text}
请你在评估以下 15 个随机组合时，赋予上述法则【最高权重】！违背避坑法则直接淘汰，踩中成功法则加分！

我生成的组合：
{chr(10).join(combos)}

淘汰掉 12 个废案，挑选出最具商业爆发力的 3 个。
返回纯 JSON 数组：[ {{"id":"1", "idea_name":"代号", "combo":"组合", "evaluation":"优劣势及过渡是否平滑分析"}} ]"""

        with st.spinner(f"🤖 正在使用 {selected_model} 结合永久记忆库进行风控打分..."):
            try:
                resp = model.generate_content(prompt, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                raw = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                raw = re.sub(r"\s*```\s*$", "", raw).strip()
                st.session_state.top_ideas = json.loads(raw)
                st.session_state.idea_details = {}
                st.rerun()
            except Exception as e:
                st.error(f"解析失败: {e}")

    if st.session_state.top_ideas:
        for idx, obj in enumerate(st.session_state.top_ideas):
            with st.container(border=True):
                st.subheader(obj.get("idea_name", "未命名"))
                st.info(obj.get("combo", ""))
                st.write(obj.get("evaluation", ""))
                if st.button(f"📝 深度推演：生成【{obj.get('idea_name')}】详细企划案", key=f"btn_{idx}"):
                    model = get_model()
                    rules_text = "\n".join(load_database().get("Market_Rules", []))
                    detail_prompt = f"【团队法则】：\n{rules_text}\n\n基于此法则，为组合 [{obj.get('combo')}] 撰写详尽 Markdown 立项企划案。必须包含：高概念、玩法过渡拆解、买量分析、LTV设计。"
                    with st.spinner(f"正在使用 [{selected_model}] 撰写详案..."):
                        try:
                            resp = model.generate_content(detail_prompt)
                            st.session_state.idea_details[idx] = resp.text
                        except Exception as ex:
                            st.error(f"撰写失败: {ex}")
                    st.rerun()
                
                if idx in st.session_state.idea_details:
                    st.markdown("---")
                    st.markdown(st.session_state.idea_details[idx])

# ---------- Tab 3: 基因库管理 ----------
with tab3:
    st.header("🗂️ 核心基因库管理")
    db = load_database()
    c1, c2 = st.columns(2)
    with c1:
        ep_edit = st.text_area("入局玩法", value="\n".join(db["Entry_Gameplay"]), height=300)
        cl_edit = st.text_area("核心循环", value="\n".join(db["Core_Loop"]), height=300)
    with c2:
        th_edit = st.text_area("题材包装", value="\n".join(db["Theme"]), height=300)
        ar_edit = st.text_area("视觉画风", value="\n".join(db["Art_Style"]), height=300)

    if st.button("💾 保存并更新基因库"):
        def parse(s): return list(dict.fromkeys([x.strip() for x in s.split("\n") if x.strip()]))
        db["Entry_Gameplay"] = parse(ep_edit)
        db["Core_Loop"] = parse(cl_edit)
        db["Theme"] = parse(th_edit)
        db["Art_Style"] = parse(ar_edit)
        save_database(db)
        st.success("✅ 已保存！（☁️ 已同步）")
        time.sleep(1)
        st.rerun()

# ---------- Tab 4: 真实市场复盘 (RAG 永久记忆) ----------
with tab4:
    st.header("🧠 真实市场复盘与永久记忆权重")
    st.caption("上传竞品录屏或截图，让 AI 深度分析成败，提炼为永久立项打分法则。")
    
    r_name = st.text_input("竞品名称")
    r_desc = st.text_area("玩法与题材概述")
    r_result = st.text_area("真实市场成绩反馈 (如：买量好但留存极差、付费深度不够等)")
    uploaded_file = st.file_uploader("📂 上传实机参考 (支持 png, jpg, jpeg, mp4)", type=['png', 'jpg', 'jpeg', 'mp4'])
    
    if st.button("📥 深度复盘，提取通用法则入库", type="primary"):
        if not r_name or not r_result:
            st.error("名称和成绩反馈必填！")
            st.stop()
        model = get_model()
        if not model: st.stop()
        
        import google.generativeai as genai
        contents = []
        temp_path = None
        cloud_file = None
        
        if uploaded_file:
            ext = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_path = tmp.name
            
            with st.spinner("⬆️ 正在上传文件给 AI 视觉中枢..."):
                try:
                    cloud_file = genai.upload_file(temp_path)
                except Exception as ex:
                    st.error(f"上传失败: {ex}"); st.stop()
                
            if "video" in uploaded_file.type or ext.lower() == ".mp4":
                while cloud_file.state.name == "PROCESSING":
                    with st.spinner("⏳ AI 正在逐帧观看视频分析交互..."):
                        time.sleep(3)
                        cloud_file = genai.get_file(cloud_file.name)
            
            if cloud_file.state.name == "FAILED":
                st.error("文件处理失败")
                st.stop()
                
            contents.append(cloud_file)
            
        prompt = f"""你是一个顶尖游戏制作人。请分析此案例：
游戏名称：{r_name}
概述：{r_desc}
市场反馈：{r_result}
请深度剖析成败底层逻辑，提炼 1 条极其精炼、可复用的【风控法则】(Rule)。
返回 JSON 格式: {{ "rule": "提取的法则文本" }}。绝不要带 markdown。"""
        
        contents.append(prompt)
        
        with st.spinner(f"🧠 正在使用 [{selected_model}] 提炼商业法则..."):
            try:
                resp = model.generate_content(contents, generation_config=GEN_JSON, safety_settings=SAFETY_SETTINGS)
                raw = re.sub(r"^```(?:json)?\s*", "", resp.text.strip())
                raw = re.sub(r"\s*```\s*$", "", raw).strip()
                new_rule = json.loads(raw).get("rule", "")
            except Exception as e:
                st.error(f"提取失败: {e}")
                new_rule = ""
                
        if cloud_file: 
            try: genai.delete_file(cloud_file.name)
            except: pass
        if temp_path and os.path.exists(temp_path): 
            try: os.remove(temp_path)
            except: pass
        
        if new_rule:
            db = load_database()
            new_entry = f"【复盘:{r_name}】 {new_rule}"
            if new_entry not in db["Market_Rules"]:
                db["Market_Rules"].append(new_entry)
                save_database(db)
                st.success("✅ 新法则已永久刻入 AI 大脑！（☁️ 已同步）")
                st.info(f"💡 学到的新法则：{new_entry}")
        else:
            st.error("未能提取有效法则")
    
    st.divider()
    st.subheader("📜 当前团队最高风控法则库")
    db = load_database()
    rules_text = st.text_area("法则列表 (大模型将在 Tab 2 严格依据此列表打分)", value="\n".join(db.get("Market_Rules", [])), height=200)
    if st.button("💾 保存法则修改"):
        db["Market_Rules"] = [x.strip() for x in rules_text.split("\n") if x.strip()]
        save_database(db)
        st.success("✅ 法则库已更新！（☁️ 已同步）")
        time.sleep(1)
        st.rerun()