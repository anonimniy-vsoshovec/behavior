from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from behaviors.behavior_analysis import calculate_typing_speed
import requests
from config import Config
from extensions import db, migrate
from models import LoginLocation, User, LoginAttempt, UserLocation
from datetime import datetime


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


def get_city_from_ip(ip_address):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        data = response.json()
        return data.get("city", "Unknown")
    except Exception:
        return "Unknown"


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Неверный формат данных"}), 400

        username = data.get("username")
        password = data.get("password")
        behavior_data = data.get("behaviorData", {})

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            return (
                jsonify({"success": False, "error": "Неверный логин или пароль"}),
                401,
            )

        typing_speed = calculate_typing_speed(behavior_data.get("keystrokes", []))

        ip_address = request.remote_addr
        city = get_city_from_ip(ip_address)

        db.session.add(LoginLocation(user_id=user.id, ip_address=ip_address, city=city))

        whitelist = UserLocation.query.filter_by(
            user_id=user.id, whitelisted=True
        ).all()
        whitelist_cities = [loc.city for loc in whitelist]

        if city not in whitelist_cities:

            location = UserLocation.query.filter_by(user_id=user.id, city=city).first()
            if not location:
                location = UserLocation(
                    user_id=user.id, city=city, success_count=1, whitelisted=False
                )
                db.session.add(location)
            else:
                location.success_count += 1
                if location.success_count >= 3:
                    location.whitelisted = True

            db.session.commit()

            session["mfa_username"] = username
            return jsonify({"success": True, "requiresMFA": True})

        login_attempt = LoginAttempt(
            user_id=user.id, typing_speed=typing_speed, timestamp=datetime.utcnow()
        )

        try:
            db.session.add(login_attempt)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"success": False, "error": "Ошибка базы данных"}), 500

        avg_speed = (
            db.session.query(db.func.avg(LoginAttempt.typing_speed))
            .filter(LoginAttempt.user_id == user.id)
            .scalar()
            or typing_speed
        )

        if abs(typing_speed - avg_speed) > 0.2 * avg_speed:
            session["mfa_username"] = username
            return jsonify({"success": True, "requiresMFA": True})

        session["user_id"] = user.id
        return jsonify(
            {"success": True, "requiresMFA": False, "redirect": url_for("dashboard")}
        )

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            data = request.get_json()
            if not data:
                return (
                    jsonify({"success": False, "error": "Неверный формат данных"}),
                    400,
                )

            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            hashed_password = generate_password_hash(password)
            confirm_password = data.get("confirm_password")
            security_question = data.get("security_question")
            security_answer = data.get("security_answer")
            behavior_data = data.get("behaviorData", {})

            if not all(
                [
                    username,
                    email,
                    password,
                    confirm_password,
                    security_question,
                    security_answer,
                ]
            ):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Все поля обязательны для заполнения",
                        }
                    ),
                    400,
                )

            if password != confirm_password:
                return jsonify({"success": False, "error": "Пароли не совпадают"}), 400

            typing_speed = calculate_typing_speed(behavior_data.get("keystrokes", []))

            new_user = User(
                username=username,
                email=email,
                password=hashed_password,
                security_question=security_question,
                security_answer=security_answer,
                typing_speed=typing_speed,
            )

            db.session.add(new_user)
            db.session.commit()

            ip_address = request.remote_addr
            city = get_city_from_ip(ip_address)

            new_location = UserLocation(
                user_id=new_user.id, city=city, success_count=1, whitelisted=False
            )
            db.session.add(new_location)
            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": "Регистрация успешна!",
                    "redirect": url_for("login"),
                }
            )

        except Exception as e:
            db.session.rollback()
            if "Duplicate entry" in str(e):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Пользователь с таким именем или email уже существует",
                        }
                    ),
                    400,
                )
            return (
                jsonify(
                    {"success": False, "error": f"Ошибка сервера при регистрации {e}"}
                ),
                500,
            )

    return render_template("register.html")


@app.route("/verify-mfa", methods=["POST"])
def verify_mfa():

    code = request.json.get("code", "").strip()
    username = session.get("mfa_username")

    if not username:
        return (
            jsonify({"success": False, "error": "Сессия истекла. Повторите вход."}),
            403,
        )

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"success": False, "error": "Пользователь не найден"}), 404

    if code == Config.SECRET_KEY:

        session["user_id"] = user.id
        session.pop("mfa_username", None)

        ip_address = request.remote_addr
        city = get_city_from_ip(ip_address)

        location = UserLocation.query.filter_by(user_id=user.id, city=city).first()
        if location:
            location.success_count += 1
            if location.success_count >= 3:
                location.whitelisted = True
        else:
            db.session.add(UserLocation(user_id=user.id, city=city, success_count=1))

        db.session.commit()

        return jsonify({"success": True, "redirect": url_for("dashboard")})

    return jsonify({"success": False, "error": "Неверный код подтверждения"}), 401


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login"))

    login_locations = (
        LoginLocation.query.filter_by(user_id=user.id)
        .order_by(LoginLocation.timestamp.desc())
        .limit(10)
        .all()
    )
    return render_template("dashboard.html", user=user, login_locations=login_locations)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
