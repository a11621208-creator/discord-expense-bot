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

# 完整的分類對應表 - 返回分類名稱而不是單元格位置
CLASSIFICATION_MAPPING = {
    # 收入類別
    '核心教材': '核心教材收入',
    '教材': '核心教材收入',
    '課程': '核心教材收入',
    '線上課程': '核心教材收入',
    
    '訂閱': '訂閱教材收入',
    '訂閱教材': '訂閱教材收入',
    
    '入門': '入門方案收入',
    '入門方案': '入門方案收入',
    
    '教練': '教練1v1 收入',
    '1v1': '教練1v1 收入',
    '一對一': '教練1v1 收入',
    
    'staking': 'Staking結算收益',
    '結算收益': 'Staking結算收益',
    
    '軟體': '軟體代理收入',
    '代理': '軟體代理收入',
    
    '其他營業': '其他營業收入',
    
    # 成本類別
    '銷貨成本': '銷貨成本',
    '進貨': '銷貨成本',
    '原料': '銷貨成本',
    '材料': '銷貨成本',
    
    '活動成本': '活動成本',
    '活動': '活動成本',
    '會議': '活動成本',
    
    '虧損': 'Staking結算虧損',
    
    '營業成本': '其他營業成本',
    
    '人事成本': '人事成本',
    '薪資': '人事成本',
    '工資': '人事成本',
    
    # 支出類別
    '人事費用': '人事費用(含獎金)',
    '獎金': '人事費用(含獎金)',
    '薪水': '人事費用(含獎金)',
    
    '租賃費用': '租賃費用(含官方Line/雲端…)',
    '租金': '租賃費用(含官方Line/雲端…)',
    '辦公室': '租賃費用(含官方Line/雲端…)',
    '雲端': '租賃費用(含官方Line/雲端…)',
    'line': '租賃費用(含官方Line/雲端…)',
    
    '勞務費': '勞務費(Ex:外包工程師)',
    '外包': '勞務費(Ex:外包工程師)',
    '工程師': '勞務費(Ex:外包工程師)',
    '承包': '勞務費(Ex:外包工程師)',
    
    '行銷費用': '行銷費用(廣告/公關)',
    '廣告': '行銷費用(廣告/公關)',
    '公關': '行銷費用(廣告/公關)',
    '宣傳': '行銷費用(廣告/公關)',
    
    '分潤': '分潤獎金',
    '分潤獎金': '分潤獎金',
    
    '雜項': '雜項費用',
    '其他': '雜項費用',
    '雜項費用': '雜項費用',
    '會計費用': '雜項費用',
    '晚餐': '雜項費用',
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
    return '雜項費用'

def parse_date_string(date_str):
    """
    解析日期字符串
    支持格式：
    - "2/15" -> 2026-02-15 (當前年份)
    - "2026-02-15" -> 2026-02-15
    返回 ISO 格式的日期字符串
    """
    try:
        if '/' in date_str:
            # 格式: M/D
            parts = date_str.split('/')
            month = int(parts[0])
            day = int(parts[1])
            year = datetime.now().year
            
            # 驗證月份和日期
            if month < 1 or month > 12:
                return None
            if day < 1 or day > 31:
                return None
            
            date_obj = datetime(year, month, day)
            return date_obj.isoformat()
        else:
            # 嘗試解析 ISO 格式或其他標準格式
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.isoformat()
    except:
        return None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} 已連接到 Discord')

