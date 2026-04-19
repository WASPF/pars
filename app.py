import streamlit as st
import asyncio
import random
import re
import os

# Настройка страницы
st.set_page_config(page_title="TG Promo Ultimate Fix", layout="wide")

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

    update_logs("[INFO] Начинаю процесс...")
    for link in group_links:
        link = link.strip()
        if not link: continue
        try:
            target = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
            try:
                await client.join_chat(target)
                update_logs(f"[+] Группа: {target}")
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
    st.title("🚀 Telegram Promo (Stable Auth Fix)")

    # Sidebar
    st.sidebar.header("🔑 Настройки")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Телефон", value=st.secrets.get("phone_number", ""))
    
    st.sidebar.divider()
    s_session_input = st.sidebar.text_area("Вставьте полученную String Session", height=100)
    
    # Основной интерфейс
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Список чатов")
        groups = st.text_area("Ссылки", height=200)
        group_list = [g.strip() for g in groups.split("\n") if g.strip()]
    with col2:
        st.subheader("📝 Реклама")
        msg = st.text_area("Текст {A|B}", height=100)
        delays = st.slider("Задержка (сек)", 10, 600, (30, 60))

    from pyrogram import Client
    from pyrogram.errors import SessionPasswordNeeded, PhoneCodeExpired, PhoneCodeInvalid

    # --- ЕДИНЫЙ ПРОЦЕСС АВТОРИЗАЦИИ ---
    if st.button("📩 ПОЛУЧИТЬ STRING SESSION"):
        if not api_id or not api_hash or not phone:
            st.error("Заполните данные в Sidebar!")
        else:
            async def get_session_flow():
                # Создаем клиент в памяти
                app = Client(":memory:", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await app.connect()
                
                try:
                    # Шаг 1: Отправка кода
                    code_info = await app.send_code(phone)
                    
                    # Создаем форму для ввода кода ПРЯМО ВНУТРИ асинхронного цикла
                    placeholder = st.empty()
                    with placeholder.container():
                        st.warning("Код отправлен! Введите его ниже.")
                        input_code = st.text_input("Код из Telegram", key="final_code")
                        input_2fa = st.text_input("2FA Пароль (если есть)", type="password", key="final_2fa")
                        confirm_btn = st.button("ПОДТВЕРДИТЬ И ПОЛУЧИТЬ СТРОКУ")

                        if confirm_btn and input_code:
                            try:
                                await app.sign_in(phone, code_info.phone_code_hash, input_code)
                            except SessionPasswordNeeded:
                                if input_2fa:
                                    await app.check_password(input_2fa)
                                else:
                                    st.error("Нужен 2FA пароль!")
                                    return
                            
                            s_string = await app.export_session_string()
                            st.success("ВАША СЕССИЯ:")
                            st.code(s_string)
                            placeholder.empty() # Убираем форму
                
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                finally:
                    await app.disconnect()

            # Запуск
            asyncio.run(get_session_flow())

    # --- ШАГ 2: ЗАПУСК РАССЫЛКИ ---
    if st.button("🚀 ЗАПУСТИТЬ РАССЫЛКУ", type="primary"):
        if not s_session_input:
            st.error("Вставьте String Session!")
        else:
            async def run_main():
                clean_s = s_session_input.strip().replace(" ", "")
                app = Client("promo_bot", session_string=clean_s, api_id=int(api_id), api_hash=api_hash)
                await app.connect()
                try:
                    await run_promotion(app, group_list, msg, delays)
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                finally:
                    await app.disconnect()
            
            asyncio.run(run_main())

if __name__ == "__main__":
    main()
