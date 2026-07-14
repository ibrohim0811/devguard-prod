from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def sorov(payment_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅", callback_data=f"accept_{payment_id}"),
                InlineKeyboardButton(text="❌", callback_data=f"decline_{payment_id}")
            ]
        ]
    )