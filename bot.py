from gtts import gTTS
import os
import tempfile
import subprocess
import pytesseract
from PIL import Image
import requests
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
API_TOKEN = '8627063543:AAHvc33DfNFjcVT--sKfgHsCVyemY72fQ7Q'

# Путь к Tesseract (нужно установить!)
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Для Windows
# Для Linux обычно: /usr/bin/tesseract

# Устанавливаем путь к Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Инициализация бота с хранилищем состояний
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

# Путь к ffmpeg
FFMPEG_PATH = r"C:\Users\anton\Downloads\dobro_loader\dobro_loader\bin\ffmpeg.exe"

# Состояния для FSM (Finite State Machine)
class BotStates(StatesGroup):
    choosing_mode = State()  # Выбор режима (озвучка/распознавание)
    tts_mode = State()       # Режим озвучки текста
    ocr_mode = State()       # Режим распознавания текста с фото
    ocr_language = State()   # Выбор языка для OCR

# ДОСТУПНЫЕ АКЦЕНТЫ
ACCENTS = {
    'us': {
        'tld': 'us',
        'name': '🇺🇸 Американский',
        'flag': '🇺🇸',
        'description': 'Американский английский'
    },
    'uk': {
        'tld': 'co.uk',
        'name': '🇬🇧 Британский',
        'flag': '🇬🇧',
        'description': 'Британский английский'
    },
    'in': {
        'tld': 'co.in',
        'name': '🇮🇳 Индийский',
        'flag': '🇮🇳',
        'description': 'Индийский английский'
    }
}

# Языки для OCR
OCR_LANGUAGES = {
    'eng': {
        'name': '🇬🇧 Английский',
        'code': 'eng',
        'tesseract_code': 'eng'
    },
    'rus': {
        'name': '🇷🇺 Русский',
        'code': 'rus',
        'tesseract_code': 'rus'
    },
    'eng+rus': {
        'name': '🇬🇧+🇷🇺 Английский и русский',
        'code': 'eng+rus',
        'tesseract_code': 'eng+rus'
    }
}

# ДОСТУПНЫЕ ФОРМАТЫ
AUDIO_FORMATS = {
    'voice': {
        'type': 'voice',
        'name': '🎤 Голосовое сообщение',
        'extension': '.ogg',
        'mime': 'audio/ogg',
        'description': 'Стандартное голосовое сообщение Telegram (OPUS)'
    },
    'mp3': {
        'type': 'audio',
        'name': '🎵 MP3 аудио',
        'extension': '.mp3',
        'mime': 'audio/mpeg',
        'description': 'Аудиофайл в формате MP3'
    },
    'opus': {
        'type': 'audio',
        'name': '🎼 OPUS аудио',
        'extension': '.opus',
        'mime': 'audio/opus',
        'description': 'Аудиофайл в формате OPUS (высокое качество)'
    },
    'wav': {
        'type': 'audio',
        'name': '🔊 WAV аудио',
        'extension': '.wav',
        'mime': 'audio/wav',
        'description': 'Аудиофайл без сжатия (качественный, большой)'
    },
    'aac': {
        'type': 'audio',
        'name': '🎧 AAC аудио',
        'extension': '.aac',
        'mime': 'audio/aac',
        'description': 'Современный формат с хорошим сжатием'
    }
}

