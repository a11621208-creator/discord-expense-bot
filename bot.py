import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GAS_URL = os.getenv('GAS_URL')

# 完整的分類對應表 - 根據你的 Sheet 結構
CLASSIFICATION_MAPPING = {
    # 收入類別 (A7~A13)
    '核心教材': 'A7',  # 核心教材收入
    '教材': 'A7',
    '課程': 'A7',
    '線上課程': 'A7',
    
    '訂閱': 'A8',  # 訂閱教材收入
    '訂閱教材': 'A8',
    
    '入門': 'A9',  # 入門方案收入
    '入門方案': 'A9',
    
    '教練': 'A10',  # 教練1v1 收入
    '1v1': 'A10',
    '一對一': 'A10',
    
    'staking': 'A11',  # Staking結算收益
    '結算收益': 'A11',
    
    '軟體': 'A12',  # 軟體代理收入
    '代理': 'A12',
    
    '其他營業': 'A13',  # 其他營業收入
    
    # 成本類別 (A15~A19)
    '銷貨成本': 'A15',
    '進貨': 'A15',
    '原料': 'A15',
    '材料': 'A15',
    
    '活動成本': 'A16',
    '活動': 'A16',
    '會議': 'A16',
    
    '虧損': 'A17',  # Staking結算虧損
    
    '營業成本': 'A18',  # 其他營業成本
    
    '人事成本': 'A19',
    '薪資': 'A19',
    '工資': 'A19',
    
    # 支出類別 (A23~A28)
    '人事費用': 'A23',
    '獎金': 'A23',
    '薪水': 'A23',
    '工資': 'A23',
    
    '租賃費用': 'A24',
    '租金': 'A24',
    '辦公室': 'A24',
    '雲端': 'A24',
    'line': 'A24',
    
    '勞務費': 'A25',
    '外包': 'A25',
    '工程師': 'A25',
    '承包': 'A25',
    
    '行銷費用': 'A26',
    '廣告': 'A26',
    '公關': 'A26',
    '宣傳': 'A26',
    
    '分潤': 'A27',
    '分潤獎金': 'A27',
    
    '雜項': 'A28',
    '其他': 'A28',
    '雜項費用': 'A28',
}

def classify_item(item_name):
    """根據項目名稱自動分類"""
    item_lower = item_name.lower()
    
    # 精確匹配
    if item_name in CLASSIFICATION_MAPPING:
        return CLASSIFICATION_MAPPING[item_name]
    
    # 關鍵字匹配（優先匹配較長的關鍵字）
    matches = []
    for keyword, category in CLASSIFICATION_MAPPING.items():
        if keyword.lower() in item_lower:
            matches.append((len(keyword), category))
    
    if matches:
        # 返回最長匹配的分類（更精確）
        matches.sort(reverse=True)
        return matches[0][1]
    
    # 預設分類為雜項費用
    return 'A28'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} 已連接到 Discord')

@bot.command(name='記帳')
async def record_expense(ctx, amount: float, *, description: str):
    """記錄支出或收入
    用法: !記帳 100 咖啡
         !記帳 -500 核心教材收入
    """
    try:
        # 自動分類
        category = classify_item(description)
        
        # 判斷是收入還是支出
        # 收入類別 (A7~A13) 和成本類別 (A15~A19) 用負數表示
        if category in ['A7', 'A8', 'A9', 'A10', 'A11', 'A12', 'A13']:
            item_type = 'income'
            actual_amount = abs(amount)
        elif category in ['A15', 'A16', 'A17', 'A18', 'A19']:
            item_type = 'cost'
            actual_amount = abs(amount)
        else:
            item_type = 'expense'
            actual_amount = abs(amount)
        
        # 準備數據
        data = {
            'action': 'record',
            'type': item_type,
            'amount': actual_amount,
            'description': description,
            'category': category,
            'date': datetime.now().isoformat()
        }
        
        # 發送到 GAS
        response = requests.post(GAS_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                await ctx.send(f'✅ 已記錄：{description} - ${actual_amount}\n分類：{category}')
            else:
                await ctx.send(f'❌ 記錄失敗：{result.get("error", "未知錯誤")}')
        else:
            await ctx.send(f'❌ 無法連接到 Google Sheet：{response.status_code}')
    
    except Exception as e:
        await ctx.send(f'❌ 發生錯誤：{str(e)}')

@bot.command(name='報告')
async def get_report(ctx):
    """獲取本月財務報告"""
    try:
        data = {
            'action': 'report',
            'date': datetime.now().isoformat()
        }
        
        response = requests.post(GAS_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                report = result.get('report', '無數據')
                await ctx.send(f'📊 本月報告：\n{report}')
            else:
                await ctx.send(f'❌ 無法獲取報告：{result.get("error", "未知錯誤")}')
        else:
            await ctx.send(f'❌ 無法連接到 Google Sheet')
    
    except Exception as e:
        await ctx.send(f'❌ 發生錯誤：{str(e)}')

bot.run(DISCORD_TOKEN)
