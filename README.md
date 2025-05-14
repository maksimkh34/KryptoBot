# Telegram Crypto Bot

A Telegram bot for processing TRX payments with authorization and admin notifications.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/maksimkh34/KryptoBot
   cd KryptoBot
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables (or copy `.env.example`):
   ```
   BOT_TOKEN=your_token
   TRON_NETWORK=(nile // mainnet)
   TRONGRID_API_KEY=trongrid_api
   ADMIN_ID=tg_admin_id
   TRX_RATE=1.02
   ```

4. Create a `data/` directory:
   ```bash
   mkdir data
   ```

5. Run the bot:
   ```bash
   python src/main.py
   ```

## Deployment

1. Copy the project to the server.
2. Update `.env` with production values (mainnet, real bot token).

## Data folder

* `keys.json`
  
      {
        "generated_keys": {
          "key1": {
            "status": "used"
          },
          "key2": {
            ...
        }
      }



* `orders.json`

      {
           "ORDER_20250513_174956": {
       "order_id": "ORDER_20250513_174956",
       "user_id": id,
       "username": "username",
       "created_at": "2025-05-13T18:22:26.872342",
       "status": "completed",
       "updated_at": "2025-05-13T18:22:39.638748",
       "currency": "TRX",
       "to_address": "TSZw...3DCKaKudxr",
       "amount": 5.0,
       "byn_amount": 5.07,
       "txid": "4efa...5de0a2c306",
       "from_address": "TCUFzxg...huy6",
       "final_amount": 5.0,
       "commission": 0
        },
        "ORDER_20250513_114243": {
          "order_id": "ORDER_20250513_114243",
          "user_id": id,
          "username": "username",
          "created_at": "2025-05-13T18:29:43.212341",
          "status": "completed",
          "updated_at": "2025-05-13T18:29:52.641689",
          "currency": "TRX",
          "to_address": "TSZw2uf...CKaKudxr",
          "amount": 5.0,
          "byn_amount": 5.07,
          "warning": "Low bandwidth: 245 < 300",
          "txid": "2c0482cd8fcc...286342577bdee7b7",
          "from_address": "TCUFzxgsZ2pV...yMthuy6",
          "final_amount": 5.0,
          "commission": 0
        },
        ...
      }



* `setings.json`
  
      {
        "currencies": [
          {
            "code": "TRX",
            "name": "TRON",
            "rate_key": "trx_rate",
            "wallet_class": "TronWallet"
          }
        ],
        "trx_rate": [rate]
      }


* `users.json`

      {
        "id1": {
          "auth_key": "[auth_key_1]"
        },
        "id2": {
          "auth_key": "[auth_key_2]"
        },
       ...
      }


* `wallets.json` **(TRX ONLY NOW)**

      {
        "active": [
          {
            "private_key": "0d59...5fc"
          },
          {
            "private_key": "97...151"
          },
       ...
       }


  


