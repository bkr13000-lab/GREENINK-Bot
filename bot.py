import os

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🖨️ الطابعات", "🧴 الأحبار"],
        ["⚙️ قطع الغيار", "🛒 السلة"],
        ["📦 طلباتي", "☎️ اتصل بنا"],
    ]

    markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "🟢 مرحباً بك في GREENINK\n\n"
        "متجرك المتخصص في الطابعات والأحبار وقطع الغيار.\n\n"
        "اختر القسم الذي تريد 👇",
        reply_markup=markup,
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    responses = {
        "🖨️ الطابعات": "🖨️ قسم الطابعات\n\nقريباً سنضيف المنتجات هنا.",
        "🧴 الأحبار": "🧴 قسم الأحبار\n\nقريباً سنضيف أنواع الأحبار هنا.",
        "⚙️ قطع الغيار": "⚙️ قسم قطع الغيار\n\nقريباً سنضيف قطع الغيار هنا.",
        "🛒 السلة": "🛒 سلة المشتريات فارغة حالياً.",
        "📦 طلباتي": "📦 لا توجد طلبات حالياً.",
        "☎️ اتصل بنا": "☎️ GREENINK\n\nيمكنك التواصل معنا للحصول على المزيد من المعلومات.",
    }

    response = responses.get(
        text,
        "اختر أحد الأقسام من القائمة 👇",
    )

    await update.message.reply_text(response)


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            buttons,
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
