import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import json

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GAS_URL = os.getenv('GAS_URL')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 分類規則
CATEGORIES = {
    '食物': ['吃飯', '早餐', '午餐', '晚餐', '咖啡', '飲料', '零食'],
    '交通': ['公車', '捷運', '計程車', '油錢', '停車', '加油'],
    '娛樂': ['電影', '遊戲', '演唱會', '旅遊', '運動'],
    '購物': ['衣服', '鞋子', '書', '電子產品'],
    '其他': []
}

def categorize_expense(description):
    """根據描述自動分類"""
    description_lower = description.lower()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category
    return '其他'

def send_to_gas(amount, description, category):
    """發送到 Google Apps Script"""
    try:
        data = {
            'action': 'addExpense',
            'amount': amount,
            'description': description,
            'category': category,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        response = requests.post(GAS_URL, json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending to GAS: {e}")
        return False

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    send_monthly_report.start()

@bot.command(name='記帳')
async def add_expense(ctx, amount: float, *, description: str):
    """記錄支出
    用法: !記帳 100 買咖啡
    """
    category = categorize_expense(description)
    
    # 發送到 Google Sheet
    success = send_to_gas(amount, description, category)
    
    if success:
        embed = discord.Embed(
            title="✅ 記帳成功",
            description=f"**金額**: ${amount}\n**描述**: {description}\n**分類**: {category}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ 記帳失敗，請稍後重試")

@bot.command(name='報告')
async def get_report(ctx):
    """手動獲取本月報告"""
    try:
        data = {'action': 'getMonthlyReport'}
        response = requests.post(GAS_URL, json=data)
        report = response.json()
        
        embed = discord.Embed(
            title="📊 本月財務報告",
            description=report.get('summary', '無數據'),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ 獲取報告失敗: {e}")

@tasks.loop(hours=24)
async def send_monthly_report():
    """每月 1 號自動發送報告"""
    if datetime.now().day == 1:
        try:
            data = {'action': 'getMonthlyReport'}
            response = requests.post(GAS_URL, json=data)
            report = response.json()
            
            webhook_data = {
                'content': '📊 **本月財務報告**',
                'embeds': [{
                    'title': '月度總結',
                    'description': report.get('summary', '無數據'),
                    'color': 3447003
                }]
            }
            requests.post(DISCORD_WEBHOOK, json=webhook_data)
        except Exception as e:
            print(f"Error sending monthly report: {e}")

@send_monthly_report.before_loop
async def before_send_report():
    await bot.wait_until_ready()

bot.run(DISCORD_TOKEN)
