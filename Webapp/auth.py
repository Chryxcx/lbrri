from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, session, send_file, make_response
from flask import jsonify
from flask import current_app
from flask_wtf.csrf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import hashlib
import mysql.connector
import json
from mysql.connector import Error
import qrcode
from io import BytesIO
from functools import wraps


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


def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and session['role'] == 'staff':
            return f(*args, **kwargs)
        else:
            flash("You must be an admin to access this page.", "warning")
            return redirect(url_for('auth.login'))
    return decorated_function

def al_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and (session['role'] == 'librarian' or session['role'] == 'admin'):
            return f(*args, **kwargs)
        else:
            flash("You must be a librarian to access this page.", "warning")
            session.clear()
            return redirect(url_for('auth.login'))
    return decorated_function

def both_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session and 'role' in session and (session['role'] == 'librarian' or session['role'] == 'admin' or session['role'] == 'staff'):
            return f(*args, **kwargs)
        else:
            flash("You must be a librarian or admin to access this page.", "warning")
            session.clear()
            return redirect(url_for('auth.login'))
    return decorated_function

@auth.route('/login/', methods=['POST', 'GET'])
def login():
    if request.method == 'POST' and 'usr_name' in request.form and 'usr_pass' in request.form:
        usr = request.form['usr_name']
        password = request.form['usr_pass']
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        try:
            # Establish a connection to the MySQL database
            connection = mysql.connector.connect(
                host='localhost',
                database='db_library',
                user='root',
                password='chocolate29'
            )

            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SET time_zone = '+08:00';")


                cursor.execute('''
                    SELECT u.*, r.name AS role_name
                    FROM userss u
                    JOIN user_roles ur ON u.id = ur.user_id
                    JOIN roles r ON ur.role_id = r.id
                    WHERE u.username = %s
                ''', (usr,))
                user = cursor.fetchone()

                if user and 'password' in user:
                    if user['password'] == hashed_password:
                        session['loggedin'] = True
                        session['id'] = user['id']
                        session['email'] = user['email']
                        session['username'] = user['username']
                        session['role'] = user['role_name']

                        cursor.execute('''
                            SELECT phn_num
                            FROM accounts_info
                            WHERE id = %s
                        ''', (user['id'],))
                        user_contact = cursor.fetchone()

                        # Check if 'phn_num' is present in the result
                        if user_contact and 'phn_num' in user_contact:
                            session['phn_num'] = user_contact['phn_num']
                        else:
                            session['phn_num'] = None

                        role = user['role_name']
                        email = user['email']
                        username = user['username']

                        cursor.execute('''
                            INSERT INTO log_cred (role, email, username, time_in)
                            VALUES (%s, %s, %s, NOW())
                        ''', (role, email, username))
                        connection.commit()

                        return redirect(url_for('auth.home'))

                    else:
                        flash('Invalid username or password', 'error')

            flash('Invalid username or password', 'error')

        except Error as e:
            print("Error while connecting to MySQL", e)
            flash('Internal server error', 'error')

    return render_template("u_login.html")

@auth.route('/logout')
@both_required
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


        with db.cursor(dictionary=True) as cursor:
            cursor.execute("SET time_zone = '+08:00';")
            query = "UPDATE log_cred SET time_out = NOW() WHERE email = %s AND time_out IS NULL"
            cursor.execute(query, (email,))

        # Commit the changes
        db.commit()

    except Exception as e:
        print("Exception during update_logout_time:", e)
    finally:
        # Ensure the cursor is closed
        if cursor:
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

@auth.route('/create_borrower', methods=['GET', 'POST'])
def create_borrower():
    db = current_app.get_db()
    print('connect::',db)
    if request.method == 'POST':
        first_name = request.form.get('l_ffname')
        print(first_name)
        last_name = request.form.get('l_llname')
        print(last_name)
        email = request.form.get('emailll')
        print(email)
        phn = request.form.get('l_contact')
        print(phn)

        if email_exists(db, email):
            flash('Email already exists.', category='error')
            return render_template("su_borrower.html")

        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO borrower_list (first_name, last_name, phone_number, email) VALUES (%s, %s, %s, %s)",
                        (first_name, last_name, phn, email))
            print('insert: ', cursor)
            db.commit()

            qr_data = f"{first_name} {last_name}"
            qr_data_encoded = qr_data.encode('utf-8')
            qr_image_base64, qr_image_path = current_app.generate_qr_code1(qr_data_encoded, qr_data)

            flash('Account created successfully!', category='success')
            # return jsonify({'success': True, 'qr_image_base64': qr_image_base64, 'image_path': qr_image_path, 'qrCodeID': qr_data})
            return render_template("su_borrower.html", qr_image_base64=qr_image_base64)
        except Exception as e:
            print(f"Error: {str(e)}")
            db.rollback()
            return jsonify({'success': False, 'error': 'Database error'})

    return render_template("su_borrower.html", qr_image_base64=None)

