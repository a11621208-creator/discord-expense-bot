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
        
        # 2. 處理金額累加
        current_cell = sheet.cell(row, col)
        current_val = int(current_cell.value) if current_cell.value else 0
        new_val = current_val + amount
        sheet.update_cell(row, col, new_val)
        
        # 3. 處理「原生附註」(Cell Note)
        # 取得舊的附註內容
        existing_note = sheet.cell(row, col).note or ""
        timestamp = now.strftime("%m/%d %H:%M")
        new_note_content = f"{existing_note}\n{timestamp}: {description} (${amount})".strip()
        
        # 更新附註 (這就是你要的：滑鼠放上去才會顯示)
        sheet.update_note(row, col, new_note_content)

        await ctx.send(f"✅ **記帳成功！**\n📁 類別：{target_category}\n💰 金額：${amount}\n📝 附註已加入儲存格")

    except Exception as e:
        await ctx.send(f"❌ 發生錯誤: {str(e)}")
