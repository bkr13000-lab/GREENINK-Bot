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


# ==========================================
# المنتجات
# ==========================================

PRODUCTS = {
    "WF-C5390": {
        "name": "EPSON WF-C5390",
        "price": 195000,
        "image": "WF-C5390_headon_690x460.jpg",
    },

    "WF-C5890": {
        "name": "EPSON WF-C5890",
        "price": 220000,
        "image": "WF-C5890_headon_690x460.jpg",
    },

    "L15160": {
        "name": "EPSON L15160",
        "price": 210000,
        "image": "EPSON_L15160.jpg",
    },
}


# ==========================================
# القائمة الرئيسية
# ==========================================

def main_keyboard():

    keyboard = [
        ["🖨 الطابعات", "🧴 الأحبار"],
        ["⚙️ قطع الغيار", "🛒 السلة"],
        ["📦 طلباتي", "☎️ اتصل بنا"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


# ==========================================
# قائمة الطابعات
# ==========================================

def printers_keyboard():

    keyboard = [
        ["🛒 EPSON WF-C5390"],
        ["🛒 EPSON WF-C5890"],
        ["🛒 EPSON L15160"],
        ["🛒 السلة", "🏠 الرئيسية"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


# ==========================================
# قائمة السلة
# ==========================================

def cart_keyboard():

    keyboard = [
        ["✅ تأكيد الطلب"],
        ["🗑 تفريغ السلة"],
        ["🖨 الطابعات", "🏠 الرئيسية"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


# ==========================================
# /start
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🟢 مرحباً بك في GREENINK\n\n"
        "متجرك المتخصص في الطابعات والأحبار وقطع الغيار.\n\n"
        "👇 اختر القسم الذي تريد",
        reply_markup=main_keyboard(),
    )


# ==========================================
# عرض الطابعات
# ==========================================

async def show_printers(update: Update):

    await update.message.reply_text(
        "🖨 قسم الطابعات\n\n"
        "👇 اختر الطابعة التي تريد إضافتها إلى السلة",
        reply_markup=printers_keyboard(),
    )

    for code, product in PRODUCTS.items():

        try:

            with open(product["image"], "rb") as photo:

                await update.message.reply_photo(
                    photo=photo,
                    caption=(
                        f"🖨 {product['name']}\n\n"
                        f"💰 السعر: {product['price']:,} دج"
                    ),
                )

        except Exception as error:

            print(
                f"Image error for {code}: {error}"
            )

            await update.message.reply_text(
                f"🖨 {product['name']}\n\n"
                f"💰 السعر: {product['price']:,} دج"
            )


# ==========================================
# إضافة منتج إلى السلة
# ==========================================

async def add_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product_code: str,
):

    cart = context.user_data.setdefault(
        "cart",
        {}
    )

    cart[product_code] = (
        cart.get(product_code, 0) + 1
    )

    product = PRODUCTS[product_code]

    quantity = cart[product_code]

    await update.message.reply_text(
        "✅ تمت الإضافة إلى السلة\n\n"
        f"🖨 {product['name']}\n"
        f"💰 السعر: {product['price']:,} دج\n"
        f"🔢 الكمية في السلة: {quantity}",
        reply_markup=printers_keyboard(),
    )


# ==========================================
# عرض السلة
# ==========================================

async def show_cart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cart = context.user_data.get(
        "cart",
        {}
    )

    if not cart:

        await update.message.reply_text(
            "🛒 سلة المشتريات فارغة حالياً.",
            reply_markup=main_keyboard(),
        )

        return

    text = "🛒 سلة المشتريات\n\n"

    total = 0

    for code, quantity in cart.items():

        product = PRODUCTS[code]

        subtotal = (
            product["price"] * quantity
        )

        total += subtotal

        text += (
            f"🖨 {product['name']}\n"
            f"💰 السعر: {product['price']:,} دج\n"
            f"🔢 الكمية: {quantity}\n"
            f"💵 المجموع: {subtotal:,} دج\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━\n"
        f"💰 المجموع الإجمالي: {total:,} دج"
    )

    await update.message.reply_text(
        text,
        reply_markup=cart_keyboard(),
    )


# ==========================================
# تأكيد الطلب
# ==========================================

async def confirm_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cart = context.user_data.get(
        "cart",
        {}
    )

    if not cart:

        await update.message.reply_text(
            "❌ لا يوجد أي منتج في السلة.",
            reply_markup=main_keyboard(),
        )

        return

    total = 0

    for code, quantity in cart.items():

        total += (
            PRODUCTS[code]["price"]
            * quantity
        )

    await update.message.reply_text(
        "✅ تم تسجيل الطلب بنجاح\n\n"
        f"💰 إجمالي الطلب: {total:,} دج\n\n"
        "🟢 شكراً لاختياركم GREENINK.",
        reply_markup=main_keyboard(),
    )

    context.user_data["cart"] = {}


# ==========================================
# معالجة الأزرار
# ==========================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text


    # ======================================
    # الطابعات
    # ======================================

    if text == "🖨 الطابعات":

        await show_printers(update)


    # ======================================
    # الرئيسية
    # ======================================

    elif text == "🏠 الرئيسية":

        await start(
            update,
            context,
        )


    # ======================================
    # WF-C5390
    # ======================================

    elif text == "🛒 EPSON WF-C5390":

        await add_product(
            update,
            context,
            "WF-C5390",
        )


    # ======================================
    # WF-C5890
    # ======================================

    elif text == "🛒 EPSON WF-C5890":

        await add_product(
            update,
            context,
            "WF-C5890",
        )


    # ======================================
    # L15160
    # ======================================

    elif text == "🛒 EPSON L15160":

        await add_product(
            update,
            context,
            "L15160",
        )


    # ======================================
    # السلة
    # ======================================

    elif text == "🛒 السلة":

        await show_cart(
            update,
            context,
        )


    # ======================================
    # تفريغ السلة
    # ======================================

    elif text == "🗑 تفريغ السلة":

        context.user_data["cart"] = {}

        await update.message.reply_text(
            "🗑 تم تفريغ السلة.",
            reply_markup=main_keyboard(),
        )


    # ======================================
    # تأكيد الطلب
    # ======================================

    elif text == "✅ تأكيد الطلب":

        await confirm_order(
            update,
            context,
        )


    # ======================================
    # الأحبار
    # ======================================

    elif text == "🧴 الأحبار":

        await update.message.reply_text(
            "🧴 قسم الأحبار\n\n"
            "قريباً سنضيف أنواع الأحبار هنا.",
            reply_markup=main_keyboard(),
        )


    # ======================================
    # قطع الغيار
    # ======================================

    elif text == "⚙️ قطع الغيار":

        await update.message.reply_text(
            "⚙️ قسم قطع الغيار\n\n"
            "قريباً سنضيف قطع الغيار هنا.",
            reply_markup=main_keyboard(),
        )


    # ======================================
    # طلباتي
    # ======================================

    elif text == "📦 طلباتي":

        await update.message.reply_text(
            "📦 طلباتي\n\n"
            "لا توجد طلبات محفوظة حالياً.",
            reply_markup=main_keyboard(),
        )


    # ======================================
    # اتصل بنا
    # ======================================

    elif text == "☎️ اتصل بنا":

        await update.message.reply_text(
            "☎️ اتصل بنا - GREENINK\n\n"

            "👤 أبوبكر\n"
            "📱 0560095387\n\n"

            "👤 عبد الحق\n"
            "📱 0775635460\n\n"

            "🟢 نحن في خدمتكم.",
            reply_markup=main_keyboard(),
        )


    # ======================================
    # رسالة غير معروفة
    # ======================================

    else:

        await update.message.reply_text(
            "👇 اختر أحد الأقسام من القائمة",
            reply_markup=main_keyboard(),
        )


# ==========================================
# تشغيل البوت
# ==========================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN is not configured"
        )

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            buttons,
        )
    )

    print(
        "GREENINK Bot is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
