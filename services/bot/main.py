import os
import sys
import django
import logging
import asyncio
from pathlib import Path

current_dir = Path(__file__).resolve().parent

django_project_dir = current_dir.parent / "drf"
sys.path.append(str(django_project_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devshield.settings')
django.setup()
from dotenv import load_dotenv
from users.models import TransactionHistory
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from datetime import datetime
from states import PaymentState
from django.utils import timezone
from datetime import timedelta

from buttons import sorov

load_dotenv()
storage = MemoryStorage() 

dp = Dispatcher(storage=storage)
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

BANK_CARD = os.getenv("CREDIT_CARD")
CARD_OWNER = os.getenv("CARD_OWNER")
ADMIN_ID = os.getenv("ADMIN_ID")

@dp.message(Command('start'))
async def start(msg: types.Message, state: FSMContext, command: CommandObject):
    args = command.args

    if args:
        payment_id = args

        try:
            # 1. Tranzaksiyani foydalanuvchisi bilan birga asinxron yuklaymiz
            tx = await sync_to_async(
                lambda: TransactionHistory.objects.select_related('user').get(payment_id=payment_id)
            )()

            tx.user.telegram_id = msg.from_user.id
            await sync_to_async(tx.user.save)() 

            if timezone.now() - tx.payment_date > timedelta(hours=1):
                await msg.answer("Ushbu to'lov havolasining muddati tugagan (1 soat). Iltimos, qaytadan yangi to'lov so'rovi yarating! ⚠️")
                
                tx.status = TransactionHistory.StatusChoices.TIMEOUT
                await sync_to_async(tx.save)() # Statusni yangilab saqlaymiz
                return

            if tx.status == TransactionHistory.StatusChoices.SUCCESS:
                await msg.answer("Bu to'lov avval amalga oshirilgan 🎉")
                return 
            
            await msg.answer(
                f"Skanerlash xizmati narxi: 20,000 so'm.\n\n"
                f"💳 Karta raqam: <b><code>{BANK_CARD}</code></b> ({CARD_OWNER})\n\n"
                f"Iltimos, to'lovni amalga oshirib, chek (rasm) variantini shu yerga yuboring.\n"
                f"Sizning to'lov ID: <code>{payment_id}</code>",
                parse_mode="HTML"
            )

            await state.update_data(
                payment_id=payment_id,
                username=msg.from_user.username,
                user_phone=tx.user.phone_number
            )
            await state.set_state(PaymentState.payment_cheque)

        except TransactionHistory.DoesNotExist:
            await msg.answer("Xato to'lov havolasi ! ❌")
    else:
        await msg.answer(f"Assalomu alaykum {msg.from_user.first_name}! Vebsaytni scan qilish uchun https://devshield.uz orqali amalga oshiring!")

@dp.message(F.photo, PaymentState.payment_cheque)
async def get_cheque(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    username = data.get("username") or msg.from_user.username or "Mavjud emas"
    user_phone = data.get("user_phone") or "Kiritilmagan"
    formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    await bot.send_photo(
        chat_id=ADMIN_ID, 
        photo=msg.photo[-1].file_id,
        caption=(
            f"💰 <b>Yangi to'lov so'rovi!</b>\n\n"
            f"👤 Foydalanuvchi: @{username}\n"
            f"📞 Telefon: {user_phone}\n"
            f"🆔 To'lov ID: <code>{payment_id}</code>\n"
            f"💵 Summa: 20 000 UZS\n"
            f"🕰️ To'lov vaqti: {formatted_time}"
        ),
        parse_mode="HTML",
        reply_markup=sorov(payment_id=payment_id)
    )
    await msg.answer("Rahmat! To'lovingiz tekshirish uchun adminga yuborildi. ⏳")
    await state.clear()  


@dp.callback_query(F.data.startswith("accept_") | F.data.startswith("decline_"))
async def yes_or_no(callback: types.CallbackQuery):
    action, payment_id = callback.data.split("_", 1)
    try:
        tx = await sync_to_async(TransactionHistory.objects.select_related('user').get)(payment_id=payment_id)

        if action == "accept":
            tx.status = TransactionHistory.StatusChoices.SUCCESS
            await sync_to_async(tx.save)() 

            
            await bot.send_message(
                tx.user.telegram_id, 
                "To'lovingiz muvaffaqiyatli qabul qilindi! Saytni qayta skan qilishingiz mumkin. ✅"
            )
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\n✅ <b>ADMIN TASDIQLADI</b>",
                parse_mode="HTML"
            )
            
        elif action == "decline":
            tx.status = TransactionHistory.StatusChoices.DECLINED
            await sync_to_async(tx.save)() 

            await bot.send_message(
                tx.user.telegram_id, 
                "Siz yuborgan to'lov cheki admin tomonidan rad etildi! Iltimos qayta tekshirib yuboring. ❌"
            )
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\n❌ <b>ADMIN RAD ETDI</b>",
                parse_mode="HTML"
            )

    except TransactionHistory.DoesNotExist:
        await callback.answer("Tranzaksiya topilmadi yoki o'chib ketgan!", show_alert=True)

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO)

    asyncio.run(main()) 