# Скорости речи
# Скорости речи с шагом 0.1 (сгруппированные)
SPEED_OPTIONS = {
    # Медленные (0.5 - 0.9)
    '0.5': {'name': '🐢 0.5x (очень медленно)', 'factor': '0.5', 'group': 'slow'},
    '0.6': {'name': '🐢 0.6x', 'factor': '0.6', 'group': 'slow'},
    '0.7': {'name': '🐢 0.7x', 'factor': '0.7', 'group': 'slow'},
    '0.8': {'name': '🐢 0.8x', 'factor': '0.8', 'group': 'slow'},
    '0.9': {'name': '🐢 0.9x', 'factor': '0.9', 'group': 'slow'},
    
    # Нормальная
    '1.0': {'name': '⏺️ 1.0x (нормально)', 'factor': '1.0', 'group': 'normal'},
    
    # Быстрые (1.1 - 2.0)
    '1.1': {'name': '⚡ 1.1x', 'factor': '1.1', 'group': 'fast'},
    '1.2': {'name': '⚡ 1.2x', 'factor': '1.2', 'group': 'fast'},
    '1.3': {'name': '⚡ 1.3x', 'factor': '1.3', 'group': 'fast'},
    '1.4': {'name': '⚡ 1.4x', 'factor': '1.4', 'group': 'fast'},
    '1.5': {'name': '🚀 1.5x (быстро)', 'factor': '1.5', 'group': 'fast'},
    '1.6': {'name': '🚀 1.6x', 'factor': '1.6', 'group': 'fast'},
    '1.7': {'name': '🚀 1.7x', 'factor': '1.7', 'group': 'fast'},
    '1.8': {'name': '🚀 1.8x', 'factor': '1.8', 'group': 'fast'},
    '1.9': {'name': '🚀 1.9x', 'factor': '1.9', 'group': 'fast'},
    '2.0': {'name': '💨 2.0x (очень быстро)', 'factor': '2.0', 'group': 'fast'}
}

# Хранилище настроек пользователей
user_settings = {}

