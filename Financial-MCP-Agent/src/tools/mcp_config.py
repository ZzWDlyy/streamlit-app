"""
MCP服务器配置模块 - 包含连接A股MCP服务器的配置信息
"""

SERVER_CONFIGS = {
    "a_share_mcp_v2": {
        "transport": "streamable_http",
        # 这个 URL 将会被下面的 mcp_client.py 动态替换
        "url": "http://placeholder.url/will/be/replaced" 
    }
}