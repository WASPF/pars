import streamlit as st
import asyncio
import random
import re
import os
import base64

# Настройка страницы
st.set_page_config(page_title="TG Promo Ultimate", layout="wide")

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
            # Извлекаем username
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
    update_logs("[DONE] Рассылка завершена.")

def main():
    st.title("🚀 Telegram Promo (String Session Mode)")
    st.markdown("""
    **Инструкция:**
    1. Заполни API ID, Hash и Телефон. Нажми **Шаг 1**.
    2. Введи код из TG (появится поле) и нажми **Шаг 1** снова.
    3. Скопируй полученную длинную строку в поле **String Session**.
    4. Нажми **Шаг 2**.
    """)

    # Sidebar
    st.sidebar.header("🔑 Настройки")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Телефон", value=st.secrets.get("phone_number", ""))
    
    st.sidebar.divider()
    # Чистим строку от случайных пробелов при вводе
    raw_session = st.sidebar.text_area("String Session (вставь сюда)", help="Длинный код из Шага 1")
    string_session = raw_session.strip().replace(" ", "")
    
    auth_code = st.sidebar.text_input("Код подтверждения", placeholder="Из чата Telegram")
    password_2fa = st.sidebar.text_input("2FA Пароль (если есть)", type="password")

    # Интерфейс
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Чаты")
        groups = st.text_area("Ссылки по одной на строку", height=200)
        group_list = [g.strip() for g in groups.split("\n") if g.strip()]
    with col2:
        st.subheader("📝 Реклама")
        msg = st.text_area("Текст с {вариант1|вариант2}", height=100)
        delays = st.slider("Задержка (сек)", 10, 600, (30, 60))

    from pyrogram import Client

    # ШАГ 1: ГЕНЕРАЦИЯ СТРОКИ
    if st.button("📩 1. ПОЛУЧИТЬ STRING SESSION"):
        if not api_id or not api_hash or not phone:
            st.error("Заполни данные в Sidebar!")
        else:
            async def get_string():
                # Только в памяти, чтобы не было binascii ошибок из-за файлов
                temp_app = Client(":memory:", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await temp_app.connect()
                try:
                    if not auth_code:
                        code_info = await temp_app.send_code(phone)
                        st.session_state['phone_code_hash'] = code_info.phone_code_hash
                        st.info("Код отправлен! Введи его слева и нажми кнопку '1' еще раз.")
                    else:
                        try:
                            await temp_app.sign_in(phone, st.session_state.get('phone_code_hash'), auth_code)
                        except Exception as e:
                            if password_2fa: await temp_app.check_password(password_2fa)
                            else: raise e
                        
                        new_session = await temp_app.export_session_string()
                        st.success("СЕССИЯ СОЗДАНА! Скопируй код ниже полностью:")
                        st.code(new_session, language="text")
                        st.warning("Теперь вставь этот код в поле 'String Session' слева и нажми кнопку '2'.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                finally:
                    await temp_app.disconnect()
            
            asyncio.run(get_string())

    # ШАГ 2: ЗАПУСК
    if st.button("🚀 2. ЗАПУСТИТЬ РАССЫЛКУ", type="primary"):
        if not string_session:
            st.error("Нет String Session! Сначала выполни Шаг 1.")
        else:
            async def run_main():
                try:
                    # Проверка валидности base64 перед запуском
                    app = Client("my_client", session_string=string_session, api_id=int(api_id), api_hash=api_hash)
                    await app.connect()
                    await run_promotion(app, group_list, msg, delays)
                    await app.disconnect()
                except Exception as e:
                    if "base64" in str(e).lower() or "binascii" in str(e).lower():
                        st.error("Ошибка в коде сессии! Попробуй скопировать его еще раз без лишних символов.")
                    else:
                        st.error(f"Ошибка: {e}")
            
            asyncio.run(run_main())

if __name__ == "__main__":
    main()
