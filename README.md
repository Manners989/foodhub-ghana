# FoodHub Ghana 🍲

A complete, production-ready food ordering website built with **Django**. Browse a menu,
add items to a cart, check out with Mobile Money / card (via Paystack) / cash on delivery,
track orders, leave reviews, and manage everything from a customized Django admin panel.

## Features

- **Modern, responsive UI** — custom design system, scroll animations, hover effects,
  mobile-first layout.
- **Menu browsing** — category filters, live search, price filter, vegetarian filter,
  sorting, pagination.
- **Food detail pages** — image, price (with optional discount badge), spice level,
  prep time, calories, star ratings, and a full review system.
- **Cart** — works for guests (session-based) and logged-in users; AJAX add/update/remove
  with live badge updates.
- **Checkout** — delivery or pickup, Ghanaian regions, Mobile Money network selection
  (MTN / Telecel / AirtelTigo), cash on delivery, and **real card/Mobile Money payments
  via Paystack**.
- **Order tracking** — order confirmation page, shareable order number, animated status
  progress bar (Pending → Confirmed → Preparing → Out for Delivery → Delivered), and a
  payment status indicator for online-paid orders.
- **Accounts** — registration, login/logout, profile editing with delivery details and
  avatar upload, order history, session-cart-to-account merge on login.
- **Admin panel** — fully customized: manage categories, food items (inline reviews),
  orders (inline items, editable status, payment status), contact messages, newsletter
  subscribers.
