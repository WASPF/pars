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
    from pyrogram import Client
    from pyrogram.errors import FloodWait, RPCError, SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired

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
        await app.connect()
        update_logs(f"[INFO] Подключение к Telegram...")

        if not await app.get_me():
            # Если не авторизован, отправляем код
            sent_code = await app.send_code(phone)
            update_logs(f"[AUTH] Код отправлен на номер {phone}. Введите его в поле справа.")
            
            # Создаем временное поле ввода кода прямо в логах или через st.text_input
            # В облаке Streamlit лучше всего использовать состояние сессии (st.session_state)
            # Но для простоты сейчас используем ожидание ввода
            st.warning("Введите код подтверждения в боковой панели и нажмите 'Запустить' снова.")
            return

        update_logs(f"[INFO] Авторизация успешна!")

        for link in group_links:
            link = link.strip()
            if not link: continue
            
            try:
                chat_id = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
                try:
                    await app.join_chat(chat_id)
                    update_logs(f"[+] Чат: {chat_id}")
                except: pass

                final_text = parse_spintax(message_template)
                await app.send_message(chat_id, final_text)
                update_logs(f"[OK] Отправлено в {chat_id}")

                wait_time = random.randint(delay_range[0], delay_range[1])
                update_logs(f"[WAIT] Пауза {wait_time} сек...")
                await asyncio.sleep(wait_time)

            except FloodWait as e:
                update_logs(f"[!] Флуд: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except Exception as e:
                update_logs(f"[ERROR] {link}: {str(e)}")

        update_logs("[FINISH] Рассылка завершена.")

    except Exception as e:
        update_logs(f"[CRITICAL] Ошибка: {str(e)}")
    finally:
        if app.is_connected:
            await app.stop()

def main():
    st.title("🚀 Telegram Promo (Cloud Auth)")

    # Sidebar
    st.sidebar.header("🔑 Данные аккаунта")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Номер телефона", value=st.secrets.get("phone_number", ""))
    
    # ПОЛЕ ДЛЯ КОДА
    auth_code = st.sidebar.text_input("Код подтверждения (из TG)", placeholder="12345")
    password_2fa = st.sidebar.text_input("Облачный пароль (если есть)", type="password")

    # Основной интерфейс
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Список чатов")
        links_input = st.text_area("Ссылки (одна на строку)", height=200)
        group_links = [l.strip() for l in links_input.split("\n") if l.strip()]

    with col2:
        st.subheader("📝 Реклама")
        message_template = st.text_area("Текст {A|B}", height=100)
        delay_range = st.slider("Задержка (сек)", 10, 600, (30, 60))

    if st.button("▶️ ЗАПУСТИТЬ РАССЫЛКУ / ПОЛУЧИТЬ КОД"):
        if not api_id or not api_hash or not phone:
            st.error("Заполните данные в Sidebar!")
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            from pyrogram import Client
            
            async def auth_and_run():
                app = Client(f"session_{phone}", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await app.connect()
                
                try:
                    if not await app.get_me():
                        if not auth_code:
                            # Шаг 1: Запрашиваем код
                            sent_code_info = await app.send_code(phone)
                            st.session_state['phone_code_hash'] = sent_code_info.phone_code_hash
                            st.info("Код отправлен! Введи его в поле 'Код подтверждения' слева и нажми кнопку еще раз.")
                        else:
                            # Шаг 2: Входим с кодом
                            try:
                                await app.sign_in(phone, st.session_state.get('phone_code_hash'), auth_code)
                            except Exception as e:
                                # Если нужен облачный пароль (2FA)
                                if "SessionPasswordNeeded" in str(type(e)) or "password" in str(e).lower():
                                    if password_2fa:
                                        await app.check_password(password_2fa)
                                    else:
                                        st.error("Нужен облачный пароль (2FA)!")
                                        return
                            st.success("Успешный вход! Начинаю рассылку...")
                            await run_promotion_task(int(api_id), api_hash, phone, group_links, message_template, delay_range)
                    else:
                        # Если уже залогинены
                        await run_promotion_task(int(api_id), api_hash, phone, group_links, message_template, delay_range)
                finally:
                    if app.is_connected:
                        await app.stop()

            loop.run_until_complete(auth_and_run())
            loop.close()

if __name__ == "__main__":
    main()
