import os
import json
import datetime
import gspread
from google.oauth2.service_account import Credentials
import discord
from discord.ext import commands

# --- 設定區 ---
SHEET_NAME = "2026損益表"

# 類別與列號對應
CATEGORY_MAP = {
    "核心教材收入": 7, "訂閱教材收入": 8, "入門方案收入": 9, "教練1v1 收入": 10,
    "Staking結算收益": 11, "軟體代理收入": 12, "其他營業收入": 13,
    "銷貨成本": 15, "活動成本": 16, "Staking結算虧損": 17, "其他營業成本": 18, "人事成本": 19,
    "人事費用(含獎金)": 23, "租賃費用(含官方Line/雲端…)": 24, "勞務費(Ex:外包工程師)": 25,
    "行銷費用(廣告/公關)": 26, "分潤獎金": 27, "雜項費用": 28
}

# 智慧匹配關鍵字
KEYWORD_RULES = {
    "教材": "核心教材收入", "訂閱": "訂閱教材收入", "入門": "入門方案收入", "教練": "教練1v1 收入",
    "staking": "Staking結算收益", "代理": "軟體代理收入",
    "成本": "銷貨成本", "活動": "活動成本", "虧損": "Staking結算虧損", "人事": "人事成本",
    "薪資": "人事費用(含獎金)", "獎金": "人事費用(含獎金)",
    "line": "租賃費用(含官方Line/雲端…)", "雲端": "租賃費用(含官方Line/雲端…)", "google": "租賃費用(含官方Line/雲端…)",
    "外包": "勞務費(Ex:外包工程師)", "工程師": "勞務費(Ex:外包工程師)",
    "廣告": "行銷費用(廣告/公關)", "行銷": "行銷費用(廣告/公關)", "公關": "行銷費用(廣告/公關)",
    "分潤": "分潤獎金"
}

def get_month_col(month):
    return 4 + (month - 1) * 3  # 1月=D(4), 2月=G(7), 3月=J(10)...

# --- 初始化 ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_gspread_client():
    # 從 Zeabur 環境變數讀取 JSON 字串
    creds_json = os.getenv('GOOGLE_CREDS')
    if not creds_json:
        raise ValueError("環境變
