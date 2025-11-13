"""
金融分析智能体系统 - 核心工作流模块 (重构版)

本文件包含金融分析智能体系统的核心执行逻辑，被重构为一个可调用的异步函数，
以便于被不同的前端（如命令行、Streamlit界面）调用。

主要功能：
- 接收用户查询
- 构建并执行LangGraph多智能体工作流
- 返回结构化的分析结果
"""

# ============================================================================
# 导入必要的模块和依赖
# ============================================================================

import os
import sys
import logging
import re
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

# 确保在项目根目录运行，以便正确导入模块
# 如果你的目录结构是 project/main.py, project/agents/...
# 那么这个路径设置是正确的
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 设置环境变量来抑制transformers和其他库的冗余输出
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# 抑制部分库的日志输出
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("accelerate").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# 项目内部模块导入
# 注意：请确保这些模块路径是正确的
try:
    from utils.logging_config import setup_logger, SUCCESS_ICON, ERROR_ICON
    from utils.state_definition import AgentState
    from utils.execution_logger import initialize_execution_logger, finalize_execution_logger
    from agents.summary_agent import summary_agent
    from agents.value_agent import value_agent
    from agents.technical_agent import technical_agent
    from agents.fundamental_agent import fundamental_agent
    from agents.news_agent import news_agent
except ImportError as e:
    print(f"模块导入错误: {e}")
    print("请确保你在项目的根目录下运行，并且所有依赖都已安装。")
    sys.exit(1)

# 加载环境变量
load_dotenv(override=True)

# 设置日志记录器
logger = setup_logger(__name__)


# ============================================================================
# 核心工作流函数
# ============================================================================

