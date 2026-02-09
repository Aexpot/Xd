import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telethon import TelegramClient
from telethon.tl import types
from telethon import functions

# Загрузка переменных окружения
load_dotenv()

# Настройка подробного логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # DEBUG для подробных логов
)
logger = logging.getLogger(__name__)

# Состояния ConversationHandler
CHOOSE_TYPE, API_ID, API_HASH, PHONE, PASSWORD, REASON, TARGET, COUNT, CONFIRM, CUSTOM_MESSAGE = range(10)

# Токен бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    print("❌ Ошибка: Укажите TELEGRAM_BOT_TOKEN в .env файле")
    exit(1)

# Хранение данных пользователей
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    logger.info(f"🟢 /start от {update.effective_user.username}")
    
    user = update.effective_user
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

🤖 Я бот для репортов Telegram.

📊 **Доступные команды:**
/report - Начать репорт аккаунта или канала
/my_sessions - Мои сессии (после создания)
/help - Помощь по использованию

⚠️ **ВАЖНО:**
• Используйте только свои аккаунты Telegram
• Получите API ID и Hash на https://my.telegram.org
• Бот не несет ответственности за ваши действия

📋 **Для начала введите:** /report
    """
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    logger.info(f"🟡 /help от {update.effective_user.username}")
    
    help_text = """
🆘 **Помощь по использованию бота:**

🔐 **Как получить API ID и Hash:**
1. Перейдите на https://my.telegram.org
2. Войдите в свой аккаунт Telegram
3. В разделе "API Development tools"
4. Создайте новое приложение
5. Скопируйте API ID и Hash

📋 **Процесс репорта (команда /report):**
1. Выберите тип репорта (аккаунт или канал)
2. Введите API ID (только цифры)
3. Введите API Hash (32 символа)
4. Введите номер телефона (+79...)
5. Введите пароль (если есть, или "нет")
6. Выберите причину репорта
7. Введите username цели (@username)
8. Укажите количество репортов
9. Подтвердите отправку

