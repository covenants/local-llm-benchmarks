"""Pytest configuration for the URL shortener acceptance suite."""


def pytest_addoption(parser):
    parser.addoption(
        "--app", action="store", required=True,
        help="Path to the app.py submission under test",
    )
