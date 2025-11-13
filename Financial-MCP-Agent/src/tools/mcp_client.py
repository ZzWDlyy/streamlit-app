from langchain_mcp_adapters.client import MultiServerMCPClient
from utils.logging_config import setup_logger, SUCCESS_ICON, ERROR_ICON, WAIT_ICON
from tools.mcp_config import SERVER_CONFIGS
import asyncio  # 异步操作所需，如get_tools
import json
import streamlit as st

logger = setup_logger(__name__)

_mcp_client_instance = None
_mcp_tools = None


def print_tool_details(tools):
    """打印工具的详细信息，用于调试"""
    logger.info(f"{SUCCESS_ICON} 工具详细信息:")
    for i, tool in enumerate(tools, 1):
        logger.info(f"  {i}. 工具名称: {tool.name}")
        logger.info(f"     描述: {tool.description}")

        # 打印其他可能的属性
        for attr in ['input_schema', 'parameters', 'schema']:
            if hasattr(tool, attr):
                attr_value = getattr(tool, attr)
                if attr_value:
                    logger.info(f"     {attr}: {attr_value}")

        logger.info(f"     工具类型: {type(tool)}")
        # logger.info(f"     所有属性: {dir(tool)}")
        logger.info("     " + "-" * 50)


async def get_mcp_tools():
    """
    初始化MultiServerMCPClient，并从云端的 a_share_mcp_v2 服务器获取工具。
    """
    global _mcp_client_instance, _mcp_tools

    if _mcp_tools is not None:
        logger.info(f"{SUCCESS_ICON} Returning cached MCP tools.")
        return _mcp_tools

    # --- 关键修改：动态配置服务器 URL ---
    try:
        # 1. 从 Streamlit Secrets 获取服务器的真实 URL
        mcp_server_url = st.secrets["mcp_server_url"]
        if not mcp_server_url:
            raise ValueError("URL is empty.")
    except (KeyError, ValueError):
        logger.error(f"{ERROR_ICON} 'mcp_server_url' not found or is empty in Streamlit Secrets!")
        _mcp_tools = []
        return []

    # 2. 复制并更新配置
    # 创建一个配置的深拷贝以避免修改原始导入的字典
    import copy
    current_configs = copy.deepcopy(SERVER_CONFIGS)
    current_configs["a_share_mcp_v2"]["url"] = mcp_server_url

    logger.info(f"{WAIT_ICON} Initializing MultiServerMCPClient with remote config: {current_configs}")
    # --- 修改结束 ---

    try:
        # 3. 使用更新后的配置初始化客户端
        _mcp_client_instance = MultiServerMCPClient(current_configs)

        logger.info(f"{WAIT_ICON} Fetching tools from MCP server '{list(current_configs.keys())[0]}' via HTTP...")
        loaded_tools = await _mcp_client_instance.get_tools()

        if not loaded_tools:
            logger.warning(f"{ERROR_ICON} No tools loaded from MCP server. Check server logs and URL.")
            _mcp_tools = []
            return []

        _mcp_tools = loaded_tools
        logger.info(f"{SUCCESS_ICON} Successfully loaded {len(_mcp_tools)} tools via HTTP.")
        return _mcp_tools

    except Exception as e:
        logger.error(f"{ERROR_ICON} Failed to initialize MCP client or load tools via HTTP: {e}", exc_info=True)
        _mcp_tools = []
        return []


async def close_mcp_client_sessions():
    """
    关闭MultiServerMCPClient管理的任何开放会话。
    如果必要，应在应用程序关闭时调用此函数。
    """
    global _mcp_client_instance
    if _mcp_client_instance:
        logger.info(f"{WAIT_ICON} Closing MCP client sessions...")
        try:
            logger.info(
                f"{SUCCESS_ICON} MCP client sessions (if any were persistently open) assumed closed or managed by library.")
            _mcp_client_instance = None   # 允许重新初始化
            global _mcp_tools
            _mcp_tools = None
        except Exception as e:
            logger.error(
                f"{ERROR_ICON} Error during MCP client session cleanup: {e}", exc_info=True)
    else:
        logger.info("MCP client was not initialized, no sessions to close.")


# 测试此模块的示例（可选，用于直接执行）
async def _main_test_mcp_client():
    logger.info("--- Testing MCP Client Tool Loading ---")
    tools = await get_mcp_tools()
    if tools:
        print(f"Successfully loaded {len(tools)} tools:")
        for tool in tools:
            print(
                f"- Name: {tool.name}")

        # 测试一个简单的工具调用（如果有合适的工具）
        if tools:
            logger.info("--- Testing Tool Call ---")
            # 尝试调用第一个工具（需要根据实际工具调整参数）
            first_tool = tools[0]
            logger.info(f"尝试调用工具: {first_tool.name}")

            # 这里需要根据实际的工具参数schema来构造测试参数
            # 暂时跳过实际调用，只是展示结构
            logger.info("工具调用测试跳过（需要实际参数）")
    else:
        print("Failed to load tools or no tools found.")

    # 测试关闭（如果适用）
    await close_mcp_client_sessions()
    logger.info("--- MCP Client Test Complete ---")

if __name__ == '__main__':
    # 这允许直接运行测试，例如：python -m src.tools.mcp_client
    # 确保您的环境已设置（例如，'uv'命令可用）。
    # E:\github\a_share_mcp的a_share_mcp服务器应该准备好运行。

    # 如果尚未配置，为测试运行设置基本日志记录
    if not logger.hasHandlers():
        import logging
        logging.basicConfig(level=logging.INFO)
        logger.info("Basic logging configured for test run.")

    asyncio.run(_main_test_mcp_client())
