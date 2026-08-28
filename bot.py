import os
import random

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")


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


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🖨 الطابعات", "🧴 الأحبار"],
            ["⚙️ قطع الغيار", "🛒 السلة"],
            ["📦 طلباتي", "☎️ اتصل بنا"],
        ],
        resize_keyboard=True,
    )


def printers_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🛒 EPSON WF-C5390"],
            ["🛒 EPSON WF-C5890"],
            ["🛒 EPSON L15160"],
            ["🛒 السلة", "🏠 الرئيسية"],
        ],
        resize_keyboard=True,
    )


def cart_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["✅ تأكيد الطلب"],
            ["🗑 تفريغ السلة"],
            ["🖨 الطابعات", "🏠 الرئيسية"],
        ],
        resize_keyboard=True,
    )


def confirm_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["✅ تأكيد نهائي"],
            ["❌ إلغاء الطلب"],
        ],
        resize_keyboard=True,
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data["step"] = None

    await update.message.reply_text(
        "🟢 مرحباً بك في GREENINK\n\n"
        "متجرك المتخصص في الطابعات والأحبار وقطع الغيار.\n\n"
        "👇 اختر القسم الذي تريد",
        reply_markup=main_keyboard(),
    )


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
            print(f"Image error for {code}: {error}")

            await update.message.reply_text(
                f"🖨 {product['name']}\n\n"
                f"💰 السعر: {product['price']:,} دج"
            )


async def add_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product_code: str,
):

    cart = context.user_data.setdefault("cart", {})

    cart[product_code] = cart.get(product_code, 0) + 1

    product = PRODUCTS[product_code]

    await update.message.reply_text(
        "✅ تمت الإضافة إلى السلة\n\n"
        f"🖨 {product['name']}\n"
        f"💰 السعر: {product['price']:,} دج\n"
        f"🔢 الكمية في السلة: {cart[product_code]}",
        reply_markup=printers_keyboard(),
    )


def calculate_cart(cart):
    total = 0

    for code, quantity in cart.items():
        total += PRODUCTS[code]["price"] * quantity

    return total


async def show_cart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cart = context.user_data.get("cart", {})

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
        subtotal = product["price"] * quantity
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


async def begin_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cart = context.user_data.get("cart", {})

    if not cart:
        await update.message.reply_text(
            "❌ السلة فارغة.",
            reply_markup=main_keyboard(),
        )
        return

    context.user_data["step"] = "name"

    await update.message.reply_text(
        "📝 تأكيد الطلب\n\n"
        "أرسل اسمك الكامل:",
    )


async def process_order_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    step = context.user_data.get("step")

    if not step:
        return False

    text = update.message.text.strip()

    if step == "name":

        context.user_data["customer_name"] = text
        context.user_data["step"] = "phone"

        await update.message.reply_text(
            "📱 أرسل رقم الهاتف:"
        )

        return True

    if step == "phone":

        context.user_data["customer_phone"] = text
        context.user_data["step"] = "wilaya"

        await update.message.reply_text(
            "📍 أرسل اسم الولاية:"
        )

        return True

    if step == "wilaya":

        context.user_data["customer_wilaya"] = text
        context.user_data["step"] = "address"

        await update.message.reply_text(
            "🏠 أرسل العنوان الكامل:"
        )

        return True

    if step == "address":

        context.user_data["customer_address"] = text
        context.user_data["step"] = "final_confirm"

        cart = context.user_data.get("cart", {})
        total = calculate_cart(cart)

        summary = (
            "📦 مراجعة الطلب\n\n"
            f"👤 الاسم: {context.user_data['customer_name']}\n"
            f"📱 الهاتف: {context.user_data['customer_phone']}\n"
            f"📍 الولاية: {context.user_data['customer_wilaya']}\n"
            f"🏠 العنوان: {context.user_data['customer_address']}\n\n"
            "🛒 المنتجات:\n"
        )

        for code, quantity in cart.items():

            product = PRODUCTS[code]

            summary += (
                f"• {product['name']} × {quantity}\n"
            )

        summary += (
            "\n━━━━━━━━━━━━━━\n"
            f"💰 المجموع: {total:,} دج\n\n"
            "هل تؤكد الطلب؟"
        )

        await update.message.reply_text(
            summary,
            reply_markup=confirm_keyboard(),
        )

        return True

    return False


