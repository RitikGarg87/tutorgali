# TutorGali — VPS Deployment Guide (Ubuntu 22.04)

Run every command on your server via SSH.

---

## Step 1 — Connect to your server

```bash
ssh ubuntu@YOUR_SERVER_IP
```

---

## Step 2 — Install system packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip nginx git
```

---

## Step 3 — Upload your project

**Option A — Git (recommended):**
```bash
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/tutorgali.git
cd tutorgali
```

**Option B — SCP from your Mac:**
```bash
# Run this on your Mac (not the server):
scp -r /Users/ritik.garg/Downloads/tutorgali ubuntu@YOUR_SERVER_IP:/home/ubuntu/tutorgali
```

---

## Step 4 — Create virtual environment and install dependencies

```bash
cd /home/ubuntu/tutorgali
python3.12 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 5 — Create and configure .env

```bash
cp .env /home/ubuntu/tutorgali/.env   # if uploaded via scp, it's already there
nano .env
```

Edit these values in `.env`:
```
SECRET_KEY=<generate a new one — see below>
DEBUG=False
ALLOWED_HOSTS=YOUR_SERVER_IP

EMAIL_HOST_USER=devilritik45@gmail.com
EMAIL_HOST_PASSWORD=sfijhuddmftkfqee

RAZORPAY_KEY_ID=rzp_test_T4a75nlxeCRp91
RAZORPAY_KEY_SECRET=9rHHj4raVUYxw40GVyoBZWmI

FAST2SMS_API_KEY=yaMmJUzKfquEHp1FRdY4kAC0l8vOG2xirQ7Zsnco35wegb6LVhlmnLxD28tWRkAwOqrPphFIbZgo9vJ4

GOOGLE_MAPS_API_KEY=AIzaSyAXefPNxvTiRdc9RCs6acRNA61AWrGORvE
```

**Generate a new SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output and paste it as the SECRET_KEY value in .env.

**Secure the .env file:**
```bash
chmod 600 .env
```

---

## Step 6 — Run Django setup commands

```bash
source env/bin/activate

# Create logs directory
mkdir -p logs

# Run database migrations
python manage.py migrate

# Collect static files into staticfiles/
python manage.py collectstatic --noinput

# Create a superuser for the admin panel
python manage.py createsuperuser

# Verify everything is OK
python manage.py check --deploy
```

---

## Step 7 — Set up systemd service (Gunicorn)

```bash
# Copy the service file
sudo cp deploy/tutorgali.service /etc/systemd/system/tutorgali.service

# Reload systemd and start the service
sudo systemctl daemon-reload
sudo systemctl enable tutorgali
sudo systemctl start tutorgali

# Check it's running
sudo systemctl status tutorgali
```

If you see `Active: active (running)` — Gunicorn is up.

---

## Step 8 — Set up Nginx

```bash
# Copy Nginx config
sudo cp deploy/nginx.conf /etc/nginx/sites-available/tutorgali

# Edit YOUR_SERVER_IP in the config
sudo nano /etc/nginx/sites-available/tutorgali
# Change: server_name YOUR_SERVER_IP;
# To:     server_name 123.456.789.0;   ← your actual IP

# Enable the site
sudo ln -s /etc/nginx/sites-available/tutorgali /etc/nginx/sites-enabled/

# Remove default Nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Test config and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 9 — Set correct file permissions

```bash
# Nginx needs to read media and staticfiles
sudo chown -R ubuntu:www-data /home/ubuntu/tutorgali/media
sudo chown -R ubuntu:www-data /home/ubuntu/tutorgali/staticfiles
sudo chmod -R 755 /home/ubuntu/tutorgali/media
sudo chmod -R 755 /home/ubuntu/tutorgali/staticfiles

# Gunicorn socket needs www-data access
sudo chown ubuntu:www-data /run/tutorgali.sock 2>/dev/null || true
```

---

## Step 10 — Open firewall ports

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## Step 11 — Test the deployment

Open your browser and go to: `http://YOUR_SERVER_IP`

You should see the TutorGali homepage.

---

## Useful commands after deployment

```bash
# Restart app after code changes
sudo systemctl restart tutorgali

# View app logs
sudo journalctl -u tutorgali -f

# View Gunicorn access log
tail -f /home/ubuntu/tutorgali/logs/gunicorn_access.log

# View Gunicorn error log
tail -f /home/ubuntu/tutorgali/logs/gunicorn_error.log

# View Nginx error log
sudo tail -f /var/log/nginx/error.log

# After pulling new code from git:
source env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart tutorgali
```

---

## Add subscription plans (required — no seed data exists)

After deployment, log into `/admin-panel/` with your superuser account and create at least one `SubscriptionPlan` (name, duration in months, price in INR).

---

## Fast2SMS OTP — verify it works

1. Go to `http://YOUR_SERVER_IP/register/`
2. Enter a mobile number and click "Send OTP"
3. You should receive an SMS within a few seconds
4. If not, check: `tail -f /home/ubuntu/tutorgali/logs/tutorgali.log`
