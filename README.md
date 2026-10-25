# Advanced Blog (Orionboard)

A full-featured blog platform built with Django and Django REST Framework.
Users can write, edit, and publish posts, upload cover images, like and
comment, and authors get a dashboard with per-post view statistics. A JSON
API is available alongside the web interface.

## Features

- User accounts: registration, login, logout, password management
- Create, edit, and publish blog posts with cover images and categories/tags
- Likes and comments (with AJAX commenting)
- Per-post view tracking and an author statistics dashboard
- Search, featured posts, gallery, FAQ, and contact pages
- REST API (Django REST Framework) with JWT authentication
- Admin panel for managing all content

## Tech stack

- **Backend:** Django 5.2, Django REST Framework
- **Auth (API):** djangorestframework-simplejwt (JWT)
- **Database:** SQLite for local development, PostgreSQL (Neon) in production
- **Static files:** WhiteNoise
- **Server:** Gunicorn
- **Image handling:** Pillow

## Running locally

### 1. Prerequisites
- Python 3.13
- Git

### 2. Get the code
```bash
git clone https://github.com/vijayant-pandey/Advanced_blog_Orionboard.git
cd Advanced_blog_Orionboard
```

### 3. Create and activate a virtual environment
```bash
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure environment variables
Copy the example file and fill in your own values:
```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```
At minimum set `SECRET_KEY`. Locally the project uses SQLite automatically,
so you do not need a database server. To generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Set up the database and admin user
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Run the server
```bash
python manage.py runserver
```
Open http://127.0.0.1:8000 in your browser. The admin panel is at
http://127.0.0.1:8000/admin and the API lives under http://127.0.0.1:8000/api.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | `True` locally, `False` in production (default `False`) |
| `ALLOWED_HOSTS` | No | Comma-separated hosts (e.g. `.onrender.com`) |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated trusted origins (e.g. `https://*.onrender.com`) |
| `DATABASE_URL` | No | PostgreSQL connection URL. If unset, SQLite is used |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | No | Individual DB settings (used only when `DATABASE_URL` is unset) |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `CONTACT_RECIPIENT_EMAIL` | No | Email configuration |

See `.env.example` for the full list.

## Deployment (Render + Neon)

The project is deployed on [Render](https://render.com) with a
[Neon](https://neon.tech) PostgreSQL database.

- **Build command:**
  ```
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
  ```
- **Start command:**
  ```
  gunicorn orionboard.wsgi:application
  ```
- Set the environment variables above in the Render dashboard, with
  `DEBUG=False` and `DATABASE_URL` pointing to the Neon database.

## Project structure

```
orionboard/      Project settings and URL configuration
accounts/        User accounts and authentication views
blogzone/        Blog models, views, forms, and the REST API
templates/       HTML templates
static/          CSS, JavaScript, fonts, and images
media/           User-uploaded files (not committed to Git)
```

## Notes

- `.env`, `db.sqlite3`, `venv/`, and `media/` are intentionally excluded from
  Git (see `.gitignore`). Never commit secrets.
- On Render's free plan the service sleeps after inactivity, so the first
  request after idle time may take ~30 seconds.
- Uploaded media files on free hosting are not persistent across redeploys;
  use a service like Cloudinary or S3 for permanent media storage.
