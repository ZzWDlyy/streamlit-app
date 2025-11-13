# app.py (修正版)

import streamlit as st
import asyncio
import time
import os
from collections import deque
from main_refactored import run_analysis_workflow

# --- 页面配置 ---
st.set_page_config(
    page_title="金融分析智能体系统",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- 页面样式 (保持不变) ---
st.markdown("""
<style>
    .stButton>button {
        font-size: 1.1rem;
        font-weight: bold;
    }
    .stTextInput>div>div>input {
        font-size: 1.1rem;
    }
    .report-container {
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 1.5rem;
        background-color: #f6f8fa;
        min-height: 500px;
    }
    .status-container {
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 1rem;
        background-color: #ffffff;
        min-height: 500px;
    }
</style>
""", unsafe_allow_html=True)


# --- 初始化 Session State (保持不变) ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'status_messages' not in st.session_state:
    st.session_state.status_messages = deque(maxlen=100)
if 'result' not in st.session_state:
    st.session_state.result = None


# --- 页面标题和介绍 (保持不变) ---
st.title("🏦 金融分析智能体系统")
st.markdown("<sub>*Financial Analysis AI Agent System*</sub>", unsafe_allow_html=True)
st.write("")

with st.expander("ℹ️ 系统介绍与使用说明", expanded=True):
    st.markdown(
        """
        本系统利用多智能体（Multi-Agent）协同工作，对A股上市公司进行全面、深入的分析。
        您只需输入公司名称或股票代码，系统即可自动执行：
        - **📊 基本面分析**: 分析财务状况、盈利能力、行业地位。
        - **📈 技术面分析**: 解读价格趋势、交易量、关键技术指标。
        - **💰 估值分析**: 评估市盈率（PE）、市净率（PB）等估值水平。
        - **📰 新闻分析**: 洞察近期新闻情感倾向及潜在风险。
        
        最终，所有分析结果将被汇总成一份综合性的投资分析报告。
        """
    )
    st.info("💡 **使用提示**: 为获得最精确的分析结果，建议使用 **公司名称 + 股票代码** 的格式，例如：`分析贵州茅台(600519)`。")


# --- 用户输入区域 (保持不变) ---
st.write("")
user_query = st.text_input(
    "**请输入您的分析需求：**",
    placeholder="例如：分析宁德时代，或者 603871 这个股票怎么样？",
    key="query_input",
    disabled=st.session_state.running
)

analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True, disabled=st.session_state.running)


# --- 分析逻辑和结果展示 ---
if analyze_button and user_query:
    st.session_state.running = True
    st.session_state.status_messages.clear()
    st.session_state.result = None
    st.rerun()

if st.session_state.running:
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("⚙️ 分析进程")
        with st.container(height=520, border=False):
            status_placeholder = st.empty()
            
            def status_callback(message: str):
                st.session_state.status_messages.append(f"`{time.strftime('%H:%M:%S')}` {message}")
                status_text = "\n\n".join(st.session_state.status_messages)
                status_placeholder.markdown(status_text)
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run_analysis_workflow(user_query, status_callback))
                st.session_state.result = result
                st.session_state.running = False
                st.rerun()
            except Exception as e:
                st.session_state.result = {"success": False, "error": "应用发生严重错误", "details": str(e)}
                st.session_state.running = False
                st.rerun()
    with col2:
        st.subheader("📄 分析报告")
        with st.spinner("⏳ 智能体正在工作中，报告生成中..."):
            st.markdown('<div class="report-container">等待分析结果...</div>', unsafe_allow_html=True)


# --- 显示最终结果 ---
if st.session_state.result:
    result = st.session_state.result
    
    # 无论成功或失败，都先显示失败信息（如果存在）
    if not result.get("success"):
        st.error(f"**分析失败**: {result.get('error', '未知错误')}", icon="🚨")
        st.error(f"**详细信息**: {result.get('details', '无')}")
        if result.get('log_dir'):
            st.info(f"错误日志已保存在: `{result.get('log_dir')}`")
    
    # 如果成功，则显示完整的双栏布局
    else:
        st.success(f"**分析成功！** 报告已生成。日志保存在: `{result.get('log_dir')}`", icon="🎉")
        
        # ***** 关键修复 *****
        # 在这个代码块内定义 col1 和 col2
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.subheader("⚙️ 分析进程")
            with st.container(height=520, border=False):
                status_text = "\n\n".join(st.session_state.status_messages)
                st.markdown(status_text)
        
        with col2:
            st.subheader("📄 分析报告")
            report_text = result.get("report", "报告内容为空。")
            with st.container(height=520, border=False):
                st.markdown(report_text)
        
        # 添加下载按钮
        if result.get("report_path"):
            try:
                with open(result["report_path"], "r", encoding='utf-8') as f:
                    report_content = f.read()
                st.download_button(
                    label="📥 下载Markdown报告",
                    data=report_content,
                    file_name=os.path.basename(result["report_path"]),
                    mime="text/markdown",
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"无法读取报告文件进行下载: {e}")

