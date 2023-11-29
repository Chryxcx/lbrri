from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, session, send_file, make_response
from flask import jsonify
from flask import current_app
from flask_wtf.csrf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from flask_mail import Message
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import mysql.connector
import json
from mysql.connector import Error
from datetime import datetime
import qrcode
import base64
from io import BytesIO
from functools import wraps


bcrypt = Bcrypt()
csrf = CSRFProtect()
auth = Blueprint('auth', __name__, static_folder='static', static_url_path='/auth/static')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and session['role'] == 'admin':
            return f(*args, **kwargs)
        else:
            flash("You must be an admin to access this page.", "warning")
            return redirect(url_for('auth.login'))
    return decorated_function


def librarian_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and session['role'] == 'librarian':
            return f(*args, **kwargs)
        else:
            flash("You must be a librarian to access this page.", "warning")
            session.clear()
            return redirect(url_for('auth.login'))
    return decorated_function

def both_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and (session['role'] == 'librarian' or session['role'] == 'admin'):
            return f(*args, **kwargs)
        else:
            flash("You must be a librarian to access this page.", "warning")
            session.clear()
            return redirect(url_for('auth.login'))
    return decorated_function


@auth.route('/get_csrf_token', methods=['GET'])
def get_csrf_token():
    csrf_token = generate_csrf()
    return jsonify({'csrf_token': csrf_token})

@auth.route('/login/', methods=['POST', 'GET'])
def login():
    message = ''
    print()
    if request.method == 'POST' and 'usr_name' in request.form and 'usr_pass' in request.form :
        usr = request.form['usr_name']
        password = request.form['usr_pass']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        print(hashed_password)
        try:
            print('connecting')
            # Establish a connection to the MySQL database
            connection = mysql.connector.connect(
                host='localhost',
                database='db_library',
                user='root',
                password='chocolate29'
            )

            if connection.is_connected():
                print("Connected to MySQL database")

                cursor = connection.cursor(dictionary=True)

                cursor.execute('''
                    SELECT u.*, r.name AS role_name
                    FROM userss u
                    JOIN user_roles ur ON u.id = ur.user_id
                    JOIN roles r ON ur.role_id = r.id
                    WHERE u.username = %s
                ''', (usr,))
                user = cursor.fetchone()
                print(user)

                if user and 'password' in user:
                    if bcrypt.check_password_hash(user['password'], password):
                        session['loggedin'] = True
                        session['id'] = user['id']
                        session['email'] = user['email']
                        session['username'] = user['username']
                        session['role'] = user['role_name']

                        role = user['role_name']
                        email = user['email']  # Assuming you want to use the email from the login user
                        username = user['username']  # Assuming you want to use the username from the login user

                        cursor.execute('''
                            INSERT INTO log_cred (role, email, username, time_in)
                            VALUES (%s, %s, %s, NOW())
                        ''', (role, email, username))
                        connection.commit()

                        print('password: ',password)
                        return redirect(url_for('auth.home'))
                    
                    else:
                        message = 'Invalid username or password'
                        return jsonify({'status': 'error', 'message': message})
        except Error as e:
            print("Error while connecting to MySQL", e)
            message = 'Internal server error'
            return jsonify({'status': 'error', 'message': message})


    return render_template("u_login.html", message=message)

@auth.route('/logout')
# @both_required
def logout():
    try:
        if 'email' in session:
            email = session['email']

            logout_time(email)

        session.clear()
        return redirect(url_for('auth.login'))
    except Exception as e:
        print("Exception during logout:", e)


def logout_time(email):
    try:
        db = current_app.get_db()
        cursor = db.cursor()
        # Update the time_out column in the log_cred table
        query = "UPDATE log_cred SET time_out = %s WHERE email = %s AND time_out IS NULL"
        cursor.execute(query, (datetime.now(), email))
        db.commit()
    except Exception as e:
        print("Exception during update_logout_time:", e)
    finally:
        cursor.close()

@auth.route('/<shelf_id>', methods=['GET', 'POST'])
def view_shelf(shelf_id):
    try:
        db = current_app.get_db()
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM {shelf_id}")
        result = cursor.fetchall()
        qr_values = [a[1] for a in result]
        return jsonify(qr_values)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)})


@auth.route('/')
def home():
    return render_template("home.html", boolean=True)

