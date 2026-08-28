import os
import random
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")


def load_admin_ids():
    raw = os.environ.get("ADMIN_CHAT_IDS", "").strip()

    # دعم المتغير القديم
    if not raw:
        raw = os.environ.get("ADMIN_CHAT_ID", "").strip()

    admins = []

    for item in raw.split(","):
        item = item.strip()

        if not item:
            continue

        try:
            admins.append(int(item))
        except ValueError:
            print(
                f"Invalid admin ID: {item}",
                flush=True,
            )

    return admins


ADMIN_CHAT_IDS = load_admin_ids()


# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = {
    "WF-C5390": {
        "name": "EPSON WF-C5390",
        "price": 195000,
        "images": [
            "WF-C5390_headon_690x460.jpg",
        ],
    },

    "WF-C5890": {
        "name": "EPSON WF-C5890",
        "price": 220000,
        "images": [
            "WF-C5890_headon_690x460.jpg",
        ],
    },

    "L15160": {
        "name": "EPSON L15160",
        "price": 210000,
        "images": [
            "EPSON L15160.jpg",
            "EPSON_L15160.jpg",
            "L15160.jpg",
            "EPSON L15160.jpeg",
            "L15160.jpeg",
            "EPSON L15160.png",
        ],
    },
}


# =========================================================
# DATABASE
# =========================================================

def db_connect():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

    print(
        "Connecting to PostgreSQL...",
        flush=True,
    )

    conn = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )

    print(
        "PostgreSQL connected ✅",
        flush=True,
    )

    return conn


def init_database():
    print(
        "Creating/checking PostgreSQL tables...",
        flush=True,
    )

    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_number VARCHAR(30) PRIMARY KEY,
                    customer_chat_id BIGINT NOT NULL,
                    customer_user_id BIGINT,
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    wilaya TEXT NOT NULL,
                    address TEXT NOT NULL,
                    total BIGINT NOT NULL,
                    status TEXT NOT NULL DEFAULT '🟡 جديد',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    id BIGSERIAL PRIMARY KEY,

                    order_number VARCHAR(30) NOT NULL
                    REFERENCES orders(order_number)
                    ON DELETE CASCADE,

                    product_code TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price BIGINT NOT NULL
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_messages (
                    order_number VARCHAR(30) NOT NULL
                    REFERENCES orders(order_number)
                    ON DELETE CASCADE,

                    admin_chat_id BIGINT NOT NULL,
                    message_id BIGINT NOT NULL,

                    PRIMARY KEY (
                        order_number,
                        admin_chat_id,
                        message_id
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_orders_customer
                ON orders(customer_chat_id);
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_orders_created
                ON orders(created_at DESC);
                """
            )

        conn.commit()

    print(
        "PostgreSQL database initialized ✅",
        flush=True,
    )


def order_exists(order_number):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT 1
                FROM orders
                WHERE order_number = %s
                """,
                (order_number,),
            )

            return cur.fetchone() is not None


def save_order(order):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO orders (
                    order_number,
                    customer_chat_id,
                    customer_user_id,
                    customer_name,
                    phone,
                    wilaya,
                    address,
                    total,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    order["number"],
                    order["chat_id"],
                    order["user_id"],
                    order["name"],
                    order["phone"],
                    order["wilaya"],
                    order["address"],
                    order["total"],
                    order["status"],
                ),
            )

            for code, quantity in order["cart"].items():

                product = PRODUCTS[code]

                cur.execute(
                    """
                    INSERT INTO order_items (
                        order_number,
                        product_code,
                        product_name,
                        quantity,
                        unit_price
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        order["number"],
                        code,
                        product["name"],
                        quantity,
                        product["price"],
                    ),
                )

        conn.commit()


def save_admin_message(
    order_number,
    admin_chat_id,
    message_id,
):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO admin_messages (
                    order_number,
                    admin_chat_id,
                    message_id
                )
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    order_number,
                    admin_chat_id,
                    message_id,
                ),
            )

        conn.commit()


def get_admin_messages(order_number):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    admin_chat_id,
                    message_id
                FROM admin_messages
                WHERE order_number = %s
                """,
                (order_number,),
            )

            return cur.fetchall()


def get_order(order_number):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT *
                FROM orders
                WHERE order_number = %s
                """,
                (order_number,),
            )

            order = cur.fetchone()

            if not order:
                return None

            cur.execute(
                """
                SELECT *
                FROM order_items
                WHERE order_number = %s
                ORDER BY id
                """,
                (order_number,),
            )

            items = cur.fetchall()

    order = dict(order)
    order["items"] = items

    return order


def update_order_status(
    order_number,
    new_status,
):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE orders
                SET
                    status = %s,
                    updated_at = NOW()
                WHERE order_number = %s
                """,
                (
                    new_status,
                    order_number,
                ),
            )

        conn.commit()


