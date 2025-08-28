from flask import Flask, redirect, session, request
from replit import db
import random, os, datetime
import sqlite3
import hashlib

app = Flask(__name__, static_url_path="/static")
app.secret_key = os.environ['sessionKey']

admin = os.environ['AdminUser']


def setup_chat_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS messages (timestamp TEXT, username TEXT, message TEXT)")
    conn.commit()
    conn.close()

setup_chat_db()

def getChat(isAdmin):
    try:
        with open("message.html", "r") as f:
            template = f.read()
    except FileNotFoundError:
        return "<p>Message template missing.</p>"

    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT timestamp, username, message FROM messages ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()

    # print("[getChat] Messages found:", len(rows))
    # if not rows:
    # print("[getChat] No messages to display.")

    result = ""
    for timestamp, username, message in rows:
        # print("[getChat] Formatting message:", message)
        msg = template
        msg = msg.replace("{username}", username)
        msg = msg.replace("{timestamp}", timestamp)
        msg = msg.replace("{message}", message)
        
        if not isAdmin:
            msg = msg.replace("{admin}", "")
        else:
            msg = msg.replace("{admin}", f'''
            <form action="/delete_chat" method="post" style="display:inline;">
                <input type="hidden" name="timestamp" value="{timestamp}">
                <button type="submit">X</button>
            </form>
            ''')
        result += msg
    # print("[getChat] Final chat HTML length:", len(result))
    # print("[getChat] Final result:", repr(result))
    return result

@app.route("/")
def index():
    try:
        with open("chat.html", "r") as f:
            page = f.read()
    except FileNotFoundError:
        return "<p>Chat page not found.</p>"

    username = session.get("username", "Guest")
    isAdmin = db.get(username, {}).get("userid", "") == admin
    chat_html = getChat(isAdmin)
    # print("[/] Chat HTML preview:", repr(chat_html[:200]))

    page = page.replace("{username}", username)
    page = page.replace("{chats}", chat_html)
    return page

@app.route("/signup")
def signup():
    if session.get('loggedIn'):
        return redirect("/sender")
    try:
        with open("account/signup.html", "r") as f:
            page = f.read()
    except FileNotFoundError:
        page = "<p>Signup page not found.</p>"
    return page

@app.route("/signup", methods=["POST"])
def create():
    if session.get('loggedIn'):
        return redirect("/sender")
    form = request.form
    username = form.get("username", "")
    name = form["name"]
    password = form["password"]

    if username not in db:
        salt = str(random.randint(1000, 9999))
        newPassword = hashlib.sha256((password + salt).encode()).hexdigest()

        
        db[username] = {
            "name": name,
            "password": newPassword,
            "salt": salt,
            "userid": admin if username == admin else "user"
        }
        return redirect("/login")
    else:
        return redirect("/signup")

@app.route("/login")
def login():
    if session.get('loggedIn'):
        return redirect("/sender")
    try:
        with open("account/login.html", "r") as f:
            page = f.read()
    except FileNotFoundError:
        page = "<p>Login page not found.</p>"
    return page

@app.route("/login", methods=["POST"])
def logUser():
    if session.get('loggedIn'):
        return redirect("/sender")
    form = request.form
    username = form.get("username", "")
    password = form["password"]

    if username not in db:
        return redirect("/login")

    user = db[username]
    salt = user["salt"]
    hashedPass = hashlib.sha256((password + salt).encode()).hexdigest()

    if hashedPass == user["password"]:
        session["loggedIn"] = True
        session["username"] = username
        # print(" Logged in as:", username)
        return redirect("/sender")
    else:
        return redirect("/login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/delete_chat", methods=["POST"])
def delete_chat():
    username = session.get("username", "")
    if db.get(username, {}).get("userid", "") != admin:
        return "Unauthorized", 403

    timestamp = request.form.get("timestamp")
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE timestamp = ?", (timestamp,))
    conn.commit()
    conn.close()
    return redirect("/sender")

@app.route("/debug/session")
def debug_session():
    return str(dict(session))

@app.route("/sender")
def sender():
    # print("[/sender] Session:", dict(session))
    try:
        with open("sender.html", "r") as f:
            page = f.read()
    except FileNotFoundError:
        return "<p>Page not found.</p>"
    username = session.get("username", "Guest")
    isAdmin = db.get(username, {}).get("userid", "") == admin
    chat_html = getChat(isAdmin)
    # print("[/sender] Chat HTML preview:", chat_html[:200])
    page = page.replace("{chats}", chat_html)

    keys = db.keys()
    # print("[/sender] Active users:", list(keys))
    return page

@app.route("/add", methods=["POST"])
def add():
    # print("[/add] Session:", dict(session))
    if not session.get("loggedIn"):
        # print("[/add] User not logged in.")
        return redirect("/login")

    username = session.get("username")
    if not username:
        # print("[/add] No username in session.")
        return redirect("/login")

    message = request.form["message"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # print("[/add] Received message:", message)
    # print("[/add] From user:", username, "at", timestamp)

    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (?, ?, ?)", (timestamp, username, message))
    conn.commit()
    conn.close()

    # print("[/add] Message saved.")
    return redirect("/sender")


app.run(host='0.0.0.0', port=81)
