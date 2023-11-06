from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, session
from flask import jsonify
from flask import current_app
from flask_login import login_user, login_required, logout_user, current_user
import MySQLdb.cursors
import MySQLdb.cursors, re, hashlib
from .model import Admin
import cv2
import qrcode
from pyzbar.pyzbar import decode
import requests
from PIL import Image
from io import BytesIO




table_prefixes = {
    'shelf1': {'prefix': 'A-', 'counter': 'shelf1_counter'},
    'shelf2': {'prefix': 'B-', 'counter': 'shelf2_counter'},
    'shelf3': {'prefix': 'C-', 'counter': 'shelf3_counter'},
    'shelf4': {'prefix': 'D-', 'counter': 'shelf4_counter'},
    # Add more shelves and prefixes as needed
}

auth = Blueprint('auth', __name__, static_folder='static', static_url_path='/auth/static')


@auth.route('/clear-cache')
def clear_cache():
    cache = current_app.config['CACHE']
    cache.clear()
    return 'Cache cleared'

@auth.route('/admin_login/', methods=['POST', 'GET'])
def admin_login():
    if request.method == 'POST' and 'admin_usr' in request.form and 'admin_pass' in request.form:
        admin_usr = request.form['admin_usr']
        password = request.form['admin_pass']

        db = current_app.get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin WHERE admin_usr = %s', (admin_usr,))
        user = cursor.fetchone()
        cursor.close()

        if user and current_app.bcrypt.check_password_hash(user['admin_pass'], password):
            # Log the admin in
            session['loggedin'] = True
            session['id'] = user['id']  # Use the actual primary key of your admin
            
            # Create an Admin instance (modify this according to your actual Admin class)
            admin_instance = Admin(id=user['id'], admin_usr=user['admin_usr'], admin_pass=user['admin_pass'])
            login_user(admin_instance, remember=True)

            return redirect(url_for('auth.home'))  # Ensure you have a view function for 'auth.home'
        else:
            flash('Incorrect username or password.', 'error')

    # If GET or credentials are wrong
    return render_template("admin_login.html", user=current_user)

@auth.route('/logout')
@login_required
def admin_logout():
    logout_user()  # This will log out the current user
    return redirect(url_for('auth.admin_login'))



@auth.route('/login_cred')
def login_cred():
    return render_template("login_credentials.html", user=current_user)      


@auth.route('/main')
def home():
    return render_template("home.html", boolean=True, user=current_user)

@auth.route('/inventory')
def inventory():
    db = current_app.get_db()
    cursor  = db.cursor()
    cursor1 = db.cursor()
    cursor2 = db.cursor()
    cursor.execute('SELECT * FROM categories')
    category_name = cursor.fetchall()
    print(category_name)
    cursor1.execute('SELECT * FROM shelves')
    shelf_num = cursor1.fetchall()
    

    try:
        db = current_app.get_db()
        print("Database:", db)
        shelf = request.args.get('shelf_id')
        print("Selected shelf:", shelf)
        category = request.args.get('catalog')
        print("Category:", category)
        search_query = request.args.get('search_query')
        print("Search:", search_query)
        
            
        if shelf is None:
            return render_template('inventory.html', category_name=category_name, shelf_num=shelf_num, user=current_user)
        else:
            cursor2.execute(f'DESCRIBE {shelf}')
            thead = cursor2.fetchall()

        cursor = db.cursor()
        
        if category == 'all':
            # Fetch all rows from the selected shelf
            query = f"SELECT id, category, title, publisher, year FROM {shelf}"
            print("Query:", query)
            cursor.execute(query)
        else:
            # Fetch rows from the selected shelf with the specified category
            query = f"SELECT id, category, title, publisher, year FROM {shelf} WHERE category = %s"
            print("Query:", query)
            cursor.execute(query, (category,))
        
        data = cursor.fetchall()

        qr_code_data_list = []
        for row in data:
            print("Row data:", row)
            qr_data = f"ID: {row[0]}, Title: {row[2]}, Category: {row[1]}"  # Adjust this according to your data
            print("QR DATA:", qr_data)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert the image to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            # qr_image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            qr_code_data = {
                'qrcode': row[0],
                'category': row[1],
                'title': row[2],
                'publisher': row[3],
                'year': row[4] 
            }
            qr_code_data_list.append(qr_code_data)
            print(qr_code_data)
            
            if search_query:
                search_query = f"%{search_query}%"  # Add wildcard characters for a partial search
                filtered_data = [item for item in qr_code_data_list if
                                search_query in item['title'].lower() or search_query in item['publisher'].lower()]
        else:
            filtered_data = qr_code_data_list

        return jsonify(filtered_data, category_name=category_name, shelf=shelf)
    except Exception as e:
        print("Exception:", e)
        return jsonify({'error': 'An error occurred during data retrieval'})
       
       

