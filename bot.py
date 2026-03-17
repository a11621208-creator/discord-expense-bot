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

# 分類對應表 - 根據用戶提供的項目清單
CLASSIFICATION_MAPPING = {
    # 收入項目 (A15~A19)
    '核心教材收入': '教材收入',
    '教材': '教材收入',
    '課程': '教材收入',
    '線上課程': '教材收入',
    
    # 成本項目 (A23~A28)
    '銷貨成本': '成本',
    '成本': '成本',
    '進貨': '成本',
    '原料': '成本',
    '材料': '成本',
    
    # 支出項目 (A7~A13)
    '咖啡': '食物',
    '食物': '食物',
    '餐飲': '食物',
    '午餐': '食物',
    '晚餐': '食物',
    '飲料': '食物',
    '便當': '食物',
    
    '交通': '交通',
    '車費': '交通',
    '油錢': '交通',
    '停車': '交通',
    '計程車': '交通',
    
    '辦公用品': '辦公用品',
    '文具': '辦公用品',
    '紙張': '辦公用品',
    '筆': '辦公用品',
    
    '電話費': '通訊費',
    '網路費': '通訊費',
    '通訊': '通訊費',
    '手機': '通訊費',
    
    '房租': '租金',
    '租金': '租金',
    '辦公室': '租金',
    
    '水電': '水電費',
    '電費': '水電費',
    '瓦斯': '水電費',
    '水費': '水電費',
    
    '保險': '保險費',
    '保險費': '保險費',
}

def classify_item(item_name):
    """根據項目名稱自動分類"""
    item_lower = item_name.lower()
    
    # 精確匹配
    if item_name in CLASSIFICATION_MAPPING:
        return CLASSIFICATION_MAPPING[item_name]
    
    # 關鍵字匹配
    for keyword, category in CLASSIFICATION_MAPPING.items():
        if keyword.lower() in item_lower or item_lower in keyword.lower():
            return category
    
    # 預設分類
    return '其他'

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
    """
    try:
        # 自動分類
        category = classify_item(description)
        
        # 準備數據
        data = {
            'action': 'record',
            'type': 'expense' if amount > 0 else 'income',
            'amount': abs(amount),
            'description': description,
            'category': category,
            'date': datetime.now().isoformat()
        }
        
        # 發送到 GAS
        response = requests.post(GAS_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                await ctx.send(f'✅ 已記錄：{description} - ${amount}\n分類：{category}')
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
