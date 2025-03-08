import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, StateFilter
import googlemaps
import aiosqlite
from keep_alive import keep_alive
import os
from dotenv import load_dotenv
from math import radians, sin, cos, sqrt, atan2

# Загрузка переменных окружения из файла .env
load_dotenv('token.env')

# API Keys and Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
GOOGLE_PLACES_API_KEY = "AIzaSyB6IPLVxeFvSPLRuHMNiMQLN3zk_fsXCms"
GMAPS = googlemaps.Client(key=GOOGLE_PLACES_API_KEY)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# States
class UserState(StatesGroup):
    language = State()
    phone = State()
    main_menu = State()
    brand = State()
    model = State()
    manual_model = State()
    mileage = State()
    oil_type = State()
    location = State()

# Keyboards
language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Русский 🇷🇺")],
        [KeyboardButton(text="Узбекский 🇺🇿")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

def create_phone_keyboard(language):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_translation(language, "share_phone_button"), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def create_main_menu_keyboard(language):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_translation(language, "my_cars_button"))],
            [KeyboardButton(text=get_translation(language, "contact_button"))],
            [KeyboardButton(text=get_translation(language, "nearest_sto_button"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def create_my_cars_keyboard(language):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_translation(language, "add_car_button"))],
            [KeyboardButton(text=get_translation(language, "main_menu_button"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def create_back_main_menu_keyboard(language):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_translation(language, "back_button"))],
            [KeyboardButton(text=get_translation(language, "main_menu_button"))]
        ],
        resize_keyboard=True
    )

# Popular car brands in Uzbekistan (example)
popular_brands_uz = [
    "Chevrolet", "Hyundai", "Kia",
    "BYD", "Toyota", "Другое"
]

def create_brand_keyboard():
    row1 = [KeyboardButton(text=brand) for brand in popular_brands_uz[:3]]
    row2 = [KeyboardButton(text=brand) for brand in popular_brands_uz[3:]]
    keyboard = [row1, row2]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

# Popular models for each brand
popular_models = {
    "Chevrolet": ["Nexia", "Cobalt", "Gentra", "Tracker", "Onix", "Другое"],
    "Hyundai": ["Sonata", "Elantra", "Tucson", "Santa Fe", "Creta", "Другое"],
    "Kia": ["K5", "Sportage", "Seltos", "Cerato", "Rio", "Другое"],
    "BYD": ["Song Plus", "Qin Plus", "Han", "Tang", "Seal", "Другое"],
    "Toyota": ["Corolla", "Camry", "Prado", "Land Cruiser", "RAV4", "Другое"],
    "Другое": []
}

# Oil recommendations
oil_recommendations = {
    "Chevrolet": {
        "Nexia": "5W-30 (GM Dexos2)",
        "Cobalt": "5W-30 (GM Dexos2)",
        "Gentra": "5W-30 (GM Dexos2)",
        "Tracker": "5W-30 (GM Dexos1 Gen2)",
        "Onix": "0W-20 (GM Dexos1 Gen3)",
        "Другое": "5W-30 (GM Dexos2)"
    },
    "Hyundai": {
        "Sonata": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Elantra": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Tucson": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Santa Fe": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Creta": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Другое": "5W-30 (API SN/SP, ACEA C2/C3)"
    },
    "Kia": {
        "K5": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Sportage": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Seltos": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Cerato": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Rio": "5W-30 (API SN/SP, ACEA C2/C3)",
        "Другое": "5W-30 (API SN/SP, ACEA C2/C3)"
    },
    "BYD": {
        "Song Plus": "0W-20 (API SP, ACEA C5)",
        "Qin Plus": "0W-20 (API SP, ACEA C5)",
        "Han": "0W-20 (API SP, ACEA C5)",
        "Tang": "0W-20 (API SP, ACEA C5)",
        "Seal": "0W-20 (API SP, ACEA C5)",
        "Другое": "0W-20 (API SP, ACEA C5)"
    },
    "Toyota": {
        "Corolla": "0W-20 (Toyota Genuine Motor Oil)",
        "Camry": "0W-20 (Toyota Genuine Motor Oil)",
        "Prado": "5W-30 (Toyota Genuine Motor Oil)",
        "Land Cruiser": "5W-30 (Toyota Genuine Motor Oil)",
        "RAV4": "0W-20 (Toyota Genuine Motor Oil)",
        "Другое": "5W-30 (Toyota Genuine Motor Oil)"
    },
    "Другое": {
        "Другое": "5W-30 (API SN/SP, ACEA C2/C3)"
    }
}

