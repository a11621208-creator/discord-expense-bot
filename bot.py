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
        raise ValueError("環境變數 GOOGLE_CREDS 未設定")
    
    info = json.loads(creds_json)
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name="記帳")
async def record(ctx, amount: int, *, description: str):
    try:
        client = get_gspread_client()
        sheet = client.open(SHEET_NAME).get_worksheet(0)
        
        now = datetime.datetime.now()
        month = now.month
        
        # 匹配類別
        target_category = "雜項費用"
        for kw, cat in KEYWORD_RULES.items():
            if kw.lower() in description.lower():
                target_category = cat
                break
        
        row = CATEGORY_MAP[target_category]
        col = get_month_col(month)
        
        # 讀取並更新金額
        current_cell = sheet.cell(row, col)
        current_val = int(current_cell.value) if current_cell.value else 0
        new_val = current_val + amount
        sheet.update_cell(row, col, new_val)
        
        # 更新備註 (填在金額右邊那一欄，即 Col + 1)
        detail_col = col + 1
        current_detail = sheet.cell(row, detail_col).value or ""
        timestamp = now.strftime("%m/%d %H:%M")
        new_detail = f"{current_detail}\n{timestamp}: {description} (${amount})" if current_detail else f"{timestamp}: {description} (${amount})"
        sheet.update_cell(row, detail_col, new_detail)

        await ctx.send(f"✅ **記帳成功！**\n📅 月份：{month}月\n📁 類別：{target_category}\n💰 金額：${amount}\n📝 內容：{description}")

    except Exception as e:
        await ctx.send(f"❌ 發生錯誤: {str(e)}")

bot.run(os.getenv('DISCORD_TOKEN'))