📊 **Доступные причины репорта:**
• 📢 Спам
• 🔞 Порнография
• 🚫 Насилие
• 🚸 Детский контент
• 📝 Другое
• ⚖️ Авторские права
• 👤 Фейковый аккаунт
• 📍 Неверная геолокация
• 💊 Наркотики
• 📱 Личные данные
    """
    
    await update.message.reply_text(help_text)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса репорта"""
    logger.info(f"🔵 /report от {update.effective_user.username}")
    
    # Очищаем предыдущие данные
    context.user_data.clear()
    logger.debug("🧹 Очищены данные пользователя")
    
    keyboard = [
        [
            InlineKeyboardButton("👤 Репорт аккаунта", callback_data="report_account"),
            InlineKeyboardButton("📢 Репорт канала", callback_data="report_channel")
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📊 **Выберите тип репорта:**\n\n👤 **Репорт аккаунта** - для репорта пользователей\n📢 **Репорт канала** - для репорта каналов/групп\n\nВыберите вариант:"
    
    logger.debug("📤 Запрос выбора типа репорта")
    
    await update.message.reply_text(text, reply_markup=reply_markup)
    return CHOOSE_TYPE

async def choose_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа репорта"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"🔘 Выбор типа репорта: {query.data}")
    
    if query.data == "report_account":
        context.user_data['report_type'] = 'account'
        report_type_text = "👤 Репорт аккаунта"
        logger.debug("✅ Выбран репорт аккаунта")
    elif query.data == "report_channel":
        context.user_data['report_type'] = 'channel'
        report_type_text = "📢 Репорт канала"
        logger.debug("✅ Выбран репорт канала")
    elif query.data == "cancel":
        logger.info("❌ Пользователь отменил выбор типа репорта")
        await query.edit_message_text("❌ **Операция отменена.**")
        return ConversationHandler.END
    
    context.user_data['report_type_text'] = report_type_text
    
    logger.debug(f"📝 Тип репорта сохранен: {report_type_text}")
    logger.debug(f"📁 Данные пользователя: {context.user_data}")
    
    await query.edit_message_text(
        f"✅ **Тип репорта:** {report_type_text}\n\n"
        "🔐 **Шаг 1 из 8: Введите ваш API ID**\n\n"
        "API ID можно получить на https://my.telegram.org\n"
        "Введите только цифры:"
    )
    return API_ID

async def api_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка API ID"""
    user_input = update.message.text
    logger.info(f"📝 API ID от {update.effective_user.username}: '{user_input}'")
    
    try:
        api_id = int(user_input)
        context.user_data['api_id'] = api_id
        
        logger.debug(f"✅ API ID сохранен: {api_id}")
        logger.debug(f"📁 Данные пользователя: {context.user_data}")
        
        await update.message.reply_text(
            "✅ **API ID сохранен!**\n\n"
            "🔐 **Шаг 2 из 8: Введите ваш API Hash**\n\n"
            "API Hash можно получить на https://my.telegram.org\n"
            "Введите hash (обычно 32 символа):"
        )
        return API_HASH
    except ValueError:
        logger.warning(f"❌ Некорректный API ID: '{user_input}'")
        await update.message.reply_text("❌ API ID должен содержать только цифры. Попробуйте снова:")
        return API_ID

async def api_hash_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка API Hash"""
    user_input = update.message.text
    logger.info(f"📝 API Hash от {update.effective_user.username}: '{user_input[:10]}...'")
    
    api_hash = user_input.strip()
    
    if len(api_hash) < 20:
        logger.warning(f"❌ Слишком короткий API Hash: {len(api_hash)} символов")
        await update.message.reply_text("❌ API Hash слишком короткий. Попробуйте снова:")
        return API_HASH
    
    context.user_data['api_hash'] = api_hash
    
    logger.debug(f"✅ API Hash сохранен: {api_hash[:10]}...")
    logger.debug(f"📁 Данные пользователя: {context.user_data}")
    
    await update.message.reply_text(
        "✅ **API Hash сохранен!**\n\n"
        "📱 **Шаг 3 из 8: Введите номер телефона**\n\n"
        "Введите номер в международном формате:\n"
        "Пример: +79123456789"
    )
    return PHONE

async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона"""
    user_input = update.message.text
    logger.info(f"📝 Телефон от {update.effective_user.username}: '{user_input}'")
    
    phone = user_input.strip()
    
    if not phone.startswith('+'):
        logger.warning(f"❌ Некорректный формат телефона: '{phone}'")
        await update.message.reply_text("❌ Номер должен начинаться с '+'. Попробуйте снова:")
        return PHONE
    
    context.user_data['phone'] = phone
    
    logger.debug(f"✅ Телефон сохранен: {phone}")
    logger.debug(f"📁 Данные пользователя: {context.user_data}")
    
    await update.message.reply_text(
        "✅ **Номер телефона сохранен!**\n\n"
        "🔑 **Шаг 4 из 8: Введите пароль (если есть)**\n\n"
        "Если у вашего аккаунта есть двухфакторная аутентификация,\n"
        "введите пароль. Если нет - просто отправьте 'нет':"
    )
    return PASSWORD

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пароля"""
    user_input = update.message.text
    logger.info(f"📝 Пароль от {update.effective_user.username}: '{user_input}'")
    
    password = user_input.strip()
    
    if password.lower() in ['нет', 'no', 'н', 'n', '0', '']:
        context.user_data['password'] = None
        password_text = "не установлен"
        logger.debug("✅ Пароль: не установлен")
    else:
        context.user_data['password'] = password
        password_text = "установлен"
        logger.debug(f"✅ Пароль сохранен: {password[:3]}...")
    
    logger.debug(f"📁 Данные пользователя: {context.user_data}")
    
    keyboard = [
        [InlineKeyboardButton("📢 Спам", callback_data="spam")],
        [InlineKeyboardButton("🔞 Порнография", callback_data="pornography")],
        [InlineKeyboardButton("🚫 Насилие", callback_data="violence")],
        [InlineKeyboardButton("🚸 Детский контент", callback_data="child_abuse")],
        [InlineKeyboardButton("📝 Другое", callback_data="other")],
        [InlineKeyboardButton("⚖️ Авторские права", callback_data="copyright")],
        [InlineKeyboardButton("👤 Фейк", callback_data="fake")],
        [InlineKeyboardButton("📍 Неверная гео", callback_data="geo_irrelevant")],
        [InlineKeyboardButton("💊 Наркотики", callback_data="illegal_drugs")],
        [InlineKeyboardButton("📱 Личные данные", callback_data="personal_details")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    logger.debug("📤 Отправка выбора причины репорта")
    
    await update.message.reply_text(
        f"✅ **Пароль:** {password_text}\n\n"
        "📋 **Шаг 5 из 8: Выберите причину репорта**\n\n"
        "Выберите одну из причин:",
        reply_markup=reply_markup
    )
    return REASON

async def reason_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора причины"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"🔘 Выбор причины репорта: {query.data}")
    
    reasons = {
        'spam': ("📢 Спам", "Spam"),
        'pornography': ("🔞 Порнография", "Pornography"),
        'violence': ("🚫 Насилие", "Violence"),
        'child_abuse': ("🚸 Детский контент", "ChildAbuse"),
        'other': ("📝 Другое", "Other"),
        'copyright': ("⚖️ Нарушение авторских прав", "Copyright"),
        'fake': ("👤 Фейковый аккаунт", "Fake"),
        'geo_irrelevant': ("📍 Неверная геолокация", "GeoIrrelevant"),
        'illegal_drugs': ("💊 Незаконные препараты", "IllegalDrugs"),
        'personal_details': ("📱 Личные данные", "PersonalDetails")
    }
    
    reason_text, reason_code = reasons.get(query.data, ("📝 Другое", "Other"))
    
    context.user_data['reason'] = reason_code
    context.user_data['reason_text'] = reason_text
    
    logger.debug(f"✅ Причина сохранена: {reason_text} ({reason_code})")
    logger.debug(f"📁 Данные пользователя: {context.user_data}")
    
    if query.data == 'other':
        logger.debug("📝 Запрос описания для причины 'Другое'")
        await query.edit_message_text(
            "📝 **Введите описание проблемы**\n\n"
            "Опишите причину репорта подробно:"
        )
        return CUSTOM_MESSAGE
    else:
        report_type = context.user_data.get('report_type', 'account')
        target_type = "аккаунта" if report_type == 'account' else "канала"
        
        logger.debug(f"🎯 Запрос цели для {target_type}")
        await query.edit_message_text(
            f"✅ **Причина выбрана:** {reason_text}\n\n"
            f"🎯 **Шаг 6 из 8: Введите username {target_type}**\n\n"
            "Введите @username или ссылку:\n"
            "Пример: @username или t.me/username"
        )
        return TARGET

async def custom_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кастомного сообщения"""
    user_input = update.message.text
    logger.info(f"📝 Описание проблемы от {update.effective_user.username}: '{user_input[:50]}...'")
    
    custom_message = user_input.strip()
    context.user_data['custom_message'] = custom_message
    
    logger.debug(f"✅ Описание сохранено: {custom_message[:50]}...")
    
    report_type = context.user_data.get('report_type', 'account')
    target_type = "аккаунта" if report_type == 'account' else "канала"
    
    await update.message.reply_text(
        f"✅ **Причина выбрана:** {context.user_data['reason_text']}\n"
        f"📝 **Описание:** {custom_message[:50]}...\n\n"
        f"🎯 **Шаг 6 из 8: Введите username {target_type}**\n\n"
        "Введите @username или ссылку:"
    )
    return TARGET

async def target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка цели репорта"""
    user_input = update.message.text
    logger.info(f"🎯 Ввод цели от {update.effective_user.username}: '{user_input}'")
    
    target = user_input.strip()
    
    # Очистка username
    if target.startswith('@'):
        target = target[1:]
        logger.debug(f"🔧 Убран @ из username: {target}")
    elif 't.me/' in target:
        target = target.split('t.me/')[-1].split('/')[0]
        logger.debug(f"🔧 Извлечен username из ссылки: {target}")
    
    context.user_data['target'] = target
    
    logger.debug(f"✅ Цель сохранена: @{target}")
    logger.debug(f"📁 Данные пользователя: {context.user_data}")
    
    report_type = context.user_data.get('report_type', 'account')
    target_type = "аккаунта" if report_type == 'account' else "канала"
    
    await update.message.reply_text(
        f"✅ **Цель сохранена:** @{target}\n\n"
        "🔢 **Шаг 7 из 8: Введите количество репортов**\n\n"
        "Рекомендуется не более 10:\n"
        "Введите число от 1 до 50:"
    )
    return COUNT

async def count_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка количества репортов"""
    user_input = update.message.text
    logger.info(f"🔢 Ввод количества репортов от {update.effective_user.username}: '{user_input}'")
    
    try:
        count = int(user_input)
        
        if count < 1:
            logger.warning(f"❌ Некорректное количество: {count} (меньше 1)")
            await update.message.reply_text("❌ Количество должно быть больше 0. Попробуйте снова:")
            return COUNT
        if count > 50:
            logger.warning(f"❌ Некорректное количество: {count} (больше 50)")
            await update.message.reply_text("❌ Слишком много репортов. Максимум 50. Попробуйте снова:")
            return COUNT
        
        context.user_data['count'] = count
        
        logger.debug(f"✅ Количество сохранено: {count}")
        logger.debug(f"📁 Данные пользователя: {context.user_data}")
        
        report_type = context.user_data.get('report_type', 'account')
        report_type_text = context.user_data.get('report_type_text', 'Репорт аккаунта')
        
        summary = f"""
📋 **Сводка репорта:**

📊 **Тип репорта:** {report_type_text}
🔑 **API ID:** `{context.user_data.get('api_id', 'Не указан')}`
🔐 **API Hash:** `{context.user_data.get('api_hash', 'Не указан')[:10]}...`
📱 **Телефон:** `{context.user_data.get('phone', 'Не указан')}`
🔑 **Пароль:** {'установлен' if context.user_data.get('password') else 'не установлен'}
🎯 **Причина:** {context.user_data.get('reason_text', 'Не указана')}
🎯 **Цель:** @{context.user_data.get('target', 'Не указан')}
🔢 **Количество:** {count}

⚠️ **Проверьте данные!**
После подтверждения начнется отправка репортов.
        """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="confirm"),
                InlineKeyboardButton("❌ Отменить", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.debug("📤 Отправка сводки репорта")
        
        await update.message.reply_text(summary, reply_markup=reply_markup)
        return CONFIRM
        
    except ValueError:
        logger.warning(f"❌ Некорректное число: '{user_input}'")
        await update.message.reply_text("❌ Введите корректное число. Попробуйте снова:")
        return COUNT

async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и отправка репортов"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"🔘 Подтверждение репорта: {query.data}")
    
    if query.data == 'cancel':
        logger.info("❌ Пользователь отменил отправку репортов")
        await query.edit_message_text("❌ **Операция отменена.**")
        context.user_data.clear()
        return ConversationHandler.END
    
    logger.info("🔄 Начало процесса отправки репортов")
    
    await query.edit_message_text("🔄 **Подключаюсь к Telegram...**")
    
    try:
        user_data = context.user_data
        user_id = query.from_user.id
        
        logger.debug(f"👤 ID пользователя: {user_id}")
        logger.debug(f"📁 Данные для отправки: {user_data}")
        
        session_name = f"sessions/user_{user_id}_{user_data.get('report_type', 'account')}"
        client = TelegramClient(
            session_name,
            user_data['api_id'],
            user_data['api_hash']
        )
        
        logger.info(f"🔗 Подключение к Telegram с API ID: {user_data['api_id']}")
        
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.info("📲 Отправка кода подтверждения...")
            await query.edit_message_text("📲 **Отправка кода подтверждения...**")
            
            try:
                sent_code = await client.send_code_request(user_data['phone'])
                
                logger.info(f"✅ Код отправлен на {user_data['phone']}")
                
                await query.message.reply_text(
                    f"🔢 **Введите код подтверждения из Telegram:**\n\n"
                    f"Код отправлен на {user_data['phone']}"
                )
                
                context.user_data['telethon_client'] = client
                context.user_data['phone_code_hash'] = sent_code.phone_code_hash
                context.user_data['waiting_for_code'] = True
                
                logger.debug("✅ Данные для ввода кода сохранены")
                
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки кода: {str(e)}")
                await query.edit_message_text(f"❌ **Ошибка отправки кода:** {str(e)}")
                await client.disconnect()
                return ConversationHandler.END
        
        logger.info("✅ Уже авторизован, начинаю отправку репортов")
        success = await process_reports(query, context, client, user_data)
        await client.disconnect()
        
        if success:
            if user_id not in user_sessions:
                user_sessions[user_id] = []
            
            session_data = {
                'api_id': user_data['api_id'],
                'api_hash': user_data['api_hash'],
                'phone': user_data['phone'],
                'password': user_data.get('password'),
                'report_type': user_data.get('report_type', 'account'),
                'session_name': session_name,
                'last_used': datetime.now().isoformat()
            }
            
            user_sessions[user_id].append(session_data)
            logger.info(f"💾 Сессия сохранена для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в процессе отправки: {str(e)}")
        await query.edit_message_text(f"❌ **Произошла ошибка:** {str(e)}")
        return ConversationHandler.END
    
    return ConversationHandler.END

async def process_reports(query, context, client, user_data):
    """Обработка отправки репортов"""
    try:
        target = user_data['target']
        report_type = user_data.get('report_type', 'account')
        
        logger.info(f"🔍 Поиск цели: @{target}, тип: {report_type}")
        await query.edit_message_text(f"🔍 **Поиск цели @{target}...**")
        
        try:
            entity = await client.get_entity(target)
            logger.info(f"✅ Цель найдена: @{target}")
        except Exception as e:
            logger.error(f"❌ Не удалось найти цель @{target}: {str(e)}")
            await query.edit_message_text(f"❌ **Ошибка:** Не удалось найти @{target}")
            return False
        
        logger.info(f"🚀 Начало отправки {user_data['count']} репортов")
        await query.edit_message_text(f"🚀 **Отправка {user_data['count']} репортов...**")
        
        success_count = 0
        
        reason_map = {
            'Spam': types.InputReportReasonSpam(),
            'Pornography': types.InputReportReasonPornography(),
            'Violence': types.InputReportReasonViolence(),
            'ChildAbuse': types.InputReportReasonChildAbuse(),
            'Copyright': types.InputReportReasonCopyright(),
            'Fake': types.InputReportReasonFake(),
            'GeoIrrelevant': types.InputReportReasonGeoIrrelevant(),
            'IllegalDrugs': types.InputReportReasonIllegalDrugs(),
            'PersonalDetails': types.InputReportReasonPersonalDetails(),
            'Other': types.InputReportReasonOther()
        }
        
        reason = reason_map.get(user_data['reason'], types.InputReportReasonOther())
        
        if user_data.get('custom_message'):
            message = user_data['custom_message']
            logger.debug(f"📝 Используется кастомное сообщение: {message[:50]}...")
        else:
            default_messages = {
                'Spam': 'Это спам',
                'Pornography': 'Порнографический контент',
                'Violence': 'Контент с насилием',
                'ChildAbuse': 'Детский контент',
                'Copyright': 'Нарушение авторских прав',
                'Fake': 'Фейковый аккаунт',
                'GeoIrrelevant': 'Неверная геолокация',
                'IllegalDrugs': 'Пропаганда наркотиков',
                'PersonalDetails': 'Раскрытие личных данных',
                'Other': 'Нарушение правил Telegram'
            }
            message = default_messages.get(user_data['reason'], 'Нарушение правил')
            logger.debug(f"📝 Используется сообщение по умолчанию: {message}")
        
        count = user_data['count']
        
        for i in range(count):
            try:
                logger.debug(f"📤 Отправка репорта {i+1}/{count}")
                
                if report_type == 'account':
                    result = await client(functions.account.ReportPeerRequest(
                        peer=entity,
                        reason=reason,
                        message=message[:200]
                    ))
                else:
                    result = await client(functions.messages.ReportRequest(
                        peer=entity,
                        id=[0],
                        reason=reason,
                        message=message[:200]
                    ))
                
                if result:
                    success_count += 1
                    logger.debug(f"✅ Репорт {i+1} отправлен успешно")
                else:
                    logger.warning(f"⚠️ Репорт {i+1} не отправлен (результат: {result})")
                
                if (i + 1) % 5 == 0 or (i + 1) == count:
                    logger.info(f"📊 Прогресс: отправлено {i + 1}/{count}")
                    await query.edit_message_text(
                        f"📤 **Отправлено {i + 1}/{count} репортов...**"
                    )
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке репорта {i + 1}: {str(e)}")
                continue
        
        logger.info(f"✅ Отправка завершена. Успешно: {success_count}/{count}")
        
        result_text = f"""
✅ **Репорты отправлены успешно!**

📊 **Статистика:**
• Тип репорта: {user_data.get('report_type_text', 'Репорт')}
• Цель: @{target}
• Причина: {user_data.get('reason_text', 'Не указана')}
• Всего отправлено: {count}
• Успешно: {success_count}
• Время: {datetime.now().strftime('%H:%M:%S')}

⚠️ **Важно:** 
• Результаты обрабатываются Telegram
• Это может занять некоторое время
• Не злоупотребляйте функцией репортов
        """
        
        await query.edit_message_text(result_text)
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке репортов: {str(e)}")
        await query.edit_message_text(f"❌ **Ошибка:** {str(e)}")
        return False

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода кода подтверждения"""
    user_input = update.message.text
    logger.info(f"🔢 Ввод кода подтверждения от {update.effective_user.username}: '{user_input}'")
    
    if not context.user_data.get('waiting_for_code'):
        logger.warning("❌ Пользователь ввел код, но не ожидается")
        return
    
    code = user_input.strip()
    client = context.user_data.get('telethon_client')
    phone_code_hash = context.user_data.get('phone_code_hash')
    
    if not client or not phone_code_hash:
        logger.error("❌ Данные сессии не найдены")
        await update.message.reply_text("❌ Ошибка: данные сессии не найдены. Начните заново /report")
        return
    
    try:
        password = context.user_data.get('password')
        
        logger.info("🔐 Попытка авторизации с кодом")
        
        if password:
            await client.sign_in(
                phone=context.user_data['phone'],
                code=code,
                phone_code_hash=phone_code_hash,
                password=password
            )
        else:
            await client.sign_in(
                phone=context.user_data['phone'],
                code=code,
                phone_code_hash=phone_code_hash
            )
        
        context.user_data['waiting_for_code'] = False
        
        logger.info("✅ Авторизация успешна")
        
        await update.message.reply_text("✅ **Авторизация успешна! Продолжаем отправку репортов...**")
        
        user_id = update.effective_user.id
        user_data = context.user_data
        
        # Создаем новое сообщение для отображения прогресса
        message = await update.message.reply_text("🔄 **Начинаю отправку репортов...**")
        
        success = await process_reports_simple(message, context, client, user_data)
        
        if success:
            if user_id not in user_sessions:
                user_sessions[user_id] = []
            
            session_name = f"sessions/user_{user_id}_{user_data.get('report_type', 'account')}"
            session_data = {
                'api_id': user_data['api_id'],
                'api_hash': user_data['api_hash'],
                'phone': user_data['phone'],
                'password': user_data.get('password'),
                'report_type': user_data.get('report_type', 'account'),
                'session_name': session_name,
                'last_used': datetime.now().isoformat()
            }
            
            user_sessions[user_id].append(session_data)
            logger.info(f"💾 Сессия сохранена для пользователя {user_id}")
        
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации: {str(e)}")
        await update.message.reply_text(f"❌ **Ошибка авторизации:** {str(e)}\nПопробуйте снова /report")

async def process_reports_simple(message, context, client, user_data):
    """Упрощенная обработка отправки репортов (для кода)"""
    try:
        target = user_data['target']
        report_type = user_data.get('report_type', 'account')
        
        logger.info(f"🔍 Поиск цели: @{target}")
        await message.edit_text(f"🔍 **Поиск цели @{target}...**")
        
        try:
            entity = await client.get_entity(target)
            logger.info(f"✅ Цель найдена: @{target}")
        except Exception as e:
            logger.error(f"❌ Не удалось найти цель @{target}: {str(e)}")
            await message.edit_text(f"❌ **Ошибка:** Не удалось найти @{target}")
            return False
        
        count = user_data['count']
        logger.info(f"🚀 Начало отправки {count} репортов")
        await message.edit_text(f"🚀 **Отправка {count} репортов...**")
        
        success_count = 0
        reason = types.InputReportReasonSpam()
        message_text = user_data.get('custom_message', 'Репорт')
        
        for i in range(count):
            try:
                if report_type == 'account':
                    result = await client(functions.account.ReportPeerRequest(
                        peer=entity,
                        reason=reason,
                        message=message_text[:200]
                    ))
                else:
                    result = await client(functions.messages.ReportRequest(
                        peer=entity,
                        id=[0],
                        reason=reason,
                        message=message_text[:200]
                    ))
                
                if result:
                    success_count += 1
                
                if (i + 1) % 5 == 0:
                    await message.edit_text(f"📤 **Отправлено {i + 1}/{count} репортов...**")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке репорта {i + 1}: {str(e)}")
                continue
        
        result_text = f"""
✅ **Репорты отправлены успешно!**

📊 **Статистика:**
• Цель: @{target}
• Всего отправлено: {count}
• Успешно: {success_count}
• Время: {datetime.now().strftime('%H:%M:%S')}
        """
        
        await message.edit_text(result_text)
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке репортов: {str(e)}")
        await message.edit_text(f"❌ **Ошибка:** {str(e)}")
        return False

async def my_sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все сессии пользователя"""
    logger.info(f"📋 /my_sessions от {update.effective_user.username}")
    
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or not user_sessions[user_id]:
        text = "📭 У вас нет сохраненных сессий.\n\nСначала создайте сессию через команду /report"
        logger.debug("📭 У пользователя нет сессий")
    else:
        sessions = user_sessions[user_id]
        text = f"📋 **Ваши сохраненные сессии:**\n\n📊 **Всего сессий:** {len(sessions)}\n\n"
        
        for i, session in enumerate(sessions, 1):
            phone_short = session['phone'][-4:]
            report_type = "👤" if session.get('report_type') == 'account' else "📢"
            text += f"{i}. {report_type} Сессия {i} (тел: ...{phone_short})\n"
        
        logger.debug(f"📊 Показано {len(sessions)} сессий")
    
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    logger.info(f"❌ Отмена операции от {update.effective_user.username}")
    
    await update.message.reply_text("❌ **Операция отменена.**")
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"❌ Необработанная ошибка: {context.error}", exc_info=True)
    
    try:
        if update and update.message:
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте снова /start")
    except:
        logger.error("❌ Не удалось отправить сообщение об ошибке")

def main():
    """Основная функция"""
    if not os.path.exists('sessions'):
        os.makedirs('sessions')
        logger.info("📁 Создана папка sessions")
    
    logger.info("🤖 Запуск бота для репортов Telegram...")
    
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_sessions", my_sessions_command))
    
    # Хендлер для кодов подтверждения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, code_handler))
    
    # ConversationHandler для обычного репорта
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("report", report_command),
        ],
        states={
            CHOOSE_TYPE: [CallbackQueryHandler(choose_type_handler, pattern="^(report_account|report_channel|cancel)$")],
            API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, api_id_handler)],
            API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, api_hash_handler)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
            REASON: [CallbackQueryHandler(reason_handler, pattern="^(spam|pornography|violence|child_abuse|other|copyright|fake|geo_irrelevant|illegal_drugs|personal_details)$")],
            CUSTOM_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_message_handler)],
            TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_handler)],
            COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, count_handler)],
            CONFIRM: [CallbackQueryHandler(confirm_handler, pattern="^(confirm|cancel)$")]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$")
        ],
        per_message=False
    )
    
    application.add_handler(conv_handler)
    
    # Хендлер ошибок
    application.add_error_handler(error_handler)
    
    print("=" * 60)
    print("🤖 Бот для репортов Telegram запущен!")
    print("📝 Основные команды:")
    print("   /start - начать работу")
    print("   /report - начать репорт (основная команда)")
    print("   /help - справка")
    print("   /my_sessions - мои сессии")
    print("=" * 60)
    print("📊 Логирование включено на уровне DEBUG")
    print("👁️  Следите за логами в консоли...")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
