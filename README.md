# Wealthreader Hub

Centralized management and billing hub for the `QuickBanks client app` client app.

## What it does

- Stores the shared Wealthreader API key once.
- Issues activation keys per client site.
- Hands out API credentials + limits to authorized client sites via a single activation endpoint.
- Receives daily signed usage reports (active connections) from client sites.
- Provides a billing view per customer.

## DocTypes

- **Wealthreader Configuration** (single): shared API key, environment, signing secret, default widget domain.
- **Wealthreader Customer** (one row per client site): activation key, site URL, allowed connections, expiry, status.
- **Wealthreader Usage Report** (one row per daily report): customer, date, active connections, monthly amount.

## API endpoints

All endpoints are `POST` and accept/return JSON.

### `wealthreader_hub.api.activate`

Client sites call this to exchange an activation key for configuration.

**Request**
```json
{
  "activation_key": "...",
  "site_url": "https://client.example.com",
  "site_name": "client-site"
}
```

**Response**
```json
{
  "status": "ok",
  "data": {
    "api_key": "...",
    "environment": "production",
    "widget_domain": "https://client.example.com",
    "allowed_connections": 5,
    "expiry_date": "2026-12-31",
    "usage_report_url": "/api/method/wealthreader_hub.wealthreader_hub.api.report_usage",
    "signature": "..."
  }
}
```

### `wealthreader_hub.api.report_usage`

Client sites call this daily with a signed usage payload.

**Request**
```json
{
  "activation_key": "...",
  "report_date": "2026-07-09",
  "active_connections": 3,
  "site_url": "https://client.example.com",
  "signature": "..."
}
```

### `wealthreader_hub.api.revoke`

Deactivates a customer.

**Request**
```json
{
  "activation_key": "..."
}
```

## Installation

```bash
bench get-app https://github.com/admbittechnologies/QuickBanks client app_hub.git
bench --site <hub-site> install-app wealthreader_hub
```

## Setup

1. Open **Wealthreader Configuration**.
2. Enter:
   - **Wealthreader API Key** — the shared key from the Wealthreader clients area.
   - **Environment** — sandbox or production.
   - **Signing Secret** — generate a strong random secret; client sites will use it to sign usage reports.
   - **Default Widget Domain** — fallback domain for clients.
3. Create **Wealthreader Customer** records. The activation key is generated automatically.
4. Give each client their activation key and the Hub URL.

## Billing

- Each active connection is billed at **€15 per month**.
- `Wealthreader Usage Report` stores daily counts per customer.
- Use a report or script to sum active connections per customer per month for invoicing.

## Security

- The shared Wealthreader API key is stored encrypted.
- Activation and usage payloads should be sent over HTTPS.
- Usage reports are signed with HMAC-SHA256 using the configured signing secret.

## License

MIT
