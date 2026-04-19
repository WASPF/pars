import streamlit as st
import asyncio
import random
import re
import os
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

# Установка конфигурации страницы
st.set_page_config(page_title="TG Promo Expert", layout="wide")

def parse_spintax(text):
    """Случайный выбор слов из формата {вариант1|вариант2}."""
    def replace(match):
        options = match.group(1).split("|")
        return random.choice(options)
    while "{" in text and "}" in text:
        text = re.sub(r'\{([^{}]*)\}', replace, text)
    return text

async def run_promotion_task(api_id, api_hash, phone, group_links, message_template, delay_range):
    """Асинхронная задача для рассылки."""
    # Создаем клиент внутри асинхронной функции
    # Имя сессии привязано к номеру телефона
    client = Client(
        name=f"session_{phone}",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
        in_memory=False
    )
    
    log_container = st.empty()
    logs = []

    def update_logs(new_log):
        logs.append(new_log)
        log_container.code("\n".join(logs[-15:]))

    try:
        await client.start()
        update_logs(f"[INFO] Аккаунт {phone} успешно подключен.")

        for link in group_links:
            link = link.strip()
            if not link:
                continue
            
            try:
                # Парсим username группы
                chat_id = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
                
                # Пробуем вступить
                try:
                    await client.join_chat(chat_id)
                    update_logs(f"[+] Вступление в чат: {chat_id}")
                except Exception:
                    pass # Если уже в чате

                # Генерируем сообщение
                final_text = parse_spintax(message_template)
                
                # Отправка
                await client.send_message(chat_id, final_text)
                update_logs(f"[OK] Отправлено в {chat_id}")

                # Пауза
                wait_time = random.randint(delay_range[0], delay_range[1])
                update_logs(f"[WAIT] Ожидание {wait_time} сек...")
                await asyncio.sleep(wait_time)

            except FloodWait as e:
                update_logs(f"[!] Ограничение флуда: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except RPCError as e:
                update_logs(f"[ERROR] Ошибка Telegram: {e}")
            except Exception as e:
                update_logs(f"[ERROR] Ошибка {link}: {str(e)}")

        update_logs("[FINISH] Рассылка завершена успешно.")

    except Exception as e:
        update_logs(f"[CRITICAL] Ошибка работы клиента: {str(e)}")
    finally:
        # Корректно закрываем сессию
        if client.is_connected:
            await client.stop()

def main():
    st.title("🚀 Telegram Cloud Promoter")

    # Читаем данные из Secrets (настраиваются в панели Streamlit Cloud)
    s_api_id = st.secrets.get("api_id", "")
    s_api_hash = st.secrets.get("api_hash", "")
    s_phone = st.secrets.get("phone_number", "")

    # Боковая панель
    st.sidebar.header("🔑 Данные аккаунта")
    api_id = st.sidebar.text_input("API ID", value=str(s_api_id) if s_api_id else "")
    api_hash = st.sidebar.text_input("API Hash", value=s_api_hash, type="password")
    phone = st.sidebar.text_input("Номер телефона", value=s_phone)

    # Основной интерфейс
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Список чатов")
        links_input = st.text_area("Ссылки (по одной на строку)", height=250)
        group_links = [l.strip() for l in links_input.split("\n") if l.strip()]

    with col2:
        st.subheader("📝 Рекламный текст")
        message_template = st.text_area("Текст (поддержка {A|B})", height=150)
        
        st.subheader("⏱ Настройки задержки")
        delay_range = st.slider("Мин/Макс задержка (сек)", 10, 600, (30, 90))

    # Кнопка запуска
    if st.button("▶️ ЗАПУСТИТЬ", use_container_width=True):
        if not api_id or not api_hash or not phone:
            st.error("Пожалуйста, укажите API ID, API Hash и Номер телефона!")
        elif not group_links:
            st.error("Список чатов пуст!")
        elif not message_template:
            st.error("Текст сообщения не заполнен!")
        else:
            # Создаем новый event loop для исключения ошибки "There is no current event loop"
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_promotion_task(
                    int(api_id),
                    api_hash,
                    phone,
                    group_links,
                    message_template,
                    delay_range
                ))
            except Exception as e:
                st.error(f"Ошибка при запуске: {e}")
            finally:
                loop.close()

if __name__ == "__main__":
    main()
