import discord
from discord.ext import commands
import requests
import os
from datetime import datetime
from flask import Flask
import threading

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
GOOGLE_SCRIPT_URL = os.getenv('GOOGLE_SCRIPT_URL')

# Flask 應用程序
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

@bot.event
async def on_ready():
    print(f'{bot.user} 已連接到 Discord')
    try:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='支出記錄'))
        requests.post(WEBHOOK_URL, json={'content': '✅ 記賬機器人已啟動！'})
    except Exception as e:
        print(f'啟動通知失敗: {e}')

@bot.command(name='測試')
async def test(ctx):
    await ctx.send('✅ Bot 正常運行！')

@bot.command(name='支出')
async def add_expense(ctx, amount: float, category: str, *, description: str = '無'):
    try:
        data = {
            'amount': amount,
            'category': category,
            'description': description,
            'date': datetime.now().isoformat(),
            'user': str(ctx.author)
        }
        response = requests.post(GOOGLE_SCRIPT_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            embed = discord.Embed(
                title='✅ 支出已記錄',
                description=f'金額: {amount} 元\n分類: {category}\n說明: {description}',
                color=discord.Color.green()
            )
            embed.set_footer(text=f'記錄者: {ctx.author}')
            await ctx.send(embed=embed)
            
            requests.post(WEBHOOK_URL, json={
                'content': f'💰 新支出記錄\n金額: {amount} 元\n分類: {category}\n說明: {description}\n記錄者: {ctx.author}'
            })
        else:
            await ctx.send(f'❌ 記錄失敗: {response.text}')
    except Exception as e:
        await ctx.send(f'❌ 錯誤: {str(e)}')

@bot.command(name='幫助')
async def help_command(ctx):
    embed = discord.Embed(
        title='💰 記賬機器人幫助',
        description='以下是可用的命令:',
        color=discord.Color.blue()
    )
    embed.add_field(name='/支出 <金額> <分類> [說明]', value='記錄一筆支出', inline=False)
    embed.add_field(name='/測試', value='測試機器人是否正常運行', inline=False)
    embed.add_field(name='/幫助', value='顯示此幫助信息', inline=False)
    await ctx.send(embed=embed)

def run_bot():
    print('正在啟動機器人...')
    bot.run(DISCORD_TOKEN)

if __name__ == '__main__':
    # 在後台線程中運行 Discord Bot
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # 運行 Flask 服務器
    app.run(host='0.0.0.0', port=8080)
