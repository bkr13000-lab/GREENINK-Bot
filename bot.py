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
            print(f"Invalid admin ID: {item}", flush=True)

    return admins


ADMIN_CHAT_IDS = load_admin_ids()


# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = {
    "WF-C5390": {
        "category": "printer",
        "name": "EPSON WF-C5390",
        "price": 195000,
        "description": (
            "🖨 EPSON WF-C5390\n"
            "✅ طابعة احترافية"
        ),
        "images": [
            "WF-C5390_headon_690x460.jpg",
        ],
    },

    "WF-C5890": {
        "category": "printer",
        "name": "EPSON WF-C5890",
        "price": 220000,
        "description": (
            "🖨 EPSON WF-C5890\n"
            "✅ طابعة احترافية"
        ),
        "images": [
            "WF-C5890_headon_690x460.jpg",
        ],
    },

    "L15160": {
        "category": "printer",
        "name": "EPSON L15160",
        "price": 210000,
        "description": (
            "🖨 EPSON L15160\n"
            "✅ طابعة احترافية"
        ),
        "images": [
            "EPSON L15160.jpg",
            "EPSON_L15160.jpg",
            "L15160.jpg",
            "EPSON L15160.jpeg",
            "L15160.jpeg",
            "EPSON L15160.png",
        ],
    },

    "INK-5390-5890": {
        "category": "ink",
        "name": "GREENINK WF-C5390 / WF-C5890",
        "price": 8000,
        "description": (
            "🧴 حبر GREENINK احترافي\n"
            "⚖️ السعة: 1KG\n\n"
            "🎨 متوفر بأربعة ألوان\n"
            "🖤 Black\n"
            "💙 Cyan\n"
            "❤️ Magenta\n"
            "💛 Yellow\n\n"
            "✅ متوافق مع:\n"
            "• EPSON WF-C5390\n"
            "• EPSON WF-C5890"
        ),
        "images": [
            "GREENINK_5390_5890_INK.png",
            "GREENINK_5390_5890_INK.jpg",
        ],
    },

    "PACK-5390": {
        "category": "pack",
        "name": "Pack WF-C5390 + 4 ألوان GREENINK",
        "price": 203000,
        "description": (
            "🔥 PACK GREENINK\n\n"
            "🖨 EPSON WF-C5390\n"
            "➕\n"
            "🧴 4 ألوان GREENINK\n\n"
            "🖤 Black 1KG\n"
            "💙 Cyan 1KG\n"
            "❤️ Magenta 1KG\n"
            "💛 Yellow 1KG\n\n"
            "🎁 Pack كامل جاهز"
        ),
        "images": [
            "WF-C5390_headon_690x460.jpg",
        ],
    },

    "PACK-5890": {
        "category": "pack",
        "name": "Pack WF-C5890 + 4 ألوان GREENINK",
        "price": 218000,
        "description": (
            "🔥 PACK GREENINK\n\n"
            "🖨 EPSON WF-C5890\n"
            "➕\n"
            "🧴 4 ألوان GREENINK\n\n"
            "🖤 Black 1KG\n"
            "💙 Cyan 1KG\n"
            "❤️ Magenta 1KG\n"
            "💛 Yellow 1KG\n\n"
            "🎁 Pack كامل جاهز"
        ),
        "images": [
            "WF-C5890_headon_690x460.jpg",
        ],
    },
}


# =========================================================
# WILAYAS
# =========================================================

WILAYAS = [
    "أدرار",
    "الشلف",
    "الأغواط",
    "أم البواقي",
    "باتنة",
    "بجاية",
    "بسكرة",
    "بشار",
    "البليدة",
    "البويرة",
    "تمنراست",
    "تبسة",
    "تلمسان",
    "تيارت",
    "تيزي وزو",
    "الجزائر",
    "الجلفة",
    "جيجل",
    "سطيف",
    "سعيدة",
    "سكيكدة",
    "سيدي بلعباس",
    "عنابة",
    "قالمة",
    "قسنطينة",
    "المدية",
    "مستغانم",
    "المسيلة",
    "معسكر",
    "ورقلة",
    "وهران",
    "البيض",
    "إليزي",
    "برج بوعريريج",
    "بومرداس",
    "الطارف",
    "تندوف",
    "تيسمسيلت",
    "الوادي",
    "خنشلة",
    "سوق أهراس",
    "تيبازة",
    "ميلة",
    "عين الدفلى",
    "النعامة",
    "عين تموشنت",
    "غرداية",
    "غليزان",
    "تيميمون",
    "برج باجي مختار",
    "أولاد جلال",
    "بني عباس",
    "عين صالح",
    "عين قزام",
    "تقرت",
    "جانت",
    "المغير",
    "المنيعة",
]


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🔥 العروض", "🖨 الطابعات"],
            ["🧴 الأحبار", "⚙️ قطع الغيار"],
            ["🛒 السلة", "📦 طلباتي"],
            ["☎️ اتصل بنا"],
        ],
        resize_keyboard=True,
    )