@auth.route('/qr_codes/<image_id>')
def serve_qr_code(image_id):
    try:
        image_path = f"Webapp/static/qr_codes/{image_id}.png"  # Replace with your actual image path
        with open(image_path, "rb") as image_file:
            response = Response(image_file.read(), content_type="image/png")
            return response
    except FileNotFoundError:
        return "Image not found", 404



# Flag to control the video streaming thread
 # Move camera instantiation outside to prevent concurrent access
streaming = False
camera = cv2.VideoCapture(0)  # Initialize the camera when the server starts.

@auth.route('/camera')
def camera_view():
    return render_template('camera.html', user=current_user)

# def retrieve_data():
#     try:
#         response = requests.get("http://127.0.0.1:5000/api/qr_data")
#         if response.status_code == 200:
#             qr_values = response.json()
#             return set(qr_values)
#         else:
#             print("Error fetching data from API:", response.text)
#             return set()
#     except Exception as e:
#         print("Error fetching data from API:", str(e))
#         return set()

def generate_frames():
    global streaming, camera

    if not camera.isOpened():
        print("Error: Camera could not be opened.")
        yield "Error: Camera could not be opened."  # This won't show an image, but it will give a message.
        return

    while streaming:
        ret, frame = camera.read()
        if not ret:
            print("Error: Frame could not be read.")
            break

        decoded_objects = decode(frame)
        for obj in decoded_objects:
            x, y, w, h = obj.rect
            qr_data = obj.data.decode('utf-8')
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_pil = Image.fromarray(frame)
        frame_io = BytesIO()
        frame_pil.save(frame_io, format='JPEG')

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_io.getvalue() + b'\r\n')

@auth.route('/start_stream')
def start_stream():
    global streaming
    streaming = True
    return "Streaming started"

@auth.route('/stop_stream')
def stop_stream():
    global streaming
    streaming = False
    return "Streaming stopped"

