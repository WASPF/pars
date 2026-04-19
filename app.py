import streamlit as st
import asyncio
import random
import re
import os

st.set_page_config(page_title="TG Promo Expert", layout="wide")

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
    st.title("🚀 Telegram Promo (String Mode)")

    st.sidebar.header("🔑 Настройки")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Телефон", value=st.secrets.get("phone_number", ""))
    
    st.sidebar.divider()
    s_session_input = st.sidebar.text_area("String Session (вставь сюда)")
    auth_code = st.sidebar.text_input("Код подтверждения")
    password_2fa = st.sidebar.text_input("2FA Пароль", type="password")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Чаты")
        groups = st.text_area("Ссылки", height=200)
        group_list = [g.strip() for g in groups.split("\n") if g.strip()]
    with col2:
        st.subheader("📝 Реклама")
        msg = st.text_area("Текст", height=100)
        delays = st.slider("Задержка", 10, 600, (30, 60))

    from pyrogram import Client

    # КНОПКА 1
    if st.button("📩 1. ПОЛУЧИТЬ STRING SESSION"):
        async def get_s():
            # Всегда создаем новый клиент в памяти
            app = Client(":memory:", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
            await app.connect()
            try:
                if not auth_code:
                    code_info = await app.send_code(phone)
                    st.session_state['c_hash'] = code_info.phone_code_hash
                    st.info("Код отправлен! Введи его и жми кнопку снова.")
                else:
                    try:
                        await app.sign_in(phone, st.session_state.get('c_hash'), auth_code)
                    except Exception as e:
                        if "SessionPasswordNeeded" in str(e) or "password" in str(e).lower():
                            if password_2fa:
                                await app.check_password(password_2fa)
                            else:
                                st.error("Введите 2FA пароль!")
                                return
                        else: raise e
                    
                    # Если дошли сюда — мы внутри
                    final_string = await app.export_session_string()
                    st.success("ГОТОВО! Копируй это:")
                    st.code(final_string)
            except Exception as e:
                st.error(f"Ошибка: {e}")
            finally:
                await app.disconnect()
        
        asyncio.run(get_s())

    # КНОПКА 2
    if st.button("🚀 2. ЗАПУСТИТЬ РАССЫЛКУ", type="primary"):
        if not s_session_input:
            st.error("Нет String Session!")
        else:
            async def run_m():
                # Убираем все пробелы из строки перед использованием
                clean_session = s_session_input.strip().replace("\n", "").replace(" ", "")
                app = Client("promo_bot", session_string=clean_session, api_id=int(api_id), api_hash=api_hash)
                await app.connect()
                try:
                    await run_promotion(app, group_list, msg, delays)
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                finally:
                    await app.disconnect()
            
            asyncio.run(run_m())

if __name__ == "__main__":
    main()
