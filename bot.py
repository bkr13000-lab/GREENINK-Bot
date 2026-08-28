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

    # ======================
    # PRINTERS
    # ======================

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


    # ======================
    # INK
    # ======================

    "INK-5390-5890": {
        "category": "ink",
        "name": "GREENINK WF-C5390 / WF-C5890",
        "price": 8000,
        "description": (
            "🧴 حبر GREENINK احترافي\n"
            "⚖️ السعة: 1KG\n\n"
            "✅ متوافق مع:\n"
            "• EPSON WF-C5390\n"
            "• EPSON WF-C5890"
        ),
        "images": [
            "GREENINK_5390_5890_INK.png",
            "GREENINK_5390_5890_INK.jpg",
        ],
    },


    # ======================
    # PACKS
    # ======================

    "PACK-5390": {
        "category": "pack",
        "name": "Pack WF-C5390 + 4 ألوان GREENINK",
        "price": 203000,
        "description": (
            "🔥 PACK GREENINK\n\n"
            "🖨 EPSON WF-C5390\n"
            "+\n"
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
            "+\n"
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
                    "🛍️ اطلب الآن",
                    callback_data=f"buy:{product_code}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🛒 أضف إلى السلة",
                    callback_data=f"cart:{product_code}",
                ),
            ],
        ]
    )


def wilaya_keyboard():

    rows = []

    for i in range(0, len(WILAYAS), 2):

        row = []

        row.append(
            InlineKeyboardButton(
                WILAYAS[i],
                callback_data=f"wilaya:{WILAYAS[i]}",
            )
        )

        if i + 1 < len(WILAYAS):

            row.append(
                InlineKeyboardButton(
                    WILAYAS[i + 1],
                    callback_data=f"wilaya:{WILAYAS[i + 1]}",
                )
            )

        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                "❌ إلغاء الطلب",
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
                    "🖼️ اختيار صورة",
                    callback_data=f"delivery_gallery:{order_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    "⏭️ بدون صورة",
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
                """
                SELECT 1
                FROM orders
                WHERE order_number = %s
                """,
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

    total = 0

    for code, quantity in cart.items():

        product = PRODUCTS.get(code)

        if not product:
            continue

        total += product["price"] * quantity

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
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
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
                SET status = %s,
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
                SET shipment_image_file_id = %s,
                    updated_at = NOW()
                WHERE order_number = %s
                """,
                (
                    file
