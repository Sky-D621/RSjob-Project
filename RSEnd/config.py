# 文件路径: RSEnd/config.py

# --- 文件路径配置 ---
RESULT_FOLDER = 'static/output'
HISTORY_INPUT_FOLDER = 'static/history_inputs'
TEMP_FOLDER = 'temp_uploads'

# --- 数据库连接配置 ---
# !! 请根据您自己的数据库设置修改这里的 password !!
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root', # 如果您的密码不是'root'，请修改这里
    'db': 'EndJob',
    'charset': 'utf8'
}