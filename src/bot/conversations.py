import requests

from datetime import datetime
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from src.config import load_config
from src.data import storage
from src.data.orders import generate_order_id, save_order, update_order_status
from src.data.logger import logger
from src.data.users import add_user
from src.crypto.factory import get_wallet_class
from src.bot.notifications import send_payment_receipt, send_payment_failure, send_insufficient_funds, send_key_activation_notification
from src.data.utils import round_byn
from tronpy.keys import PrivateKey
from telegram import Update
from telegram.ext import ContextTypes

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

# Состояния для авторизации
AUTH_KEY = 0

# Состояния для платежа
CURRENCY, WALLET, AMOUNT, CONFIRMATION = range(1, 5)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает максимальный баланс среди всех кошельков для оплаты."""
    logger.info(f"Пользователь {update.effective_user.id} запросил максимальный баланс")

    try:
        # Загружаем кошельки из wallets.json
        wallets_data = storage.load_file(storage.WALLETS).get("active", [])

        if not wallets_data:
            logger.info("Кошельки не найдены")
            await update.message.reply_text("Кошельки не найдены")
            return

        max_balance = 0
        wallet_class = get_wallet_class("TronWallet")
        wallet = wallet_class()
        # Проверяем баланс каждого кошелька
        for wallet_data in wallets_data:
            priv_key = PrivateKey(bytes.fromhex(wallet_data['private_key']))
            address = priv_key.public_key.to_base58check_address()
            w_balance = wallet.get_balance(address)
            logger.debug(f"Баланс кошелька {w_balance}...: {balance} TRX")

            if w_balance > max_balance:
                max_balance = w_balance

        # Форматируем сумму с 6 знаками после запятой (стандарт для TRX)
        formatted_balance = f"{max_balance}"
        logger.info(f"Максимальный баланс: {formatted_balance} TRX")
        await update.message.reply_text(f"Максимальная сумма для оплаты: {formatted_balance} TRX")

    except FileNotFoundError:
        logger.error("Файл wallets.json не найден")
        await update.message.reply_text("Ошибка: Кошельки не найдены")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Ошибка подключения к Tron: {str(e)}")
        await update.message.reply_text("Ошибка подключения к сети Tron")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении баланса: {str(e)}")
        await update.message.reply_text("Произошла ошибка при получении баланса")

async def auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс авторизации."""
    args = context.args
    if args:
        context.user_data["auth_key"] = args[0]
        return await process_auth_key(update, context)
    else:
        await update.message.reply_text("Введите ваш ключ авторизации:")
        return AUTH_KEY

async def process_auth_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенный ключ авторизации."""
    user_id = str(update.effective_user.id)
    input_key = context.user_data.get("auth_key") or update.message.text.strip()
    keys_data = storage.load_file(storage.KEYS)

    if input_key in keys_data.get("generated_keys", {}):
        if keys_data["generated_keys"][input_key]["status"] == "active":
            keys_data["generated_keys"][input_key]["status"] = "used"
            storage.save_file(keys_data, storage.KEYS)
            add_user(user_id, input_key)
            await update.message.reply_text("✅ Авторизация успешна!")
            await send_key_activation_notification(
                context.bot,
                update.effective_user.username or "unknown",
                user_id,
                input_key
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Ключ уже использован!")
    else:
        await update.message.reply_text("❌ Неверный ключ авторизации!")
    return ConversationHandler.END

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс платежа."""
    from src.bot.handlers import check_auth_middleware
    if not await check_auth_middleware(update, context):
        return ConversationHandler.END

    order_id = generate_order_id()
    context.user_data["payment_data"] = {
        "order_id": order_id,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "created_at": datetime.now().isoformat(),
        "status": "created"
    }
    save_order(context.user_data["payment_data"])

    settings = storage.load_file(storage.SETTINGS)
    currencies = [[currency["code"] for currency in settings.get("currencies", [])]]
    if not currencies[0]:
        await update.message.reply_text("❌ Нет доступных валют!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    markup = ReplyKeyboardMarkup(
        currencies,
        one_time_keyboard=True,
        resize_keyboard=True,
        input_field_placeholder="Выберите валюту"
    )
    await update.message.reply_text("Выберите криптовалюту:", reply_markup=markup)
    return CURRENCY

