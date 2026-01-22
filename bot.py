import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = "8327104214:AAHW7N79Td91Pqs1i1-ST8nAt6GD58mikPw"

# Force join channels
FORCE_CHANNELS = ["@linksharepromote", "@the_mysterious_market"]
FREE_PROMO_CHANNEL = "@the_mysterious_market"
PREMIUM_PREVIEW_CHANNEL = "@ViralPulseAds"

# user_id -> {limits, referred}
users = {}
# user_id -> {"type": "free"/"premium", step:..., data}
pending = {}


# ---------- HELPERS ----------
async def is_joined(bot, user_id):
    for ch in FORCE_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    users.setdefault(uid, {"limits": 1, "referred": 0})

    text = (
        "🤖 *Welcome to Promotion Bot*\n\n"
        "⚠️ If bot doesn’t work properly, please /start again.\n\n"
        "👉 First join required channels:"
    )
    buttons = [
        [InlineKeyboardButton("Join Channel 1", url="https://t.me/linksharepromote")],
        [InlineKeyboardButton("Join Channel 2", url="https://t.me/the_mysterious_market")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


# ---------- VERIFY ----------
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    joined = await is_joined(context.bot, uid)
    if not joined:
        await q.edit_message_text(
            "❌ You must join both channels first.\n\n"
            "Please join and click ✅ Verify again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Verify", callback_data="verify")]
            ])
        )
        return

    users.setdefault(uid, {"limits": 1, "referred": 0})
    await main_menu(q)


# ---------- MAIN MENU ----------
async def main_menu(q):
    buttons = [
        [InlineKeyboardButton("🚀 Promote Now", callback_data="promote")],
        [InlineKeyboardButton("💎 Premium Promotion", callback_data="premium")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🆘 Support", url="https://t.me/PaidPromo23Bot")]
    ]
    await q.edit_message_text("🏠 *Main Menu*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


# ---------- BACK ----------
async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update.callback_query)


# ---------- PROFILE ----------
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    ref_link = f"https://t.me/{context.bot.username}?start={uid}"

    text = (
        f"👤 *Your Profile*\n\n"
        f"🎯 Available Limits: {users[uid]['limits']}\n"
        f"👥 Referrals: {users[uid]['referred']}\n\n"
        f"🔗 Referral Link:\n{ref_link}\n\n"
        f"➡️ 1 Refer = 1 Free Promotion (24h)"
    )
    buttons = [
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


# ---------- FREE PROMOTION ----------
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if users[uid]["limits"] <= 0:
        await q.edit_message_text(
            "❌ You don’t have promotion limit.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
        )
        return

    pending[uid] = {"type": "free", "step": "link"}
    await q.edit_message_text(
        "🔗 Send your Channel / Group link",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
    )


# ---------- PREMIUM PROMOTION ----------
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    pending[uid] = {"type": "premium", "step": "link"}
    await q.edit_message_text(
        "💎 Premium Promotion\n\n🔗 Send your channel / group link",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
    )


# ---------- TEXT HANDLER (FREE & PREMIUM FLOW) ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid not in pending:
        return

    data = pending[uid]

    # ----- FREE PROMOTION -----
    if data["type"] == "free":
        if data["step"] == "link":
            data["link"] = update.message.text
            data["step"] = "desc"
            await update.message.reply_text(
                "📝 Send promotion description",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
            )
        elif data["step"] == "desc":
            link = data["link"]
            desc = update.message.text

            btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Join Channel", url=link)]])
            msg = await context.bot.send_message(FREE_PROMO_CHANNEL, desc, reply_markup=btn)

            users[uid]["limits"] -= 1
            pending.pop(uid)

            await update.message.reply_text("✅ Your promotion is live for 24 hours!")

            asyncio.create_task(delete_after_24h(context, msg.chat_id, msg.message_id))

    # ----- PREMIUM FLOW -----
    elif data["type"] == "premium":
        step = data["step"]
        if step == "link":
            data["link"] = update.message.text
            data["step"] = "desc"
            await update.message.reply_text(
                "📝 Send promotion description",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
            )
        elif step == "desc":
            data["desc"] = update.message.text
            data["step"] = "plan"
            buttons = [
                [InlineKeyboardButton("10 Channels", callback_data="pay_10")],
                [InlineKeyboardButton("25 Channels", callback_data="pay_25")],
                [InlineKeyboardButton("50 Channels", callback_data="pay_50")],
                [InlineKeyboardButton("75 Channels", callback_data="pay_75")],
                [InlineKeyboardButton("100+ Channels", callback_data="pay_100")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
            ]
            await update.message.reply_text(
                "📊 How many channels do you want to promote on?\n\n1 Channel ≈ 6K members",
                reply_markup=InlineKeyboardMarkup(buttons)
            )


# ---------- DELETE MESSAGE AFTER 24H ----------
async def delete_after_24h(context, chat_id, msg_id):
    await asyncio.sleep(86400)
    try:
        await context.bot.delete_message(chat_id, msg_id)
    except:
        pass


# ---------- PREMIUM PAYMENT ----------
async def premium_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = pending.get(uid)
    if not data or data.get("type") != "premium":
        return

    urls = {
        "pay_10": "http://t.me/send?start=IV1yWmw2aIny",
        "pay_25": "http://t.me/send?start=IVIBILvGoeBY",
        "pay_50": "http://t.me/send?start=IVSnfH5KIEL1",
        "pay_75": "http://t.me/send?start=IVC21mWh0CHl",
        "pay_100": "http://t.me/send?start=IVXsUN5iuUX8",
    }

    text = (
        "💰 We receive crypto payment only\n"
        "Make payment and send txn hash\n\n"
        f"🔗 Link: {data['link']}\n"
        f"📝 Description:\n{data['desc']}"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Pay Now", url=urls[q.data])],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ])

    await q.edit_message_text(text, reply_markup=btn)


# ---------- RUN BOT ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(CallbackQueryHandler(back_main, pattern="back_main"))
app.add_handler(CallbackQueryHandler(profile, pattern="profile"))
app.add_handler(CallbackQueryHandler(promote, pattern="promote"))
app.add_handler(CallbackQueryHandler(premium, pattern="premium"))
app.add_handler(CallbackQueryHandler(premium_pay, pattern="pay_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Bot is running...")
app.run_polling()
