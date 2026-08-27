from pathlib import Path


def test_user_templates_have_password_visibility_controls():
    templates = ("login.html", "signup.html", "my-page.html")

    for template in templates:
        assert "data-password-toggle" in Path("static/templates", template).read_text()


def test_documentation_covers_refresh_cookie():
    documentation = Path("docs/api/user-api.md").read_text()

    assert "HttpOnly" in documentation
    assert "/api/v1/users/refresh" in documentation