def shop_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🔥 العروض", "🛒 السلة"],
            ["🖨 الطابعات", "🧴 الأحبار"],
            ["🏠 الرئيسية"],
        ],
        resize_keyboard=True,
    )


def cart_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["✅ تأكيد الطلب"],
            ["🗑 تفريغ السلة"],
            ["🔥 العروض"],
            ["🖨 الطابعات", "🧴 الأحبار"],
            ["🏠 الرئيسية"],
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


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["❌ إلغاء الطلب"],
        ],
        resize_keyboard=True,
    )


def product_inline_keyboard(product_code):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "اطلب الآن",
                    callback_data=f"buy:{product_code}",
                    style="success",
                ),
                InlineKeyboardButton(
                    "🛒 أضف للسلة",
                    callback_data=f"cart:{product_code}",
                ),
            ]
        ]
    )


def wilaya_keyboard():
    rows = []

    for i in range(0, len(WILAYAS), 2):
        row = [
            InlineKeyboardButton(
                WILAYAS[i],
                callback_data=f"wilaya:{i}",
            )
        ]

        if i + 1 < len(WILAYAS):
            row.append(
                InlineKeyboardButton(
                    WILAYAS[i + 1],
                    callback_data=f"wilaya:{i + 1}",
                )
            )

        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                "❌ إلغاء",
                callback_data="order_cancel_inline",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


# =========================================================
# ADMIN KEYBOARDS
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
                    callback_data=f"delivery_camera:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🖼 اختيار صورة",
                    callback_data=f"delivery_gallery:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "⏭ بدون صورة",
                    callback_data=f"delivery_skip:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ إلغاء",
                    callback_data=f"delivery_cancel:{order_number}",
                )
            ],
        ]
    )


# =========================================================
# DATABASE
# =========================================================

def db_connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not found")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


def init_database():
    print("Creating/checking PostgreSQL tables...", flush=True)

    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id BIGSERIAL PRIMARY KEY,
                    order_number TEXT UNIQUE NOT NULL,
                    customer_chat_id BIGINT NOT NULL,
                    telegram_username TEXT,
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    wilaya TEXT NOT NULL,
                    address TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT '🆕 طلب جديد',
                    shipment_image_file_id TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS telegram_username TEXT
                """
            )

            cur.execute(
                """
                ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS shipment_image_file_id TEXT
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    id BIGSERIAL PRIMARY KEY,
                    order_number TEXT NOT NULL,
                    product_code TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price INTEGER NOT NULL,
                    subtotal INTEGER NOT NULL
                )
                """
            )

            cur.execute(
                """
                ALTER TABLE order_items
                ADD COLUMN IF NOT EXISTS product_code TEXT
                """
            )

            cur.execute(
                """
                ALTER TABLE order_items
                ADD COLUMN IF NOT EXISTS product_name TEXT
                """
            )

            cur.execute(
                """
                ALTER TABLE order_items
                ADD COLUMN IF NOT EXISTS quantity INTEGER
                """
            )

            cur.execute(
                """
                ALTER TABLE order_items
                ADD COLUMN IF NOT EXISTS unit_price INTEGER
                """
            )

            cur.execute(
                """
                ALTER TABLE order_items
                ADD COLUMN IF NOT EXISTS subtotal INTEGER
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_messages (
                    id BIGSERIAL PRIMARY KEY,
                    order_number TEXT NOT NULL,
                    admin_chat_id BIGINT NOT NULL,
                    message_id BIGINT NOT NULL,
                    UNIQUE(order_number, admin_chat_id)
                )
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_orders_customer
                ON orders(customer_chat_id)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_orders_number
                ON orders(order_number)
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_order_items_number
                ON order_items(order_number)
                """
            )

        conn.commit()

    print("PostgreSQL database initialized ✅", flush=True)


def order_exists(order_number):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM orders WHERE order_number = %s",
                (order_number,),
            )

            return cur.fetchone() is not None


def save_order(
    order_number,
    customer_chat_id,
    username,
    name,
    phone,
    wilaya,
    address,
    cart,
):
    total = calculate_cart_total(cart)

    with db_connect() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO orders (
                    order_number,
                    customer_chat_id,
                    telegram_username,
                    customer_name,
                    phone,
                    wilaya,
                    address,
                    total,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    order_number,
                    customer_chat_id,
                    username,
                    name,
                    phone,
                    wilaya,
                    address,
                    total,
                    "🆕 طلب جديد",
                ),
            )

            for code, quantity in cart.items():
                product = PRODUCTS.get(code)

                if not product:
                    continue

                subtotal = product["price"] * quantity

                cur.execute(
                    """
                    INSERT INTO order_items (
                        order_number,
                        product_code,
                        product_name,
                        quantity,
                        unit_price,
                        subtotal
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order_number,
                        code,
                        product["name"],
                        quantity,
                        product["price"],
                        subtotal,
                    ),
                )

        conn.commit()

    return total


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

    return {
        "order": order,
        "items": items,
    }


