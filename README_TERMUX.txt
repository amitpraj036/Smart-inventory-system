SMART INVENTORY — FLASK / TERMUX

1) Extract this ZIP into ~/SmartInventory_Flask_Termux
2) In Termux run:
   pkg update
   pkg install python unzip -y
   cd ~/SmartInventory_Flask_Termux
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   python app.py
3) Open http://127.0.0.1:8000 in your phone browser.
4) Stop server with CTRL+C.

Files:
- app.py: Flask routes and server
- database.py: original DatabaseManager / database logic
- templates/index.html: original HTML
- static/css/style.css: extracted original CSS
- static/js/app.js: extracted original JavaScript
- smart_inventory.db: created automatically on first run
- db_config.json: database configuration, created when changed

SQLite is the default. Keep smart_inventory.db and db_config.json for persistence.
The original Tailwind and Google Fonts CDN links are retained, so those resources need internet access.