@auth.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@auth.route('/insert', methods=['GET','POST'])
def insert():
    db = current_app.get_db()
    cursor  = db.cursor()
    cursor1 = db.cursor()
    cursor.execute('SELECT * FROM categories')
    category_name = cursor.fetchall()
    print(category_name)
    cursor1.execute('SELECT * FROM shelves')
    shelf = cursor1.fetchall()


    if request.method == "POST":
        db = current_app.get_db()
        cursor = db.cursor()
        table = request.form.get('b_shelves')
        cate = request.form.get('b_cata')
        isbn = request.form.get('isbn')
        title = request.form.get('b_title')
        publisher = request.form.get('b_publisher')
        year = int(request.form.get('b_year'))

        try:
            table_prefixes = {
                'shelf1': {'prefix': 'A-', 'counter': 'shelf1_counter'},
                'shelf2': {'prefix': 'B-', 'counter': 'shelf2_counter'},
                'shelf3': {'prefix': 'C-', 'counter': 'shelf3_counter'},
                'shelf4': {'prefix': 'D-', 'counter': 'shelf4_counter'},
                # Add more tables and prefixes as needed
            }

            if table not in table_prefixes:
                return jsonify({'success': False, 'error': 'Table not found'})

            table_info = table_prefixes[table]  # Get table-specific info

            # Define initial counter values for categories
            category_to_initial_counter = {
                'Science': 99,
                'Language': 199,
                'Novel': 299,
                'Math': 0
            }
            
            max_counters = {
                ('Science', 'shelf1'): 199,
                ('Language', 'shelf1'): 299,
                ('Novel', 'shelf1'): 399,
                ('Math', 'shelf1'): 99,
                ('Science', 'shelf2'): 199,
                ('Language', 'shelf2'): 299,
                ('Novel', 'shelf2'): 399,
                ('Math', 'shelf2'): 99,
                ('Science', 'shelf3'): 199,
                ('Language', 'shelf3'): 299,
                ('Novel', 'shelf3'): 399,
                ('Math', 'shelf3'): 99,
                ('Science', 'shelf4'): 199,
                ('Language', 'shelf4'): 299,
                ('Novel', 'shelf4'): 399,
                ('Math', 'shelf4'): 99,
                # Add more category and shelf combinations as needed
            }
            
            if (cate, table) not in max_counters:
                return jsonify({'success': False, 'error': 'Invalid category or shelf'})

            max_counter_value = max_counters[(cate, table)]

            # Check if the selected category is in the mapping
            if cate not in category_to_initial_counter:
                return jsonify({'success': False, 'error': 'Invalid category'})

            # Retrieve the current counter value for the selected category
            cursor.execute(f"SELECT {table_info['counter']} FROM counters WHERE category = %s", (cate,))
            counter_result = cursor.fetchone()

            if counter_result is not None:
                current_counter = counter_result[0]
            else:
                current_counter = category_to_initial_counter[cate]

            # Calculate the next counter value
            next_counter_value = current_counter + 1
            
            if next_counter_value > max_counter_value:
                return jsonify({'success': False, 'error': 'Category and shelf counter limit reached'})

            # Reset the counter for the previous category to its current value
            if 'current_category' in session:
                prev_category = session['current_category']
                cursor.execute(f"SELECT {table_info['counter']} FROM counters WHERE category = %s", (prev_category,))
                prev_counter_result = cursor.fetchone()
                if prev_counter_result is not None:
                    prev_counter = prev_counter_result[0]
                    cursor.execute(f"UPDATE counters SET {table_info['counter']} = %s WHERE category = %s", (prev_counter, prev_category))
                    db.commit()


            # Update the counter with the new value for the selected category
            cursor.execute(f"UPDATE counters SET {table_info['counter']} = %s WHERE category = %s", (next_counter_value, cate))
            db.commit()

            # Construct the book ID by combining the prefix and the counter value
            id = f'{table_info["prefix"]}{next_counter_value}'
            
            # Update the current category in the session
            session['current_category'] = cate
            

            query = f"INSERT INTO {table} (id, category, isbn, title, publisher, year) VALUES (%s, %s, %s, %s, %s, %s)"
            print(f'Inserted: {query}')

            cursor.execute(query, (id, cate, isbn, title, publisher, year))
            db.commit()

            qr_data = f"ID: {id}, Title: {title}"
            qr_data_encoded = qr_data.encode('utf-8')
            qr_image_base64, image_path = current_app.generate_qr_code(qr_data_encoded, str(id))

            cursor.close()
            db.close()

            flash('Data successfully inserted!', 'success')

            return jsonify({'success': True, 'qr_image_base64': qr_image_base64, 'image_path': image_path, 'qrCodeID': id})

        except Exception as e:
            print("Exception:", e)
            cursor.close()
            db.close()

            flash('Error inserting data into the database', 'error')
            return jsonify({'success': False, 'error': 'Error inserting data into the database'})

    return render_template("insert.html", qr_image_base64=None, category_name=category_name, shelf=shelf, user=current_user)