async def final_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cart = context.user_data.get("cart", {})

    if not cart:
        await update.message.reply_text(
            "❌ السلة فارغة.",
            reply_markup=main_keyboard(),
        )
        return

    order_number = f"GR-{random.randint(100000, 999999)}"

    total = calculate_cart(cart)

    order = {
        "number": order_number,
        "name": context.user_data.get("customer_name", ""),
        "phone": context.user_data.get("customer_phone", ""),
        "wilaya": context.user_data.get("customer_wilaya", ""),
        "address": context.user_data.get("customer_address", ""),
        "cart": cart.copy(),
        "total": total,
        "status": "🟡 جديد",
    }

    orders = context.user_data.setdefault("orders", [])

    orders.append(order)

    context.user_data["cart"] = {}
    context.user_data["step"] = None

    await update.message.reply_text(
        "✅ تم تأكيد طلبك بنجاح\n\n"
        f"🔢 رقم الطلب: {order_number}\n"
        f"💰 المجموع: {total:,} دج\n"
        "📦 الحالة: جديد\n\n"
        "احتفظ برقم الطلب للمتابعة.\n"
        "🟢 GREENINK",
        reply_markup=main_keyboard(),
    )


async def show_orders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    orders = context.user_data.get("orders", [])

    if not orders:
        await update.message.reply_text(
            "📦 طلباتي\n\n"
            "لا توجد طلبات حالياً.",
            reply_markup=main_keyboard(),
        )
        return

    text = "📦 طلباتي\n\n"

    for order in reversed(orders[-10:]):

        text += (
            f"🔢 {order['number']}\n"
            f"💰 {order['total']:,} دج\n"
            f"📍 {order['wilaya']}\n"
            f"📦 الحالة: {order['status']}\n"
            "━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(),
    )


async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    step = context.user_data.get("step")

    if step in [
        "name",
        "phone",
        "wilaya",
        "address",
    ]:
        handled = await process_order_data(
            update,
            context,
        )

        if handled:
            return

    if text == "✅ تأكيد نهائي":
        await final_confirm(
            update,
            context,
        )

    elif text == "❌ إلغاء الطلب":

        context.user_data["step"] = None

        await update.message.reply_text(
            "❌ تم إلغاء عملية تأكيد الطلب.\n"
            "السلة لم يتم حذفها.",
            reply_markup=main_keyboard(),
        )

    elif text == "🖨 الطابعات":
        await show_printers(update)

    elif text == "🏠 الرئيسية":
        await start(update, context)

    elif text == "🛒 EPSON WF-C5390":
        await add_product(
            update,
            context,
            "WF-C5390",
        )

    elif text == "🛒 EPSON WF-C5890":
        await add_product(
            update,
            context,
            "WF-C5890",
        )

    elif text == "🛒 EPSON L15160":
        await add_product(
            update,
            context,
            "L15160",
        )

    elif text == "🛒 السلة":
        await show_cart(
            update,
            context,
        )

    elif text == "✅ تأكيد الطلب":
        await begin_order(
            update,
            context,
        )

    elif text == "🗑 تفريغ السلة":

        context.user_data["cart"] = {}

        await update.message.reply_text(
            "🗑 تم تفريغ السلة.",
            reply_markup=main_keyboard(),
        )

    elif text == "📦 طلباتي":
        await show_orders(
            update,
            context,
        )

    elif text == "🧴 الأحبار":

        await update.message.reply_text(
            "🧴 قسم الأحبار\n\n"
            "قريباً سنضيف أنواع الأحبار هنا.",
            reply_markup=main_keyboard(),
        )

    elif text == "⚙️ قطع الغيار":

        await update.message.reply_text(
            "⚙️ قسم قطع الغيار\n\n"
            "قريباً سنضيف قطع الغيار هنا.",
            reply_markup=main_keyboard(),
        )

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

    else:

        await update.message.reply_text(
            "👇 اختر أحد الأقسام من القائمة",
            reply_markup=main_keyboard(),
        )


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

    print("GREENINK Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