- **Automated tests** — model, view, cart, checkout, payment, and authorization coverage
  (see [Testing](#testing) below).

## Tech Stack

- Python 3.12 / Django 6.0
- SQLite for local development (zero setup — this is all `requirements.txt` installs),
  PostgreSQL for production via `requirements-postgres.txt` + `DATABASE_URL` (installed
  automatically inside Docker — no code changes needed either way)
- Paystack for card + Ghanaian Mobile Money payments
- Whitenoise for static file serving, Gunicorn as the production WSGI server
- Bootstrap 5 + Bootstrap Icons (via CDN) + custom CSS/JS (no frontend build step)
- Docker + docker-compose for a one-command full local stack, ready for Render/Railway/Fly

## Getting Started (without Docker)

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies (SQLite is used by default — no PostgreSQL needed for local dev)
pip install -r requirements.txt

# 3. Copy the example environment file and fill it in
cp .env.example .env
# At minimum, generate a real SECRET_KEY (see the comment in .env.example).
# Leave DATABASE_URL blank to use local SQLite.

# 4. Apply database migrations
python manage.py migrate

# 5. (Optional but recommended) Seed sample categories & dishes
python manage.py seed_data

# 6. Create your own admin account
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser, and **http://127.0.0.1:8000/admin/**
for the admin panel.

> This project intentionally does **not** ship a database file or a pre-made admin
> account — a real project should never bake credentials into a file that ends up in
> version control. Always create your own superuser with `createsuperuser`.

### Sample data

`python manage.py seed_data` populates 8 categories and 16 sample dishes using hotlinked
Unsplash photos, so the site isn't empty on first run. Upload your own photos per item in
the admin panel — they automatically take priority over the demo photo. To wipe and
re-seed: `python manage.py seed_data --flush`.

## Getting Started (with Docker — recommended)

This spins up the app **and** a real PostgreSQL database with one command:

```bash
cp .env.example .env
# fill in SECRET_KEY and (optionally) Paystack keys in .env

docker compose up --build
```

Then, in a second terminal:

```bash
docker compose exec web python manage.py seed_data
docker compose exec web python manage.py createsuperuser
```

Open **http://localhost:8000/**. Static files are collected automatically and media
uploads persist in the `media_data` Docker volume across restarts.

## Environment Variables

All configuration lives in environment variables (loaded from `.env` in development —
see `.env.example` for the full list with explanations). Nothing sensitive is hardcoded
in the codebase.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django's cryptographic signing key. Generate a real one — never reuse the example. |
| `DEBUG` | `True` in development only. Defaults to `False` so a forgotten variable fails safe. |
| `ALLOWED_HOSTS` | Comma-separated list of domains allowed to serve the site. |
| `CSRF_TRUSTED_ORIGINS` | Needed in production when behind HTTPS-terminating proxies (Render/Railway/Fly). |
| `DATABASE_URL` | Full database URL. Unset = local SQLite. Set to a `postgres://...` URL in production. |
| `EMAIL_*` | SMTP settings for sending real email. Defaults to printing emails to the console in development. |
| `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` | From your [Paystack dashboard](https://dashboard.paystack.com/#/settings/developers). Required for Mobile Money / card checkout to work. |

## Payments

Card and Mobile Money payments are processed through **Paystack**
(`store/payments.py`), which supports MTN, Telecel and AirtelTigo Mobile Money as well
as cards, all through one hosted checkout page — customer card/PIN details never touch
this server.

Flow:
1. Customer chooses Mobile Money or Card at checkout → an unpaid `Order` is created and
   the customer is redirected to Paystack's hosted checkout.
2. Paystack redirects back to `/payment/callback/` with a transaction reference.
3. The app **re-verifies that reference directly with Paystack's API** (never trusting
   the redirect alone) before marking the order paid and clearing the cart.
4. If verification fails, the unpaid order is deleted and the customer is sent back to
   checkout — nothing is left in a half-finished state.

Cash on delivery skips all of this — the order is placed immediately and settled by the
driver.

To test payments locally, use Paystack's test keys and their published test card /
Mobile Money numbers.

## Testing

```bash
python manage.py test
```

With a coverage report:

```bash
coverage run manage.py test
coverage report -m
```

The suite covers: model behavior (slug generation, pricing, order-number uniqueness),
cart operations, the full checkout flow for both cash-on-delivery and Paystack-backed
payments (mocked — no real API calls in tests), the payment callback (including a
verification-failure path), order-detail authorization (guest vs. account-owned orders),
registration, login-triggered cart merging, and profile editing.

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs this suite automatically on
every push and pull request.

## Deploying to production

The same codebase runs anywhere — only environment variables change.

### Option A: Docker on Render / Railway / Fly.io

All three platforms can build directly from the included `Dockerfile`.

**Render**: push to GitHub, then *New → Blueprint* and point it at this repo — the
included `render.yaml` provisions the web service and a managed Postgres database
automatically. You'll be prompted for `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY`.

**Railway**: `railway init`, then `railway up` — Railway detects the `Dockerfile`
automatically. Add a Postgres plugin from the Railway dashboard and it will inject
`DATABASE_URL` for you; add the other variables from `.env.example` under *Variables*.

**Fly.io**: `fly launch` (accept the detected Dockerfile), `fly postgres create` and
`fly postgres attach` to wire up a database, then `fly secrets set SECRET_KEY=... PAYSTACK_SECRET_KEY=...`
for the rest.

### Option B: Any host that runs Docker Compose

```bash
cp .env.example .env   # fill in production values, especially SECRET_KEY and Paystack keys
docker compose up --build -d
```

Point `DATABASE_URL` at a managed Postgres instance in production rather than the bundled
`db` service if you want managed backups. If you run the app outside Docker against
Postgres, remember to also `pip install -r requirements-postgres.txt`.

### Production checklist

- [ ] `DEBUG=False`
- [ ] Real, unique `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` set to your real domain(s)
- [ ] `DATABASE_URL` pointing at PostgreSQL, not SQLite
- [ ] Real `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` (live, not test, keys)
- [ ] Real SMTP credentials if you want order confirmation emails to actually send
- [ ] HTTPS is terminated somewhere in front of the app (Render/Railway/Fly all do this
      for you) — `settings.py` automatically applies HSTS, secure cookies, and SSL
      redirects once `DEBUG=False`

## Project Structure

```
foodhub/
├── foodhub/                 # project settings, root urls
│   └── settings.py          # entirely environment-driven — see Environment Variables above
├── store/                   # core app: menu, cart, checkout, orders, reviews, payments, admin
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── cart.py               # session/user cart resolution helper
│   ├── payments.py           # Paystack API client
│   ├── context_processors.py
│   ├── tests.py
│   └── management/commands/seed_data.py
├── accounts/                 # registration, login, profile
│   └── tests.py
├── templates/                 # all HTML templates (base.html + store/ + accounts/)
├── static/                    # css/js/img (no build tools needed)
├── media/                      # uploaded images (created at runtime, git-ignored)
├── Dockerfile / docker-compose.yml / docker-entrypoint.sh
├── render.yaml                 # Render.com deployment blueprint
├── .github/workflows/ci.yml    # runs the test suite on every push
├── .env.example                 # every environment variable, documented
└── requirements.txt / requirements-postgres.txt
```

## Notes & Assumptions

- Prices are shown in Ghanaian Cedis (GH₵) and delivery defaults assume a Ghana-based
  audience (regions list, Mobile Money networks) — easy to adapt for another market by
  editing `store/forms.py` (`GHANA_REGIONS`), `store/payments.py` (currency code), and
  the currency symbol in `settings.py`.
- Delivery fee is a flat GH₵15, free above GH₵150 — adjust `DELIVERY_FEE` and
  `FREE_DELIVERY_THRESHOLD` at the top of `store/views.py`.
- Guest orders remain trackable by order number alone (no account needed) by design.
  Once an order is tied to a logged-in account, only that account (or staff) can view
  its details — this is enforced in `store/views.py::_can_view_order`.