def email_exists(db, email):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM borrower_list WHERE email = %s", (email,))
    count = cursor.fetchone()[0]
    return count > 0



@auth.route('/create_librarian', methods=['GET', 'POST'])
@admin_required
def create_librarian():
    db = current_app.get_db()
    if request.method == 'POST':
        first_name = request.form.get('l_ffname')
        last_name = request.form.get('l_llname')
        email = request.form.get('emailll')
        phn = request.form.get('l_contact')
        usrnm = request.form.get('l_usrnm')
        role = request.form.get('role')
        password1 = request.form.get('lib_pass1')
        password2 = request.form.get('lib_pass2')
        print(first_name)
        print(last_name)
        print(email)
        print(phn)
        print(usrnm)

        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM accounts_info WHERE email = %s", (email,))
            user = cursor.fetchone()
            print(user)

            if user:
                flash('Email already exists.', category='error')
            # elif email is None or len(email) < 4:
            #     flash('Email must be greater than 3 characters.', category='error')
            elif len(first_name) < 2:
                flash('Name must be greater than 1 character.', category='error')
            elif password1 != password2:
                flash('Passwords don\'t match.', category='error')
            elif len(password1) < 7:
                flash('Password must be at least 7 characters.', category='error')
            else:
                hashed_password = hashlib.sha256(password1.encode('utf-8')).hexdigest()
                cursor.execute("INSERT INTO accounts_info (first_name, last_name, email, phn_num, username, password, role) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (first_name, last_name, email, phn, usrnm, hashed_password, role))
                usr_id = cursor.lastrowid
                print(usr_id)
                cursor.execute("INSERT INTO userss (email, username, password) VALUES (%s, %s, %s)",
                            (email, usrnm, hashed_password))
                cursor.execute("INSERT INTO user_roles (user_id, role_id) VALUES ( %s, %s)",
                            (usr_id, 2))

                db.commit()

                qr_data = f"{usrnm}"
                qr_data_encoded = qr_data.encode('utf-8')
                qr_image_base64, qr_image_path = current_app.generate_qr_code2(qr_data_encoded, qr_data)
                flash('Account created!', category='success')
                # return jsonify({'success': True, 'qr_image_base64': qr_image_base64, 'image_path': qr_image_path, 'qrCodeID': qr_data})
                return render_template("create_librarian.html")
            cursor.close()

        except Exception as e:
            print(f"Error: {str(e)}")
            db.rollback()
            return jsonify({'success': False, 'error': 'Database error'})
    return render_template("create_librarian.html")


@auth.route('/profile')
@both_required
def profile():
    # if 'id' not in session:
    #     return "Unauthorized access"  # Unauthorized access

    db = current_app.get_db()
    user_id = session['id']
    cursor = db.cursor()

    # Fetch user data from the database
    cursor.execute("SELECT username FROM accounts_info WHERE id = %s", (user_id,))
    user = cursor.fetchone()[0]
    print(user)

    cursor.close()

    if user is None:
        return "User not found"  # User not found

    # Generate a QR code for the user data
    user_data = f"{user}"
    print(user_data)
    qr_data_encoded = user_data.encode('utf-8')
    qr_code_image, qr_image_path = current_app.generate_qr_code3(qr_data_encoded, user_data)

    # Pass data to the template
    return render_template('profile.html', user_data=user_data, qr_code_image=qr_code_image, qr_image_path=qr_image_path)


@auth.route('/borrowers_list')
@both_required
def borrowers():
    try:
        db = current_app.get_db()
        cursor = db.cursor()
        search_query = request.args.get('search_query')

        base_query = 'SELECT CONCAT_WS(" ", `first_name`, `last_name`) AS `Full_Name`, `phone_number`, `email` FROM `borrower_list`'

        # Check if a search query is provided and append a WHERE clause accordingly
        if search_query:
            search_query = f"%{search_query}%"  # Add wildcard characters for a partial search
            query = f"{base_query} WHERE `first_name` LIKE %s OR `last_name` LIKE %s OR `phone_number` LIKE %s OR `email` LIKE %s"

            # Execute the query with the search parameters
            cursor.execute(query, (search_query, search_query, search_query, search_query))
        else:
            # Execute the query without search parameters
            cursor.execute(base_query)

        data = [{'Full_Name': row[0], 'phone_number': row[1], 'email': row[2]} for row in cursor.fetchall()]
        print(data)

        return render_template('borrowers.html', data=data)
    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})