async def process_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор валюты."""
    currency = update.message.text.strip().upper()
    settings = storage.load_file(storage.SETTINGS)
    valid_currencies = {c["code"] for c in settings.get("currencies", [])}

    if currency not in valid_currencies:
        await update.message.reply_text("❌ Валюта не поддерживается", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    context.user_data["payment_data"]["currency"] = currency
    update_order_status(
        context.user_data["payment_data"]["order_id"],
        "currency_selected",
        {"currency": currency}
    )
    await update.message.reply_text("Введите адрес кошелька получателя:", reply_markup=ReplyKeyboardRemove())
    return WALLET

async def process_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенный адрес кошелька."""
    wallet = update.message.text.strip()
    context.user_data["payment_data"]["wallet"] = wallet
    currency = context.user_data["payment_data"]["currency"]
    await update.message.reply_text(
        f"Введите сумму в {currency}:",
        reply_markup=ReplyKeyboardRemove()
    )
    update_order_status(
        context.user_data["payment_data"]["order_id"],
        "wallet_entered",
        {"to_address": wallet}
    )
    return AMOUNT

async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенную сумму."""
    try:
        amount = float(update.message.text.replace(",", "."))
        context.user_data["payment_data"]["amount"] = amount
        config = load_config()
        settings = storage.load_file(storage.SETTINGS)

        # Найти валюту и её курс
        currency = context.user_data["payment_data"]["currency"]
        currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
        if not currency_info:
            await update.message.reply_text("❌ Ошибка конфигурации валюты!", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        rate_key = currency_info["rate_key"]
        rate = settings.get(rate_key, -1)
        byn_amount = round_byn(amount * rate)

        # Выбор кошелька и расчет комиссии
        wallet_class = get_wallet_class(currency_info["wallet_class"])
        wallet = wallet_class()
        wallets = storage.load_file(storage.WALLETS).get("active", [])
        bandwidth_required = 270
        bandwidth_fee_per_point = 0.001
        sufficient_bandwidth_wallets = []
        insufficient_bandwidth_wallets = []

        for f_wallet in wallets:
            try:
                priv_key = PrivateKey(bytes.fromhex(f_wallet["private_key"]))
                address = priv_key.public_key.to_base58check_address()
                balance = wallet.get_balance(address)
                bandwidth = wallet.estimate_bandwidth_usage(address)
                commission = (bandwidth_required - bandwidth) * bandwidth_fee_per_point if bandwidth < bandwidth_required else 0
                total_amount = amount + commission

                if balance >= total_amount:
                    wallet_info = {
                        "private_key": f_wallet["private_key"],
                        "address": address,
                        "balance": balance,
                        "bandwidth": bandwidth,
                        "commission": commission,
                        "total_amount": total_amount
                    }
                    if bandwidth >= bandwidth_required:
                        sufficient_bandwidth_wallets.append(wallet_info)
                    else:
                        insufficient_bandwidth_wallets.append(wallet_info)
            except Exception as e:
                logger.error(f"Ошибка проверки кошелька {f_wallet.get('address', 'unknown')}: {str(e)}")
                continue

        selected_wallet = None
        if sufficient_bandwidth_wallets:
            selected_wallet = min(
                sufficient_bandwidth_wallets,
                key=lambda w: w["balance"] - w["total_amount"],
                default=None
            )
            logger.info(f"Выбран кошелек {selected_wallet['address']} с bandwidth {selected_wallet['bandwidth']} >= {bandwidth_required}")
        elif insufficient_bandwidth_wallets:
            selected_wallet = min(
                insufficient_bandwidth_wallets,
                key=lambda w: w["balance"] - w["total_amount"],
                default=None
            )
            logger.info(
                f"Выбран кошелек {selected_wallet['address']} с bandwidth {selected_wallet['bandwidth']} < {bandwidth_required}, "
                f"комиссия {selected_wallet['commission']} TRX"
            )

        if not selected_wallet:
            await update.message.reply_text("❌ Недостаточно средств на кошельках!", reply_markup=ReplyKeyboardRemove())
            update_order_status(
                context.user_data["payment_data"]["order_id"],
                "failed",
                {"error": "Insufficient funds or bandwidth"}
            )
            await send_insufficient_funds(context.bot, context.user_data["payment_data"], update.effective_user.username)
            return ConversationHandler.END

        # Сохраняем выбранный кошелек
        context.user_data["selected_wallet"] = selected_wallet
        commission_note = (f"\nВключена комиссия: {round_byn(selected_wallet['commission'])}"
                           f" {currency}") if selected_wallet["commission"] > 0 else ""
        byn_total = round_byn(selected_wallet["total_amount"] * rate)

        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        await update.message.reply_text(
            f"Сумма: {amount} {currency}\n"
            f"Комиссия: {selected_wallet['commission']} {currency}\n"
            f"Итого: {selected_wallet['total_amount']} {currency}\n"
            f"Сумма к оплате: {byn_total} BYN\n"
            f"Курс: 1 {currency} = {rate} BYN\n\n"
            f"Подтвердите платеж:{commission_note}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        update_order_status(
            context.user_data["payment_data"]["order_id"],
            "amount_entered",
            {
                "amount": amount,
                "byn_amount": float(byn_amount),
                "commission": selected_wallet["commission"],
                "total_amount": selected_wallet["total_amount"]
            }
        )
        return CONFIRMATION
    except ValueError:
        await update.message.reply_text("❌ Неверный формат суммы!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает подтверждение платежа."""
    query = update.callback_query
    await query.answer()
    payment_data = context.user_data.get("payment_data")
    selected_wallet = context.user_data.get("selected_wallet")
    if not payment_data or not selected_wallet:
        await query.edit_message_text("❌ Ошибка: данные платежа или кошелька утеряны")
        return ConversationHandler.END

    order_id = payment_data.get("order_id", "UNKNOWN_ORDER")
    try:
        update_order_status(
            order_id=order_id,
            status="processing",
            additional_data={"updated_at": datetime.now().isoformat()}
        )
        settings = storage.load_file(storage.SETTINGS)
        currency = payment_data["currency"]
        currency_info = next((c for c in settings.get("currencies", []) if c["code"] == currency), None)
        if not currency_info:
            raise ValueError("Currency not found in settings")

        wallet_class = get_wallet_class(currency_info["wallet_class"])
        wallet = wallet_class()

        if not wallet.validate_address(payment_data["wallet"]):
            update_order_status(order_id, "failed", {"error": "Invalid address"})
            await query.edit_message_text("❌ Неверный адрес кошелька")
            return ConversationHandler.END

        # Проверка свободного баланса
        if selected_wallet["balance"] < selected_wallet["total_amount"]:
            logger.info(f"Недостаточно свободного баланса на кошельке {selected_wallet['address']}. Инициируем разморозку.")
            try:
                txid = wallet.unfreeze_balance(selected_wallet["private_key"])
                update_order_status(
                    order_id,
                    "pending_unfreeze",
                    {
                        "unfreeze_txid": txid,
                        "warning": "Недостаточно свободного баланса. Инициирована разморозка TRX. Повторите платеж через 14 дней.",
                        "updated_at": datetime.now().isoformat()
                    }
                )
                await query.edit_message_text(
                    "⚠️ Недостаточно свободного баланса. Инициирована разморозка TRX. Повторите платеж через 14 дней."
                )
                config = load_config()
                await context.bot.send_message(
                    chat_id=config["ADMIN_ID"],
                    text=(
                        f"⚠️ Недостаточно свободного баланса на кошельке `{selected_wallet['address']}`!\n"
                        f"Инициирована разморозка, TXID: `{txid}`\n"
                        f"Свободный баланс: {selected_wallet['balance']} TRX\n"
                        f"Повторите платеж через 14 дней."
                    ),
                    parse_mode="Markdown"
                )
                return ConversationHandler.END
            except Exception as e:
                logger.error(f"Ошибка разморозки кошелька {selected_wallet['address']}: {str(e)}")
                update_order_status(order_id, "failed", {"error": f"Unfreeze failed: {str(e)}"})
                await query.edit_message_text("❌ Ошибка при разморозке кошелька")
                return ConversationHandler.END

        # Выполняем транзакцию
        txid = wallet.send_transaction(
            private_key=selected_wallet["private_key"],
            to_address=payment_data["wallet"],
            amount=selected_wallet["total_amount"]
        )
        update_order_status(
            order_id,
            "completed",
            {
                "txid": txid,
                "from_address": selected_wallet["address"],
                "final_amount": payment_data["amount"],
                "commission": selected_wallet["commission"],
                "total_amount": selected_wallet["total_amount"],
                "updated_at": datetime.now().isoformat()
            }
        )
        await send_payment_receipt(
            context.bot,
            payment_data,
            txid,
            update.effective_user.username,
            selected_wallet["address"],
            selected_wallet["commission"],
            selected_wallet["total_amount"]
        )
        rate_key = currency_info["rate_key"]
        rate = settings.get(rate_key, -1)
        commission_note = f"\nВключена комиссия: {selected_wallet['commission']} TRX" if selected_wallet["commission"] > 0 else ""
        await query.edit_message_text(
            f"✅ Платеж успешно выполнен!\n"
            f"Сумма: {payment_data['amount']} {currency}\n"
            f"Комиссия: {selected_wallet['commission']} {currency}\n"
            f"Итого: {selected_wallet['total_amount']} "
            f"{currency} ({round_byn(float(selected_wallet['total_amount'] * rate))} BYN)\n"
            f"TXID: `{txid}`{commission_note}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Payment error: {str(e)}")
        update_order_status(
            order_id,
            "failed",
            {
                "error": str(e),
                "commission": selected_wallet["commission"] if selected_wallet else 0,
                "total_amount": selected_wallet["total_amount"] if selected_wallet else payment_data["amount"],
                "updated_at": datetime.now().isoformat()
            }
        )
        await send_payment_failure(
            context.bot,
            payment_data,
            str(e),
            update.effective_user.username,
            selected_wallet["address"] if selected_wallet else None,
            selected_wallet["commission"] if selected_wallet else 0,
            selected_wallet["total_amount"] if selected_wallet else payment_data["amount"]
        )
        await query.edit_message_text("❌ Ошибка при выполнении платежа")
    finally:
        context.user_data.clear()
    return ConversationHandler.END

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает отмену платежа."""
    query = update.callback_query
    await query.answer()
    order_id = context.user_data["payment_data"]["order_id"]
    update_order_status(order_id, "cancelled")
    await query.edit_message_text("❌ Платеж отменен")
    context.user_data.clear()
    return ConversationHandler.END

async def freeze_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Замораживает 90% TRX на всех активных кошельках для bandwidth."""
    from src.bot.handlers import check_auth_middleware
    if not await check_auth_middleware(update, context):
        return

    wallets = storage.load_file(storage.WALLETS).get("active", [])
    if not wallets:
        await update.message.reply_text("❌ Нет активных кошельков!")
        return

    wallet_class = get_wallet_class("TronWallet")
    wallet = wallet_class()
    FREEZE_PERCENTAGE = 0.9
    MIN_FREE_BALANCE = 1.0

    results = []
    for f_wallet in wallets:
        try:
            priv_key = PrivateKey(bytes.fromhex(f_wallet["private_key"]))
            address = priv_key.public_key.to_base58check_address()
            balance = wallet.get_balance(address)
            frozen_balance = wallet.get_frozen_balance(address)
            available_balance = balance - frozen_balance

            if available_balance <= MIN_FREE_BALANCE:
                results.append(f"Кошелек `{address}`: Недостаточно свободного баланса ({available_balance} TRX)")
                continue

            amount_to_freeze = (available_balance - MIN_FREE_BALANCE) * FREEZE_PERCENTAGE
            if amount_to_freeze < 1.0:
                results.append(f"Кошелек `{address}`: Сумма для заморозки слишком мала ({amount_to_freeze} TRX)")
                continue

            txid = wallet.freeze_balance(f_wallet["private_key"], amount_to_freeze)
            f_wallet["frozen_amount"] = f_wallet.get("frozen_amount", 0) + amount_to_freeze
            f_wallet["freeze_txid"] = txid
            f_wallet["freeze_timestamp"] = datetime.now().isoformat()
            results.append(f"Кошелек `{address}`: Заморожено {amount_to_freeze} TRX, TXID: `{txid}`")
        except Exception as e:
            results.append(f"Кошелек `{address}`: Ошибка заморозки: {str(e)}")
            logger.error(f"Ошибка заморозки кошелька {address}: {str(e)}")

    storage.save_file({"active": wallets}, storage.WALLETS)
    await update.message.reply_text(
        "Результаты заморозки:\n" + "\n".join(results),
        parse_mode="Markdown"
    )

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавляет новый кошелек для администратора."""
    config = load_config()
    if str(update.effective_user.id) != str(config["ADMIN_ID"]):
        await update.message.reply_text("❌ Доступно только администратору!")
        return

    if not context.args:
        await update.message.reply_text("❌ Укажите приватный ключ: /add_wallet <private_key>")
        return

    private_key = context.args[0].strip()
    try:
        priv_key = PrivateKey(bytes.fromhex(private_key))
        address = priv_key.public_key.to_base58check_address()
        wallet_class = get_wallet_class("TronWallet")
        wallet = wallet_class()

        # Проверка валидности адреса
        if not wallet.validate_address(address):
            await update.message.reply_text("❌ Неверный адрес кошелька!")
            return

        # Проверка, существует ли кошелек
        wallets_data = storage.load_file(storage.WALLETS)
        active_wallets = wallets_data.get("active", [])
        if any(w["private_key"] == private_key for w in active_wallets):
            await update.message.reply_text("❌ Кошелек уже существует!")
            return

        # Добавление кошелька
        active_wallets.append({"private_key": private_key})
        wallets_data["active"] = active_wallets
        storage.save_file(wallets_data, storage.WALLETS)
        await update.message.reply_text(
            f"✅ Кошелек `{address}` успешно добавлен!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка добавления кошелька: {str(e)}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def remove_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет кошелек по адресу или приватному ключу для администратора."""
    config = load_config()
    if str(update.effective_user.id) != str(config["ADMIN_ID"]):
        await update.message.reply_text("❌ Доступно только администратору!")
        return

    if not context.args:
        await update.message.reply_text("❌ Укажите адрес или приватный ключ: /remove_wallet <address_or_private_key>")
        return

    input_arg = context.args[0].strip()
    try:
        wallet_class = get_wallet_class("TronWallet")
        wallet = wallet_class()
        wallets_data = storage.load_file(storage.WALLETS)
        active_wallets = wallets_data.get("active", [])

        # Проверяем, является ли аргумент адресом
        if wallet.validate_address(input_arg):
            address = input_arg
            # Ищем кошелек по адресу
            initial_len = len(active_wallets)
            active_wallets = [
                w for w in active_wallets
                if PrivateKey(bytes.fromhex(w["private_key"])).public_key.to_base58check_address() != address
            ]
            if len(active_wallets) == initial_len:
                await update.message.reply_text("❌ Кошелек не найден!")
                return
        else:
            # Проверяем, является ли аргумент приватным ключом
            try:
                priv_key = PrivateKey(bytes.fromhex(input_arg))
                address = priv_key.public_key.to_base58check_address()
                # Ищем кошелек по приватному ключу
                initial_len = len(active_wallets)
                active_wallets = [
                    w for w in active_wallets
                    if w["private_key"] != input_arg
                ]
                if len(active_wallets) == initial_len:
                    await update.message.reply_text("❌ Кошелек не найден!")
                    return
            except ValueError:
                await update.message.reply_text("❌ Неверный адрес или приватный ключ!")
                return

        # Сохраняем обновленный список кошельков
        wallets_data["active"] = active_wallets
        storage.save_file(wallets_data, storage.WALLETS)
        await update.message.reply_text(
            f"✅ Кошелек `{address}` успешно удален!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка удаления кошелька: {str(e)}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def wallets_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает информацию о всех кошельках для администратора."""
    config = load_config()
    if str(update.effective_user.id) != str(config["ADMIN_ID"]):
        await update.message.reply_text("❌ Доступно только администратору!")
        return

    wallets_data = storage.load_file(storage.WALLETS)
    active_wallets = wallets_data.get("active", [])
    if not active_wallets:
        await update.message.reply_text("❌ Нет активных кошельков!")
        return

    wallet_class = get_wallet_class("TronWallet")
    wallet = wallet_class()
    info = ["📋 Информация о кошельках:"]
    for w in active_wallets:
        try:
            priv_key = PrivateKey(bytes.fromhex(w["private_key"]))
            address = priv_key.public_key.to_base58check_address()
            balance = wallet.get_balance(address)
            bandwidth = wallet.estimate_bandwidth_usage(address)
            info.append(
                f"▪ `{address}`\n"
                f"   Баланс: {balance:.2f} TRX\n"
                f"   Bandwidth: {bandwidth:.0f}"
            )
        except Exception as e:
            logger.error(f"Ошибка получения данных кошелька {w.get('address', 'unknown')}: {str(e)}")
            info.append(f"▪ Ошибка для кошелька: {str(e)}")

    await update.message.reply_text("\n".join(info), parse_mode="Markdown")

def get_auth_conversation() -> ConversationHandler:
    """Возвращает ConversationHandler для авторизации."""
    return ConversationHandler(
        entry_points=[CommandHandler("auth", auth_start)],
        states={
            AUTH_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_auth_key)]
        },
        fallbacks=[],
        per_message=False
    )

def get_payment_conversation() -> ConversationHandler:
    """Возвращает ConversationHandler для платежей."""
    settings = storage.load_file(storage.SETTINGS)
    valid_currencies = "|".join(c["code"] for c in settings.get("currencies", []))
    return ConversationHandler(
        entry_points=[CommandHandler("pay", start_payment)],
        states={
            CURRENCY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.Regex(f"^{valid_currencies}$"),
                    process_currency
                )
            ],
            WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet)
            ],
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount)
            ],
            CONFIRMATION: [
                CallbackQueryHandler(confirm_payment, pattern="^confirm$"),
                CallbackQueryHandler(cancel_payment, pattern="^cancel$")
            ]
        },
        fallbacks=[
            CommandHandler("start", cancel_payment),
            CommandHandler("pay", start_payment)
        ],
        per_message=False
    )