def check_ffmpeg():
    """Проверяет наличие ffmpeg"""
    if os.path.exists(FFMPEG_PATH):
        try:
            result = subprocess.run([FFMPEG_PATH, '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return True
        except:
            pass
    return False

def check_tesseract():
    """Проверяет наличие Tesseract"""
    if os.path.exists(TESSERACT_PATH):
        try:
            result = subprocess.run([TESSERACT_PATH, '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ Tesseract найден")
                return True
        except:
            pass
    logger.error(f"❌ Tesseract не найден по пути: {TESSERACT_PATH}")
    return False

def convert_audio(input_file: str, output_format: str, speed_factor: str = '1.0') -> str:
    """Конвертирует аудио в нужный формат"""
    if not os.path.exists(FFMPEG_PATH):
        return input_file
    
    base = os.path.splitext(input_file)[0]
    speed = SPEED_OPTIONS.get(speed_factor, SPEED_OPTIONS['1.0'])
    format_info = AUDIO_FORMATS.get(output_format, AUDIO_FORMATS['mp3'])
    output_file = f"{base}_{speed_factor}x{format_info['extension']}"
    
    format_params = {
        'mp3': ['-c:a', 'libmp3lame', '-b:a', '128k'],
        'opus': ['-c:a', 'libopus', '-b:a', '24k', '-application', 'voip'],
        'aac': ['-c:a', 'aac', '-b:a', '128k'],
        'wav': ['-c:a', 'pcm_s16le'],
        'voice': ['-c:a', 'libopus', '-b:a', '24k', '-application', 'voip']
    }
    
    cmd = [FFMPEG_PATH, '-i', input_file, '-y']
    
    if speed['factor'] != '1.0':
        try:
            speed_float = float(speed['factor'])
            if speed_float <= 2.0:
                cmd.extend(['-af', f"atempo={speed_float}"])
            else:
                cmd.extend(['-af', f"atempo=2.0,atempo={speed_float/2.0}"])
        except:
            pass
    
    cmd.extend(format_params.get(output_format, format_params['mp3']))
    cmd.append(output_file)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            if input_file != output_file and os.path.exists(input_file):
                os.unlink(input_file)
            return output_file
    except:
        pass
    
    return input_file

def generate_speech(text: str, tld: str = 'us', speed: str = '1.0') -> str:
    """Генерирует речь"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        filename = fp.name
    
    try:
        tts = gTTS(
            text=text,
            lang='en',
            tld=tld,
            slow=False,
            lang_check=False
        )
        tts.save(filename)
        
        file_size = os.path.getsize(filename)
        if file_size < 100:
            raise Exception(f"Файл слишком мал: {file_size} байт")
        
        if speed != '1.0' and check_ffmpeg():
            filename = convert_audio(filename, 'mp3', speed)
        
        return filename
        
    except Exception as e:
        if os.path.exists(filename):
            os.unlink(filename)
        raise e

async def download_file(file_id: str) -> str:
    """Скачивает файл из Telegram и возвращает путь к нему"""
    file = await bot.get_file(file_id)
    file_path = file.file_path
    destination = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1]).name
    await bot.download_file(file_path, destination)
    return destination

def ocr_image(image_path: str, lang: str = 'eng') -> str:
    """Распознает текст на изображении"""
    try:
        # Открываем изображение
        image = Image.open(image_path)
        
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Распознаем текст
        text = pytesseract.image_to_string(image, lang=lang)
        
        # Очищаем текст
        text = text.strip()
        if not text:
            return "❌ Текст не найден на изображении"
        
        return text
        
    except Exception as e:
        logger.error(f"Ошибка OCR: {e}")
        return f"❌ Ошибка распознавания: {e}"
    finally:
        # Удаляем временный файл
        if os.path.exists(image_path):
            os.unlink(image_path)

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Настройки по умолчанию
    if user_id not in user_settings:
        user_settings[user_id] = {
            'accent': 'us',
            'speed': '1.0',
            'format': 'voice',
            'ocr_lang': 'eng'
        }
    
    # Проверяем наличие компонентов
    ffmpeg_ok = check_ffmpeg()
    tesseract_ok = check_tesseract()
    
    status_text = []
    if ffmpeg_ok:
        status_text.append("✅ FFmpeg: доступен")
    else:
        status_text.append("⚠️ FFmpeg: не найден (скорость и форматы ограничены)")
    
    if tesseract_ok:
        status_text.append("✅ Tesseract: доступен")
    else:
        status_text.append("⚠️ Tesseract: не найден (OCR недоступен)")
    
    welcome_text = (
        "👋 **Привет! Я многофункциональный бот!**\n\n"
        "📝 **Что я умею:**\n"
        "1️⃣ **Озвучивать текст** - отправь текст, получу аудио\n"
        "2️⃣ **Распознавать текст с фото** - отправь фото, получу текст\n\n"
        f"🔧 **Статус:**\n" + "\n".join(status_text) + "\n\n"
        "👇 **Выберите режим работы:**"
    )
    
    # Клавиатура выбора режима
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Озвучить текст", callback_data="mode_tts")],
        [InlineKeyboardButton(text="📷 Распознать текст с фото", callback_data="mode_ocr")]
    ])
    
    await state.set_state(BotStates.choosing_mode)
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "mode_tts")
async def process_tts_mode(callback: types.CallbackQuery, state: FSMContext):
    """Переход в режим озвучки"""
    await state.set_state(BotStates.tts_mode)
    
    user_id = callback.from_user.id
    settings = user_settings.get(user_id, {})
    accent = ACCENTS.get(settings.get('accent', 'us'), ACCENTS['us'])
    
    await callback.message.edit_text(
        f"🔊 **Режим озвучки текста**\n\n"
        f"Текущие настройки:\n"
        f"• Акцент: {accent['flag']} {accent['description']}\n"
        f"• Скорость: {SPEED_OPTIONS[settings.get('speed', '1.0')]['name']}\n"
        f"• Формат: {AUDIO_FORMATS[settings.get('format', 'voice')]['name']}\n\n"
        f"📝 Отправьте текст на английском, и я пришлю аудио.\n\n"
        f"⚙️ Для изменения настроек используйте команды:\n"
        f"/accent - выбрать акцент\n"
        f"/speed - настроить скорость\n"
        f"/format - выбрать формат\n"
        f"/menu - вернуться в главное меню",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "mode_ocr")
async def process_ocr_mode(callback: types.CallbackQuery, state: FSMContext):
    """Переход в режим OCR"""
    if not check_tesseract():
        await callback.message.edit_text(
            "❌ **OCR недоступен**\n\n"
            "Tesseract не установлен. Для работы OCR требуется:\n"
            "1. Установить Tesseract с https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Установить языковые пакеты\n"
            "3. Указать правильный путь в коде\n\n"
            "Пока доступен только режим озвучки /start",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    await state.set_state(BotStates.ocr_mode)
    
    user_id = callback.from_user.id
    settings = user_settings.get(user_id, {})
    ocr_lang = OCR_LANGUAGES.get(settings.get('ocr_lang', 'eng'), OCR_LANGUAGES['eng'])
    
    # Клавиатура выбора языка
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for lang_code, lang_info in OCR_LANGUAGES.items():
        marker = "✅ " if lang_code == settings.get('ocr_lang', 'eng') else ""
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{marker}{lang_info['name']}",
                callback_data=f"ocr_lang_{lang_code}"
            )
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")
    ])
    
    await callback.message.edit_text(
        f"📷 **Режим распознавания текста**\n\n"
        f"Текущий язык: {ocr_lang['name']}\n\n"
        f"📸 Отправьте фото с текстом, и я распознаю его.\n\n"
        f"💡 Совет: Чем четче фото, тем лучше результат!\n\n"
        f"👇 **Выберите язык для распознавания:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('ocr_lang_'))
async def process_ocr_lang(callback: types.CallbackQuery, state: FSMContext):
    """Выбор языка для OCR"""
    user_id = callback.from_user.id
    lang_code = callback.data.replace('ocr_lang_', '')
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    
    user_settings[user_id]['ocr_lang'] = lang_code
    lang_info = OCR_LANGUAGES[lang_code]
    
    # Обновляем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for code, info in OCR_LANGUAGES.items():
        marker = "✅ " if code == lang_code else ""
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{marker}{info['name']}",
                callback_data=f"ocr_lang_{code}"
            )
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")
    ])
    
    await callback.message.edit_text(
        f"📷 **Режим распознавания текста**\n\n"
        f"✅ Язык изменен на: {lang_info['name']}\n\n"
        f"📸 Отправьте фото с текстом, и я распознаю его.\n\n"
        f"👇 **Выберите язык для распознавания:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.set_state(BotStates.choosing_mode)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Озвучить текст", callback_data="mode_tts")],
        [InlineKeyboardButton(text="📷 Распознать текст с фото", callback_data="mode_ocr")]
    ])
    
    await callback.message.edit_text(
        "👋 **Главное меню**\n\n"
        "Выберите режим работы:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()
    
@dp.callback_query(lambda c: c.data == "noop")
async def process_noop(callback: types.CallbackQuery):
    """Заглушка для кнопок-заголовков"""
    await callback.answer()
    
@dp.callback_query(lambda c: c.data == "back_to_tts")
async def back_to_tts(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в режим TTS"""
    await state.set_state(BotStates.tts_mode)
    
    user_id = callback.from_user.id
    settings = user_settings.get(user_id, {})
    accent = ACCENTS.get(settings.get('accent', 'us'), ACCENTS['us'])
    
    await callback.message.edit_text(
        f"🔊 **Режим озвучки текста**\n\n"
        f"Текущие настройки:\n"
        f"• Акцент: {accent['flag']} {accent['description']}\n"
        f"• Скорость: {SPEED_OPTIONS[settings.get('speed', '1.0')]['name']}\n"
        f"• Формат: {AUDIO_FORMATS[settings.get('format', 'voice')]['name']}\n\n"
        f"📝 Отправьте текст на английском, и я пришлю аудио.\n\n"
        f"⚙️ Для изменения настроек используйте команды:\n"
        f"/accent - выбрать акцент\n"
        f"/speed - настроить скорость\n"
        f"/format - выбрать формат\n"
        f"/menu - вернуться в главное меню",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(Command('menu'))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.set_state(BotStates.choosing_mode)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Озвучить текст", callback_data="mode_tts")],
        [InlineKeyboardButton(text="📷 Распознать текст с фото", callback_data="mode_ocr")]
    ])
    
    await message.answer(
        "👋 **Главное меню**\n\n"
        "Выберите режим работы:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Команды для режима озвучки
@dp.message(Command('accent'))
async def cmd_accent(message: types.Message, state: FSMContext):
    """Выбор акцента"""
    current_state = await state.get_state()
    if current_state != BotStates.tts_mode:
        await message.answer("Сначала выберите режим озвучки через /menu")
        return
    
    user_id = message.from_user.id
    current_accent = user_settings.get(user_id, {}).get('accent', 'us')
    
    keyboard = []
    row = []
    for code, accent in ACCENTS.items():
        marker = "✅ " if code == current_accent else ""
        button = InlineKeyboardButton(
            text=f"{marker}{accent['flag']} {accent['name']}",
            callback_data=f"accent_{code}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("🌎 **Выберите акцент:**", reply_markup=markup, parse_mode="Markdown")

@dp.message(Command('speed'))
async def cmd_speed(message: types.Message, state: FSMContext):
    """Выбор скорости речи с группировкой по категориям"""
    current_state = await state.get_state()
    if current_state != BotStates.tts_mode:
        await message.answer("Сначала выберите режим озвучки через /menu")
        return
    
    ffmpeg_ok = check_ffmpeg()
    
    if not ffmpeg_ok:
        await message.answer(
            "⚠️ **Функция изменения скорости недоступна**\n\n"
            "FFmpeg не найден. Доступна только нормальная скорость.",
            parse_mode="Markdown"
        )
        return
    
    user_id = message.from_user.id
    current_speed = user_settings.get(user_id, {}).get('speed', '1.0')
    
    # Создаем клавиатуру сгруппированную по категориям
    keyboard = []
    
    # Заголовок для медленных скоростей
    keyboard.append([InlineKeyboardButton(text="🐢 МЕДЛЕННЫЕ", callback_data="noop")])
    
    # Медленные скорости (по 3 в ряд)
    slow_row = []
    for speed_code, speed_info in SPEED_OPTIONS.items():
        if speed_info.get('group') == 'slow':
            marker = "✅ " if speed_code == current_speed else ""
            button = InlineKeyboardButton(
                text=f"{marker}{speed_info['name'].replace('🐢 ', '')}",
                callback_data=f"speed_{speed_code}"
            )
            slow_row.append(button)
            if len(slow_row) == 3:
                keyboard.append(slow_row)
                slow_row = []
    if slow_row:
        keyboard.append(slow_row)
    
    # Нормальная скорость
    keyboard.append([InlineKeyboardButton(text="⏺️ НОРМАЛЬНАЯ", callback_data="noop")])
    for speed_code, speed_info in SPEED_OPTIONS.items():
        if speed_info.get('group') == 'normal':
            marker = "✅ " if speed_code == current_speed else ""
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{marker}{speed_info['name'].replace('⏺️ ', '')}",
                    callback_data=f"speed_{speed_code}"
                )
            ])
    
    # Быстрые скорости
    keyboard.append([InlineKeyboardButton(text="⚡ БЫСТРЫЕ", callback_data="noop")])
    fast_row = []
    for speed_code, speed_info in SPEED_OPTIONS.items():
        if speed_info.get('group') == 'fast':
            marker = "✅ " if speed_code == current_speed else ""
            # Убираем эмодзи из текста для компактности
            clean_name = speed_info['name'].replace('⚡ ', '').replace('🚀 ', '').replace('💨 ', '')
            button = InlineKeyboardButton(
                text=f"{marker}{clean_name}",
                callback_data=f"speed_{speed_code}"
            )
            fast_row.append(button)
            if len(fast_row) == 3:
                keyboard.append(fast_row)
                fast_row = []
    if fast_row:
        keyboard.append(fast_row)
    
    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="back_to_tts")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        "⚡ **Выберите скорость речи:**\n"
        "(шаг 0.1x от 0.5x до 2.0x, без искажения тона)",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
@dp.message(Command('format'))
async def cmd_format(message: types.Message, state: FSMContext):
    """Выбор формата"""
    current_state = await state.get_state()
    if current_state != BotStates.tts_mode:
        await message.answer("Сначала выберите режим озвучки через /menu")
        return
    
    ffmpeg_ok = check_ffmpeg()
    user_id = message.from_user.id
    current_format = user_settings.get(user_id, {}).get('format', 'voice')
    
    keyboard = []
    row = []
    for format_code, format_info in AUDIO_FORMATS.items():
        if not ffmpeg_ok and format_code not in ['voice', 'mp3']:
            continue
        marker = "✅ " if format_code == current_format else ""
        button = InlineKeyboardButton(
            text=f"{marker}{format_info['name']}",
            callback_data=f"format_{format_code}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("📁 **Выберите формат:**", reply_markup=markup, parse_mode="Markdown")
    
@dp.message(Command('settings'))
async def cmd_settings(message: types.Message, state: FSMContext):
    """Показать текущие настройки"""
    user_id = message.from_user.id
    
    # Настройки по умолчанию, если нет
    if user_id not in user_settings:
        user_settings[user_id] = {
            'accent': 'us',
            'speed': '1.0',
            'format': 'voice',
            'ocr_lang': 'eng'
        }
    
    settings = user_settings[user_id]
    accent_info = ACCENTS[settings['accent']]
    speed_info = SPEED_OPTIONS[settings['speed']]
    format_info = AUDIO_FORMATS[settings['format']]
    
    # Проверяем текущий режим
    current_state = await state.get_state()
    
    # Добавляем информацию о языке OCR если в режиме OCR
    ocr_info = ""
    if current_state == BotStates.ocr_mode:
        ocr_lang = OCR_LANGUAGES.get(settings.get('ocr_lang', 'eng'), OCR_LANGUAGES['eng'])
        ocr_info = f"🔤 Язык OCR: {ocr_lang['name']}\n"
    
    mode_info = ""
    if current_state == BotStates.tts_mode:
        mode_info = "🔊 **Режим озвучки текста**\n\n"
    elif current_state == BotStates.ocr_mode:
        mode_info = "📷 **Режим распознавания текста**\n\n"
    else:
        mode_info = "👋 **Главное меню**\n\n"
    
    text = (
        f"{mode_info}"
        f"⚙️ **Текущие настройки:**\n\n"
        f"🎤 Акцент: {accent_info['flag']} {accent_info['description']}\n"
        f"⚡ Скорость: {speed_info['name']}\n"
        f"📁 Формат: {format_info['name']}\n"
        f"{ocr_info}\n"
        f"📝 **Доступные команды:**\n"
        f"/accent - изменить акцент\n"
        f"/speed - изменить скорость\n"
        f"/format - изменить формат\n"
        f"/menu - вернуться в главное меню"
    )
    
    await message.answer(text, parse_mode="Markdown")

# Обработчики callback'ов
@dp.callback_query(lambda c: c.data.startswith('accent_'))
async def process_accent(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    accent_code = callback.data.replace('accent_', '')
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    
    user_settings[user_id]['accent'] = accent_code
    accent_info = ACCENTS[accent_code]
    
    await callback.answer(f"Выбран акцент: {accent_info['name']}")
    await callback.message.edit_text(
        f"✅ Акцент изменен на {accent_info['flag']} {accent_info['description']}\n\n"
        f"Продолжайте отправлять текст для озвучки."
    )

@dp.callback_query(lambda c: c.data.startswith('speed_'))
async def process_speed(callback: types.CallbackQuery):
    """Обработка выбора скорости"""
    if not check_ffmpeg():
        await callback.answer("❌ FFmpeg не найден, скорость изменить нельзя", show_alert=True)
        return
        
    user_id = callback.from_user.id
    speed_code = callback.data.replace('speed_', '')
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    
    user_settings[user_id]['speed'] = speed_code
    speed_info = SPEED_OPTIONS[speed_code]
    
    await callback.answer(f"Выбрана скорость: {speed_info['name']}")
    
    # Показываем обновленные настройки
    settings = user_settings[user_id]
    accent = ACCENTS.get(settings.get('accent', 'us'), ACCENTS['us'])
    
    await callback.message.edit_text(
        f"🔊 **Режим озвучки текста**\n\n"
        f"✅ Скорость изменена на: {speed_info['name']}\n\n"
        f"Текущие настройки:\n"
        f"• Акцент: {accent['flag']} {accent['description']}\n"
        f"• Скорость: {SPEED_OPTIONS[settings.get('speed', '1.0')]['name']}\n"
        f"• Формат: {AUDIO_FORMATS[settings.get('format', 'voice')]['name']}\n\n"
        f"📝 Отправьте текст для озвучки или используйте команды:\n"
        f"/accent - изменить акцент\n"
        f"/speed - изменить скорость\n"
        f"/format - изменить формат",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith('format_'))
async def process_format(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    format_code = callback.data.replace('format_', '')
    
    if user_id not in user_settings:
        user_settings[user_id] = {}
    
    user_settings[user_id]['format'] = format_code
    format_info = AUDIO_FORMATS[format_code]
    
    await callback.answer(f"Выбран формат: {format_info['name']}")
    await callback.message.edit_text(
        f"✅ Формат изменен на: {format_info['name']}\n\n"
        f"Продолжайте отправлять текст для озвучки."
    )

# Обработчик текста в режиме озвучки
@dp.message(BotStates.tts_mode)
async def handle_tts_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст!")
        return
    
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {
        'accent': 'us',
        'speed': '1.0',
        'format': 'voice'
    })
    
    accent_info = ACCENTS[settings['accent']]
    
    await bot.send_chat_action(message.chat.id, action="record_voice")
    
    try:
        filename = generate_speech(
            message.text,
            accent_info['tld'],
            settings['speed']
        )
        
        final_file = filename
        if check_ffmpeg() and settings['format'] != 'mp3':
            final_file = convert_audio(filename, settings['format'], '1.0')
        
        audio_file = FSInputFile(final_file)
        
        if settings['format'] == 'voice' or not check_ffmpeg():
            await message.answer_voice(
                audio_file,
                caption=f"{accent_info['flag']} {accent_info['description']}"
            )
        else:
            await message.answer_audio(
                audio_file,
                caption=f"{accent_info['flag']} {accent_info['description']}"
            )
        
        if os.path.exists(final_file):
            os.unlink(final_file)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# Обработчик фото в режиме OCR
@dp.message(BotStates.ocr_mode)
async def handle_ocr_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото с текстом!")
        return
    
    user_id = message.from_user.id
    settings = user_settings.get(user_id, {'ocr_lang': 'eng'})
    lang_code = settings.get('ocr_lang', 'eng')
    lang_info = OCR_LANGUAGES[lang_code]
    
    await bot.send_chat_action(message.chat.id, action="typing")
    
    try:
        # Получаем фото максимального размера
        photo = message.photo[-1]
        
        # Отправляем статус
        status_msg = await message.answer("🔄 Скачиваю изображение...")
        
        # Скачиваем фото
        image_path = await download_file(photo.file_id)
        
        await status_msg.edit_text("🔄 Распознаю текст...")
        
        # Распознаем текст
        recognized_text = ocr_image(image_path, lang_info['tesseract_code'])
        
        # Отправляем результат
        if recognized_text.startswith("❌"):
            await message.answer(recognized_text)
        else:
            # Разбиваем длинный текст на части
            if len(recognized_text) > 4000:
                parts = [recognized_text[i:i+4000] for i in range(0, len(recognized_text), 4000)]
                for i, part in enumerate(parts, 1):
                    await message.answer(f"📝 **Распознанный текст (часть {i}/{len(parts)}):**\n```\n{part}\n```", parse_mode="Markdown")
            else:
                await message.answer(f"📝 **Распознанный текст:**\n```\n{recognized_text}\n```", parse_mode="Markdown")
        
        await status_msg.delete()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.error(f"OCR error: {e}")

# Обработчик для непонятных сообщений
@dp.message()
async def handle_unknown(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    
    if not current_state:
        await message.answer(
            "👋 Используйте /start для начала работы\n"
            "или /menu для выбора режима"
        )
    elif current_state == BotStates.tts_mode:
        await message.answer("Пожалуйста, отправьте текст для озвучки!")
    elif current_state == BotStates.ocr_mode:
        await message.answer("Пожалуйста, отправьте фото с текстом!")
    else:
        await message.answer("Используйте кнопки меню для выбора действия.")

async def main():
    """Запуск бота"""
    logger.info("🚀 Бот запускается...")
    
    # Проверяем компоненты
    if check_ffmpeg():
        logger.info("✅ FFmpeg доступен")
    else:
        logger.warning("⚠️ FFmpeg не найден")
    
    if check_tesseract():
        logger.info("✅ Tesseract доступен")
    else:
        logger.warning("⚠️ Tesseract не найден - OCR будет недоступен")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())