@auth.route('/create_librarian', methods=['GET', 'POST'])
def create_acc():
    db = current_app.get_db()
    if request.method == 'POST':
        first_name = request.form.get('f_signup')
        last_name = request.form.get('l_signup')
        email = request.form.get('l_email1')
        phn = request.form.get('contact')
        usrnm = request.form.get('u_signup')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('Name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            hashed_password = generate_password_hash(password1, method='sha256')
            cursor.execute("INSERT INTO users (first_name, last_name, email, phn_num, username, password) VALUES (%s, %s, %s, %s, %s, %s)",
                           (first_name, last_name, email, phn, hashed_password))
            db.commit()
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))

        cursor.close()

    return render_template("create_acc.html")


@auth.route('/profile')
# @both_required
def profile():
    # if 'id' not in session:
    #     return "Unauthorized access"  # Unauthorized access
    
    # db = current_app.get_db()
    # user_id = session['id']
    # cursor = db.cursor()
    
    # # Fetch user data from the database
    # cursor.execute("SELECT username, email, phn_num, role FROM accounts_info WHERE id = %s", (user_id,))
    # user = cursor.fetchone()
    # print(user)
    
    # cursor.close()
    
    # if user is None:
    #     return "user not found"  # User not found
    return render_template('profile.html')


@auth.route('/borrowers_list')
# @both_required
def borrowers():
    try:
        db = current_app.get_db()
        cursor = db.cursor()
        print(f'cursor: {cursor}')

        cursor.execute('SELECT COALESCE(first_name, last_name) AS Full_Name, phone_number, email FROM borrower_list')
        data = cursor.fetchall()
        print('data: ', data)

        return render_template('borrowers.html', data=data)
    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})


@auth.route('/borrowed_record')
def borrowed_record():
    try:
        db = current_app.get_db()
        cursor = db.cursor()
        
        query = "SELECT * FROM bb_rec"
        cursor.execute(query,)
        data = cursor.fetchall()
        

        return render_template('borrowed.html', data=data)
    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})
    
@auth.route('/borrower_list/<full_name>')
def generate_qr(full_name):
    # Create a QR code with the full name
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )
    qr.add_data(full_name)
    qr.make(fit=True)

    # Create an image from the QR code
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image to a BytesIO object
    img_stream = BytesIO()
    img.save(img_stream)
    img_stream.seek(0)

    # Create a Flask response containing the image
    response = make_response(send_file(img_stream, mimetype='image/png'))
    response.headers['Content-Disposition'] = f'inline; filename={full_name}_qr.png'

    return response


@auth.route('/inventory')
# @both_required
def inventory():
    try:
        db = current_app.get_db()
        cursor = db.cursor()

        cursor.execute('SELECT * FROM categories')
        category_name = cursor.fetchall()

        cursor.execute('SELECT * FROM shelves')
        shelf_num = cursor.fetchall()

        cursor.execute('SELECT * FROM gen_books')
        gen_books = cursor.fetchall()

        shelf = request.args.get('shelf_id')
        category = request.args.get('catalog')
        search_query = request.args.get('search_query')

        columns = []

        if shelf is None:
            return render_template('inventory.html', category_name=category_name, shelf_num=shelf_num, gen_books=gen_books, columns=columns)

        if category == 'all' and shelf == 'all':
            query = "SELECT book_id, category, isbn, title, publisher, year_published, quantity, availability FROM gen_books"
            cursor.execute(query)
        elif category == 'all':
            query = f"SELECT book_id, category, isbn, title, publisher, year_published FROM {shelf}"
            cursor.execute(query)
        elif shelf == 'all':
            query = f"SELECT book_id, category, isbn, title, publisher, year_published FROM gen_books WHERE category = %s"
            cursor.execute(query, (category,))
        else:
            query = f"SELECT book_id, category, isbn, title, publisher, year_published FROM {shelf} WHERE category = %s"
            cursor.execute(query, (category,))

        data = cursor.fetchall()

        data_list = []

        for row in data:
            if shelf == "all":
                data_item = {
                    'book_id': row[0],
                    'category': row[1],
                    'isbn': row[2],
                    'title': row[3],
                    'publisher': row[4],
                    'year_published': row[5],
                    'quantity': row[6],
                    'availability': row[7]
                }
            else:
                data_item = {
                    'book_id': row[0],
                    'category': row[1],
                    'isbn': row[2],
                    'title': row[3],
                    'publisher': row[4],
                    'year_published': row[5]
                }

            data_list.append(data_item)

        filtered_data = data_list

        if search_query:
            search_query = f"%{search_query}%"  # Add wildcard characters for a partial search
            filtered_data = [item for item in data_list if
                             search_query in item['title'].lower() or search_query in item['publisher'].lower()]

        return jsonify(filtered_data)

    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})
    