def get_customer_orders(
    chat_id,
    limit=10,
):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT *
                FROM orders
                WHERE customer_chat_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (
                    chat_id,
                    limit,
                ),
            )

            return cur.fetchall()


# =========================================================
# KEYBOARDS
# =========================================================

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


def admin_order_keyboard(order_number):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ قبول الطلب",
                    callback_data=f"accept:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 قيد التحضير",
                    callback_data=f"prepare:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🚚 قيد التوصيل",
                    callback_data=f"delivery:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ تم التسليم",
                    callback_data=f"done:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ إلغاء الطلب",
                    callback_data=f"cancel:{order_number}",
                )
            ],
        ]
    )


# =========================================================
# HELPERS
# =========================================================

def calculate_cart(cart):
    total = 0

    for code, quantity in cart.items():
        total += (
            PRODUCTS[code]["price"]
            * quantity
        )

    return total


def find_product_image(product):
    for image_name in product["images"]:

        path = Path(image_name)

        if path.exists():
            return path

    return None


def build_admin_order_text(order):
    products_text = ""

    for item in order["items"]:

        products_text += (
            f"• {item['product_name']} "
            f"× {item['quantity']}\n"
        )

    return (
        "🟢 طلب جديد - GREENINK\n\n"
        f"🔢 رقم الطلب: "
        f"{order['order_number']}\n\n"

        f"👤 الاسم: "
        f"{order['customer_name']}\n"

        f"📱 الهاتف: "
        f"{order['phone']}\n"

        f"📍 الولاية: "
        f"{order['wilaya']}\n"

        f"🏠 العنوان: "
        f"{order['address']}\n\n"

        "🛒 المنتجات:\n"
        f"{products_text}\n"

        f"💰 المجموع: "
        f"{order['total']:,} دج\n\n"

        f"📦 الحالة: "
        f"{order['status']}"
    )


def customer_status_message(
    order_number,
    status,
):
    if status == "✅ تم قبول الطلب":

        body = (
            "✅ تم قبول طلبك "
            "من طرف GREENINK."
        )

    elif status == "📦 قيد التحضير":

        body = (
            "📦 طلبك راه قيد "
            "التحضير حالياً."
        )

    elif status == "🚚 قيد التوصيل":

        body = (
            "🚚 طلبك خرج للتوصيل."
        )

    elif status == "✅ تم التسليم":

        body = (
            "✅ تم تسليم طلبك بنجاح.\n\n"
            "شكراً لاختيارك GREENINK."
        )

    elif status == "❌ تم إلغاء الطلب":

        body = (
            "❌ تم إلغاء طلبك.\n\n"
            "للمزيد من المعلومات "
            "تواصل معنا."
        )

    else:

        body = (
            f"📦 حالة طلبك أصبحت:\n"
            f"{status}"
        )

    return (
        "🔔 تحديث طلب GREENINK\n\n"
        f"🔢 رقم الطلب: "
        f"{order_number}\n\n"

        f"{body}\n\n"

        "🟢 GREENINK"
    )


# =========================================================
# START / ID
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["step"] = None

    await update.message.reply_text(
        "🟢 مرحباً بك في GREENINK\n\n"
        "متجرك المتخصص في الطابعات "
        "والأحبار وقطع الغيار.\n\n"
        "👇 اختر القسم الذي تريد",
        reply_markup=main_keyboard(),
    )


async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        "🆔 Chat ID تاع هذا الحساب هو:\n\n"
        f"{chat_id}"
    )


# =========================================================
# PRINTERS
# =========================================================

async def show_printers(update: Update):
    await update.message.reply_text(
        "🖨 قسم الطابعات\n\n"
        "👇 اختر الطابعة التي تريد "
        "إضافتها للسلة",
        reply_markup=printers_keyboard(),
    )

    for code, product in PRODUCTS.items():

        image_path = find_product_image(
            product
        )

        if image_path:

            try:
                with open(
                    image_path,
                    "rb",
                ) as photo:

                    await update.message.reply_photo(
                        photo=photo,
                        caption=(
                            f"🖨 {product['name']}\n\n"
                            f"💰 السعر: "
                            f"{product['price']:,} دج"
                        ),
                    )

            except Exception as error:

                print(
                    f"Image error for "
                    f"{code}: {error}",
                    flush=True,
                )

                await update.message.reply_text(
                    f"🖨 {product['name']}\n\n"
                    f"💰 السعر: "
                    f"{product['price']:,} دج"
                )

        else:

            await update.message.reply_text(
                f"🖨 {product['name']}\n\n"
                f"💰 السعر: "
                f"{product['price']:,} دج"
            )