def get_customer_orders(chat_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM orders
                WHERE customer_chat_id = %s
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (chat_id,),
            )

            return cur.fetchall()


def update_order_status(order_number, status):
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
                    status,
                    order_number,
                ),
            )

        conn.commit()


def save_shipment_image(order_number, file_id):
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
                ON CONFLICT (
                    order_number,
                    admin_chat_id
                )
                DO UPDATE
                SET message_id = EXCLUDED.message_id
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
                SELECT *
                FROM admin_messages
                WHERE order_number = %s
                """,
                (order_number,),
            )

            return cur.fetchall()


# =========================================================
# HELPERS
# =========================================================

def find_product_image(product):
    for filename in product.get("images", []):
        path = Path(filename)

        if path.exists():
            return path

    return None


def build_product_caption(product):
    return (
        f"{product['description']}\n\n"
        f"💰 السعر: {product['price']:,} دج"
    )


def calculate_cart_total(cart):
    total = 0

    for code, quantity in cart.items():
        product = PRODUCTS.get(code)

        if product:
            total += product["price"] * quantity

    return total


def build_cart_text(cart):
    if not cart:
        return "🛒 السلة فارغة."

    lines = [
        "🛒 سلة المشتريات",
        "━━━━━━━━━━━━━━",
        "",
    ]

    for code, quantity in cart.items():
        product = PRODUCTS.get(code)

        if not product:
            continue

        subtotal = product["price"] * quantity

        lines.extend(
            [
                f"📦 {product['name']}",
                f"الكمية: {quantity}",
                f"المجموع: {subtotal:,} دج",
                "",
            ]
        )

    total = calculate_cart_total(cart)

    lines.extend(
        [
            "━━━━━━━━━━━━━━",
            f"💰 الإجمالي: {total:,} دج",
        ]
    )

    return "\n".join(lines)


def generate_order_number():
    for _ in range(20):
        order_number = f"GR-{random.randint(100000, 999999)}"

        try:
            if not order_exists(order_number):
                return order_number
        except Exception:
            pass

    return f"GR-{int(time.time())}"


def build_order_text(data):
    order = data["order"]
    items = data["items"]

    lines = [
        f"🧾 الطلب: {order['order_number']}",
        "━━━━━━━━━━━━━━",
        "",
    ]

    for item in items:
        lines.extend(
            [
                f"📦 {item['product_name']}",
                f"الكمية: {item['quantity']}",
                f"السعر: {item['unit_price']:,} دج",
                f"المجموع: {item['subtotal']:,} دج",
                "",
            ]
        )

    username = order.get("telegram_username")

    username_text = (
        f"@{username}"
        if username
        else "بدون username"
    )

    lines.extend(
        [
            "━━━━━━━━━━━━━━",
            f"👤 الزبون: {order['customer_name']}",
            f"📱 الهاتف: {order['phone']}",
            f"📍 الولاية: {order['wilaya']}",
            f"🏠 العنوان: {order['address']}",
            f"💬 Telegram: {username_text}",
            "",
            f"💰 الإجمالي: {order['total']:,} دج",
            "",
            f"📌 الحالة: {order['status']}",
        ]
    )

    return "\n".join(lines)


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("step", None)
    context.user_data.pop("order_data", None)
    context.user_data.pop("direct_order", None)

    await update.message.reply_text(
        (
            "🟢 GREENINK\n\n"
            "مرحبا بك في متجر GREENINK 👋\n\n"
            "🔥 Packs وعروض\n"
            "🖨 طابعات\n"
            "🧴 أحبار\n"
            "⚙️ قطع غيار\n\n"
            "اختر القسم الذي تريد 👇"
        ),
        reply_markup=main_keyboard(),
    )


async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        f"Chat ID:\n{update.effective_chat.id}"
    )


# =========================================================
# PRODUCTS
# =========================================================

async def show_category(
    update: Update,
    category: str,
):
    titles = {
        "printer": (
            "🖨 طابعات GREENINK\n\n"
            "اختر الطابعة 👇"
        ),
        "ink": (
            "🧴 أحبار GREENINK\n\n"
            "اختر المنتج 👇"
        ),
        "pack": (
            "🔥 عروض GREENINK\n\n"
            "🎁 Packs جاهزة\n"
            "طابعة + 4 ألوان GREENINK 👇"
        ),
    }

    await update.message.reply_text(
        titles.get(
            category,
            "المنتجات 👇",
        ),
        reply_markup=shop_keyboard(),
    )

    for code, product in PRODUCTS.items():
        if product.get("category") != category:
            continue

        caption = build_product_caption(product)
        image_path = find_product_image(product)

        if image_path:
            try:
                with open(image_path, "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=product_inline_keyboard(code),
                    )

                continue

            except Exception as exc:
                print(
                    f"Product image error {image_path}: {exc}",
                    flush=True,
                )

        await update.message.reply_text(
            caption,
            reply_markup=product_inline_keyboard(code),
        )


# =========================================================
# CART
# =========================================================

async def show_cart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get("cart", {})

    await update.message.reply_text(
        build_cart_text(cart),
        reply_markup=cart_keyboard(),
    )


async def add_product_callback(
    query,
    context,
    product_code,
):
    product = PRODUCTS.get(product_code)

    if not product:
        await query.answer(
            "المنتج غير موجود",
            show_alert=True,
        )
        return

    cart = context.user_data.setdefault("cart", {})

    cart[product_code] = (
        cart.get(product_code, 0) + 1
    )

    await query.answer(
        f"✅ تمت الإضافة للسلة ×{cart[product_code]}"
    )


# =========================================================
# CHECKOUT
# =========================================================

async def start_direct_order_callback(
    query,
    context,
    product_code,
):
    product = PRODUCTS.get(product_code)

    if not product:
        await query.answer(
            "المنتج غير موجود",
            show_alert=True,
        )
        return

    context.user_data["cart"] = {
        product_code: 1
    }

    context.user_data["direct_order"] = True
    context.user_data["order_data"] = {}
    context.user_data["step"] = "name"

    await query.answer()

    await query.message.reply_text(
        (
            "🛍 طلب مباشر\n\n"
            f"📦 {product['name']}\n"
            f"💰 {product['price']:,} دج\n\n"
            "👤 اكتب اسمك الكامل:"
        ),
        reply_markup=cancel_keyboard(),
    )


async def begin_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get("cart", {})

    if not cart:
        await update.message.reply_text(
            "🛒 السلة فارغة.",
            reply_markup=shop_keyboard(),
        )
        return

    context.user_data["order_data"] = {}
    context.user_data["step"] = "name"

    await update.message.reply_text(
        "👤 اكتب اسمك الكامل:",
        reply_markup=cancel_keyboard(),
    )


async def process_order_data(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()
    step = context.user_data.get("step")
    data = context.user_data.setdefault("order_data", {})

    if step == "name":
        if len(text) < 2:
            await update.message.reply_text(
                "⚠️ اكتب الاسم الكامل من فضلك."
            )
            return

        data["name"] = text
        context.user_data["step"] = "phone"

        await update.message.reply_text(
            "📱 اكتب رقم الهاتف:",
            reply_markup=cancel_keyboard(),
        )
        return

    if step == "phone":
        clean_phone = (
            text
            .replace(" ", "")
            .replace("-", "")
            .replace(".", "")
        )

        phone_check = (
            clean_phone[1:]
            if clean_phone.startswith("+")
            else clean_phone
        )

        if (
            not phone_check.isdigit()
            or len(phone_check) < 9
        ):
            await update.message.reply_text(
                "⚠️ رقم الهاتف غير صحيح.\n"
                "اكتب رقم هاتف صحيح."
            )
            return

        data["phone"] = clean_phone
        context.user_data["step"] = "wilaya"

        await update.message.reply_text(
            "📍 اختر الولاية من القائمة 👇",
            reply_markup=cancel_keyboard(),
        )

        await update.message.reply_text(
            "📍 الولايات:",
            reply_markup=wilaya_keyboard(),
        )
        return

    if step == "address":
        if len(text) < 3:
            await update.message.reply_text(
                "⚠️ اكتب العنوان الكامل."
            )
            return

        data["address"] = text
        context.user_data["step"] = "final_confirm"

        await show_order_review(
            update,
            context,
        )


async def select_wilaya_callback(
    query,
    context,
    index_text,
):
    if context.user_data.get("step") != "wilaya":
        await query.answer(
            "انتهت جلسة الطلب.",
            show_alert=True,
        )
        return

    try:
        index = int(index_text)
        wilaya = WILAYAS[index]

    except (
        ValueError,
        IndexError,
    ):
        await query.answer(
            "الولاية غير صحيحة.",
            show_alert=True,
        )
        return

    data = context.user_data.setdefault(
        "order_data",
        {},
    )

    data["wilaya"] = wilaya
    context.user_data["step"] = "address"

    await query.answer(
        f"📍 {wilaya}"
    )

    try:
        await query.edit_message_text(
            f"✅ الولاية: {wilaya}"
        )
    except Exception:
        pass

    await query.message.reply_text(
        (
            f"📍 الولاية: {wilaya}\n\n"
            "🏠 اكتب العنوان الكامل:"
        ),
        reply_markup=cancel_keyboard(),
    )


async def show_order_review(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get("cart", {})
    data = context.user_data.get("order_data", {})
    total = calculate_cart_total(cart)

    lines = [
        "🧾 تأكيد الطلب",
        "━━━━━━━━━━━━━━",
        "",
    ]

    for code, quantity in cart.items():
        product = PRODUCTS.get(code)

        if not product:
            continue

        subtotal = product["price"] * quantity

        lines.extend(
            [
                f"📦 {product['name']}",
                f"الكمية: {quantity}",
                f"المجموع: {subtotal:,} دج",
                "",
            ]
        )

    lines.extend(
        [
            "━━━━━━━━━━━━━━",
            f"👤 الاسم: {data.get('name', '')}",
            f"📱 الهاتف: {data.get('phone', '')}",
            f"📍 الولاية: {data.get('wilaya', '')}",
            f"🏠 العنوان: {data.get('address', '')}",
            "",
            f"💰 الإجمالي: {total:,} دج",
            "",
            "اضغط ✅ تأكيد نهائي لإرسال الطلب.",
        ]
    )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=confirm_keyboard(),
    )


async def final_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    cart = context.user_data.get("cart", {})
    data = context.user_data.get("order_data", {})

    if not cart:
        await update.message.reply_text(
            "🛒 السلة فارغة.",
            reply_markup=main_keyboard(),
        )
        return

    for key in (
        "name",
        "phone",
        "wilaya",
        "address",
    ):
        if not data.get(key):
            await update.message.reply_text(
                "⚠️ معلومات الطلب ناقصة."
            )
            return

    order_number = generate_order_number()
    username = update.effective_user.username

    try:
        total = save_order(
            order_number,
            update.effective_chat.id,
            username,
            data["name"],
            data["phone"],
            data["wilaya"],
            data["address"],
            cart,
        )

    except Exception as exc:
        print(
            f"Save order error: {exc}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ حدث خطأ أثناء تسجيل الطلب."
        )
        return

    context.user_data.pop("cart", None)
    context.user_data.pop("step", None)
    context.user_data.pop("order_data", None)
    context.user_data.pop("direct_order", None)

    await update.message.reply_text(
        (
            "✅ تم تسجيل طلبك بنجاح\n\n"
            f"🧾 رقم الطلب: {order_number}\n"
            f"💰 الإجمالي: {total:,} دج\n\n"
            "📦 سنقوم بإعلامك بكل تحديث على الطلب."
        ),
        reply_markup=main_keyboard(),
    )

    await notify_admins(
        context,
        order_number,
    )


async def cancel_current_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("step", None)
    context.user_data.pop("order_data", None)
    context.user_data.pop("direct_order", None)

    await update.message.reply_text(
        "❌ تم إلغاء الطلب.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# ADMIN
# =========================================================

async def notify_admins(
    context,
    order_number,
):
    data = get_order(order_number)

    if not data:
        return

    text = (
        "🔔 طلب جديد GREENINK\n\n"
        + build_order_text(data)
    )

    for admin_id in ADMIN_CHAT_IDS:
        try:
            message = await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=admin_order_keyboard(
                    order_number
                ),
            )

            save_admin_message(
                order_number,
                admin_id,
                message.message_id,
            )

        except Exception as exc:
            print(
                f"Admin notification error "
                f"{admin_id}: {exc}",
                flush=True,
            )


async def refresh_admin_messages(
    context,
    order_number,
):
    data = get_order(order_number)

    if not data:
        return

    text = build_order_text(data)

    for row in get_admin_messages(
        order_number
    ):
        try:
            await context.bot.edit_message_text(
                chat_id=row["admin_chat_id"],
                message_id=row["message_id"],
                text=text,
                reply_markup=admin_order_keyboard(
                    order_number
                ),
            )

        except Exception:
            pass


async def send_customer_status(
    context,
    order_number,
    status,
):
    data = get_order(order_number)

    if not data:
        return

    order = data["order"]

    try:
        await context.bot.send_message(
            chat_id=order["customer_chat_id"],
            text=(
                "📦 تحديث حالة الطلب\n\n"
                f"🧾 {order_number}\n"
                f"{status}"
            ),
        )

    except Exception as exc:
        print(
            f"Customer notification error: {exc}",
            flush=True,
        )


async def change_admin_status(
    query,
    context,
    order_number,
    status,
):
    if query.from_user.id not in ADMIN_CHAT_IDS:
        await query.answer(
            "غير مسموح.",
            show_alert=True,
        )
        return

    if not get_order(order_number):
        await query.answer(
            "الطلب غير موجود.",
            show_alert=True,
        )
        return

    update_order_status(
        order_number,
        status,
    )

    await query.answer(status)

    await refresh_admin_messages(
        context,
        order_number,
    )

    await send_customer_status(
        context,
        order_number,
        status,
    )


# =========================================================
# DELIVERY
# =========================================================

async def start_delivery_photo(
    query,
    context,
    order_number,
):
    if query.from_user.id not in ADMIN_CHAT_IDS:
        await query.answer(
            "غير مسموح.",
            show_alert=True,
        )
        return

    context.user_data[
        "pending_delivery_order"
    ] = order_number

    await query.answer()

    await query.message.reply_text(
        (
            f"🚚 الطلب {order_number}\n\n"
            "هل تريد إرسال صورة وصل التوصيل؟"
        ),
        reply_markup=delivery_photo_keyboard(
            order_number
        ),
    )


async def request_delivery_photo(
    query,
    context,
    order_number,
    mode,
):
    if query.from_user.id not in ADMIN_CHAT_IDS:
        await query.answer(
            "غير مسموح.",
            show_alert=True,
        )
        return

    context.user_data[
        "pending_delivery_order"
    ] = order_number

    await query.answer()

    if mode == "camera":
        text = (
            "📷 أرسل الآن صورة وصل التوصيل.\n\n"
            "استعمل زر الكاميرا أو 📎 داخل Telegram."
        )
    else:
        text = (
            "🖼 اختر صورة وصل التوصيل من الهاتف "
            "وأرسلها هنا."
        )

    await query.message.reply_text(text)


async def delivery_without_photo(
    query,
    context,
    order_number,
):
    if query.from_user.id not in ADMIN_CHAT_IDS:
        await query.answer(
            "غير مسموح.",
            show_alert=True,
        )
        return

    context.user_data.pop(
        "pending_delivery_order",
        None,
    )

    status = "🚚 قيد التوصيل"

    update_order_status(
        order_number,
        status,
    )

    await query.answer("✅ تم")

    await refresh_admin_messages(
        context,
        order_number,
    )

    await send_customer_status(
        context,
        order_number,
        status,
    )


async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if update.effective_user.id not in ADMIN_CHAT_IDS:
        return

    order_number = context.user_data.get(
        "pending_delivery_order"
    )

    if not order_number or not update.message.photo:
        return

    file_id = update.message.photo[-1].file_id

    save_shipment_image(
        order_number,
        file_id,
    )

    update_order_status(
        order_number,
        "🚚 قيد التوصيل",
    )

    data = get_order(order_number)

    if not data:
        return

    customer_chat_id = data["order"]["customer_chat_id"]

    try:
        await context.bot.send_message(
            chat_id=customer_chat_id,
            text=(
                "🚚 طلبك أصبح قيد التوصيل\n\n"
                f"🧾 رقم الطلب: {order_number}"
            ),
        )

        await context.bot.send_photo(
            chat_id=customer_chat_id,
            photo=file_id,
            caption=(
                "📄 وصل / معلومات التوصيل\n"
                f"🧾 {order_number}"
            ),
        )

    except Exception as exc:
        print(
            f"Shipment photo error: {exc}",
            flush=True,
        )

    context.user_data.pop(
        "pending_delivery_order",
        None,
    )

    await refresh_admin_messages(
        context,
        order_number,
    )

    await update.message.reply_text(
        "✅ تم حفظ الصورة وتحديث حالة الطلب."
    )


# =========================================================
# MY ORDERS
# =========================================================

async def show_orders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        orders = get_customer_orders(
            update.effective_chat.id
        )

    except Exception as exc:
        print(
            f"Get orders error: {exc}",
            flush=True,
        )

        await update.message.reply_text(
            "❌ تعذر تحميل الطلبات."
        )
        return

    if not orders:
        await update.message.reply_text(
            "📦 لا توجد طلبات سابقة.",
            reply_markup=main_keyboard(),
        )
        return

    lines = [
        "📦 طلباتي",
        "",
    ]

    for order in orders:
        lines.extend(
            [
                f"🧾 {order['order_number']}",
                f"💰 {order['total']:,} دج",
                f"📌 {order['status']}",
                "────────────",
            ]
        )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=main_keyboard(),
    )


# =========================================================
# CALLBACKS
# =========================================================

async def callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    data = query.data or ""

    if data.startswith("buy:"):
        product_code = data.split(":", 1)[1]

        await start_direct_order_callback(
            query,
            context,
            product_code,
        )
        return

    if data.startswith("cart:"):
        product_code = data.split(":", 1)[1]

        await add_product_callback(
            query,
            context,
            product_code,
        )
        return

    if data.startswith("wilaya:"):
        index_text = data.split(":", 1)[1]

        await select_wilaya_callback(
            query,
            context,
            index_text,
        )
        return

    if data == "order_cancel_inline":
        context.user_data.pop("step", None)
        context.user_data.pop("order_data", None)
        context.user_data.pop("direct_order", None)

        await query.answer(
            "تم إلغاء الطلب"
        )

        try:
            await query.edit_message_text(
                "❌ تم إلغاء الطلب."
            )
        except Exception:
            pass

        return

    if data.startswith("accept:"):
        order_number = data.split(":", 1)[1]

        await change_admin_status(
            query,
            context,
            order_number,
            "✅ تم قبول الطلب",
        )
        return

    if data.startswith("prepare:"):
        order_number = data.split(":", 1)[1]

        await change_admin_status(
            query,
            context,
            order_number,
            "📦 قيد التحضير",
        )
        return

    if data.startswith("delivery:"):
        order_number = data.split(":", 1)[1]

        await start_delivery_photo(
            query,
            context,
            order_number,
        )
        return

    if data.startswith("done:"):
        order_number = data.split(":", 1)[1]

        await change_admin_status(
            query,
            context,
            order_number,
            "✅ تم التسليم",
        )
        return

    if data.startswith("cancel:"):
        order_number = data.split(":", 1)[1]

        await change_admin_status(
            query,
            context,
            order_number,
            "❌ تم إلغاء الطلب",
        )
        return

    if data.startswith("delivery_camera:"):
        order_number = data.split(":", 1)[1]

        await request_delivery_photo(
            query,
            context,
            order_number,
            "camera",
        )
        return

    if data.startswith("delivery_gallery:"):
        order_number = data.split(":", 1)[1]

        await request_delivery_photo(
            query,
            context,
            order_number,
            "gallery",
        )
        return

    if data.startswith("delivery_skip:"):
        order_number = data.split(":", 1)[1]

        await delivery_without_photo(
            query,
            context,
            order_number,
        )
        return

    if data.startswith("delivery_cancel:"):
        context.user_data.pop(
            "pending_delivery_order",
            None,
        )

        await query.answer(
            "تم الإلغاء"
        )

        try:
            await query.edit_message_text(
                "❌ تم إلغاء خطوة التوصيل."
            )
        except Exception:
            pass

        return

    await query.answer()


# =========================================================
# TEXT BUTTONS
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()
    step = context.user_data.get("step")

    if text == "❌ إلغاء الطلب":
        await cancel_current_order(
            update,
            context,
        )
        return

    if step in (
        "name",
        "phone",
        "address",
    ):
        await process_order_data(
            update,
            context,
        )
        return

    if step == "wilaya":
        await update.message.reply_text(
            "📍 اختر الولاية من الأزرار الموجودة فوق 👆",
            reply_markup=cancel_keyboard(),
        )
        return

    if (
        text == "✅ تأكيد نهائي"
        and step == "final_confirm"
    ):
        await final_confirm(
            update,
            context,
        )
        return

    if text == "🏠 الرئيسية":
        await start(
            update,
            context,
        )
        return

    if text == "🖨 الطابعات":
        await show_category(
            update,
            "printer",
        )
        return

    if text == "🧴 الأحبار":
        await show_category(
            update,
            "ink",
        )
        return

    if text == "🔥 العروض":
        await show_category(
            update,
            "pack",
        )
        return

    if text == "🛒 السلة":
        await show_cart(
            update,
            context,
        )
        return

    if text == "✅ تأكيد الطلب":
        await begin_order(
            update,
            context,
        )
        return

    if text == "🗑 تفريغ السلة":
        context.user_data["cart"] = {}

        await update.message.reply_text(
            "🗑 تم تفريغ السلة.",
            reply_markup=shop_keyboard(),
        )
        return

    if text == "📦 طلباتي":
        await show_orders(
            update,
            context,
        )
        return

    if text == "⚙️ قطع الغيار":
        await update.message.reply_text(
            (
                "⚙️ قطع الغيار\n\n"
                "سيتم إضافة المنتجات قريباً."
            ),
            reply_markup=main_keyboard(),
        )
        return

    if text == "☎️ اتصل بنا":
        await update.message.reply_text(
            (
                "☎️ اتصل بنا\n\n"
                "0560095387\n"
                "أبوبكر\n\n"
                "0775635460\n"
                "عبد الحق"
            ),
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(
        "اختر من القائمة 👇",
        reply_markup=main_keyboard(),
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(
        f"Telegram error: {context.error}",
        flush=True,
    )


# =========================================================
# POST INIT
# =========================================================

async def post_init(application):
    print(
        "Initializing PostgreSQL...",
        flush=True,
    )

    last_error = None

    for attempt in range(1, 4):
        try:
            print(
                f"PostgreSQL attempt {attempt}/3",
                flush=True,
            )

            init_database()

            print(
                "PostgreSQL database ready ✅",
                flush=True,
            )

            print(
                f"Admins loaded: {len(ADMIN_CHAT_IDS)}",
                flush=True,
            )

            return

        except Exception as exc:
            last_error = exc

            print(
                f"PostgreSQL error: {exc}",
                flush=True,
            )

            time.sleep(3)

    raise RuntimeError(
        f"Database initialization failed: {last_error}"
    )


# =========================================================
# MAIN
# =========================================================

def main():
    print(
        "Starting GREENINK Bot...",
        flush=True,
    )

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN not found"
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL not found"
        )

    print(
        "Environment variables OK ✅",
        flush=True,
    )

    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "id",
            my_id,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callbacks
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            buttons,
        )
    )

    application.add_error_handler(
        error_handler
    )

    print(
        "Telegram polling starting...",
        flush=True,
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
