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

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


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

                    status TEXT NOT NULL
                    DEFAULT '🟡 جديد',

                    shipment_image_file_id TEXT,

                    created_at TIMESTAMPTZ
                    NOT NULL DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                    NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS
                shipment_image_file_id TEXT;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    id BIGSERIAL PRIMARY KEY,

                    order_number VARCHAR(30)
                    NOT NULL
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
                    order_number VARCHAR(30)
                    NOT NULL
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


def save_shipment_image(
    order_number,
    file_id,
):
    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE orders
                SET
                    shipment_image_file_id = %s,
                    updated_at = NOW()
                WHERE order_number = %s
                """,
                (
                    file_id,
                    order_number,
                ),
            )

        conn.commit()


# =========================================================
# MAIN KEYBOARDS
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


# =========================================================
# PRODUCT INLINE BUTTONS
# =========================================================

def product_inline_keyboard(product_code):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛍️ اطلب الآن",
                    callback_data=f"buy:{product_code}",
                ),
                InlineKeyboardButton(
                    "🛒 أضف إلى السلة",
                    callback_data=f"cart:{product_code}",
                ),
            ]
        ]
    )


# =========================================================
# ADMIN INLINE BUTTONS
# =========================================================

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


def delivery_photo_keyboard(order_number):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📷 تصوير الوصل",
                    callback_data=(
                        f"delivery_camera:"
                        f"{order_number}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🖼️ اختيار صورة",
                    callback_data=(
                        f"delivery_gallery:"
                        f"{order_number}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⏭️ بدون صورة",
                    callback_data=(
                        f"delivery_skip:"
                        f"{order_number}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ إلغاء",
                    callback_data=(
                        f"delivery_cancel:"
                        f"{order_number}"
                    ),
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


def parse_customer_info(text):
    name = ""
    phone = ""
    wilaya = ""

    for line in text.splitlines():

        line = line.strip()

        if line.startswith("الاسم:"):

            name = line.replace(
                "الاسم:",
                "",
                1,
            ).strip()

        elif line.startswith("الهاتف:"):

            phone = line.replace(
                "الهاتف:",
                "",
                1,
            ).strip()

        elif line.startswith("الولاية:"):

            wilaya = line.replace(
                "الولاية:",
                "",
                1,
            ).strip()

    return name, phone, wilaya


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
# START
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
    await update.message.reply_text(
        "🆔 Chat ID تاع هذا الحساب هو:\n\n"
        f"{update.effective_chat.id}"
    )


# =========================================================
# SHOW PRODUCTS
# =========================================================

async def show_printers(update: Update):
    await update.message.reply_text(
        "🖨 قسم الطابعات\n\n"
        "اختر المنتج 👇",
        reply_markup=printers_keyboard(),
    )

    for code, product in PRODUCTS.items():

        image_path = find_product_image(
            product
        )

        caption = (
            f"🖨 {product['name']}\n\n"
            f"💰 السعر: "
            f"{product['price']:,} دج"
        )

        if image_path:

            try:

                with open(
                    image_path,
                    "rb",
                ) as photo:

                    await update.message.reply_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=(
                            product_inline_keyboard(
                                code
                            )
                        ),
                    )

            except Exception as error:

                print(
                    f"Image error for "
                    f"{code}: {error}",
                    flush=True,
                )

                await update.message.reply_text(
                    caption,
                    reply_markup=(
                        product_inline_keyboard(
                            code
                        )
                    ),
                )

        else:

            await update.message.reply_text(
                caption,
                reply_markup=(
                    product_inline_keyboard(
                        code
                    )
                ),
            )


# =========================================================
# DIRECT BUY
# =========================================================

async def start_direct_order_callback(
    query,
    context,
    product_code,
):
    product = PRODUCTS.get(
        product_code
    )

    if not product:

        await query.answer(
            "❌ المنتج غير موجود",
            show_alert=True,
        )

        return

    context.user_data["cart"] = {
        product_code: 1
    }

    context.user_data[
        "direct_order"
    ] = True

    context.user_data[
        "step"
    ] = "customer_info"

    await query.answer()

    await query.message.reply_text(
        "🛍️ شراء مباشر\n\n"

        f"🖨 {product['name']}\n"
        f"💰 {product['price']:,} دج\n\n"

        "أرسل معلوماتك في "
        "رسالة واحدة هكذا:\n\n"

        "الاسم: محمد\n"
        "الهاتف: 0550000000\n"
        "الولاية: تلمسان"
    )


# =========================================================
# ADD PRODUCT TO CART
# =========================================================

async def add_product_callback(
    query,
    context,
    product_code,
):
    product = PRODUCTS.get(
        product_code
    )

    if not product:

        await query.answer(
            "❌ المنتج غير موجود",
            show_alert=True,
        )

        return

    cart = context.user_data.setdefault(
        "cart",
        {},
    )

    cart[product_code] = (
        cart.get(product_code, 0)
        + 1
    )

    await query.answer(
        "✅ تمت الإضافة إلى السلة"
    )

    await query.message.reply_text(
        "🛒 تمت الإضافة للسلة\n\n"

        f"🖨 {product['name']}\n"
        f"🔢 الكمية: "
        f"{cart[product_code]}"
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
# BEGIN CART ORDER
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

    context.user_data[
        "direct_order"
    ] = False

    context.user_data[
        "step"
    ] = "customer_info"

    await update.message.reply_text(
        "📝 معلومات الطلب\n\n"

        "أرسل معلوماتك في "
        "رسالة واحدة هكذا:\n\n"

        "الاسم: محمد\n"
        "الهاتف: 0550000000\n"
        "الولاية: تلمسان"
    )


# =========================================================
# CUSTOMER DATA
# =========================================================

async def process_order_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    step = context.user_data.get(
        "step"
    )

    if not step:
        return False

    text = update.message.text.strip()

    if step == "customer_info":

        name, phone, wilaya = (
            parse_customer_info(text)
        )

        if (
            not name
            or not phone
            or not wilaya
        ):

            await update.message.reply_text(
                "❌ المعلومات ناقصة.\n\n"

                "أرسلها بهذا الشكل:\n\n"

                "الاسم: محمد\n"
                "الهاتف: 0550000000\n"
                "الولاية: تلمسان"
            )

            return True

        context.user_data[
            "customer_name"
        ] = name

        context.user_data[
            "customer_phone"
        ] = phone

        context.user_data[
            "customer_wilaya"
        ] = wilaya

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
# SEND ORDER TO ADMINS
# =========================================================

async def send_order_to_admins(
    context,
    order_number,
):
    if not ADMIN_CHAT_IDS:

        print(
            "ADMIN_CHAT_IDS "
            "is not configured",
            flush=True,
        )

        return

    order = get_order(
        order_number
    )

    if not order:
        return

    text = build_admin_order_text(
        order
    )

    for admin_id in ADMIN_CHAT_IDS:

        try:

            message = (
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=(
                        admin_order_keyboard(
                            order_number
                        )
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
            f"Database error: {error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ تعذر الاتصال "
            "بقاعدة البيانات."
        )

        return

    total = calculate_cart(
        cart
    )

    order = {
        "number": order_number,

        "chat_id":
            update.effective_chat.id,

        "user_id":
            update.effective_user.id,

        "name":
            context.user_data.get(
                "customer_name",
                "",
            ),

        "phone":
            context.user_data.get(
                "customer_phone",
                "",
            ),

        "wilaya":
            context.user_data.get(
                "customer_wilaya",
                "",
            ),

        "address":
            context.user_data.get(
                "customer_address",
                "",
            ),

        "cart":
            cart.copy(),

        "total":
            total,

        "status":
            "🟡 جديد",
    }

    try:

        save_order(order)

    except Exception as error:

        print(
            f"Save order error: {error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ حدث خطأ أثناء "
            "حفظ الطلب."
        )

        return

    context.user_data["cart"] = {}
    context.user_data["step"] = None
    context.user_data["direct_order"] = False

    await update.message.reply_text(
        "✅ تم تأكيد طلبك بنجاح\n\n"

        f"🔢 رقم الطلب: "
        f"{order_number}\n"

        f"💰 المجموع: "
        f"{total:,} دج\n"

        "📦 الحالة: جديد\n\n"

        "احتفظ برقم الطلب "
        "للمتابعة.\n\n"

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
    try:

        orders = get_customer_orders(
            update.effective_chat.id,
            10,
        )

    except Exception as error:

        print(
            f"Get orders error: {error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ تعذر تحميل الطلبات.",
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
            f"🔢 {order['order_number']}\n"

            f"💰 "
            f"{order['total']:,} دج\n"

            f"📍 "
            f"{order['wilaya']}\n"

            f"📦 "
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
    context,
    order_number,
):
    order = get_order(
        order_number
    )

    if not order:
        return

    text = build_admin_order_text(
        order
    )

    messages = get_admin_messages(
        order_number
    )

    for item in messages:

        try:

            await context.bot.edit_message_text(
                chat_id=item[
                    "admin_chat_id"
                ],

                message_id=item[
                    "message_id"
                ],

                text=text,

                reply_markup=(
                    admin_order_keyboard(
                        order_number
                    )
                ),
            )

        except Exception as error:

            print(
                f"Admin message update: "
                f"{error}",
                flush=True,
            )


# =========================================================
# DELIVERY WITHOUT IMAGE
# =========================================================

async def finish_delivery_without_image(
    context,
    order_number,
):
    order = get_order(
        order_number
    )

    if not order:
        return

    update_order_status(
        order_number,
        "🚚 قيد التوصيل",
    )

    await update_admin_messages(
        context,
        order_number,
    )

    await context.bot.send_message(
        chat_id=order[
            "customer_chat_id"
        ],

        text=customer_status_message(
            order_number,
            "🚚 قيد التوصيل",
        ),
    )


# =========================================================
# CALLBACKS
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    try:

        action, value = (
            query.data.split(
                ":",
                1,
            )
        )

    except Exception:

        await query.answer(
            "❌ أمر غير صالح",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # CUSTOMER PRODUCT BUTTONS
    # -----------------------------------------------------

    if action == "buy":

        await start_direct_order_callback(
            query,
            context,
            value,
        )

        return

    if action == "cart":

        await add_product_callback(
            query,
            context,
            value,
        )

        return

    # -----------------------------------------------------
    # ADMIN SECURITY
    # -----------------------------------------------------

    admin_id = query.from_user.id

    if admin_id not in ADMIN_CHAT_IDS:

        await query.answer(
            "❌ غير مسموح لك "
            "بإدارة الطلبات",
            show_alert=True,
        )

        return

    order_number = value

    # -----------------------------------------------------
    # DELIVERY MAIN
    # -----------------------------------------------------

    if action == "delivery":

        order = get_order(
            order_number
        )

        if not order:

            await query.answer(
                "❌ الطلب غير موجود",
                show_alert=True,
            )

            return

        await query.answer()

        await context.bot.send_message(
            chat_id=admin_id,

            text=(
                "🚚 تجهيز التوصيل\n\n"

                f"🔢 الطلب: "
                f"{order_number}\n\n"

                "هل تريد إرسال "
                "صورة تتبع الطرد؟"
            ),

            reply_markup=(
                delivery_photo_keyboard(
                    order_number
                )
            ),
        )

        return

    # -----------------------------------------------------
    # DELIVERY IMAGE MODE
    # -----------------------------------------------------

    if action in (
        "delivery_camera",
        "delivery_gallery",
    ):

        context.user_data[
            "pending_delivery_order"
        ] = order_number

        await query.answer()

        await context.bot.send_message(
            chat_id=admin_id,

            text=(
                "📸 أرسل الآن صورة "
                "وصل أو تتبع الطرد.\n\n"

                "استعمل زر 📎 أو 📷 "
                "في Telegram.\n\n"

                f"🔢 الطلب: "
                f"{order_number}"
            ),
        )

        return

    # -----------------------------------------------------
    # DELIVERY SKIP IMAGE
    # -----------------------------------------------------

    if action == "delivery_skip":

        await query.answer(
            "تم تحويل الطلب "
            "للتوصيل ✅"
        )

        await finish_delivery_without_image(
            context,
            order_number,
        )

        return

    # -----------------------------------------------------
    # DELIVERY CANCEL
    # -----------------------------------------------------

    if action == "delivery_cancel":

        context.user_data.pop(
            "pending_delivery_order",
            None,
        )

        await query.answer(
            "تم الإلغاء"
        )

        return

    # -----------------------------------------------------
    # NORMAL ADMIN STATUS
    # -----------------------------------------------------

    order = get_order(
        order_number
    )

    if not order:

        await query.answer(
            "❌ الطلب غير موجود",
            show_alert=True,
        )

        return

    status_map = {
        "accept":
            "✅ تم قبول الطلب",

        "prepare":
            "📦 قيد التحضير",

        "done":
            "✅ تم التسليم",

        "cancel":
            "❌ تم إلغاء الطلب",
    }

    new_status = status_map.get(
        action
    )

    if not new_status:

        await query.answer(
            "❌ حالة غير صالحة",
            show_alert=True,
        )

        return

    if order["status"] == new_status:

        await query.answer(
            "الحالة محدثة من قبل ✅"
        )

        return

    update_order_status(
        order_number,
        new_status,
    )

    await query.answer(
        "تم تحديث حالة الطلب ✅"
    )

    await update_admin_messages(
        context,
        order_number,
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
            f"Customer notification "
            f"error: {error}",
            flush=True,
        )


# =========================================================
# DELIVERY PHOTO
# =========================================================

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    admin_id = update.effective_user.id

    if admin_id not in ADMIN_CHAT_IDS:
        return

    order_number = (
        context.user_data.get(
            "pending_delivery_order"
        )
    )

    if not order_number:
        return

    order = get_order(
        order_number
    )

    if not order:

        await update.message.reply_text(
            "❌ الطلب غير موجود."
        )

        return

    photo = update.message.photo[-1]

    file_id = photo.file_id

    try:

        save_shipment_image(
            order_number,
            file_id,
        )

        update_order_status(
            order_number,
            "🚚 قيد التوصيل",
        )

    except Exception as error:

        print(
            f"Shipment image error: "
            f"{error}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ تعذر حفظ صورة التتبع."
        )

        return

    context.user_data.pop(
        "pending_delivery_order",
        None,
    )

    await update.message.reply_text(
        "✅ تم حفظ صورة التتبع "
        "وإرسالها للزبون."
    )

    await update_admin_messages(
        context,
        order_number,
    )

    await context.bot.send_message(
        chat_id=order[
            "customer_chat_id"
        ],

        text=customer_status_message(
            order_number,
            "🚚 قيد التوصيل",
        ),
    )

    await context.bot.send_photo(
        chat_id=order[
            "customer_chat_id"
        ],

        photo=file_id,

        caption=(
            "📦 صورة تتبع الطرد\n\n"

            f"🔢 رقم الطلب: "
            f"{order_number}\n"

            "🚚 طلبك راه "
            "قيد التوصيل.\n\n"

            "🟢 GREENINK"
        ),
    )


# =========================================================
# TEXT BUTTONS
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text

    step = context.user_data.get(
        "step"
    )

    if step in (
        "customer_info",
        "address",
    ):

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

        context.user_data[
            "step"
        ] = None

        context.user_data[
            "direct_order"
        ] = False

        context.user_data[
            "cart"
        ] = {}

        await update.message.reply_text(
            "❌ تم إلغاء الطلب.",
            reply_markup=main_keyboard(),
        )

    elif text == "🖨 الطابعات":

        await show_printers(
            update
        )

    elif text == "🏠 الرئيسية":

        await start(
            update,
            context,
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

        context.user_data[
            "cart"
        ] = {}

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
            "قريباً سنضيف المنتجات.",
            reply_markup=main_keyboard(),
        )

    elif text == "⚙️ قطع الغيار":

        await update.message.reply_text(
            "⚙️ قسم قطع الغيار\n\n"
            "قريباً سنضيف المنتجات.",
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
# ERROR HANDLER
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

    for attempt in range(
        1,
        4,
    ):

        try:

            print(
                f"PostgreSQL attempt "
                f"{attempt}/3",
                flush=True,
            )

            init_database()

            print(
                "PostgreSQL ready ✅",
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
            callback_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
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