@auth.route('/borrowed_record')
@both_required
def borrowed_record():
    try:
        db = current_app.get_db()
        cursor = db.cursor()

        query = "SELECT book_id, staff_librarian, borrower, date_borrowed, date_return, status FROM borrowed_books"
        cursor.execute(query)

        # Fetch the data as dictionaries
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        print(data)

        filtered_data = data

        search_query = request.args.get('search_query')
        if search_query:
            search_query = f"%{search_query}%"  # Add wildcard characters for a partial search
            filtered_data = [item for item in filtered_data if
                             search_query in item['staff_librarian'].lower() or
                             search_query in item['status'].lower() or
                             search_query in item['borrower'].lower() or
                             search_query in item['date_borrowed'].lower() or
                             search_query in item['date_return'].lower()]

        return render_template('borrowed.html', data=filtered_data)

    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})

@auth.route('/books_inserted')
@both_required
def books_inserted():
    db = current_app.get_db()
    cursor = db.cursor()
    search_query = request.args.get('search_query')

    query = "SELECT book_loc, category, isbn, title, publisher, year_published, librarian, role, time_inserted FROM insert_record"
    cursor.execute(query)
    data = [{'book_loc': row[0], 'category': row[1], 'isbn': row[2], 'title': row[3], 'publisher':row[4], 'year_published':row[5], 'librarian':row[6], 'role':row[7], 'time_inserted':row[8]} for row in cursor.fetchall()]
    print(data)

    filtered_data = data

    if search_query:
        search_query = f"%{search_query}%"
        filtered_data = [item for item in filtered_data if
                        search_query in str(item['book_loc']).lower() or
                        search_query in str(item['category']).lower() or
                        search_query in str(item['title']).lower() or
                        search_query in str(item['publisher']).lower() or
                        search_query in str(item['year_published']).lower() or
                        search_query in str(item['librarian']).lower()]

    return render_template('insert_record.html', data=filtered_data)


@auth.route('/borrower_list/<Full_Name>')
@admin_required
def generate_qr(Full_Name):
    # Create a QR code with the full name
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        border=0,
    )
    qr.add_data(Full_Name)
    qr.make(fit=True)

    # Create an image from the QR code
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image to a BytesIO object
    img_stream = BytesIO()
    img.save(img_stream)
    img_stream.seek(0)

    # Create a Flask response containing the image
    response = make_response(send_file(img_stream, mimetype='image/png'))
    response.headers['Content-Disposition'] = f'inline; filename={Full_Name}_qr.png'

    return response


@auth.route('/inventory')
@both_required
def inventory():
    try:
        db = current_app.get_db()
        cursor = db.cursor()

        cursor.execute('SELECT * FROM categories')
        category_name = cursor.fetchall()
        print(category_name)

        cursor.execute('SELECT * FROM shelves')
        shelf_num = cursor.fetchall()

        cursor.execute('SELECT * FROM gen_books')
        gen_books = cursor.fetchall()

        shelf = request.args.get('shelf_id')
        category = request.args.get('cate_id')
        search_query = request.args.get('search_query')
        print('shelf:', shelf)
        print('category:', category)

        columns = []

        if shelf is None:
            return render_template('inventory.html', category_name=category_name, shelf_num=shelf_num, gen_books=gen_books, columns=columns)

        if category == 'all' and shelf == 'all':
            query = "SELECT book_loc, category, isbn, title, author, publisher, year_published, quantity, availability FROM gen_books"
            cursor.execute(query)
        elif category == 'all':
            query = f"SELECT book_loc, category, isbn, title, author, publisher, year_published FROM {shelf}"
            cursor.execute(query)
        elif shelf == 'all':
            query = "SELECT book_loc, category, isbn, title, author, publisher, year_published, quantity, availability FROM gen_books WHERE category = %s"
            cursor.execute(query, (category,))

        else:
            query = f"SELECT book_loc, category, isbn, title, author, publisher, year_published FROM {shelf} WHERE category = %s"
            cursor.execute(query, (category,))

        data = cursor.fetchall()
        print('data:',  data)
        data_list = []

        for row in data:
            if shelf == "all":
                data_item = {
                    'book_loc': row[0],
                    'category': row[1],
                    'isbn': row[2],
                    'title': row[3],
                    'author': row[4],
                    'publisher': row[5],
                    'year_published': row[6],
                    'quantity': row[7],
                }
            else:
                data_item = {
                    'book_loc': row[0],
                    'category': row[1],
                    'isbn': row[2],
                    'title': row[3],
                    'author': row[4],
                    'publisher': row[5],
                    'year_published': row[6]
                }

            data_list.append(data_item)

        filtered_data = data_list

        if search_query:
            search_query = f"%{search_query}%"  # Add wildcard characters for a partial search
            filtered_data = [item for item in data_list if
                             search_query in item['category'].lower() or search_query in item['isbn'].lower() or search_query in item['title'].lower() or search_query in item['author'].lower() or search_query in item['publisher'].lower() or search_query in item['year_published'].lower()]

        return jsonify(filtered_data)

    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})

