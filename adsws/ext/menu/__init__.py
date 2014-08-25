"""Administration menu."""

from flask.ext.menu import Menu

menu = Menu()


def setup_app(app):
    """Register all subitems to the 'main.admin' menu item."""
    menu.init_app(app)

    @app.before_first_request
    def register_item():
        item = app.extensions['menu'].submenu('main.admin')
        item.register('admin.index', 'Admin')