def setup_app(app):
    """
    Extend application template filters with custom filters and fixes.


    """
    from . import config
    app.config.from_object(config)


    for ext in app.config.get('JINJA2_EXTENSIONS', []):
        try:
            app.jinja_env.add_extension(ext)
        except:
            app.logger.error('Problem with loading extension: "%s"' % (ext, ))

    
    return app