@auth.route('/<shelf>/<row>', methods=['GET','POST'])
def shelf_row(shelf, row):

    try:
        db = current_app.get_db()
        cursor = db.cursor()
        print(f'cursor: {cursor}')

        query = f"SELECT book_loc FROM {shelf} WHERE book_row = %s"
        cursor.execute(query,(row,))  
        result = cursor.fetchall()

        book_locs = [item[0] for item in result]

        print('result', book_locs)

        # columns = [column[0] for column in cursor.description]  # Get column names from cursor description
        # result = [dict(zip(columns, row)) for row in category_name]

        return jsonify(book_locs)

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)})

@auth.route('/inventory/<shelf>', methods=['GET','POST'])
def per_shelf(shelf):
    shelf = request.args.get('shelf_id')
    print("Selected shelf:", shelf)
    category = request.args.get('catalog')
    print("Category:", category)
    search_query = request.args.get('search_query')
    print("Search:", search_query)

    try:
        db = current_app.get_db()
        cursor = db.cursor()
        print(f'cursor: {cursor}')

        cursor.execute('SELECT * FROM categories')
        category_name = cursor.fetchall()
        print(category_name)

        cursor.execute('SELECT * FROM shelves')
        shelf_num = cursor.fetchall()

        cursor.execute('SELECT * FROM gen_books')
        gen_books = cursor.fetchall()

        columns = []

        if shelf is None:
            return render_template('inventory.html', category_name=category_name, shelf_num=shelf_num, gen_books=gen_books, columns=columns)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)})


@auth.route('/forgot_pass', methods=['GET', 'POST'])
def forgot_pass():
    if request.method == 'POST':
        email = request.form['fp_email']

        # Get database connection
        db = current_app.get_db()
        cursor = db.cursor()

        # Check if the user exists in the database
        cursor.execute('SELECT * FROM accounts_info WHERE email = %s', (email,))  # Replace 'user_table' with your actual user table name
        user = cursor.fetchone()

        if not user:
            flash('No account found with that email address.', 'error')
            return render_template('forgot_password.html')

        with current_app.app_context():
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

            try:
                msg = Message('Password Reset Request',
                              sender=current_app.config['MAIL_DEFAULT_SENDER'],
                              recipients=[email])
                link = url_for('auth.reset_token', token=token, _external=True)
                msg.body = f'Your link to reset your password is {link}'
                current_app.mail.send(msg)
            except Exception as e:
                current_app.logger.error(f'Error sending email: {e}')
                flash('An error occurred while sending the reset email. Please try again.', 'error')
                return render_template('forgot_password.html')

            flash('A password reset email has been sent if the email is registered.', 'success')
            return render_template('check_email.html')

    return render_template('forgot_password.html')

@auth.route('/reset/<token>', methods=['GET', 'POST'])
def reset_token(token):
    db = current_app.get_db()
    cursor = db.cursor()
    try:
        with current_app.app_context():
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            email = s.loads(token, salt=current_app.config['SECURITY_PASSWORD_SALT'], max_age=3600)
            print(email)
            # Check if the user exists in the database (Add this part)
        if request.method == 'POST':
                password = request.form['password']
                confirm_password = request.form['confirm_password']

                # Add password validation logic as needed
                if password != confirm_password:
                    flash('Passwords do not match.', 'error')
                    return redirect(url_for('auth.reset_token', token=token))

                # Set the new password and save to the database
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                print(hashed_password)
                cursor.execute("UPDATE accounts_info SET password = %s WHERE email = %s", (hashed_password, email))
                cursor.execute("UPDATE userss SET password = %s WHERE email = %s", (hashed_password, email))
                db.commit()
                print(db)

                flash('Password reset successfully. You can now log in with your new password.', 'success')
                return redirect(url_for('auth.login'))

    except SignatureExpired:
        flash('The token is expired!', 'error')
        return redirect(url_for('auth.forgot_pass'))
    except Exception as e:
        flash('Invalid or expired token.', 'error')
        return redirect(url_for('auth.forgot_pass'))

    return render_template('reset_token.html', token=token)


@auth.route('/qr_codes/<image_id>')
def qr_codes(image_id):
    try:
        image_path = f"Webapp/static/qr_codes/{image_id}.png"
        with open(image_path, "rb") as image_file:  
            response = Response(image_file.read(), content_type="image/png")
            return response
    except FileNotFoundError:
        return "Image not found", 404