@bot.command(name='記帳')
async def record_expense(ctx, amount: float, *, args: str):
    """記錄支出或收入
    用法: !記帳 100 咖啡
         !記帳 500 核心教材
         !記帳 100 咖啡 2/15  (指定日期：2月15日)
    """
    try:
        # 解析參數：可能包含日期
        parts = args.rsplit(' ', 1)  # 從右邊分割，最多分割1次
        
        description = parts[0]
        date_str = None
        
        # 檢查是否有日期參數
        if len(parts) > 1:
            potential_date = parts[1]
            # 檢查是否看起來像日期 (包含 / 或 -)
            if '/' in potential_date or '-' in potential_date:
                parsed_date = parse_date_string(potential_date)
                if parsed_date:
                    date_str = parsed_date
                    description = parts[0]
                else:
                    # 日期格式無效，將整個 args 視為描述
                    description = args
        
        # 自動分類
        category = classify_item(description)
        
        # 判斷是收入還是支出
        if category in ['核心教材收入', '訂閱教材收入', '入門方案收入', '教練1v1 收入', 'Staking結算收益', '軟體代理收入', '其他營業收入']:
            item_type = 'income'
            actual_amount = abs(amount)
        elif category in ['銷貨成本', '活動成本', 'Staking結算虧損', '其他營業成本', '人事成本']:
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
            'date': date_str or datetime.now().isoformat()
        }
        
        # 發送到 GAS
        response = requests.post(GAS_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                date_info = ''
                if date_str:
                    date_obj = datetime.fromisoformat(date_str)
                    date_info = f' ({date_obj.strftime("%Y-%m-%d")})'
                await ctx.send(f'✅ 已記錄：{description} - ${actual_amount}{date_info}\n分類：{category}')
            else:
                await ctx.send(f'❌ 記錄失敗：{result.get("error", "未知錯誤")}')
        else:
            await ctx.send(f'❌ 無法連接到 Google Sheet：{response.status_code}')
    
    except Exception as e:
        await ctx.send(f'❌ 發生錯誤：{str(e)}')

@bot.command(name='修改')
async def update_expense(ctx, timestamp: str, amount: float, *, description: str):
    """修改已記錄的支出
    用法: !修改 [時間戳] 150 咖啡
    """
    try:
        # 自動分類
        category = classify_item(description)
        
        # 準備數據
        data = {
            'action': 'update',
            'recordId': timestamp,
            'amount': abs(amount),
            'description': description,
            'date': datetime.now().isoformat()
        }
        
        # 發送到 GAS
        response = requests.post(GAS_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                await ctx.send(f'✅ 已更新：{description} - ${abs(amount)}\n分類：{category}')
            else:
                await ctx.send(f'❌ 更新失敗：{result.get("error", "未知錯誤")}')
        else:
            await ctx.send(f'❌ 無法連接到 Google Sheet：{response.status_code}')
    
    except Exception as e:
        await ctx.send(f'❌ 發生錯誤：{str(e)}')

@bot.command(name='報告')
async def get_report(ctx, date_str: str = None):
    """獲取財務報告
    用法: !報告          (本月)
         !報告 2/15     (2月份)
    """
    try:
        report_date = None
        if date_str:
            parsed_date = parse_date_string(date_str)
            if parsed_date:
                report_date = parsed_date
            else:
                await ctx.send(f'❌ 日期格式無效，請使用 M/D 格式 (例如：2/15)')
                return
        
        data = {
            'action': 'getReport',
            'date': report_date or datetime.now().isoformat()
        }
        
        response = requests.post(GAS_URL, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                report = result.get('report', '無數據')
                # 格式化報告輸出
                report_text = f'📊 {report.get("yearMonth", "本月")} 財務報告：\n'
                if isinstance(report, dict) and 'data' in report:
                    for category, items in report['data'].items():
                        report_text += f'\n**{category}**\n'
                        if isinstance(items, dict):
                            for item_name, value in items.items():
                                report_text += f'  {item_name}: {value}\n'
                        else:
                            report_text += f'  {items}\n'
                else:
                    report_text += str(report)
                
                await ctx.send(report_text)
            else:
                await ctx.send(f'❌ 無法獲取報告：{result.get("error", "未知錯誤")}')
        else:
            await ctx.send(f'❌ 無法連接到 Google Sheet')
    
    except Exception as e:
        await ctx.send(f'❌ 發生錯誤：{str(e)}')

bot.run(DISCORD_TOKEN)
