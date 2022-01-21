"""Administration menu."""

from flask_menu import Menu, register_menu

menu = Menu()


def setup_app(app):
    """Register all subitems to the 'main.admin' menu item."""
    menu.init_app(app)

    @app.before_first_request
    def register_item():
        item = app.extensions['menu'].submenu('main.admin')