async def add_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    product_code,
):
    cart = context.user_data.setdefault(
        "cart",
        {},
    )

    cart[product_code] = (
        cart.get(product_code, 0) + 1
    )

    product = PRODUCTS[product_code]

    await update.message.reply_text(
        "✅ تمت الإضافة إلى السلة\n\n"
        f"🖨 {product['name']}\n"
        f"💰 السعر: "
        f"{product['price']:,} دج\n"
        f"🔢 الكمية: "
        f"{cart[product_code]}",
        reply_markup=printers_keyboard(),
    )


# =========================================================
# CART
# =========================================================

async def show_cart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get(
        "cart",
        {},
    )

    if not cart:

        await update.message.reply_text(
            "🛒 سلة المشتريات "
            "فارغة حالياً.",
            reply_markup=main_keyboard(),
        )

        return

    text = "🛒 سلة المشتريات\n\n"

    total = 0

    for code, quantity in cart.items():

        product = PRODUCTS[code]

        subtotal = (
            product["price"]
            * quantity
        )

        total += subtotal

        text += (
            f"🖨 {product['name']}\n"
            f"💰 السعر: "
            f"{product['price']:,} دج\n"
            f"🔢 الكمية: "
            f"{quantity}\n"
            f"💵 المجموع: "
            f"{subtotal:,} دج\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━\n"
        f"💰 المجموع الإجمالي: "
        f"{total:,} دج"
    )

    await update.message.reply_text(
        text,
        reply_markup=cart_keyboard(),
    )


# =========================================================
# CHECKOUT
# =========================================================

async def begin_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get(
        "cart",
        {},
    )

    if not cart:

        await update.message.reply_text(
            "❌ السلة فارغة.",
            reply_markup=main_keyboard(),
        )

        return

    context.user_data["step"] = "name"

    await update.message.reply_text(
        "📝 تأكيد الطلب\n\n"
        "👤 أرسل اسمك الكامل:"
    )


async def process_order_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    step = context.user_data.get("step")

    if not step:
        return False

    text = update.message.text.strip()

    if step == "name":

        context.user_data[
            "customer_name"
        ] = text

        context.user_data[
            "step"
        ] = "phone"

        await update.message.reply_text(
            "📱 أرسل رقم الهاتف:"
        )

        return True

    if step == "phone":

        context.user_data[
            "customer_phone"
        ] = text

        context.user_data[
            "step"
        ] = "wilaya"

        await update.message.reply_text(
            "📍 أرسل اسم الولاية:"
        )

        return True

    if step == "wilaya":

        context.user_data[
            "customer_wilaya"
        ] = text

        context.user_data[
            "step"
        ] = "address"

        await update.message.reply_text(
            "🏠 أرسل العنوان الكامل:"
        )

        return True

    if step == "address":

        context.user_data[
            "customer_address"
        ] = text

        context.user_data[
            "step"
        ] = "final_confirm"

        cart = context.user_data.get(
            "cart",
            {},
        )

        total = calculate_cart(cart)

        summary = (
            "📦 مراجعة الطلب\n\n"

            f"👤 الاسم: "
            f"{context.user_data['customer_name']}\n"

            f"📱 الهاتف: "
            f"{context.user_data['customer_phone']}\n"

            f"📍 الولاية: "
            f"{context.user_data['customer_wilaya']}\n"

            f"🏠 العنوان: "
            f"{context.user_data['customer_address']}\n\n"

            "🛒 المنتجات:\n"
        )

        for code, quantity in cart.items():

            product = PRODUCTS[code]

            summary += (
                f"• {product['name']} "
                f"× {quantity}\n"
            )

        summary += (
            "\n━━━━━━━━━━━━━━\n"
            f"💰 المجموع: "
            f"{total:,} دج\n\n"

            "هل تؤكد الطلب؟"
        )

        await update.message.reply_text(
            summary,
            reply_markup=confirm_keyboard(),
        )

        return True

    return False


# =========================================================
# ADMIN NOTIFICATION
# =========================================================

