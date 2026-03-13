import edge_tts
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
    tts_settings = State()   # Настройки озвучки
    ocr_mode = State()       # Режим распознавания текста с фото
    ocr_settings = State()   # Настройки OCR
    choosing_voice = State() # Выбор голоса
    choosing_accent = State() # Выбор акцента
    choosing_speed = State()  # Выбор скорости
    choosing_format = State() # Выбор формата

# АКТУАЛЬНЫЙ СПИСОК ГОЛОСОВ
VOICES = {
    'us': {
        'name': '🇺🇸 Американский английский',
        'voices': [
            {'id': 'en-US-AnaNeural', 'name': '👩 Ана', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-US-AndrewMultilingualNeural', 'name': '👨 Эндрю (мультиязычный)', 'gender': 'male', 'style': 'мультиязычный'},
            {'id': 'en-US-AndrewNeural', 'name': '👨 Эндрю', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-US-AriaNeural', 'name': '👩 Ария', 'gender': 'female', 'style': 'эмоциональный'},
            {'id': 'en-US-AvaMultilingualNeural', 'name': '👩 Ава (мультиязычный)', 'gender': 'female', 'style': 'мультиязычный'},
            {'id': 'en-US-AvaNeural', 'name': '👩 Ава', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-US-BrianMultilingualNeural', 'name': '👨 Брайан (мультиязычный)', 'gender': 'male', 'style': 'мультиязычный'},
            {'id': 'en-US-BrianNeural', 'name': '👨 Брайан', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-US-ChristopherNeural', 'name': '👨 Кристофер', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-US-EmmaMultilingualNeural', 'name': '👩 Эмма (мультиязычный)', 'gender': 'female', 'style': 'мультиязычный'},
            {'id': 'en-US-EmmaNeural', 'name': '👩 Эмма', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-US-EricNeural', 'name': '👨 Эрик', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-US-GuyNeural', 'name': '👨 Гай', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-US-JennyNeural', 'name': '👩 Дженни', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-US-MichelleNeural', 'name': '👩 Мишель', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-US-RogerNeural', 'name': '👨 Роджер', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-US-SteffanNeural', 'name': '👨 Стефан', 'gender': 'male', 'style': 'нейтральный'},
        ]
    },
    'uk': {
        'name': '🇬🇧 Британский английский',
        'voices': [
            {'id': 'en-GB-LibbyNeural', 'name': '👩 Либби', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-GB-MaisieNeural', 'name': '👩 Мэйзи', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-GB-RyanNeural', 'name': '👨 Райан', 'gender': 'male', 'style': 'нейтральный'},
            {'id': 'en-GB-SoniaNeural', 'name': '👩 Соня', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-GB-ThomasNeural', 'name': '👨 Томас', 'gender': 'male', 'style': 'нейтральный'},
        ]
    },
    'in': {
        'name': '🇮🇳 Индийский английский',
        'voices': [
            {'id': 'en-IN-NeerjaExpressiveNeural', 'name': '👩 Нирджа (экспрессивный)', 'gender': 'female', 'style': 'экспрессивный'},
            {'id': 'en-IN-NeerjaNeural', 'name': '👩 Нирджа', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-IN-PrabhatNeural', 'name': '👨 Прабат', 'gender': 'male', 'style': 'нейтральный'},
        ]
    },
    'au': {
        'name': '🇦🇺 Австралийский английский',
        'voices': [
            {'id': 'en-AU-NatashaNeural', 'name': '👩 Наташа', 'gender': 'female', 'style': 'нейтральный'},
            {'id': 'en-AU-WilliamNeural', 'name': '👨 Уильям', 'gender': 'male', 'style': 'нейтральный'},
        ]
    }
}

# ДОСТУПНЫЕ АКЦЕНТЫ
ACCENTS = {
    'us': {
        'tld': 'us',
        'name': '🇺🇸 Американский',
        'flag': '🇺🇸',
        'description': 'Американский английский',
        'default_voice': 'en-US-JennyNeural'
    },
    'uk': {
        'tld': 'co.uk',
        'name': '🇬🇧 Британский',
        'flag': '🇬🇧',
        'description': 'Британский английский',
        'default_voice': 'en-GB-SoniaNeural'
    },
    'in': {
        'tld': 'co.in',
        'name': '🇮🇳 Индийский',
        'flag': '🇮🇳',
        'description': 'Индийский английский',
        'default_voice': 'en-IN-NeerjaNeural'
    },
    'au': {
        'tld': 'com.au',
        'name': '🇦🇺 Австралийский',
        'flag': '🇦🇺',
        'description': 'Австралийский английский',
        'default_voice': 'en-AU-NatashaNeural'
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
        'description': 'Стандартное голосовое сообщение Telegram'
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
        'description': 'Аудиофайл в формате OPUS'
    },
    'wav': {
        'type': 'audio',
        'name': '🔊 WAV аудио',
        'extension': '.wav',
        'mime': 'audio/wav',
        'description': 'Аудиофайл без сжатия'
    },
    'aac': {
        'type': 'audio',
        'name': '🎧 AAC аудио',
        'extension': '.aac',
        'mime': 'audio/aac',
        'description': 'Современный формат'
    }
}

# Скорости речи
SPEED_OPTIONS = {
    '0.5': {'name': '🐢 0.5x (очень медленно)', 'factor': '0.5', 'group': 'slow'},
    '0.6': {'name': '🐢 0.6x', 'factor': '0.6', 'group': 'slow'},
    '0.7': {'name': '🐢 0.7x', 'factor': '0.7', 'group': 'slow'},
    '0.8': {'name': '🐢 0.8x', 'factor': '0.8', 'group': 'slow'},
    '0.9': {'name': '🐢 0.9x', 'factor': '0.9', 'group': 'slow'},
    '1.0': {'name': '⏺️ 1.0x (нормально)', 'factor': '1.0', 'group': 'normal'},
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

# Вспомогательная функция для получения настроек с значениями по умолчанию
def get_user_settings(user_id: int) -> dict:
    """Возвращает настройки пользователя со значениями по умолчанию"""
    if user_id not in user_settings:
        user_settings[user_id] = {}
    
    settings = user_settings[user_id]
    
    # Акцент по умолчанию
    if 'accent' not in settings:
        settings['accent'] = 'us'
    
    # Голос по умолчанию для акцента
    accent_code = settings['accent']
    default_voice = ACCENTS.get(accent_code, ACCENTS['us'])['default_voice']
    if 'voice' not in settings:
        settings['voice'] = default_voice
    
    # Скорость по умолчанию (1.0)
    if 'speed' not in settings:
        settings['speed'] = '1.0'
    
    # Формат по умолчанию (voice)
    if 'format' not in settings:
        settings['format'] = 'voice'
    
    # Язык OCR по умолчанию
    if 'ocr_lang' not in settings:
        settings['ocr_lang'] = 'eng'
    
    return settings

# Функция для создания клавиатуры навигации
def get_navigation_keyboard(back_callback: str = "back_to_tts", show_main_menu: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру навигации"""
    keyboard = []
    
    # Кнопка "Назад"
    if back_callback:
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)])
    
    # Кнопка "Главное меню"
    if show_main_menu:
        keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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

async def generate_speech_edge(text: str, voice: str, speed: str = '1.0') -> str:
    """Генерирует речь через Edge TTS (Microsoft) с выбранным голосом"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        filename = fp.name
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)
        
        # Проверяем размер файла
        if os.path.getsize(filename) < 100:
            raise Exception("Сгенерированный файл слишком мал")
        
        if speed != '1.0' and check_ffmpeg():
            filename = convert_audio(filename, 'mp3', speed)
        
        return filename
    except Exception as e:
        if os.path.exists(filename):
            os.unlink(filename)
        logger.error(f"Ошибка в generate_speech_edge: {e}")
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

# Функция для отображения главного меню
async def show_main_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню"""
    await state.set_state(BotStates.choosing_mode)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Озвучить текст", callback_data="mode_tts")],
        [InlineKeyboardButton(text="📷 Распознать текст с фото", callback_data="mode_ocr")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings")]
    ])
    
    await message.answer(
        "👋 **Главное меню**\n\n"
        "Выберите режим работы:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Функция для отображения настроек TTS
async def show_tts_settings(message: types.Message, user_id: int):
    """Показывает настройки TTS"""
    settings = get_user_settings(user_id)
    accent = ACCENTS.get(settings['accent'], ACCENTS['us'])
    
    # Находим информацию о текущем голосе
    current_voice = settings['voice']
    voice_info = "неизвестно"
    for accent_code, voice_data in VOICES.items():
        for v in voice_data['voices']:
            if v['id'] == current_voice:
                voice_info = v['name']
                break
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{accent['flag']} Акцент: {accent['name']}", callback_data="choose_accent")],
        [InlineKeyboardButton(text=f"🗣 Голос: {voice_info}", callback_data="choose_voice")],
        [InlineKeyboardButton(text=f"⚡ Скорость: {SPEED_OPTIONS[settings['speed']]['name']}", callback_data="choose_speed")],
        [InlineKeyboardButton(text=f"📁 Формат: {AUDIO_FORMATS[settings['format']]['name']}", callback_data="choose_format")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tts"),
         InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    
    await message.answer(
        f"🔊 **Настройки озвучки**\n\n"
        f"Текущие параметры:\n"
        f"• {accent['flag']} Акцент: {accent['description']}\n"
        f"• 🗣 Голос: {voice_info}\n"
        f"• ⚡ Скорость: {SPEED_OPTIONS[settings['speed']]['name']}\n"
        f"• 📁 Формат: {AUDIO_FORMATS[settings['format']]['name']}\n\n"
        f"👇 **Выберите параметр для изменения:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Функция для отображения настроек OCR
async def show_ocr_settings(message: types.Message, user_id: int):
    """Показывает настройки OCR"""
    settings = get_user_settings(user_id)
    ocr_lang = OCR_LANGUAGES.get(settings['ocr_lang'], OCR_LANGUAGES['eng'])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔤 Язык: {ocr_lang['name']}", callback_data="choose_ocr_lang")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_ocr"),
         InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    
    await message.answer(
        f"📷 **Настройки распознавания текста**\n\n"
        f"Текущий язык: {ocr_lang['name']}\n\n"
        f"👇 **Выберите параметр для изменения:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    get_user_settings(user_id)  # Инициализируем настройки
    
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
    
    await show_main_menu(message, state)

@dp.callback_query(lambda c: c.data == "mode_tts")
async def process_tts_mode(callback: types.CallbackQuery, state: FSMContext):
    """Переход в режим озвучки"""
    await state.set_state(BotStates.tts_mode)
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    accent = ACCENTS[settings['accent']]
    
    # Находим информацию о текущем голосе
    current_voice = settings['voice']
    voice_info = "неизвестно"
    for accent_code, voice_data in VOICES.items():
        for v in voice_data['voices']:
            if v['id'] == current_voice:
                voice_info = v['name']
                break
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки озвучки", callback_data="tts_settings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(
        f"🔊 **Режим озвучки текста**\n\n"
        f"Текущие настройки:\n"
        f"• Акцент: {accent['flag']} {accent['description']}\n"
        f"• Голос: {voice_info}\n"
        f"• Скорость: {SPEED_OPTIONS[settings['speed']]['name']}\n"
        f"• Формат: {AUDIO_FORMATS[settings['format']]['name']}\n\n"
        f"📝 **Отправьте текст для озвучки**\n\n"
        f"👇 **Или настройте параметры:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "tts_settings")
async def show_tts_settings_menu(callback: types.CallbackQuery, state: FSMContext):
    """Показывает меню настроек TTS"""
    await state.set_state(BotStates.tts_settings)
    user_id = callback.from_user.id
    await show_tts_settings(callback.message, user_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "mode_ocr")
async def process_ocr_mode(callback: types.CallbackQuery, state: FSMContext):
    """Переход в режим OCR"""
    if not check_tesseract():
        keyboard = get_navigation_keyboard(back_callback="back_to_menu", show_main_menu=False)
        await callback.message.edit_text(
            "❌ **OCR недоступен**\n\n"
            "Tesseract не установлен. Для работы OCR требуется:\n"
            "1. Установить Tesseract с https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Установить языковые пакеты\n"
            "3. Указать правильный путь в коде",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    await state.set_state(BotStates.ocr_mode)
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    ocr_lang = OCR_LANGUAGES[settings['ocr_lang']]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки OCR", callback_data="ocr_settings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(
        f"📷 **Режим распознавания текста**\n\n"
        f"Текущий язык: {ocr_lang['name']}\n\n"
        f"📸 **Отправьте фото с текстом**\n\n"
        f"👇 **Или настройте параметры:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "ocr_settings")
async def show_ocr_settings_menu(callback: types.CallbackQuery, state: FSMContext):
    """Показывает меню настроек OCR"""
    await state.set_state(BotStates.ocr_settings)
    user_id = callback.from_user.id
    await show_ocr_settings(callback.message, user_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "choose_accent")
async def choose_accent(callback: types.CallbackQuery, state: FSMContext):
    """Выбор акцента"""
    await state.set_state(BotStates.choosing_accent)
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    current_accent = settings['accent']
    
    keyboard = []
    for code, accent in ACCENTS.items():
        marker = "✅ " if code == current_accent else ""
        keyboard.append([InlineKeyboardButton(
            text=f"{marker}{accent['flag']} {accent['name']}",
            callback_data=f"select_accent_{code}"
        )])
    
    # Добавляем навигацию
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="tts_settings"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "🌎 **Выберите акцент:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('select_accent_'))
async def process_accent_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора акцента"""
    user_id = callback.from_user.id
    accent_code = callback.data.replace('select_accent_', '')
    
    settings = get_user_settings(user_id)
    settings['accent'] = accent_code
    settings['voice'] = ACCENTS[accent_code]['default_voice']
    
    await callback.answer(f"Акцент изменен")
    await state.set_state(BotStates.tts_settings)
    await show_tts_settings(callback.message, user_id)

@dp.callback_query(lambda c: c.data == "choose_voice")
async def choose_voice(callback: types.CallbackQuery, state: FSMContext):
    """Выбор голоса"""
    await state.set_state(BotStates.choosing_voice)
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    accent_code = settings['accent']
    
    if accent_code not in VOICES:
        accent_code = 'us'
    
    voice_data = VOICES[accent_code]
    current_voice = settings['voice']
    
    # Создаем клавиатуру с голосами
    keyboard = []
    
    # Женские голоса
    female_voices = [v for v in voice_data['voices'] if v['gender'] == 'female']
    if female_voices:
        keyboard.append([InlineKeyboardButton(text="👩 ЖЕНСКИЕ ГОЛОСА", callback_data="noop")])
        for voice in female_voices:
            marker = "✅ " if voice['id'] == current_voice else ""
            button_text = f"{marker}{voice['name']}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"select_voice_{voice['id']}")])
    
    # Мужские голоса
    male_voices = [v for v in voice_data['voices'] if v['gender'] == 'male']
    if male_voices:
        keyboard.append([InlineKeyboardButton(text="👨 МУЖСКИЕ ГОЛОСА", callback_data="noop")])
        for voice in male_voices:
            marker = "✅ " if voice['id'] == current_voice else ""
            button_text = f"{marker}{voice['name']}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"select_voice_{voice['id']}")])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="tts_settings"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        f"🎤 **Выберите голос для {VOICES[accent_code]['name']}**\n\n"
        f"Всего доступно: {len(voice_data['voices'])} голосов",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('select_voice_'))
async def process_voice_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора голоса"""
    user_id = callback.from_user.id
    voice_id = callback.data.replace('select_voice_', '')
    
    settings = get_user_settings(user_id)
    settings['voice'] = voice_id
    
    # Обновляем акцент в соответствии с голосом
    for accent_code, voice_data in VOICES.items():
        for v in voice_data['voices']:
            if v['id'] == voice_id:
                settings['accent'] = accent_code
                break
    
    await callback.answer(f"Голос выбран")
    await state.set_state(BotStates.tts_settings)
    await show_tts_settings(callback.message, user_id)

@dp.callback_query(lambda c: c.data == "choose_speed")
async def choose_speed(callback: types.CallbackQuery, state: FSMContext):
    """Выбор скорости"""
    await state.set_state(BotStates.choosing_speed)
    
    if not check_ffmpeg():
        keyboard = get_navigation_keyboard(back_callback="tts_settings", show_main_menu=True)
        await callback.message.edit_text(
            "⚠️ **Функция изменения скорости недоступна**\n\n"
            "FFmpeg не найден. Доступна только нормальная скорость.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    current_speed = settings['speed']
    
    keyboard = []
    
    # Медленные скорости
    keyboard.append([InlineKeyboardButton(text="🐢 МЕДЛЕННЫЕ", callback_data="noop")])
    for speed_code, speed_info in SPEED_OPTIONS.items():
        if speed_info.get('group') == 'slow':
            marker = "✅ " if speed_code == current_speed else ""
            keyboard.append([InlineKeyboardButton(
                text=f"{marker}{speed_info['name']}",
                callback_data=f"select_speed_{speed_code}"
            )])
    
    # Нормальная скорость
    keyboard.append([InlineKeyboardButton(text="⏺️ НОРМАЛЬНАЯ", callback_data="noop")])
    for speed_code, speed_info in SPEED_OPTIONS.items():
        if speed_info.get('group') == 'normal':
            marker = "✅ " if speed_code == current_speed else ""
            keyboard.append([InlineKeyboardButton(
                text=f"{marker}{speed_info['name']}",
                callback_data=f"select_speed_{speed_code}"
            )])
    
    # Быстрые скорости
    keyboard.append([InlineKeyboardButton(text="⚡ БЫСТРЫЕ", callback_data="noop")])
    for speed_code, speed_info in SPEED_OPTIONS.items():
        if speed_info.get('group') == 'fast':
            marker = "✅ " if speed_code == current_speed else ""
            keyboard.append([InlineKeyboardButton(
                text=f"{marker}{speed_info['name']}",
                callback_data=f"select_speed_{speed_code}"
            )])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="tts_settings"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "⚡ **Выберите скорость речи:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('select_speed_'))
async def process_speed_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора скорости"""
    user_id = callback.from_user.id
    speed_code = callback.data.replace('select_speed_', '')
    
    settings = get_user_settings(user_id)
    settings['speed'] = speed_code
    
    await callback.answer(f"Скорость изменена")
    await state.set_state(BotStates.tts_settings)
    await show_tts_settings(callback.message, user_id)

@dp.callback_query(lambda c: c.data == "choose_format")
async def choose_format(callback: types.CallbackQuery, state: FSMContext):
    """Выбор формата"""
    await state.set_state(BotStates.choosing_format)
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    current_format = settings['format']
    ffmpeg_ok = check_ffmpeg()
    
    keyboard = []
    for format_code, format_info in AUDIO_FORMATS.items():
        if not ffmpeg_ok and format_code not in ['voice', 'mp3']:
            continue
        marker = "✅ " if format_code == current_format else ""
        keyboard.append([InlineKeyboardButton(
            text=f"{marker}{format_info['name']}",
            callback_data=f"select_format_{format_code}"
        )])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="tts_settings"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "📁 **Выберите формат:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('select_format_'))
async def process_format_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора формата"""
    user_id = callback.from_user.id
    format_code = callback.data.replace('select_format_', '')
    
    settings = get_user_settings(user_id)
    settings['format'] = format_code
    
    await callback.answer(f"Формат изменен")
    await state.set_state(BotStates.tts_settings)
    await show_tts_settings(callback.message, user_id)

@dp.callback_query(lambda c: c.data == "choose_ocr_lang")
async def choose_ocr_lang(callback: types.CallbackQuery, state: FSMContext):
    """Выбор языка для OCR"""
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    current_lang = settings['ocr_lang']
    
    keyboard = []
    for lang_code, lang_info in OCR_LANGUAGES.items():
        marker = "✅ " if lang_code == current_lang else ""
        keyboard.append([InlineKeyboardButton(
            text=f"{marker}{lang_info['name']}",
            callback_data=f"select_ocr_lang_{lang_code}"
        )])
    
    # Навигация
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="ocr_settings"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "🔤 **Выберите язык для распознавания:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('select_ocr_lang_'))
async def process_ocr_lang_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора языка OCR"""
    user_id = callback.from_user.id
    lang_code = callback.data.replace('select_ocr_lang_', '')
    
    settings = get_user_settings(user_id)
    settings['ocr_lang'] = lang_code
    
    await callback.answer(f"Язык изменен")
    await show_ocr_settings(callback.message, user_id)

@dp.callback_query(lambda c: c.data == "back_to_tts")
async def back_to_tts(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в режим TTS"""
    await state.set_state(BotStates.tts_mode)
    await process_tts_mode(callback, state)

@dp.callback_query(lambda c: c.data == "back_to_ocr")
async def back_to_ocr(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в режим OCR"""
    await state.set_state(BotStates.ocr_mode)
    await process_ocr_mode(callback, state)

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await show_main_menu(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "show_settings")
async def show_settings(callback: types.CallbackQuery, state: FSMContext):
    """Показывает общие настройки"""
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    
    accent_info = ACCENTS[settings['accent']]
    speed_info = SPEED_OPTIONS[settings['speed']]
    format_info = AUDIO_FORMATS[settings['format']]
    ocr_lang = OCR_LANGUAGES[settings['ocr_lang']]
    
    # Находим информацию о голосе
    voice_info = "неизвестно"
    for accent_code, voice_data in VOICES.items():
        for v in voice_data['voices']:
            if v['id'] == settings['voice']:
                voice_info = v['name']
                break
    
    text = (
        f"⚙️ **Текущие настройки:**\n\n"
        f"🔊 **Озвучка:**\n"
        f"• Акцент: {accent_info['flag']} {accent_info['description']}\n"
        f"• Голос: {voice_info}\n"
        f"• Скорость: {speed_info['name']}\n"
        f"• Формат: {format_info['name']}\n\n"
        f"📷 **OCR:**\n"
        f"• Язык: {ocr_lang['name']}\n\n"
        f"👇 **Выберите режим для настройки:**"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 Настройки озвучки", callback_data="tts_settings")],
        [InlineKeyboardButton(text="📷 Настройки OCR", callback_data="ocr_settings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "noop")
async def process_noop(callback: types.CallbackQuery):
    """Заглушка для кнопок-заголовков"""
    await callback.answer()

@dp.message(Command('menu'))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Возврат в главное меню"""
    await show_main_menu(message, state)

# Обработчик текста в режиме озвучки
@dp.message(BotStates.tts_mode)
async def handle_tts_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст!")
        return
    
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    
    accent_info = ACCENTS[settings['accent']]
    voice_id = settings['voice']
    
    # Находим информацию о голосе
    voice_name = "выбранный голос"
    for accent_code, voice_data in VOICES.items():
        for v in voice_data['voices']:
            if v['id'] == voice_id:
                voice_name = v['name']
                break
    
    await bot.send_chat_action(message.chat.id, action="record_voice")
    
    try:
        status_msg = await message.answer(f"🔄 Генерирую речь голосом {voice_name}...")
        
        filename = await generate_speech_edge(
            message.text, 
            voice_id, 
            settings['speed']
        )
        
        await status_msg.edit_text("🔄 Конвертирую в нужный формат...")
        
        final_file = filename
        if settings['format'] != 'mp3' and check_ffmpeg():
            final_file = convert_audio(filename, settings['format'], '1.0')
        
        audio_file = FSInputFile(final_file)
        
        await status_msg.delete()
        
        if settings['format'] == 'voice':
            await message.answer_voice(
                audio_file,
                caption=f"{accent_info['flag']} {voice_name}"
            )
        else:
            format_name = AUDIO_FORMATS[settings['format']]['name']
            await message.answer_audio(
                audio_file,
                caption=f"{accent_info['flag']} {voice_name} ({format_name})"
            )
        
        for f in [filename, final_file]:
            if os.path.exists(f) and f != filename:
                os.unlink(f)
        
    except Exception as e:
        logger.error(f"Ошибка генерации речи: {e}")
        await message.answer(f"❌ Ошибка: {e}")

# Обработчик фото в режиме OCR
@dp.message(BotStates.ocr_mode)
async def handle_ocr_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото с текстом!")
        return
    
    user_id = message.from_user.id
    settings = get_user_settings(user_id)
    lang_info = OCR_LANGUAGES[settings['ocr_lang']]
    
    await bot.send_chat_action(message.chat.id, action="typing")
    
    try:
        photo = message.photo[-1]
        
        status_msg = await message.answer("🔄 Скачиваю изображение...")
        
        image_path = await download_file(photo.file_id)
        
        await status_msg.edit_text("🔄 Распознаю текст...")
        
        recognized_text = ocr_image(image_path, lang_info['tesseract_code'])
        
        await status_msg.delete()
        
        if recognized_text.startswith("❌"):
            await message.answer(recognized_text)
        else:
            if len(recognized_text) > 4000:
                parts = [recognized_text[i:i+4000] for i in range(0, len(recognized_text), 4000)]
                for i, part in enumerate(parts, 1):
                    await message.answer(f"📝 **Распознанный текст (часть {i}/{len(parts)}):**\n```\n{part}\n```", parse_mode="Markdown")
            else:
                await message.answer(f"📝 **Распознанный текст:**\n```\n{recognized_text}\n```", parse_mode="Markdown")
        
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
        keyboard = get_navigation_keyboard(back_callback="back_to_menu", show_main_menu=False)
        await message.answer(
            "❓ Неизвестная команда. Используйте кнопки навигации.",
            reply_markup=keyboard
        )

async def main():
    """Запуск бота"""
    logger.info("🚀 Бот запускается...")
    
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