@auth.route('/<shelf>/<row>', methods=['GET','POST'])
# @admin_required
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
    category = request.args.get('cate_l')
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


@auth.route('/reset_pass', methods=['GET', 'POST'])
@both_required
def reset_pass():
    print("Reset pass route called!")
    print(session)
    if request.method == 'POST':
        print('post')
        if 'email' in session:
            email_from_session = session['email']
            entered_email = request.form['l_email']
            print('emailfromsession: ', email_from_session)
            print('email: ',entered_email)

            # Check if the entered email matches the one in the session
            if email_from_session != entered_email:
                flash('Please enter the email associated with your account.', 'error')
                return render_template('forgot_password.html')
            with current_app.app_context():
                s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                token = s.dumps(email_from_session, salt=current_app.config['SECURITY_PASSWORD_SALT'])

                try:
                    msg = Message('Password Reset Request',
                                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                                  recipients=[email_from_session])
                    link = url_for('auth.reset_token', token=token, _external=True)
                    msg.body = f'Your link to reset your password is {link}'
                    current_app.mail.send(msg)
                except Exception as e:
                    current_app.logger.error(f'Error sending email: {e}')
                    flash('An error occurred while sending the reset email. Please try again.', 'error')
                    return "error"

            flash('A password reset email has been sent if the email is registered.', 'success')
            return render_template('check_email.html')

    return render_template('forgot_password.html')

@auth.route('/reset/<token>', methods=['GET', 'POST'])
@both_required
def reset_token(token):
    db = current_app.get_db()
    try:
        cursor = db.cursor()
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
                hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
                print(hashed_password)
                cursor.execute("UPDATE accounts_info SET password = %s WHERE email = %s", (hashed_password, email))
                cursor.execute("UPDATE userss SET password = %s WHERE email = %s", (hashed_password, email))
                db.commit()
                print(db)

                flash('Password reset successfully. You can now log in with your new password.', 'success')
                return redirect(url_for('auth.home'))

    except SignatureExpired:
        flash('The token is expired!', 'error')
        return redirect(url_for('auth.forgot_pass'))


    return render_template('reset_token.html', token=token)


@auth.route('/qr_codes/<image_id>')
@both_required
def qr_codes(image_id):
    try:
        image_path = f"Webapp/static/qr_codes/{image_id}.png"
        with open(image_path, "rb") as image_file:
            response = Response(image_file.read(), content_type="image/png")
            return response
    except FileNotFoundError:
        return "Image not found", 404


@auth.route('/qr_usr/<image_id>')
@both_required
def qr_usr(image_id):
    try:
        image_path = f"Webapp/static/qr_usr/{image_id}.png"
        with open(image_path, "rb") as image_file:
            response = Response(image_file.read(), content_type="image/png")
            return response
    except FileNotFoundError:
        return "Image not found", 404

@auth.route('/qr_lib/<image_id>')
@admin_required
def qr_lib(image_id):
    try:
        image_path = f"Webapp/static/qr_lib/{image_id}.png"
        with open(image_path, "rb") as image_file:
            response = Response(image_file.read(), content_type="image/png")
            return response
    except FileNotFoundError:
        return "Image not found", 404

@auth.route('/qr_login/<image_id>')
@admin_required
def qr_login(image_id):
    try:
        image_path = f"Webapp/static/qr_login/{image_id}.png"
        with open(image_path, "rb") as image_file:
            response = Response(image_file.read(), content_type="image/png")
            return response
    except FileNotFoundError:
        return "Image not found", 404





