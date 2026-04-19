import streamlit as st
import asyncio
import random
import re
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

# Установка конфигурации страницы
st.set_page_config(page_title="TG Promo Expert", layout="wide")

def parse_spintax(text):
    """Разбирает синтаксис {word1|word2} для рандомизации текста."""
    def replace(match):
        options = match.group(1).split("|")
        return random.choice(options)
    while "{" in text and "}" in text:
        text = re.sub(r'\{([^{}]*)\}', replace, text)
    return text

async def send_messages_async(api_id, api_hash, phone, group_links, message_template, delay_range):
    """Асинхронная функция для работы с Pyrogram внутри Streamlit."""
    # Инициализируем клиент внутри асинхронной функции
    app = Client(
        f"session_{phone}", 
        api_id=api_id, 
        api_hash=api_hash, 
        phone_number=phone,
        in_memory=False # Сессия будет сохраняться в файл
    )
    
    log_container = st.empty()
    logs = []

    def update_logs(new_log):
        logs.append(new_log)
        log_container.code("\n".join(logs[-15:]))

    try:
        # Пытаемся запустить клиент
        await app.start()
        update_logs(f"[INFO] Сессия запущена для {phone}")

        for link in group_links:
            link = link.strip()
            if not link:
                continue
            
            try:
                # Очистка юзернейма группы
                chat_id = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
                
                # Попытка вступления
                try:
                    await app.join_chat(chat_id)
                    update_logs(f"[+] Вступил в чат: {chat_id}")
                except Exception:
                    pass # Если уже в чате

                # Генерация сообщения
                final_message = parse_spintax(message_template)
                
                # Отправка
                await app.send_message(chat_id, final_message)
                update_logs(f"[OK] Отправлено в {chat_id}")

                # Задержка
                wait_time = random.randint(delay_range[0], delay_range[1])
                update_logs(f"[WAIT] Ожидание {wait_time} сек...")
                await asyncio.sleep(wait_time)

            except FloodWait as e:
                update_logs(f"[ERROR] Флуд-контроль: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except RPCError as e:
                update_logs(f"[ERROR] Ошибка Telegram: {e}")
            except Exception as e:
                update_logs(f"[ERROR] Ошибка с {link}: {str(e)}")

        update_logs("[FINISH] Рассылка завершена.")
    
    except Exception as e:
        update_logs(f"[CRITICAL] Ошибка клиента: {str(e)}")
    finally:
        # Обязательно останавливаем клиент
        if app.is_connected:
            await app.stop()

def main():
    st.title("🚀 Telegram Cloud Promoter")

    # Получение данных из Secrets (Streamlit Cloud)
    s_api_id = st.secrets.get("api_id", "")
    s_api_hash = st.secrets.get("api_hash", "")
    s_phone = st.secrets.get("phone_number", "")

    # Настройки в боковой панели
    st.sidebar.header("Параметры аккаунта")
    api_id = st.sidebar.text_input("API ID", value=str(s_api_id) if s_api_id else "")
    api_hash = st.sidebar.text_input("API Hash", value=s_api_hash, type="password")
    phone = st.sidebar.text_input("Телефон", value=s_phone)

    # Интерфейс рассылки
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Группы")
        links_input = st.text_area("Ссылки (каждая с новой строки)", height=200)
        group_links = [l.strip() for l in links_input.split("\n") if l.strip()]

    with col2:
        st.subheader("Сообщение")
        message_template = st.text_area("Текст (с {Spintax|Спинтакс})", height=100)
        delay_range = st.slider("Задержка (сек)", 10, 600, (30, 60))

    if st.button("ЗАПУСТИТЬ РАССЫЛКУ", use_container_width=True):
        if not api_id or not api_hash or not phone:
            st.error("Заполните данные API и номер телефона!")
        elif not group_links:
            st.error("Список групп пуст!")
        else:
            # Исправление для RuntimeError: создаем новый цикл событий для каждого запуска
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_messages_async(
                    int(api_id), 
                    api_hash, 
                    phone, 
                    group_links, 
                    message_template, 
                    delay_range
                ))
                loop.close()
            except Exception as e:
                st.error(f"Ошибка выполнения: {e}")

if __name__ == "__main__":
    main()
