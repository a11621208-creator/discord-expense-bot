import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
from aiohttp import web
import asyncio
import logging

# 設置日誌
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GAS_URL = os.getenv('GAS_URL')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORIES = {
    '食物': ['吃飯', '早餐', '午餐', '晚餐', '咖啡', '飲料', '零食'],
    '交通': ['公車', '捷運', '計程車', '油錢', '停車', '加油'],
    '娛樂': ['電影', '遊戲', '演唱會', '旅遊', '運動'],
    '購物': ['衣服', '鞋子', '書', '電子產品'],
    '其他': []
}

def categorize_expense(description):
    description_lower = description.lower()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category
    return '其他'

def send_to_gas(amount, description, category):
    try:
        logger.info(f"📤 正在發送到 Google Apps Script: 金額={amount}, 描述={description}, 分類={category}")
        data = {
            'action': 'addExpense',
            'amount': amount,
            'description': description,
            'category': category,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        response = requests.post(GAS_URL, json=data, timeout=10)
        logger.info(f"📥 Google Apps Script 回應: 狀態碼={response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ 發送到 Google Apps Script 失敗: {e}")
        return False

@bot.event
async def on_ready():
    logger.info(f"✅ Bot 已連接到 Discord: {bot.user}")
    print(f'{bot.user} has connected to Discord!')
    send_monthly_report.start()

@bot.event
async def on_message(message):
    logger.info(f"📨 收到消息 - 用戶: {message.author}, 內容: {message.content}, 頻道: {message.channel}")
    await bot.process_commands(message)

@bot.command(name='記帳')
async def add_expense(ctx, amount: float, *, description: str):
    logger.info(f"🔔 收到記帳命令 - 用戶: {ctx.author}, 金額: {amount}, 描述: {description}")
    
    try:
        category = categorize_expense(description)
        logger.info(f"📂 自動分類: {category}")
        
        success = send_to_gas(amount, description, category)
        
        if success:
            logger.info(f"✅ 記帳成功")
            embed = discord.Embed(
                title="✅ 記帳成功",
                description=f"**金額**: ${amount}\n**描述**: {description}\n**分類**: {category}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"❌ 記帳失敗 - Google Apps Script 返回錯誤")
            await ctx.send("❌ 記帳失敗，Google Apps Script 返回錯誤，請稍後重試")
    except Exception as e:
        logger.error(f"❌ 記帳命令出錯: {e}")
        await ctx.send(f"❌ 記帳失敗: {str(e)}")

@bot.command(name='報告')
async def get_report(ctx):
    logger.info(f"🔔 收到報告命令 - 用戶: {ctx.author}")
    
    try:
        data = {'action': 'getMonthlyReport'}
        response = requests.post(GAS_URL, json=data, timeout=10)
        logger.info(f"📥 Google Apps Script 回應: 狀態碼={response.status_code}")
        
        report = response.json()
        
        embed = discord.Embed(
            title="📊 本月財務報告",
            description=report.get('summary', '無數據'),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"❌ 獲取報告失敗: {e}")
        await ctx.send(f"❌ 獲取報告失敗: {str(e)}")

@bot.command(name='測試')
async def test_command(ctx):
    logger.info(f"🔔 收到測試命令 - 用戶: {ctx.author}")
    await ctx.send("✅ Bot 正常運行！")

@tasks.loop(hours=24)
async def send_monthly_report():
    if datetime.now().day == 1 and datetime.now().hour == 0:
        try:
            logger.info("📊 開始發送月度報告")
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
            logger.info("✅ 月度報告已發送")
        except Exception as e:
            logger.error(f"❌ 發送月度報告失敗: {e}")

# HTTP 服務器（保持容器運行）
async def health_check(request):
    return web.Response(text="Bot is running", status=200)

async def start_http_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("HTTP server started on port 8080")
    print("HTTP server started on port 8080")

async def main():
    # 啟動 HTTP 服務器
    await start_http_server()
    # 啟動 Discord Bot
    await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
