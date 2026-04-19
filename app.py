import streamlit as st
import asyncio
import random
import re

# Настройка страницы
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
    """Асинхронная задача рассылки."""
    # Импортируем внутри функции, чтобы избежать ошибок при загрузке модуля
    from pyrogram import Client
    from pyrogram.errors import FloodWait, RPCError

    # Создаем клиент
    app = Client(
        name=f"session_{phone}",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone
    )
    
    log_container = st.empty()
    logs = []

    def update_logs(new_log):
        logs.append(new_log)
        log_container.code("\n".join(logs[-15:]))

    try:
        # Используем асинхронный запуск
        await app.start()
        update_logs(f"[INFO] Аккаунт {phone} в сети.")

        for link in group_links:
            link = link.strip()
            if not link:
                continue
            
            try:
                # Очистка юзернейма
                chat_id = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
                
                # Попытка вступления
                try:
                    await app.join_chat(chat_id)
                    update_logs(f"[+] Чат: {chat_id}")
                except Exception:
                    pass

                # Генерация и отправка
                final_text = parse_spintax(message_template)
                await app.send_message(chat_id, final_text)
                update_logs(f"[OK] Отправлено в {chat_id}")

                # Пауза
                wait_time = random.randint(delay_range[0], delay_range[1])
                update_logs(f"[WAIT] Ожидание {wait_time} сек...")
                await asyncio.sleep(wait_time)

            except FloodWait as e:
                update_logs(f"[!] Флуд: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except Exception as e:
                update_logs(f"[ERROR] Ошибка чата {link}: {str(e)}")

        update_logs("[FINISH] Рассылка завершена.")

    except Exception as e:
        update_logs(f"[CRITICAL] Ошибка: {str(e)}")
    finally:
        if app.is_connected:
            await app.stop()

def main():
    st.title("🚀 Управление рассылкой Telegram")

    # Sidebar для ввода данных
    st.sidebar.header("🔑 Данные API")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Номер телефона", value=st.secrets.get("phone_number", ""))

    # Основной интерфейс
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Список чатов")
        links_input = st.text_area("Ссылки (одна на строку)", height=250)
        group_links = [l.strip() for l in links_input.split("\n") if l.strip()]

    with col2:
        st.subheader("📝 Рекламный текст")
        message_template = st.text_area("Текст {A|B}", height=150)
        
        st.subheader("⏱ Настройки паузы")
        delay_range = st.slider("Мин/Макс задержка (сек)", 10, 600, (30, 90))

    if st.button("▶️ ЗАПУСТИТЬ РАССЫЛКУ", use_container_width=True):
        if not api_id or not api_hash or not phone:
            st.error("Заполните все данные в левой панели!")
        elif not group_links:
            st.error("Список чатов пуст!")
        else:
            # Создаем чистый Event Loop для каждого запуска
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_promotion_task(
                    int(api_id), api_hash, phone, group_links, message_template, delay_range
                ))
            except Exception as e:
                st.error(f"Ошибка выполнения: {e}")
            finally:
                loop.close()

if __name__ == "__main__":
    main()
