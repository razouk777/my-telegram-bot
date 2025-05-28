import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# إعداد تسجيل الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===============================================================
# !! معلومات البوت !!
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
# ===============================================================

# تعريف مراحل المحادثة
SELECTING_CATEGORY, AWAITING_MESSAGE = range(2)

# قائمة التصنيفات المحدثة
CATEGORIES = {
    'admissions': 'استفسار عن المفاضلة',
    'exams': 'استفسار عن الامتحانات',
    'jobs': 'استفسار عن الوظائف',
    'other': 'موضوع اخر'
}


# --- بداية دوال المحادثة ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يبدأ المحادثة ويعرض أزرار التصنيفات."""
    keyboard = [
        [InlineKeyboardButton(text, callback_data=key)] for key, text in CATEGORIES.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "أهلاً بك في بوت التواصل مع الفريق الأكاديمي.\n\n"
        "يرجى اختيار طبيعة رسالتك أولاً:",
        reply_markup=reply_markup
    )
    return SELECTING_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بعد اختيار التصنيف، يحفظه ويطلب الرسالة."""
    query = update.callback_query
    await query.answer()
    
    category_key = query.data
    category_text = CATEGORIES[category_key]
    
    # حفظ التصنيف المختار في بيانات المستخدم لهذه المحادثة
    context.user_data['category'] = category_text
    
    await query.edit_message_text(
        text=f"تم اختيار: *{category_text}*.\n\nالآن، تفضل بإرسال رسالتك (نص، صورة، أو ملف)."
    )
    return AWAITING_MESSAGE

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يعالج الرسالة النهائية (نص، صورة، ملف) ويرسلها للمدير."""
    user = update.effective_user
    message = update.message
    
    # استرجاع التصنيف الذي تم حفظه
    category = context.user_data.get('category', 'غير محدد')
    
    # بناء الرسالة للمدير
    header = (
        f"📩 رسالة جديدة من: {user.full_name} (@{user.username})\n"
        f"👤 معرف المستخدم: {user.id}\n"
        f"📋 **الموضوع: {category}**"
    )

    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=file_id, caption=header)
        elif message.document:
            file_id = message.document.file_id
            await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=file_id, caption=header)
        else: # رسالة نصية
            full_message_to_admin = f"{header}\n\n---\n{message.text}"
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=full_message_to_admin)
        
        await message.reply_text("✅ شكرًا لك. تم إرسال رسالتك بنجاح وسيتم مراجعتها قريبًا.")
    except Exception as e:
        logger.error(f"خطأ في إرسال الرسالة النهائية: {e}")
        await message.reply_text("عذرًا، حدث خطأ ما. حاول مرة أخرى.")
    
    # إنهاء المحادثة
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يلغي المحادثة الحالية."""
    await update.message.reply_text("تم إلغاء العملية. يمكنك البدء من جديد بإرسال /start.")
    return ConversationHandler.END

# --- نهاية دوال المحادثة ---


# دالة الرد على المستخدم (تبقى كما هي، لا تتأثر بالمحادثة)
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.reply_to_message:
        return

    original_message = update.message.reply_to_message
    source_text = original_message.text or original_message.caption

    if not source_text:
        return

    match = re.search(r"معرف المستخدم: (\d+)", source_text)
    if match:
        user_id = int(match.group(1))
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✉️ رد من الفريق الأكاديمي:\n\n{update.message.text}"
            )
            await update.message.reply_text("✅ تم إرسال ردك بنجاح.")
        except Exception as e:
            await update.message.reply_text(f"لم أتمكن من إرسال الرد. قد يكون المستخدم حظر البوت.\nالخطأ: {e}")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    admin_id = int(ADMIN_CHAT_ID)

    # إعداد معالج المحادثة لتصنيف الرسائل
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_CATEGORY: [CallbackQueryHandler(category_selected)],
            AWAITING_MESSAGE: [MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, handle_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=300 # إنهاء المحادثة بعد 5 دقائق من الخمول
    )

    # 1. إضافة معالج المحادثة (الآن هو نقطة البداية الرئيسية للمستخدمين)
    application.add_handler(conv_handler)
    
    # 2. معالج الردود من المدير (يبقى مستقلاً)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.REPLY & filters.Chat(chat_id=admin_id), 
        reply_to_user
    ))

    print("البوت قيد التشغيل مع ميزة تصنيف الرسائل...")
    application.run_polling()

if __name__ == '__main__':
    main()