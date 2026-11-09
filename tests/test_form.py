"""Автоматичні перевірки через Flask test_client(). Запуск: python -m pytest або python tests/test_form.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as appmod  # noqa: E402

appmod.SUBMISSIONS = Path(tempfile.mkdtemp()) / "submissions"
client = appmod.app.test_client()
GOOD = {"name": "Марія", "email": "maria@example.com", "quantity": "2", "topic": "Вебформи"}


def count():
    return len(list(appmod.SUBMISSIONS.glob("*.txt"))) if appmod.SUBMISSIONS.exists() else 0


def post(**override):
    return client.post("/form", data={**GOOD, **override})


def test_get_empty_form():
    r = client.get("/form")
    assert r.status_code == 200 and 'method="post"' in r.get_data(as_text=True)


def test_success_prg_and_file():
    before = count()
    r = post()
    assert r.status_code == 303 and "/result?" in r.headers["Location"]
    assert count() == before + 1
    page = client.get(r.headers["Location"])
    assert page.status_code == 200 and "Марія" in page.get_data(as_text=True)
    assert count() == before + 1  # GET /result нічого не пише


def test_empty_fields_and_no_file():
    before = count()
    r = client.post("/form", data={"name": " ", "email": "wrong", "quantity": "abc"})
    html = r.get_data(as_text=True)
    assert r.status_code == 422 and count() == before
    for label in ("Ім’я", "Електронна адреса", "Кількість учасників", "Тема участі"):
        assert label in html


def test_quantity_bounds():
    for bad in ("0", "101", "-1", "1.5", "abc", "1000", "12345678901234567890"):
        before = count()
        assert post(quantity=bad).status_code == 422, bad
        assert count() == before
    for good in ("1", "100"):
        assert post(quantity=good).status_code == 303, good


def test_escaping_and_special_chars():
    r = post(name="<b>Марія</b> & Ко+", topic="a&b +c <script>")
    assert r.status_code == 303
    html = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "&lt;b&gt;Марія&lt;/b&gt;" in html and "<b>Марія</b>" not in html
    # значення зберігаються у формі після помилки
    r = post(name="<i>x</i>", email="bad")
    assert r.status_code == 422 and "&lt;i&gt;x&lt;/i&gt;" in r.get_data(as_text=True)


def test_two_posts_two_files():
    before = count()
    post(); post()
    assert count() == before + 2


def test_storage_failure():
    old = appmod.SUBMISSIONS
    blocker = Path(tempfile.mkdtemp()) / "plain_file"
    blocker.write_text("x")
    appmod.SUBMISSIONS = blocker / "sub"
    try:
        r = post()
        html = r.get_data(as_text=True)
        assert r.status_code == 500 and "Location" not in r.headers
        assert "Марія" in html and "Не вдалося зберегти" in html
    finally:
        appmod.SUBMISSIONS = old


def test_too_large_body():
    assert client.post("/form", data={**GOOD, "topic": "x" * 20000}).status_code == 413


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