@auth.route('/insert', methods=['GET', 'POST'])
# @both_required
def insert():
    db = current_app.get_db()
    cursor = db.cursor()
    cursor1 = db.cursor()
    cursor2 = db.cursor()
    cursor.execute('SELECT * FROM categories')
    category_name = cursor.fetchall()
    print(category_name)
    cursor1.execute('SELECT * FROM shelves')
    shelf = cursor1.fetchall()
    cursor2.execute('SELECT * FROM book_row')
    b_rows = cursor2.fetchall()

    if request.method == "POST":
        table = request.form.get('b_shelves')
        cate = request.form.get('b_cate')
        isbn = request.form.get('isbn')
        title = request.form.get('b_title')
        publisher = request.form.get('b_publisher')
        year = int(request.form.get('b_year'))
        row = request.form.get('num_row')
        print(row)

        try:
            username = session.get('username')
            role = session.get('role')

            query_get_shelf_value = "SELECT shelf_value FROM shelves WHERE shelf_name = %s"
            cursor.execute(query_get_shelf_value, (table,))
            shelf_value = cursor.fetchone()[0]
            print('shelf value: ', shelf_value)

            query_book_row = "SELECT row_value FROM book_row WHERE id = %s"
            cursor.execute(query_book_row, (row,))
            num_row = cursor.fetchone()[0]
            print('Numrow: ', num_row)

            query_categ = "SELECT category_prefix FROM categories WHERE category_name = %s"
            cursor.execute(query_categ, (cate,))
            c_id = cursor.fetchone()[0]
            print('category_id: ', c_id)

            query = "INSERT INTO gen_books (book_row, category, isbn, title, publisher, year_published, quantity) VALUES (%s, %s, %s, %s, %s, %s, 1)"
            cursor.execute(query, (num_row, cate, isbn, title, publisher, year))
            s_id = cursor.lastrowid

            query1 = f"INSERT INTO {table} (book_row, category, isbn, title, publisher, year_published) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(query1, (num_row, cate, isbn, title, publisher, year))
            s_id1 = cursor.lastrowid

            query2 = "INSERT INTO insert_record (book_row, category, isbn, title, publisher, year_published, librarian, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query2, (num_row, cate, isbn, title, publisher, year, username, role))
            s_id2 = cursor.lastrowid

            p_id = f"{shelf_value}{num_row}"
            cat_id = f"{c_id}{s_id}"
            cat_id1 = f"{c_id}{s_id1}"
            bookloc_data = f"{p_id} {cat_id1}"
            query3 = "UPDATE gen_books SET book_id = %s, categ_id = %s, book_loc = %s WHERE id = %s"
            cursor.execute(query3, (p_id, cat_id, bookloc_data, s_id))
            print(query3)

            p_id1 = f"{shelf_value}{num_row}"
           
    

            query4 = f"UPDATE {table} SET book_id = %s, categ_id = %s, book_loc = %s WHERE id = %s"
            cursor.execute(query4, (p_id1, cat_id1, bookloc_data, s_id1))
            print(query4)

            p_id2 = f"{shelf_value}{num_row}"
            cat_id2 = f"{c_id}{s_id2}"
        

            query5 = "UPDATE insert_record SET book_id = %s, categ_id = %s, book_loc = %s WHERE id = %s"
            cursor.execute(query5, (p_id2, cat_id2, bookloc_data, s_id2))
            print('insert record: ',query5)

            db.commit()

            cursor.execute("SELECT id, quantity FROM gen_books WHERE book_id = %s", (p_id,))
            inventory_record = cursor.fetchall()
            print('inventor_record: ', inventory_record)

            qr_data = f"{p_id} {cat_id1}"
            print(qr_data)
            qr_data_encoded = qr_data.encode('utf-8')
            print(qr_data_encoded)
            qr_image_base64, image_path = current_app.generate_qr_code(qr_data_encoded, str(qr_data))

            cursor.close()
            db.close()

            flash('Data successfully inserted!', 'success')

            return jsonify({'success': True, 'qr_image_base64': qr_image_base64, 'image_path': image_path, 'qrCodeID': qr_data})

        except Exception as e:
            print("Exception:", e)
            db.rollback()
            cursor.close()
            db.close()

            flash('Error inserting data into the database', 'error')
            return jsonify({'success': False, 'error': 'Error inserting data into the database'})

    return render_template("insert.html", qr_image_base64=None, category_name=category_name, shelf=shelf, b_rows=b_rows)


@auth.route('/log_cred')
def log_cred():
    db = current_app.get_db()
    cursor = db.cursor()
    search_query = request.args.get('search_query')

    query = "SELECT role, email, username, time_in, time_out from log_cred"
    cursor.execute(query,)
    result = cursor.fetchall()
    print(result)

    filtered_data = result

    if search_query:
        search_query = f"%{search_query}%"  # Add wildcard characters for a partial search
        filtered_data = [item for item in filtered_data if
                            search_query in item['username'].lower() or search_query in item['time_in'].lower()]
    return render_template('login_credentials.html', result=result)