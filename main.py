import os
import json
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import discord
from discord.ext import commands

# --- 設定區 ---
SHEET_NAME = "2026損益表"

CATEGORY_MAP = {
    "核心教材收入": 7, "訂閱教材收入": 8, "入門方案收入": 9, "教練1v1 收入": 10,
    "Staking結算收益": 11, "軟體代理收入": 12, "其他營業收入": 13,
    "銷貨成本": 15, "活動成本": 16, "Staking結算虧損": 17, "其他營業成本": 18, "人事成本": 19,
    "人事費用(含獎金)": 23, "租賃費用(含官方Line/雲端…)": 24, "勞務費(Ex:外包工程師)": 25,
    "行銷費用(廣告/公關)": 26, "分潤獎金": 27, "雜項費用": 28
}

KEYWORD_RULES = {
    "教材": "核心教材收入", "訂閱": "訂閱教材收入", "入門": "入門方案收入", "教練": "教練1v1 收入",
    "staking": "Staking結算收益", "代理": "軟體代理收入",
    "成本": "銷貨成本", "活動": "活動成本", "虧損": "Staking結算虧損", "人事": "人事成本",
    "薪資": "人事費用(含獎金)", "獎金": "人事費用(含獎金)", "薪水": "人事費用(含獎金)",
    "line": "租賃費用(含官方Line/雲端…)", "雲端": "租賃費用(含官方Line/雲端…)", "google": "租賃費用(含官方Line/雲端…)",
    "外包": "勞務費(Ex:外包工程師)", "工程師": "勞務費(Ex:外包工程師)",
    "廣告": "行銷費用(廣告/公關)", "行銷": "行銷費用(廣告/公關)", "公關": "行銷費用(廣告/公關)",
    "分潤": "分潤獎金"
}

def get_month_col(month):
    return 4 + (month - 1) * 3

# --- 初始化 ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_gspread_client():
    creds_json = os.getenv('GOOGLE_CREDS')
    if not creds_json:
        raise ValueError("環境變數 GOOGLE_CREDS 未設定")
    info = json.loads(creds_json)
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

@bot.event
async def on_ready():
    print(f'✅ 記帳機器人已就緒: {bot.user}')

@bot.command(name="記帳")
async def record(ctx, amount: int, *, description: str):
    try:
        client = get_gspread_client()
        sheet = client.open(SHEET_NAME).get_worksheet(0)
        
        now = datetime.datetime.now()
        month = now.month
        
        # 1. 匹配類別
        target_category = "雜項費用"
        for kw, cat in KEYWORD_RULES.items():
            if kw.lower() in description.lower():
                target_category = cat
                break
        
        row = CATEGORY_MAP[target_category]
        col = get_month_col(month)
        
        # 2. 獲取儲存格資訊 (包含數值與附註)
        cell_data = sheet.cell(row, col)
        raw_value = cell_data.value
        
        # --- 終極數字過濾邏輯 ---
        if raw_value:
            # 使用正則表達式只留下數字，排除逗號、空格、貨幣符號等
            clean_value = re.sub(r'[^\d]', '', str(raw_value))
            current_val = int(clean_value) if clean_value else 0
        else:
            current_val = 0
            
        new_val = current_val + amount
        
        # 3. 更新 Google Sheets
        sheet.update_cell(row, col, new_val)
        
        # 4. 加入「小三角」附註 (Note)
        existing_note = cell_data.note or ""
        timestamp = now.strftime("%m/%d %H:%M")
        new_note_content = f"{existing_note}\n{timestamp}: {description} (${amount:,})".strip()
        sheet.update_note(row, col, new_note_content)

        await ctx.send(f"✅ **入帳成功！**\n📁 類別：`{target_category}`\n💰 金額：`${amount:,}`\n📅 月份：{month}月\n📝 明細已加入儲存格附註")

    except Exception as e:
        # 輸出更詳細的錯誤資訊方便 debug
        await ctx.send(f"❌ 記帳失敗！\n錯誤原因：`{str(e)}`")

bot.run(os.getenv('DISCORD_TOKEN'))