async def send_order_to_admins(
    context: ContextTypes.DEFAULT_TYPE,
    order_number,
):
    if not ADMIN_CHAT_IDS:

        print(
            "ADMIN_CHAT_IDS "
            "is not configured",
            flush=True,
        )

        return

    order = get_order(order_number)

    if not order:
        return

    text = build_admin_order_text(order)

    for admin_id in ADMIN_CHAT_IDS:

        try:

            message = (
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=admin_order_keyboard(
                        order_number
                    ),
                )
            )

            save_admin_message(
                order_number,
                admin_id,
                message.message_id,
            )

        except Exception as error:

            print(
                f"Admin notification error "
                f"{admin_id}: {error}",
                flush=True,
            )


# =========================================================
# FINAL CONFIRM
# =========================================================

async def final_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get(
        "cart",
        {},
    )

    if not cart:

        await update.message.reply_text(
            "❌ السلة فارغة.",
            reply_markup=main_keyboard(),
        )

        return

    try:

        while True:

            order_number = (
                f"GR-"
                f"{random.randint(100000, 999999)}"
            )

            if not order_exists(
                order_number
            ):
                break

    except Exception as error:

        print(
            f"Database order number "
            f"error: {error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ تعذر الاتصال بقاعدة "
            "البيانات حالياً."
        )

        return

    total = calculate_cart(cart)

    order = {
        "number": order_number,
        "chat_id": update.effective_chat.id,
        "user_id": update.effective_user.id,

        "name": context.user_data.get(
            "customer_name",
            "",
        ),

        "phone": context.user_data.get(
            "customer_phone",
            "",
        ),

        "wilaya": context.user_data.get(
            "customer_wilaya",
            "",
        ),

        "address": context.user_data.get(
            "customer_address",
            "",
        ),

        "cart": cart.copy(),
        "total": total,
        "status": "🟡 جديد",
    }

    try:

        save_order(order)

    except Exception as error:

        print(
            f"Database order save error: "
            f"{error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ حدث خطأ أثناء حفظ الطلب.\n\n"
            "حاول مرة أخرى بعد قليل."
        )

        return

    context.user_data["cart"] = {}
    context.user_data["step"] = None

    await update.message.reply_text(
        "✅ تم تأكيد طلبك بنجاح\n\n"

        f"🔢 رقم الطلب: "
        f"{order_number}\n"

        f"💰 المجموع: "
        f"{total:,} دج\n"

        "📦 الحالة: جديد\n\n"

        "احتفظ برقم الطلب للمتابعة.\n\n"

        "🟢 GREENINK",
        reply_markup=main_keyboard(),
    )

    await send_order_to_admins(
        context,
        order_number,
    )


# =========================================================
# CUSTOMER ORDERS
# =========================================================

async def show_orders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat_id = update.effective_chat.id

    try:

        orders = get_customer_orders(
            chat_id,
            10,
        )

    except Exception as error:

        print(
            f"Get orders error: "
            f"{error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ تعذر تحميل الطلبات حالياً.",
            reply_markup=main_keyboard(),
        )

        return

    if not orders:

        await update.message.reply_text(
            "📦 طلباتي\n\n"
            "لا توجد طلبات حالياً.",
            reply_markup=main_keyboard(),
        )

        return

    text = "📦 طلباتي\n\n"

    for order in orders:

        text += (
            f"🔢 رقم الطلب: "
            f"{order['order_number']}\n"

            f"💰 المبلغ: "
            f"{order['total']:,} دج\n"

            f"📍 الولاية: "
            f"{order['wilaya']}\n"

            f"📦 الحالة: "
            f"{order['status']}\n"

            "━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(),
    )


# =========================================================
# UPDATE ADMIN MESSAGES
# =========================================================