@auth.route('/insert', methods=['GET', 'POST'])
@al_required
def insert():
    db = current_app.get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM categories')
    category_name = cursor.fetchall()
    print(category_name)
    cursor.execute('SELECT * FROM shelves')
    shelf = cursor.fetchall()
    cursor.execute('SELECT * FROM book_row')
    b_rows = cursor.fetchall()
    cursor.execute("SET time_zone = '+08:00';")

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

            query_existing_book = "SELECT id, quantity FROM gen_books WHERE title = %s"
            cursor.execute(query_existing_book, (title,))
            existing_book = cursor.fetchone()
            print('inventor_record: ', existing_book)

            if existing_book:
                # Book already exists, update the quantity
                existing_id, existing_quantity = existing_book
                new_quantity = existing_quantity + 1
                print(new_quantity)

                cursor.fetchall()

                # Update the quantity in the gen_books table
                query_update_quantity = "UPDATE gen_books SET quantity = %s WHERE id = %s"
                cursor.execute(query_update_quantity, (new_quantity, existing_id))
                print(query_update_quantity)

                flash('Existing book found. Quantity updated!', 'success')
            else:
                # Book doesn't exist, insert a new record
                query_insert_gen_books = "INSERT INTO gen_books (book_row, category, isbn, title, publisher, year_published, quantity, availability) VALUES (%s, %s, %s, %s, %s, %s, 1, 'available')"
                cursor.execute(query_insert_gen_books, (num_row, cate, isbn, title, publisher, year))
                s_id = cursor.lastrowid

                query_insert_table = f"INSERT INTO {table} (book_row, category, isbn, title, publisher, year_published) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(query_insert_table, (num_row, cate, isbn, title, publisher, year))
                s_id1 = cursor.lastrowid

                query_insert_record = "INSERT INTO insert_record (book_row, category, isbn, title, publisher, year_published, librarian, role, time_inserted) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())"
                cursor.execute(query_insert_record, (num_row, cate, isbn, title, publisher, year, username, role))
                s_id2 = cursor.lastrowid

                p_id = f"{shelf_value}{num_row}"
                cat_id = f"{c_id}{s_id}"
                cat_id1 = f"{c_id}{s_id1}"
                bookloc_data = f"{p_id} {cat_id1}"
                query_update_gen_books = "UPDATE gen_books SET book_id = %s, categ_id = %s, book_loc = %s WHERE id = %s"
                cursor.execute(query_update_gen_books, (p_id, cat_id, bookloc_data, s_id))
                print(query_update_gen_books)

                p_id1 = f"{shelf_value}{num_row}"
                query_update_table = f"UPDATE {table} SET book_id = %s, categ_id = %s, book_loc = %s WHERE id = %s"
                cursor.execute(query_update_table, (p_id1, cat_id1, bookloc_data, s_id1))
                print(query_update_table)

                p_id2 = f"{shelf_value}{num_row}"
                cat_id2 = f"{c_id}{s_id2}"
                query_update_record = "UPDATE insert_record SET book_id = %s, categ_id = %s, book_loc = %s WHERE id = %s"
                cursor.execute(query_update_record, (p_id2, cat_id2, bookloc_data, s_id2))
                print('insert record: ', query_update_record)

                cursor.execute("SELECT id, quantity FROM gen_books WHERE book_id = %s", (p_id,))
                inventory_record = cursor.fetchall()
                print('inventory_record: ', inventory_record)

                qr_data = f"{p_id} {cat_id1}"
                print(qr_data)
                qr_data_encoded = qr_data.encode('utf-8')
                print(qr_data_encoded)
                qr_image_base64, image_path = current_app.generate_qr_code(qr_data_encoded, str(qr_data))

                flash('Data successfully inserted!', 'success')
                db.commit()
                return jsonify({'success': True, 'qr_image_base64': qr_image_base64, 'image_path': image_path, 'qrCodeID': qr_data})

            db.commit()


        except Exception as e:
            print("Exception:", e)
            db.rollback()
            flash('Error inserting data into the database', 'error')
            return jsonify({'success': False, 'error': 'Error inserting data into the database'})

        finally:
            cursor.close()
            db.close()

    return render_template("insert.html", qr_image_base64=None, category_name=category_name, shelf=shelf, b_rows=b_rows)




@auth.route('/log_cred')
@both_required
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