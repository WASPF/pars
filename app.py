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

async def run_promotion_logic(app, group_links, message_template, delay_range):
    """Основной цикл рассылки."""
    log_area = st.empty()
    logs = []

    def update_logs(msg):
        logs.append(msg)
        log_area.code("\n".join(logs[-15:]))

    update_logs("[INFO] Начинаю процесс рассылки...")
    
    for link in group_links:
        link = link.strip()
        if not link:
            continue
        
        try:
            # Парсим цель (username или ссылка)
            target = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
            
            # Попытка вступления
            try:
                from pyrogram.raw.functions.channels import JoinChannel
                await app.join_chat(target)
                update_logs(f"[+] Проверка/Вступление: {target}")
            except:
                pass

            # Отправка сообщения
            msg_text = parse_spintax(message_template)
            await app.send_message(target, msg_text)
            update_logs(f"[OK] Отправлено в {target}")

            # Пауза
            wait = random.randint(delay_range[0], delay_range[1])
            update_logs(f"[WAIT] Ожидание {wait} сек...")
            await asyncio.sleep(wait)

        except Exception as e:
            from pyrogram.errors import FloodWait
            if isinstance(e, FloodWait):
                update_logs(f"[!] Флуд: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            else:
                update_logs(f"[ERROR] Ошибка с {link}: {str(e)}")

    update_logs("[DONE] Рассылка завершена.")

def main():
    st.title("🚀 Telegram Promo (Fixed Auth)")

    # Sidebar
    st.sidebar.header("🔑 Настройки аккаунта")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Номер телефона", value=st.secrets.get("phone_number", ""))
    
    st.sidebar.divider()
    auth_code = st.sidebar.text_input("Код из Telegram", placeholder="12345")
    password_2fa = st.sidebar.text_input("2FA Пароль", type="password")

    # Основной интерфейс
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Чаты")
        groups_input = st.text_area("Список ссылок", height=200)
        group_list = [g.strip() for g in groups_input.split("\n") if g.strip()]
    with col2:
        st.subheader("📝 Реклама")
        msg_template = st.text_area("Текст {A|B}", height=100)
        delays = st.slider("Задержка (сек)", 10, 600, (30, 60))

    # Кнопки действий
    btn_col1, btn_col2 = st.columns(2)

    from pyrogram import Client

    if btn_col1.button("📩 1. ПОЛУЧИТЬ КОД"):
        if not api_id or not api_hash or not phone:
            st.error("Заполни API ID, Hash и Телефон!")
        else:
            async def get_code():
                app = Client(f"session_{phone}", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await app.connect()
                try:
                    code_info = await app.send_code(phone)
                    st.session_state['phone_code_hash'] = code_info.phone_code_hash
                    st.success("Код отправлен в твой Telegram!")
                except Exception as e:
                    st.error(f"Ошибка отправки кода: {e}")
                finally:
                    await app.disconnect()
            
            asyncio.run(get_code())

    if btn_col2.button("🚀 2. ЗАПУСТИТЬ"):
        if not auth_code:
            st.error("Сначала введи код из Telegram!")
        else:
            async def start_app():
                app = Client(f"session_{phone}", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await app.connect()
                try:
                    # Попытка входа
                    if not await app.get_me():
                        try:
                            await app.sign_in(phone, st.session_state.get('phone_code_hash'), auth_code)
                        except Exception as e:
                            if password_2fa:
                                await app.check_password(password_2fa)
                            else:
                                raise e
                    
                    st.success("Авторизация успешна!")
                    await run_promotion_logic(app, group_list, msg_template, delays)
                    
                except Exception as e:
                    st.error(f"Ошибка запуска: {e}")
                finally:
                    await app.disconnect()

            asyncio.run(start_app())

if __name__ == "__main__":
    main()
