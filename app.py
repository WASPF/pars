import streamlit as st
import asyncio
import random
import re
from pyrogram import Client
from pyrogram.errors import FloodWait

# 1. Настройка страницы
st.set_page_config(page_title="TG Sender", layout="centered")

def parse_spintax(text):
    """Выбирает случайный вариант из {Привет|Здравствуйте}"""
    def replace(match):
        options = match.group(1).split("|")
        return random.choice(options)
    while "{" in text and "}" in text:
        text = re.sub(r'\{([^{}]*)\}', replace, text)
    return text

async def run_bot(api_id, api_hash, phone, groups, message, delays):
    """Логика работы бота"""
    # Создаем клиент. Файл .session создастся сам автоматически!
    app = Client(f"session_{phone}", api_id=api_id, api_hash=api_hash, phone_number=phone)
    
    log_area = st.empty()
    logs = []

    def update_log(text):
        logs.append(text)
        log_area.code("\n".join(logs[-10:]))

    try:
        await app.start()
        update_log("[INFO] Бот запущен!")

        for group in groups:
            group = group.strip()
            if not group: continue
            
            try:
                # Убираем лишнее из ссылки
                target = group.replace("https://t.me/", "").replace("@", "")
                
                # Вступаем и отправляем
                try:
                    await app.join_chat(target)
                except:
                    pass
                
                text = parse_spintax(message)
                await app.send_message(target, text)
                update_log(f"[OK] Отправлено в {target}")
                
                wait = random.randint(delays[0], delays[1])
                update_log(f"[WAIT] Ждем {wait} сек...")
                await asyncio.sleep(wait)

            except FloodWait as e:
                update_log(f"[!] Ошибка флуда: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except Exception as e:
                update_log(f"[ERROR] {group}: {e}")

        update_log("[DONE] Все готово!")
    finally:
        await app.stop()

def main():
    st.title("Telegram Promo Bot")

    # Берем данные из Secrets (настраиваются на сайте Streamlit)
    api_id = st.secrets.get("api_id")
    api_hash = st.secrets.get("api_hash")
    phone = st.secrets.get("phone_number")

    if not api_id or not api_hash:
        st.error("Настрой Secrets в панели управления Streamlit!")
        return

    # Интерфейс
    groups_text = st.text_area("Список групп (по одной на строку)")
    msg_text = st.text_area("Сообщение (с {A|B})")
    delay_val = st.slider("Задержка (сек)", 10, 300, (30, 60))

    if st.button("СТАРТ"):
        group_list = groups_text.split("\n")
        # Запускаем асинхронный движок
        asyncio.run(run_bot(int(api_id), api_hash, phone, group_list, msg_text, delay_val))

if __name__ == "__main__":
    main()