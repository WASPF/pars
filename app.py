import streamlit as st
import asyncio
import random
import re
import os

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
        if not link: continue
        
        try:
            target = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
            
            try:
                await app.join_chat(target)
                update_logs(f"[+] Чат: {target}")
            except: pass

            msg_text = parse_spintax(message_template)
            await app.send_message(target, msg_text)
            update_logs(f"[OK] Отправлено в {target}")

            wait = random.randint(delay_range[0], delay_range[1])
            update_logs(f"[WAIT] Пауза {wait} сек...")
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
    st.title("🚀 Telegram Promo (Session Fix)")

    # Sidebar
    st.sidebar.header("🔑 Настройки аккаунта")
    api_id = st.sidebar.text_input("API ID", value=str(st.secrets.get("api_id", "")))
    api_hash = st.sidebar.text_input("API Hash", value=st.secrets.get("api_hash", ""), type="password")
    phone = st.sidebar.text_input("Номер телефона", value=st.secrets.get("phone_number", ""))
    
    st.sidebar.divider()
    auth_code = st.sidebar.text_input("Код из Telegram", placeholder="12345")
    password_2fa = st.sidebar.text_input("2FA Пароль (если есть)", type="password")

    # Кнопка для полной очистки сессии, если всё сломалось
    if st.sidebar.button("🗑️ Сбросить сессию (очистка)"):
        session_file = f"session_{phone}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
            st.sidebar.success("Файл сессии удален. Попробуйте 'Получить код' заново.")
        else:
            st.sidebar.info("Файлов сессий не найдено.")

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

    from pyrogram import Client

    # --- КНОПКА 1: ПОЛУЧЕНИЕ КОДА ---
    if st.button("📩 1. ПОЛУЧИТЬ КОД", use_container_width=True):
        if not api_id or not api_hash or not phone:
            st.error("Заполни API ID, Hash и Телефон!")
        else:
            async def get_code():
                # Удаляем старую битую сессию перед новым запросом
                session_file = f"session_{phone}.session"
                if os.path.exists(session_file):
                    os.remove(session_file)
                
                app = Client(f"session_{phone}", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await app.connect()
                try:
                    code_info = await app.send_code(phone)
                    st.session_state['phone_code_hash'] = code_info.phone_code_hash
                    st.success("Код отправлен! Введи его слева и нажми 'Запустить'.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                finally:
                    await app.disconnect()
            
            asyncio.run(get_code())

    # --- КНОПКА 2: ЗАПУСК ---
    if st.button("🚀 2. ЗАПУСТИТЬ", use_container_width=True, type="primary"):
        if not auth_code:
            st.error("Введи код подтверждения из Telegram!")
        else:
            async def start_app():
                app = Client(f"session_{phone}", api_id=int(api_id), api_hash=api_hash, phone_number=phone)
                await app.connect()
                try:
                    me = await app.get_me()
                    if not me:
                        # Пытаемся войти по коду
                        code_hash = st.session_state.get('phone_code_hash')
                        if not code_hash:
                            st.error("Хэш кода не найден. Нажми '1. Получить код' еще раз.")
                            return
                        
                        try:
                            await app.sign_in(phone, code_hash, auth_code)
                        except Exception as e:
                            # Обработка 2FA пароля
                            if password_2fa:
                                await app.check_password(password_2fa)
                            else:
                                raise e
                    
                    st.success("Авторизация прошла успешно!")
                    await run_promotion_logic(app, group_list, msg_template, delays)
                    
                except Exception as e:
                    # Если ключ все еще битый — предлагаем удалить файл
                    if "AUTH_KEY_UNREGISTERED" in str(e):
                        st.error("Критическая ошибка сессии. Нажми кнопку 'Сбросить сессию' в левом меню и начни заново.")
                    else:
                        st.error(f"Ошибка: {e}")
                finally:
                    await app.disconnect()

            asyncio.run(start_app())

if __name__ == "__main__":
    main()