# Oil options
oil_options = {
    "5W-30": "Универсальное",
    "5W-40": "Для пробега",
    "0W-20": "Энергосберегающее"
}

def create_oil_keyboard(language):
    keyboard = [
        [KeyboardButton(text="5W-30\n(Универсальное)")],
        [KeyboardButton(text="5W-40\n(Для пробега)")],
        [KeyboardButton(text="0W-20\n(Энергосберегающее)")],
        [KeyboardButton(text=get_translation(language, "back_button"))],
        [KeyboardButton(text=get_translation(language, "main_menu_button"))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Translations
translations = {
    "ru": {
        "start_message": "Привет! Выберите язык:",
        "phone_message": "Пожалуйста, поделитесь своим номером телефона:",
        "share_phone_button": "📞 Поделиться номером",
        "brand_message": "Выберите марку вашего автомобиля:",
        "model_message": "Выберите модель вашего автомобиля:",
        "manual_model_message": "Пожалуйста, введите марку и модель вашего автомобиля вручную:",
        "mileage_message": "Введите пробег вашего автомобиля (км):",
        "oil_type_message": "Выберите тип масла:",
        "location_message": "Пожалуйста, отправьте свою геолокацию:",
        "sto_list_message": "Ближайшие СТО:",
        "back_button": "🔙 Назад",
        "main_menu_button": "🏠 Главное меню",
        "my_cars_button": "🚗 Мои авто",
        "add_car_button": "➕ Добавить авто",
        "contact_button": "📞 Связаться",
        "nearest_sto_button": "📍 Ближайшие СТО",
        "invalid_mileage": "Некорректный пробег. Введите число.",
        "error_location": "Произошла ошибка при получении СТО. Попробуйте еще раз.",
        "no_sto_found_message": "К сожалению, поблизости не найдено СТО.",
        "start_over": "Начнем заново? Введите /start",
        "main_menu_message": "Главное меню:",
        "my_cars_message": "Ваши автомобили:",
        "no_cars_message": "У вас пока нет автомобилей. Добавьте первый автомобиль.",
    },
    "uz": {
        "start_message": "Salom! Tilni tanlang:",
        "phone_message": "Iltimos, telefon raqamingizni yuboring:",
        "share_phone_button": "📞 Raqamni ulashish",
        "brand_message": "Avtomobilingiz markasini tanlang:",
        "model_message": "Avtomobilingiz modelini kiriting:",
        "manual_model_message": "Iltimos, avtomobilingiz marka va modelini qo'lda kiriting:",
        "mileage_message": "Avtomobilingizning yurgan masofasini kiriting (km):",
        "oil_type_message": "Moy turini tanlang:",
        "location_message": "Iltimos, joylashuvingizni yuboring:",
        "sto_list_message": "Eng yaqin STOlar:",
        "back_button": "🔙 Ортга",
        "main_menu_button": "🏠 Асосий меню",
        "my_cars_button": "🚗 Mening avtomobillarim",
        "add_car_button": "➕ Avtomobil qo'shish",
        "contact_button": "📞 Bog'lanish",
        "nearest_sto_button": "📍 Eng yaqin STO",
        "invalid_mileage": "Noto'g'ri masofa. Raqam kiriting.",
        "error_location": "STOlarni olishda xatolik yuz berdi. Qayta urinib ko'ring.",
        "no_sto_found_message": "Afsuski, yaqin atrofda STO topilmadi.",
        "start_over": "Qayta boshlaymizmi? /start ni kiriting",
        "main_menu_message": "Asosiy menyu:",
        "my_cars_message": "Sizning avtomobillaringiz:",
        "no_cars_message": "Sizda hali avtomobil yo'q. Birinchi avtomobilni qo'shing.",
    }
}

def get_translation(language, key):
    return translations[language][key]

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT,
                phone TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                car_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                brand TEXT,
                model TEXT,
                mileage INTEGER,
                oil_type TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )
        await db.commit()

async def save_user_data(user_id, language, phone):
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            """
            INSERT INTO users (user_id, language, phone)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                language = excluded.language,
                phone = excluded.phone
            """,
            (user_id, language, phone),
        )
        await db.commit()

