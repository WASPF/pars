import streamlit as st
import asyncio
import random
import re
import os

# Настройка страницы
st.set_page_config(page_title="TG Promo String Edition", layout="wide")

def parse_spintax(text):
    def replace(match):
        options = match.group(1).split("|")
        return random.choice(options)
    while "{" in text and "}" in text:
        text = re.sub(r'\{([^{}]*)\}', replace, text)
    return text

async def run_promotion(client, group_links, message_template, delay_range):
    log_area = st.empty()
    logs = []
    def update_logs(msg):
        logs.append(msg)
        log_area.code("\n".join(logs[-15:]))

    update_logs("[INFO] Начинаю рассылку...")
    for link in group_links:
        link = link.strip()
        if not link: continue
        try:
            target = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
            try:
                await client.join_chat(target)
                update_logs(f"[+] Чат: {target}")
            except: pass
            
            msg = parse_spintax(message_template)
            await client.send_message(target, msg)
            update_logs(f"[OK] Отправлено в {target}")
            
            wait = random.randint(delay_range[0], delay_range[1])
            update_logs(f"[WAIT] Пауза {wait} сек...")
            await asyncio.sleep(wait)
        except Exception as e:
            update_logs(f"[ERROR] {link}: {str(e)}")
    update_logs("[DONE] Завершено.")

def main():
    st.title("🚀 Telegram Promo (String Session)")
    st.info("Метод String Session избавляет от ошибок с файлами сессий.")

    # Sidebar
    st.sidebar.header("🔑 Настройки")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Телефон", value=st.secrets.get("phone_number", ""))
    
    st.sidebar.divider()
    string_session = st.sidebar.text_area("String Session (если уже есть)", help="Вставь сюда полученную строку")
    auth_code = st.sidebar.text_input("Код из TG", placeholder="Для получения сессии")
    password_2fa = st.sidebar.text_input("2FA Пароль", type="password")

    # Интерфейс
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Чаты")
        groups = st.text_area("Ссылки", height=200)
        group_list = [g.strip() for g in groups.split("\n") if g.strip()]
    with col2:
        st.subheader("📝 Реклама")
        msg = st.text_area("Текст {A|B}", height=100)
        delays = st.slider("Задержка", 10, 600, (30, 60))

    from pyrogram import Client

    # КНОПКА 1: ПОЛУЧЕНИЕ СЕССИИ
    if st.button("📩 1. ПОЛУЧИТЬ / АВТОРИЗОВАТЬ СТРОКУ"):
        async def get_string():
            # Работаем только в памяти! Никаких файлов!
            temp_client = Client(":memory:", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
            await temp_client.connect()
            try:
                if not auth_code:
                    code = await temp_client.send_code(phone)
                    st.session_state['hash'] = code.phone_code_hash
                    st.info("Код отправлен! Введи его слева и нажми кнопку еще раз.")
                else:
                    try:
                        await temp_client.sign_in(phone, st.session_state['hash'], auth_code)
                    except Exception as e:
                        if password_2fa: await temp_client.check_password(password_2fa)
                        else: raise e
                    
                    # Генерируем магическую строку
                    s_session = await temp_client.export_session_string()
                    st.success("Твоя String Session (сохрани её!):")
                    st.code(s_session)
            except Exception as e:
                st.error(f"Ошибка: {e}")
            finally:
                await temp_client.disconnect()
        
        asyncio.run(get_string())

    # КНОПКА 2: ЗАПУСК
    if st.button("🚀 2. ЗАПУСТИТЬ РАССЫЛКУ", type="primary"):
        if not string_session:
            st.error("Сначала получи и вставь String Session!")
        else:
            async def run_main():
                # Запуск клиента ИЗ СТРОКИ (без файлов!)
                app = Client("my_bot", session_string=string_session, api_id=int(api_id), api_hash=api_hash)
                await app.connect()
                try:
                    await run_promotion(app, group_list, msg, delays)
                except Exception as e:
                    st.error(f"Критическая ошибка: {e}")
                finally:
                    await app.disconnect()
            
            asyncio.run(run_main())

if __name__ == "__main__":
    main()
