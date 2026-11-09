import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
# Обмеження розміру тіла запиту (16 КБ): більший запит дає відповідь 413
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

LABELS = {
    "name": "Ім’я",
    "email": "Електронна адреса",
    "quantity": "Кількість учасників",
    "topic": "Тема участі",
}
LIMITS = {"name": 80, "email": 254, "quantity": 3, "topic": 200}

# Файли зберігаються в instance/, поза каталогом static
SUBMISSIONS = Path(app.instance_path) / "submissions"


@app.route("/")
def index():
    return "<h1>Вітаємо у Flask!</h1><p><a href='/form'>Реєстрація на захід</a></p>"


@app.route("/info")
def info():
    return "Це інформаційний маршрут Flask.", 200, {
        "Content-Type": "text/plain; charset=utf-8"
    }


@app.route("/hello/<name>")
def hello(name):
    return render_template("hello.html.j2", name=name)


def validate(values):
    """Серверна валідація. Повертає словник {поле: повідомлення}."""
    errors = {}

    # 1. Заповненість, довжина, один рядок
    for field in LABELS:
        value = values[field]
        if not value:
            errors[field] = "Поле є обов’язковим."
        elif len(value) > LIMITS[field]:
            errors[field] = f"Дозволено не більше {LIMITS[field]} символів."
        elif any(char in value for char in "\r\n"):
            errors[field] = "Введіть значення одним рядком."

    # 2. Формат електронної адреси
    if "email" not in errors:
        if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]) is None:
            errors["email"] = "Перевірте формат електронної адреси."

    # 3. Число: лише цифри, потім діапазон
    if "quantity" not in errors:
        number = values["quantity"]
        if re.fullmatch(r"[0-9]+", number) is None:
            errors["quantity"] = "Використовуйте лише цифри від 0 до 9."
        elif not 1 <= int(number) <= 100:
            errors["quantity"] = "Допустимий діапазон: від 1 до 100."

    return errors


def save_submission(values):
    """Записує відправлення в окремий UTF-8 файл і повертає його ім’я."""
    SUBMISSIONS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_%f")
    filename = f"submission_{stamp}_{uuid4().hex}.txt"
    # режим "x" забороняє перезапис наявного файлу
    with (SUBMISSIONS / filename).open("x", encoding="utf-8") as output:
        for field, label in LABELS.items():
            output.write(f"{label}: {values[field]}\n")
    return filename


@app.route("/form", methods=["GET", "POST"])
def form():
    values = {field: "" for field in LABELS}
    errors = {}

    if request.method == "POST":
        values = {
            field: request.form.get(field, "").strip() for field in LABELS
        }
        errors = validate(values)

        if not errors:
            try:
                filename = save_submission(values)
            except OSError:
                app.logger.exception("Не вдалося зберегти відправлення")
                errors["_storage"] = "Не вдалося зберегти дані. Спробуйте пізніше."
                return render_template(
                    "form.html", values=values, errors=errors, labels=LABELS
                ), 500
            # Post/Redirect/Get
            return redirect(url_for("result", filename=filename, **values), code=303)

    status = 422 if errors else 200
    return render_template(
        "form.html", values=values, errors=errors, labels=LABELS
    ), status


@app.get("/result")
def result():
    values = {field: request.args.get(field, "") for field in LABELS}
    filename = request.args.get("filename", "")
    return render_template(
        "result.html", values=values, filename=filename, labels=LABELS
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
