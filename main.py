from Webapp import create_app
from flask_wtf.csrf import CSRFProtect


app = create_app()
csrf = CSRFProtect(app)

if __name__ == '__main__':
    csrf.init_app(app)
    app.run(host='0.0.0.0', port= 5000, debug=True) 