async def run_analysis_workflow(user_query: str, status_callback=None):
    """
    执行金融分析工作流的核心逻辑。

    :param user_query: 用户的查询字符串。
    :param status_callback: 一个可选的回调函数，用于向UI发送状态更新。
    :return: 一个包含最终报告和路径的字典。
    """
    
    def update_status(message: str):
        """安全地调用状态回调函数"""
        logger.info(message)
        if status_callback:
            try:
                status_callback(message)
            except Exception as e:
                logger.warning(f"调用状态回调函数时出错: {e}")

    execution_logger = initialize_execution_logger()
    update_status(f"✅ 执行日志系统已初始化，目录: {execution_logger.execution_dir}")

    try:
        # 1. 定义LangGraph工作流
        workflow = StateGraph(AgentState)
        workflow.add_node("start_node", lambda state: state)
        workflow.add_node("fundamental_analyst", fundamental_agent)
        workflow.add_node("technical_analyst", technical_agent)
        workflow.add_node("value_analyst", value_agent)
        workflow.add_node("news_analyst", news_agent)
        workflow.add_node("summarizer", summary_agent)
        workflow.set_entry_point("start_node")
        workflow.add_edge("start_node", "fundamental_analyst")
        workflow.add_edge("start_node", "technical_analyst")
        workflow.add_edge("start_node", "value_analyst")
        workflow.add_edge("start_node", "news_analyst")
        workflow.add_edge("fundamental_analyst", "summarizer")
        workflow.add_edge("technical_analyst", "summarizer")
        workflow.add_edge("value_analyst", "summarizer")
        workflow.add_edge("news_analyst", "summarizer")
        workflow.add_edge("summarizer", END)
        app = workflow.compile()
        update_status("✅ LangGraph 工作流构建完成。")

        # 2. 自然语言处理和股票信息提取
        # (将原始文件中的 extract_stock_info 函数完整地复制到这里)
        def extract_stock_info(query):
            """精确提取股票代码和公司名称"""
            stock_code = None
            company_name = None
            patterns = [
                r'请帮我分析一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]',
                r'分析一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]',
                r'分析\s*([^（(]+?)\s*[（(](\d{5,6})[)）]',
                r'分析\s*[（(](\d{5,6})[)）]\s*([^）)]+)',
                r'帮我看看\s*[（(](\d{5,6})[)）]\s*([^）)]+?)(?:\s*这只|\s*这个)?\s*股票',
                r'我想了解一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]',
                r'帮我看看\s*([^（(]+?)\s*[（(](\d{5,6})[)）]',
                r'^([^（(]+?)\s*[（(](\d{5,6})[)）]'
            ]
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    if len(match.groups()) == 2:
                        if match.group(1).isdigit():
                            stock_code, company_name = match.group(1), match.group(2).strip()
                        else:
                            company_name, stock_code = match.group(1).strip(), match.group(2)
                        return company_name, stock_code
            
            # 如果没有匹配到带括号的组合，则分别匹配公司名和代码
            # 优先匹配代码
            code_match = re.search(r'\b(\d{5,6})\b', query)
            if code_match:
                stock_code = code_match.group(1)

            # 匹配公司名称 (更通用的模式)
            name_patterns = [
                r'分析(?:一下)?\s*([^0-9（）()\s]+)',
                r'([^0-9（）()\s]+)\s*(?:这只|这个|的)?\s*股票',
                r'(?:了解|看看|给我分析)一下\s*([^0-9（）()\s]+)',
                r'([^0-9（）()\s]+?)\s*的\s*(?:财务|估值|风险|价值|基本面)',
            ]
            for pattern in name_patterns:
                name_match = re.search(pattern, query)
                if name_match:
                    potential_name = name_match.group(1).strip()
                    # 避免匹配到 "股票" "价值" 等词
                    if len(potential_name) >= 2 and potential_name not in ["股票", "价值", "公司"]:
                         company_name = potential_name
                         break # 找到一个就停止

            if company_name:
                stop_words = ['的', '这个', '这只', '一下', '看看', '了解', '分析', '帮我', '我想', '给我']
                for word in stop_words:
                    company_name = company_name.replace(word, '').strip()
                if len(company_name) < 2: company_name = None

            return company_name, stock_code

        company_name, stock_code = extract_stock_info(user_query)
        update_status(f"🔎 从查询中提取到信息 - 公司: {company_name or '未识别'}, 代码: {stock_code or '未识别'}")

        # 3. 时间信息处理
        current_datetime = datetime.now()
        current_date_en = current_datetime.strftime("%Y-%m-%d")

        # 4. 准备初始状态数据
        initial_data = {
            "query": user_query,
            "current_date": current_date_en,
            "analysis_timestamp": current_datetime.isoformat()
        }
        if company_name:
            initial_data["company_name"] = company_name
        if stock_code:
            if stock_code.startswith('6'):
                initial_data["stock_code"] = f"sh.{stock_code}"
            elif stock_code.startswith(('0', '3')):
                initial_data["stock_code"] = f"sz.{stock_code}"
            else:
                initial_data["stock_code"] = stock_code
        
        if not company_name and not stock_code:
            raise ValueError("无法从您的查询中识别出有效的公司名称或股票代码，请提供更明确的信息。")

        initial_state = AgentState(messages=[], data=initial_data, metadata={})

        # 5. 执行工作流
        update_status("\n🚀 **开始执行分析任务...**")
        update_status("   - 📊 基本面分析 Agent 启动...")
        update_status("   - 📈 技术面分析 Agent 启动...")
        update_status("   - 💰 估值分析 Agent 启动...")
        update_status("   - 📰 新闻分析 Agent 启动...")
        update_status("\n*分析过程可能需要1-2分钟，请耐心等待...*")

        final_state = await app.ainvoke(initial_state)
        update_status("\n✅ **所有分析模块执行完毕！**")
        update_status("   - 🤖 总结 Agent 正在整合报告...")

        # 6. 结果处理和报告生成
        if final_state and final_state.get("data") and "final_report" in final_state["data"]:
            report_path = final_state['data'].get('report_path')
            execution_logger.log_final_report(final_state["data"]["final_report"], report_path)
            finalize_execution_logger(success=True)
            update_status(f"🎉 **报告生成成功！**")
            
            return {
                "success": True,
                "report": final_state["data"]["final_report"],
                "report_path": report_path,
                "log_dir": execution_logger.execution_dir
            }
        else:
            raise RuntimeError("工作流执行完毕，但未能生成最终报告。")

    except Exception as e:
        logger.error(f"工作流执行期间发生错误: {e}", exc_info=True)
        finalize_execution_logger(success=False, error=str(e))
        update_status(f"❌ **发生错误**: {e}")
        return {
            "success": False,
            "error": "工作流执行期间发生错误。",
            "details": str(e),
            "log_dir": execution_logger.execution_dir,
        }

# ============================================================================
# 程序入口点 (用于直接运行此文件进行测试)
# ============================================================================
async def cli_main():
    """保留原始的命令行交互功能，用于测试。"""
    print("金融分析智能体系统 - 命令行测试模式")
    user_query = input("💬 请输入您的分析需求: ")
    if not user_query.strip():
        print("输入不能为空！")
        return

    def cli_status_callback(message: str):
        """命令行版本的状态回调函数"""
        print(message.replace('**', '')) # 移除Markdown标记

    result = await run_analysis_workflow(user_query, cli_status_callback)

    if result["success"]:
        print("\n--- 最终分析报告 ---")
        print(result["report"])
        if result["report_path"]:
            print(f"\n报告已保存到: {result['report_path']}")
        print(f"执行日志已保存到: {result['log_dir']}")
    else:
        print(f"\n分析失败: {result['error']}")
        print(f"详情: {result['details']}")
        print(f"错误日志已保存到: {result['log_dir']}")

if __name__ == "__main__":
    # 如果直接运行此文件，则进入命令行测试模式
    # 要运行UI界面，请运行 `streamlit run app.py`
    try:
        asyncio.run(cli_main())
    except KeyboardInterrupt:
        print("\n程序已终止。")

