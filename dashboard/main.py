from flask import Flask
from database import init_db
from routes.dashboard import bp as dashboard_bp
from routes.emails import bp as emails_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(emails_bp)
    return app

if __name__ == '__main__':
    app = create_app()
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
