import streamlit as st
import asyncio
import random
import re
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

# 1. Настройка страницы
st.set_page_config(page_title="TG Promo Expert", layout="wide")

def parse_spintax(text):
    """Рандомизация текста: {Привет|Хай}"""
    def replace(match):
        options = match.group(1).split("|")
        return random.choice(options)
    while "{" in text and "}" in text:
        text = re.sub(r'\{([^{}]*)\}', replace, text)
    return text

async def start_promotion_process(api_id, api_hash, phone, group_links, message_template, delay_range):
    """Основная асинхронная функция рассылки"""
    # Создаем клиент с уникальным именем сессии
    # in_memory=False заставляет Pyrogram создавать файл .session
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
        # Запускаем клиент асинхронно
        await app.start()
        update_logs(f"[INFO] Аккаунт {phone} успешно подключен!")

        for link in group_links:
            link = link.strip()
            if not link:
                continue
            
            try:
                # Очищаем ссылку до юзернейма
                chat_id = link.replace("https://t.me/", "").replace("@", "").split("/")[0]
                
                # Пробуем вступить в группу
                try:
                    await app.join_chat(chat_id)
                    update_logs(f"[+] Вступил в чат: {chat_id}")
                except Exception:
                    # Если уже там — игнорим ошибку
                    pass

                # Генерируем текст сообщения
                final_text = parse_spintax(message_template)
                
                # Отправляем сообщение
                await app.send_message(chat_id, final_text)
                update_logs(f"[OK] Отправлено в {chat_id}")

                # Рандомная задержка
                wait_time = random.randint(delay_range[0], delay_range[1])
                update_logs(f"[WAIT] Пауза {wait_time} сек...")
                await asyncio.sleep(wait_time)

            except FloodWait as e:
                update_logs(f"[!] Флуд-фильтр: ждем {e.value} сек.")
                await asyncio.sleep(e.value)
            except RPCError as e:
                update_logs(f"[ERROR] Ошибка Telegram: {e}")
            except Exception as e:
                update_logs(f"[ERROR] Ошибка с {link}: {str(e)}")

        update_logs("[FINISH] Рассылка завершена успешно.")

    except Exception as e:
        update_logs(f"[CRITICAL] Не удалось запустить сессию: {str(e)}")
    finally:
        # Важно корректно остановить клиент
        if app.is_connected:
            await app.stop()

def main():
    st.title("🚀 Telegram Promo System")

    # Берем данные из Secrets Streamlit (если они там есть)
    s_id = st.secrets.get("api_id", "")
    s_hash = st.secrets.get("api_hash", "")
    s_phone = st.secrets.get("phone_number", "")

    # Боковая панель для ввода данных
    st.sidebar.header("🔑 Настройки")
    api_id = st.sidebar.text_input("API ID", value=str(s_id) if s_id else "")
    api_hash = st.sidebar.text_input("API Hash", value=s_hash, type="password")
    phone = st.sidebar.text_input("Телефон", value=s_phone)

    # Основная область
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Группы")
        links_input = st.text_area("Ссылки (по одной на строку)", height=250)
        group_list = [l.strip() for l in links_input.split("\n") if l.strip()]

    with col2:
        st.subheader("📝 Реклама")
        msg_template = st.text_area("Текст (поддержка {A|B})", height=150)
        delay_range = st.slider("Задержка между постами (сек)", 10, 600, (30, 90))

    # Кнопка запуска
    if st.button("▶️ ЗАПУСТИТЬ", use_container_width=True):
        if not api_id or not api_hash or not phone:
            st.error("Заполни данные API и телефон в Sidebar!")
        elif not group_list:
            st.error("Список групп пуст!")
        else:
            # РЕШЕНИЕ ОШИБКИ: Принудительно создаем и устанавливаем новый Event Loop
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_promotion_process(
                    int(api_id),
                    api_hash,
                    phone,
                    group_list,
                    msg_template,
                    delay_range
                ))
            except Exception as e:
                st.error(f"Ошибка выполнения: {e}")
            finally:
                loop.close()

if __name__ == "__main__":
    main()