async def update_admin_messages(
    context: ContextTypes.DEFAULT_TYPE,
    order_number,
):
    order = get_order(order_number)

    if not order:
        return

    text = build_admin_order_text(order)

    admin_messages = get_admin_messages(
        order_number
    )

    for item in admin_messages:

        try:

            await context.bot.edit_message_text(
                chat_id=item[
                    "admin_chat_id"
                ],

                message_id=item[
                    "message_id"
                ],

                text=text,

                reply_markup=admin_order_keyboard(
                    order_number
                ),
            )

        except Exception as error:

            print(
                "Admin message update: "
                f"{error}",
                flush=True,
            )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    admin_id = query.from_user.id

    if admin_id not in ADMIN_CHAT_IDS:

        await query.answer(
            "❌ غير مسموح لك "
            "بإدارة الطلبات",
            show_alert=True,
        )

        return

    try:

        action, order_number = (
            query.data.split(":", 1)
        )

    except Exception:

        await query.answer(
            "❌ أمر غير صالح",
            show_alert=True,
        )

        return

    try:

        order = get_order(
            order_number
        )

    except Exception as error:

        print(
            f"Get admin order error: "
            f"{error}",
            flush=True,
        )

        await query.answer(
            "❌ تعذر الاتصال "
            "بقاعدة البيانات",
            show_alert=True,
        )

        return

    if not order:

        await query.answer(
            "❌ الطلب غير موجود",
            show_alert=True,
        )

        return

    status_map = {
        "accept": "✅ تم قبول الطلب",
        "prepare": "📦 قيد التحضير",
        "delivery": "🚚 قيد التوصيل",
        "done": "✅ تم التسليم",
        "cancel": "❌ تم إلغاء الطلب",
    }

    new_status = status_map.get(action)

    if not new_status:

        await query.answer(
            "❌ حالة غير صالحة",
            show_alert=True,
        )

        return

    if order["status"] == new_status:

        await query.answer(
            "الحالة راهي "
            "محدثة من قبل ✅"
        )

        return

    try:

        update_order_status(
            order_number,
            new_status,
        )

    except Exception as error:

        print(
            f"Status database error: "
            f"{error}",
            flush=True,
        )

        await query.answer(
            "❌ خطأ في تحديث الطلب",
            show_alert=True,
        )

        return

    await query.answer(
        "تم تحديث حالة الطلب ✅"
    )

    try:

        await update_admin_messages(
            context,
            order_number,
        )

    except Exception as error:

        print(
            f"Admin messages update "
            f"error: {error}",
            flush=True,
        )

    try:

        await context.bot.send_message(
            chat_id=order[
                "customer_chat_id"
            ],

            text=customer_status_message(
                order_number,
                new_status,
            ),
        )

    except Exception as error:

        print(
            "Customer notification "
            f"error: {error}",
            flush=True,
        )


# =========================================================
# TEXT BUTTONS
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text

    step = context.user_data.get("step")

    if step in [
        "name",
        "phone",
        "wilaya",
        "address",
    ]:

        handled = (
            await process_order_data(
                update,
                context,
            )
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
            "❌ تم إلغاء عملية "
            "تأكيد الطلب.\n\n"
            "السلة لم يتم حذفها.",
            reply_markup=main_keyboard(),
        )

    elif text == "🖨 الطابعات":

        await show_printers(update)

    elif text == "🏠 الرئيسية":

        await start(
            update,
            context,
        )

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
            "قريباً سنضيف أنواع "
            "الأحبار هنا.",
            reply_markup=main_keyboard(),
        )

    elif text == "⚙️ قطع الغيار":

        await update.message.reply_text(
            "⚙️ قسم قطع الغيار\n\n"
            "قريباً سنضيف قطع "
            "الغيار هنا.",
            reply_markup=main_keyboard(),
        )

    elif text == "☎️ اتصل بنا":

        await update.message.reply_text(
            "☎️ اتصل بنا - GREENINK\n\n"

            "📱 0560095387\n"
            "أبوبكر\n\n"

            "📱 0775635460\n"
            "عبد الحق\n\n"

            "🟢 نحن في خدمتكم.",
            reply_markup=main_keyboard(),
        )

    else:

        await update.message.reply_text(
            "👇 اختر أحد الأقسام "
            "من القائمة",
            reply_markup=main_keyboard(),
        )


# =========================================================
# ERRORS
# =========================================================

async def error_handler(
    update,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(
        "TELEGRAM ERROR:",
        repr(context.error),
        flush=True,
    )


# =========================================================
# STARTUP
# =========================================================

async def post_init(application):
    print(
        "Initializing PostgreSQL...",
        flush=True,
    )

    last_error = None

    # نحاول 3 مرات فقط
    for attempt in range(1, 4):

        try:

            print(
                f"PostgreSQL attempt "
                f"{attempt}/3",
                flush=True,
            )

            init_database()

            print(
                "PostgreSQL database ready ✅",
                flush=True,
            )

            last_error = None
            break

        except Exception as error:

            last_error = error

            print(
                f"POSTGRES ERROR: "
                f"{type(error).__name__}: "
                f"{error}",
                flush=True,
            )

            if attempt < 3:
                print(
                    "Retrying PostgreSQL "
                    "in 3 seconds...",
                    flush=True,
                )

                time.sleep(3)

    if last_error is not None:
        raise last_error

    print(
        f"Admins loaded: "
        f"{len(ADMIN_CHAT_IDS)}",
        flush=True,
    )


def main():
    print(
        "Starting GREENINK Bot...",
        flush=True,
    )

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not configured"
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

    print(
        "Environment variables OK ✅",
        flush=True,
    )

    app = (
        Application
        .builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            my_id,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_callback
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            buttons,
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "Telegram polling starting...",
        flush=True,
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
