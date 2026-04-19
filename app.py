import streamlit as st
import asyncio
import random
import re

# Настройка страницы
st.set_page_config(page_title="TG Sender Admin", layout="wide")

# Функция рандомизации текста
def parse_spintax(text):
    def replace(match):
        options = match.group(1).split("|")
        return random.choice(options)
    while "{" in text and "}" in text:
        text = re.sub(r'\{([^{}]*)\}', replace, text)
    return text

async def run_promotion_logic(api_id, api_hash, phone, group_links, message_template, delay_range):
    """
    Вся логика работы с Telegram вынесена внутрь асинхронной функции, 
    чтобы избежать конфликтов с потоками Streamlit.
    """
    # Импортируем Pyrogram только здесь, чтобы он не упал при запуске приложения
    from pyrogram import Client
    from pyrogram.errors import FloodWait, RPCError

    # Инициализация клиента
    app = Client(
        name=f"session_{phone}",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone
    )
    
    log_area = st.empty()
    logs = []

    def update_logs(msg):
        logs.append(msg)
        log_area.code("\n".join(logs[-15:]))

    try:
        await app.start()
        update_logs(f"[INFO] Аккаунт {phone} подключен!")

        for link in group_links:
            link = link.strip()
            if not link:
                continue
            
            try:
                # Очистка ссылки
                chat_id = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
                
                # Пробуем вступить
                try:
                    await app.join_chat(chat_id)
                    update_logs(f"[+] Вступил в чат: {chat_id}")
                except:
                    pass

                # Отправка
                msg_text = parse_spintax(message_template)
                await app.send_message(chat_id, msg_text)
                update_logs(f"[OK] Отправлено в {chat_id}")

                # Пауза
                wait = random.randint(delay_range[0], delay_range[1])
                update_logs(f"[WAIT] Пауза {wait} сек...")
                await asyncio.sleep(wait)

            except FloodWait as e:
                update_logs(f"[!] Лимит! Ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except Exception as e:
                update_logs(f"[ERROR] Ошибка с {link}: {str(e)}")

        update_logs("[DONE] Рассылка завершена.")

    except Exception as e:
        update_logs(f"[CRITICAL] Ошибка: {str(e)}")
    finally:
        if app.is_connected:
            await app.stop()

def main():
    st.title("🚀 Управление рассылкой Telegram")

    # --- Админ-панель в Sidebar ---
    st.sidebar.header("🔑 Данные аккаунта")
    
    # Пытаемся подтянуть из Secrets, если они там есть, иначе пусто
    api_id_val = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash_val = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone_val = st.sidebar.text_input("Номер телефона", value=st.secrets.get("phone_number", ""), placeholder="+7...")

    st.sidebar.divider()
    st.sidebar.info("Данные можно вводить вручную или прописать в Secrets на Streamlit Cloud.")

    # --- Основной интерфейс ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Список чатов")
        groups_input = st.text_area("Ссылки (каждая с новой строки)", height=250, placeholder="https://t.me/chat1")
        group_list = [g.strip() for g in groups_input.split("\n") if g.strip()]

    with col2:
        st.subheader("📝 Рекламный текст")
        msg_template = st.text_area("Текст с {A|B|C}", height=150, placeholder="{Привет|Здравствуйте}! {Куплю|Продам}...")
        
        st.subheader("⏱ Настройки пауз")
        delays = st.slider("Задержка (сек)", 10, 600, (30, 60))

    # --- Кнопка запуска ---
    if st.button("▶️ ЗАПУСТИТЬ РАССЫЛКУ", use_container_width=True):
        if not api_id_val or not api_hash_val or not phone_val:
            st.error("Заполни данные API и номер телефона в левой панели!")
        elif not group_list:
            st.error("Добавь ссылки на чаты!")
        elif not msg_template:
            st.error("Введи текст сообщения!")
        else:
            # Создаем новый цикл событий для текущего потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_promotion_logic(
                    int(api_id_val),
                    api_hash_val,
                    phone_val,
                    group_list,
                    msg_template,
                    delays
                ))
            except Exception as e:
                st.error(f"Произошла ошибка: {e}")
            finally:
                loop.close()

if __name__ == "__main__":
    main()
