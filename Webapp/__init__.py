from flask import Flask
from flask_wtf import CSRFProtect
import mysql.connector
from flask_login import LoginManager, UserMixin
from flask_bootstrap import Bootstrap
from flask_bcrypt import Bcrypt
import qrcode
from io import BytesIO
import base64



def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='/auth/static')
    csrf = CSRFProtect(app)
    bcrypt = Bcrypt(app)
    app.bcrypt = bcrypt
    Bootstrap(app)
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'chocolate29'
    app.config['MYSQL_DB'] = 'db_library'
    app.config['STATIC_FOLDER'] = 'path/to/static'
    app.config['SECRET_KEY'] = 'jdfhajksdfjkasdlfjdasklfjklj'
    
    app.mysql = mysql.connector

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.admin_login'

    @login_manager.user_loader
    def load_user(user_id):
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE id = %s", (user_id,))
        user_record = cursor.fetchone()
        cursor.close()
        db.close()

        if user_record:
            user = UserMixin()
            user.id = user_record['id']
            # Add other user properties from record as needed
            return user
        return None

    def get_db():
        db = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            auth_plugin='mysql_native_password'
        )
        return db
   
    app.get_db = get_db 
    
    def generate_qr_code(data, filename):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        img_stream = BytesIO()
        qr_img.save(img_stream, format="PNG")
        img_stream.seek(0)
        image_path = f"Webapp/static/qr_codes/{filename}.png"
        with open(image_path, "wb") as image_file:
            image_file.write(img_stream.read())
        img_base64 = base64.b64encode(img_stream.getvalue()).decode()
        return img_base64, image_path
    
    app.generate_qr_code = generate_qr_code 
    
    
    from .view import view
    from .auth import auth
    
    app.register_blueprint(view,url_prefix='/')
    app.register_blueprint(auth,url_prefix='/')
    
    
    
    return app




    