async def save_car_data(user_id, brand, model, mileage, oil_type):
    async with aiosqlite.connect("users.db") as db:
        await db.execute(
            """
            INSERT INTO cars (user_id, brand, model, mileage, oil_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, brand, model, mileage, oil_type),
        )
        await db.commit()

async def get_user_cars(user_id):
    async with aiosqlite.connect("users.db") as db:
        cursor = await db.execute(
            "SELECT brand, model, mileage, oil_type FROM cars WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchall()

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # радиус Земли в километрах
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return round(distance * 1000)  # возвращаем в метрах

# Handlers
@dp.message(CommandStart(), StateFilter('*'))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply(get_translation("ru", "start_message"), reply_markup=language_keyboard)
    await state.set_state(UserState.language)

@dp.message(F.text, StateFilter(UserState.language))
async def set_language(message: types.Message, state: FSMContext):
    language = "ru" if message.text == "Русский 🇷🇺" else "uz"
    await state.update_data(language=language)
    phone_keyboard = create_phone_keyboard(language)
    await message.reply(get_translation(language, "phone_message"), reply_markup=phone_keyboard)
    await state.set_state(UserState.phone)

@dp.message(F.contact, StateFilter(UserState.phone))
async def set_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    await save_user_data(message.from_user.id, language, phone)
    await message.reply(get_translation(language, "main_menu_message"), reply_markup=create_main_menu_keyboard(language))
    await state.set_state(UserState.main_menu)

@dp.message(F.text == get_translation("ru", "main_menu_button"))
async def return_to_main_menu(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    await message.reply(get_translation(language, "main_menu_message"), reply_markup=create_main_menu_keyboard(language))
    await state.set_state(UserState.main_menu)

@dp.message(F.text == get_translation("ru", "my_cars_button"))
async def my_cars(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    cars = await get_user_cars(message.from_user.id)
    
    if cars:
        cars_message = get_translation(language, "my_cars_message") + "\n"
        for car in cars:
            cars_message += f"🚗 {car[0]} {car[1]}, пробег: {car[2]} км, масло: {car[3]}\n"
        await message.reply(cars_message, reply_markup=create_my_cars_keyboard(language))
    else:
        await message.reply(get_translation(language, "no_cars_message"), reply_markup=create_my_cars_keyboard(language))

@dp.message(F.text == get_translation("ru", "add_car_button"))
async def add_car(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    brand_keyboard = create_brand_keyboard()
    await message.reply(get_translation(language, "brand_message"), reply_markup=brand_keyboard)
    await state.set_state(UserState.brand)

@dp.message(F.text == get_translation("ru", "contact_button"))
async def contact(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    await message.reply(f"Свяжитесь с нами: @yrlaurenne", reply_markup=create_main_menu_keyboard(language))

@dp.message(F.text == get_translation("ru", "nearest_sto_button"))
async def nearest_sto(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    await message.reply(get_translation(language, "location_message"), reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.location)

@dp.message(F.text, StateFilter(UserState.brand))
async def set_brand(message: types.Message, state: FSMContext):
    brand = message.text
    await state.update_data(brand=brand)
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    
    if brand == "Другое":
        await message.reply(get_translation(language, "manual_model_message"), reply_markup=ReplyKeyboardRemove())
        await state.set_state(UserState.manual_model)
    else:
        model_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=model)] for model in popular_models.get(brand, [])],
            resize_keyboard=True
        )
        await message.reply(get_translation(language, "model_message"), reply_markup=model_keyboard)
        await state.set_state(UserState.model)

@dp.message(F.text, StateFilter(UserState.model))
async def set_model(message: types.Message, state: FSMContext):
    model = message.text
    await state.update_data(model=model)
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    brand = user_data.get("brand")
    recommendation = oil_recommendations.get(brand, {}).get(model, "Уточните у производителя")
    
    await state.update_data(recommendation=recommendation)
    
    await message.reply(get_translation(language, "mileage_message"), reply_markup=create_back_main_menu_keyboard(language))
    await state.set_state(UserState.mileage)

@dp.message(F.text, StateFilter(UserState.manual_model))
async def set_manual_model(message: types.Message, state: FSMContext):
    manual_model = message.text
    await state.update_data(model=manual_model)
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    
    await message.reply(get_translation(language, "mileage_message"), reply_markup=create_back_main_menu_keyboard(language))
    await state.set_state(UserState.mileage)

@dp.message(F.text, StateFilter(UserState.mileage))
async def set_mileage(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(mileage=message.text)
        user_data = await state.get_data()
        language = user_data.get("language", "ru")
        oil_keyboard = create_oil_keyboard(language)
        
        recommendation = user_data.get("recommendation", "Уточните у производителя")
        
        oil_message = (
            f"Рекомендуемое масло: {recommendation}\n"
            f"{get_translation(language, 'oil_type_message')}"
        )
        await message.reply(oil_message, reply_markup=oil_keyboard)
        await state.set_state(UserState.oil_type)
    else:
        user_data = await state.get_data()
        language = user_data.get("language", "ru")
        await message.reply(get_translation(language, "invalid_mileage"), reply_markup=create_back_main_menu_keyboard(language))

@dp.message(F.text, StateFilter(UserState.oil_type))
async def set_oil_type(message: types.Message, state: FSMContext):
    oil_type = message.text
    await state.update_data(oil_type=oil_type)
    user_data = await state.get_data()
    language = user_data.get("language", "ru")
    
    recommendation = user_data.get("recommendation", "Уточните у производителя")
    
    oil_confirmation_message = (
        f"Вы выбрали масло: {oil_type}\n"
        f"Рекомендуемое масло: {recommendation}\n"
        f"{get_translation(language, 'location_message')}"
    )
    await message.reply(oil_confirmation_message, reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserState.location)

@dp.message(F.location, StateFilter(UserState.location))
async def get_location(message: types.Message, state: FSMContext):
    try:
        latitude = message.location.latitude
        longitude = message.location.longitude
        user_data = await state.get_data()
        language = user_data.get("language", "ru")

        await save_user_data(
            user_id=message.from_user.id,
            language=user_data.get("language"),
            phone=user_data.get("phone")
        )

        places_result = GMAPS.places_nearby(location=(latitude, longitude), radius=5000, type="car_repair")
        
        if places_result.get('results'):
            nearest_places = []
            for place in places_result['results']:
                place_lat = place['geometry']['location']['lat']
                place_lng = place['geometry']['location']['lng']
                distance = calculate_distance(latitude, longitude, place_lat, place_lng)
                place['distance'] = distance
                nearest_places.append(place)
            
            # Сортируем места по расстоянию
            sorted_places = sorted(nearest_places, key=lambda x: x['distance'])[:5]

            sto_list = []
            for place in sorted_places:
                name = place.get('name', 'Неизвестное СТО')
                rating = place.get('rating', 'Нет рейтинга')
                distance = place['distance']  # теперь у нас точно есть расстояние
                
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
                
                sto_info = (
                    f"🏢 {name}\n"
                    f"⭐ Рейтинг: {rating}\n"
                    f"📍 Расстояние: {distance} м\n"
                    f"🗺️ [Маршрут]({maps_url})\n"
                )
                sto_list.append(sto_info)

            sto_message = f"{get_translation(language, 'sto_list_message')}\n\n" + "\n".join(sto_list)
            await message.reply(sto_message, parse_mode=ParseMode.MARKDOWN, reply_markup=create_main_menu_keyboard(language))
        else:
            await message.reply(get_translation(language, "no_sto_found_message"), reply_markup=create_main_menu_keyboard(language))
    except Exception as e:
        logger.error(f"Error fetching location: {e}")
        await message.reply(get_translation(language, "error_location"), reply_markup=create_main_menu_keyboard(language))

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    keep_alive()
    asyncio.run(main())
