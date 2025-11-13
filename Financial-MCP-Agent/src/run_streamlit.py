import sys
import os
from streamlit.web import cli as stcli

if __name__ == '__main__':
    # 如果是打包后的环境
    if getattr(sys, 'frozen', False):
        # 设置工作目录为可执行文件所在目录
        os.chdir(os.path.dirname(sys.executable))
    
    # 获取 app.py 的路径
    if getattr(sys, 'frozen', False):
        app_path = os.path.join(sys._MEIPASS, 'app.py')
    else:
        app_path = 'app.py'
    
    # 启动 Streamlit
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
