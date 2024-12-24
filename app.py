from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import psycopg2
from connect import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from werkzeug.utils import secure_filename
import os
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit
import urllib.parse







app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Set 30 minutes for shared devices
app.config['UPLOAD_FOLDER'] = "./static/uploads" #we specify the path the image will be uploaded 
socketio = SocketIO(app)

# // Password Reset Configuration //#
# Set up the configuration for flask_mail.
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
# //update it with your gmail
app.config['MAIL_USERNAME'] = 'efezinorich@gmail.com'
# //update it with your password
app.config['MAIL_PASSWORD'] = 'wmuu eyhw eiyh mhms'
app.config['MAIL_USE_SSL'] = True

# Create an instance of Mail.
mail = Mail(app)
# Configure URLSafeTimedSerializer
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
# Define the route and send mail, Just to test If The App can send email out.

@app.route("/send_email")
def send_email():
  msg = Message('Hello from the other side!', sender = 'efezinorich@gmail.com', recipients = ['cyjustwebsolution@gmail.com'])
  msg.body = "hey, sending out email from flask!!!"
  msg.html = "<h1>Message Sent</h1>"
  mail.send(msg)
  return msg.html
# // Password Reset Configuration //#



# Define the allowed file extensions
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif',
    'pdf',  # PDF files
    'xlsx', 'xls',  # Excel files
    'doc', 'docx',  # Word documents
    'ppt', 'pptx',  # PowerPoint presentations
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return filename
    return None


from functools import wraps
from flask import session, redirect, url_for, flash

# Combined function to check if user is authenticated (staff or admin)
def login_required(role='staff'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if role == 'staff':
                # Check for 'user_id' instead of 'staff_id'
                if session.get('user_id') is None:
                    flash('You need to be logged in as staff to access this page.', 'error')
                    return redirect(url_for('login'))
            elif role == 'admin':
                if session.get('admin_id') is None:
                    flash('You need to be logged in as admin to access this page.', 'error')
                    return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator



@app.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, full_name, username, department, position, branch
        FROM staffs
        WHERE approved = FALSE
    """)

    pending_staff = cur.fetchall()
    pending_staff = [
        {
            'id': row[0],
            'full_name': row[1],
            'username': row[2],
            'department': row[3],
            'position': row[4],
            'branch': row[5]
        }
        for row in pending_staff
    ]

    cur.close()
    conn.close()

    return render_template('admin_dashboard.html', pending_staff=pending_staff)

@app.route('/approve_staff/<int:staff_id>', methods=['POST'])
@login_required(role='admin')
def approve_staff(staff_id):
    staff_number = request.form['staff_number']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE staffs
        SET staff_number = %s, approved = TRUE
        WHERE id = %s
    """, (staff_number, staff_id))
    conn.commit()

    cur.close()
    conn.close()

    flash('Staff member approved and staff number assigned.', 'success')
    return redirect(url_for('admin_dashboard'))

# @app.route('/register', methods=['GET', 'POST'])
# def show_register_form():
#     if request.method == 'POST':
#         full_name = request.form['full_name']
#         username = request.form['username']
#         email = request.form['email']
#         password = request.form['password']
#         department = request.form['department']
#         position = request.form['position']
#         branch = request.form['branch']

#         conn = get_db_connection()
#         cur = conn.cursor()

#         # Insert new staff into the database
#         cur.execute("""
#             INSERT INTO staffs (full_name, username, email, password, department, position, branch, approved)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
#             RETURNING id
#         """, (full_name, username, email, generate_password_hash(password), department, position, branch))
#         staff_id = cur.fetchone()[0]

#         # Automatically assign default tools to the new staff member
#         cur.execute("SELECT id FROM tools")
#         default_tools = cur.fetchall()

#         for tool in default_tools:
#             cur.execute("""
#                 INSERT INTO staff_tools (staff_id, tool_id, added_by_admin)
#                 VALUES (%s, %s, FALSE)
#             """, (staff_id, tool[0]))

#         conn.commit()
#         cur.close()
#         conn.close()

#         flash('Registration successful. Awaiting approval.', 'success')
#         return redirect(url_for('index'))
    
#     return render_template('register.html')


def add_new_staff(full_name, username, email, password, department, position, branch):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Step 1: Insert the new staff into the `staffs` table
        cur.execute("""
            INSERT INTO staffs (full_name, username, email, password, department, position, branch, approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
            RETURNING id;
        """, (full_name, username, email, generate_password_hash(password), department, position, branch))
        
        staff_id = cur.fetchone()[0]  # Get the newly created staff's ID

        # Step 2: Automatically assign default tools to the new staff member
        cur.execute("SELECT id FROM tools")
        default_tools = cur.fetchall()

        for tool in default_tools:
            cur.execute("""
                INSERT INTO staff_tools (staff_id, tool_id, added_by_admin)
                VALUES (%s, %s, FALSE)
            """, (staff_id, tool[0]))

        conn.commit()  # Commit all changes

    except psycopg2.errors.UniqueViolation:
        conn.rollback()  # Rollback in case of a unique violation (e.g., duplicate email)
        raise ValueError("This email is already registered. Please use a different email.")
    
    finally:
        cur.close()
        conn.close()



@app.route('/register', methods=['GET', 'POST'])
def show_register_form():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']
        position = request.form['position']
        branch = request.form['branch']

        # Check if the email ends with '@rprogroup.net'
        if not email.endswith('@rprogroup.net'):
            flash('Please use your official company email (ending with @rprogroup.net) to register.', 'error')
            return render_template('register.html', full_name=full_name, username=username, email=email,
                                   department=department, position=position, branch=branch)

        try:
            # Call add_new_staff to handle staff insertion and tool assignment
            add_new_staff(full_name, username, email, password, department, position, branch)
            flash('Registration successful. Awaiting approval.', 'success')
            return redirect(url_for('index'))

        except ValueError as e:
            # Handle unique violation (duplicate email)
            flash(str(e), 'error')
            return render_template('register.html', full_name=full_name, username=username, email=email,
                                   department=department, position=position, branch=branch)

    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        device_type = request.form.get('device_type', 'personal')  # Default to 'personal'

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the user is an admin
        cur.execute("SELECT id, password FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()

        if admin and check_password_hash(admin[1], password):
            session['admin_logged_in'] = True
            session['admin_id'] = admin[0]
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))

        # Check if the user is a staff member
        cur.execute("SELECT id, password, username, profile_pic, full_name FROM staffs WHERE username = %s AND approved = TRUE", (username,))
        staff = cur.fetchone()

        if staff and check_password_hash(staff[1], password):
            session['user_logged_in'] = True
            session['user_id'] = staff[0]
            session['full_name'] = staff[4]
            session['username'] = staff[2]
            session['avatar'] = staff[3]
            session['device_type'] = device_type

            # Handle session expiration for shared devices
            if device_type == 'shared':
                session.permanent = False
                flash("You're logged in on a shared device. Please sign out from all external tools after you're done for security.", 'warning')
            else:
                session.permanent = True

            flash('Staff login successful!', 'success')
            return redirect(url_for('user_dashboard'))

        flash("Invalid username or password, or account not approved.", 'danger')
        cur.close()
        conn.close()

    return render_template('login.html')



# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         device_type = request.form['device_type']  # Get the device type

#         conn = get_db_connection()
#         cur = conn.cursor()
#         cur.execute("SELECT id, password FROM staffs WHERE username = %s AND approved = TRUE", (username,))
#         user = cur.fetchone()
#         cur.close()
#         conn.close()

#         if user and check_password_hash(user[1], password):
#             session['user_logged_in'] = True
#             session['user_id'] = user[0]
#             session['device_type'] = device_type  # Save device_type in the session

#             # Handle session expiration for shared devices
#             if device_type == 'shared':
#                 session.permanent = False  # Auto-logout after inactivity
#                 flash("You're logged in on a shared device. Please sign out from all external tools after you're done for security.", 'warning')
#             else:
#                 session.permanent = True  # Persistent session for personal devices

#             flash('Login successful!', 'success')
#             return redirect(url_for('user_dashboard'))
#         else:
#             flash("Invalid username or password, or account not approved.", 'danger')

#     return render_template('login.html')





## Forgotton password Route and Functions ##

def generate_reset_token(user_id):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(user_id, salt='password-reset-salt')

def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        user_id = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return None
    return user_id

def send_reset_email(email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message('Password Reset Request', sender='efezinorich@gmail.com', recipients=[email])
    msg.body = f'To reset your password, click the following link: {reset_url}'
    msg.html = f'<p>To reset your password, click the following link: <a href="{reset_url}">{reset_url}</a></p>'
    mail.send(msg)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM staffs WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            token = generate_reset_token(user[0])
            send_reset_email(email, token)
            flash('An email with a password reset link has been sent to your email address.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email address not found.', 'error')
        

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = verify_reset_token(token)
    if not user_id:
        flash('The reset link is invalid or has expired.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE staffs SET password = %s WHERE id = %s', (hashed_password, user_id))
        conn.commit()
        cur.close()
        conn.close()

        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')



@app.route('/user_dashboard', methods=['GET', 'POST'])
@login_required(role='staff')
def user_dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    # Define the default tools (you can adjust this based on your tool data)
    DEFAULT_TOOLS = ['Slack', 'WhatsApp', 'Titan']
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM staffs WHERE id = %s", (user_id,))
    user = cur.fetchone()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('logout'))

    # Fetch tools for the logged-in staff member, including the logo_url
    cur.execute("""
        SELECT t.id, t.name, COALESCE(st.custom_url, t.url) as url, t.logo_url
        FROM staff_tools st
        JOIN tools t ON st.tool_id = t.id
        WHERE st.staff_id = %s
    """, (user_id,))
    tools = cur.fetchall()

    # Fetch all staff members except the logged-in user
    cur.execute("SELECT id, full_name, profile_pic FROM staffs WHERE id != %s", (user_id,))
    staff_list = cur.fetchall()
    
    # Store in session
    session['staff_list'] = staff_list
    staff_id = session.get('user_id')
    cur.execute("SELECT * FROM local_tools WHERE staff_id = %s", (staff_id,))
    local_tools = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('user_dashboard.html', user=user, tools=tools, staff_list=staff_list, local_tools=local_tools, default_tools=DEFAULT_TOOLS)



# @app.route('/user_dashboard')
# @login_required(role='staff')
# def user_dashboard():
#     if 'user_id' not in session:
#         flash('Please log in to access the dashboard.', 'warning')
#         return redirect(url_for('login'))

#     user_id = session['user_id']
    
#     conn = get_db_connection()
#     cur = conn.cursor()

#     cur.execute("SELECT * FROM staffs WHERE id = %s", (user_id,))
#     user = cur.fetchone()

#     if not user:
#         flash("User not found.", "danger")
#         return redirect(url_for('logout'))

#     # Fetch tools for the logged-in staff member
#     cur.execute("""
#         SELECT t.id, t.name, COALESCE(st.custom_url, t.url) as url
#         FROM staff_tools st
#         JOIN tools t ON st.tool_id = t.id
#         WHERE st.staff_id = %s
#     """, (user_id,))
#     tools = cur.fetchall()

#     # Fetch all staff members except the logged-in user
#     cur.execute("SELECT id, full_name, profile_pic FROM staffs WHERE id != %s", (user_id,))
#     staff_list = cur.fetchall()
    
#     # Store in session
#     session['staff_list'] = staff_list

#     cur.close()
#     conn.close()

#     return render_template('user_dashboard.html', user=user, tools=tools, staff_list=staff_list)



@app.route('/profile', methods=['GET', 'POST'])
def update_staff_profile():
    if 'user_logged_in' not in session:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch current staff details
    cur.execute("SELECT username, branch, email, description, profile_pic FROM staffs WHERE id = %s", (user_id,))
    staff = cur.fetchone()

    if request.method == 'POST':
        username = request.form['username']
        branch = request.form['branch']
        email = request.form['email']
        password = request.form['password']
        description = request.form['description']
        file = request.files.get('profile_pic')

        errors = []

        # Basic validation for email
        if not email.endswith('@rprogroup.net'):
            errors.append('Please use your official company email (ending with @rprogroup.net).')

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            # Only update password if it's provided
            if password:
                hashed_password = generate_password_hash(password)
                cur.execute("UPDATE staffs SET password = %s WHERE id = %s", (hashed_password, user_id))

            # Handle profile picture upload
            if file and allowed_file(file.filename):
                filename =secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                cur.execute("UPDATE staffs SET profile_pic = %s WHERE id = %s", (file_path, user_id))
                session['avatar'] = file_path
  
            
            # Update other fields
            cur.execute("""
                UPDATE staffs
                SET username = %s, branch = %s, email = %s, description = %s
                WHERE id = %s
            """, (username, branch, email, description, user_id))

            conn.commit()
            flash('Profile updated successfully!', 'success')

        return redirect(url_for('update_staff_profile'))

    conn.close()

    return render_template('profile.html', staff=staff)





@app.route('/add_tool', methods=['GET', 'POST'])
@login_required(role='staff')
def add_tool():
    if request.method == 'POST':
        tool_name = request.form['name']
        tool_url = request.form['url']
        
        # Parse the domain from the provided tool URL
        domain = urllib.parse.urlparse(tool_url).netloc
        
        # Fetch the favicon from Google's Favicon API
        favicon_url = f"https://www.google.com/s2/favicons?sz=64&domain={domain}"
        
        conn = get_db_connection()
        cur = conn.cursor()

        # Insert the new tool into the tools table, including the favicon URL
        cur.execute("""
            INSERT INTO tools (name, url, logo_url)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (tool_name, tool_url, favicon_url))
        new_tool_id = cur.fetchone()[0]

        # Assign this tool to the logged-in staff member
        user_id = session.get('user_id')
        cur.execute("""
            INSERT INTO staff_tools (staff_id, tool_id, added_by_admin)
            VALUES (%s, %s, FALSE)
        """, (user_id, new_tool_id))

        conn.commit()
        cur.close()
        conn.close()

        flash('Tool added and assigned to your account successfully.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('add_tool.html')




@app.route('/add_local_tool', methods=['GET', 'POST'])
@login_required(role='staff')
def add_local_tool():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = upload_file(file)
            if filename:
                staff_id = session.get('user_id')
                file_type = file.content_type  # Get the MIME type of the uploaded file
                
                # Log the MIME type for debugging
                print(f"Uploaded file type: {file_type}")  # Add this line to log the file type

                conn = get_db_connection()
                cur = conn.cursor()
                
                # Insert the local tool into the database
                cur.execute("""
                    INSERT INTO local_tools (staff_id, file_name, file_url, file_type)
                    VALUES (%s, %s, %s, %s)
                """, (staff_id, filename, f"./static/uploads/{filename}", file_type))
                
                conn.commit()
                cur.close()
                conn.close()
                
                flash('Local tool uploaded successfully.', 'success')
                return redirect(url_for('user_dashboard'))

    # Fetch the uploaded local tools for display
    conn = get_db_connection()
    cur = conn.cursor()
    
    staff_id = session.get('user_id')
    cur.execute("SELECT * FROM local_tools WHERE staff_id = %s", (staff_id,))
    local_tools = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('add_local_tool.html', local_tools=local_tools)


# _____Update Web Tool_____
@app.route('/edit_tool/<int:tool_id>', methods=['GET', 'POST'])
@login_required(role='staff')
def edit_tool(tool_id):
    conn = get_db_connection()
    cur = conn.cursor()


    # Fetch tool data by tool_id
    cur.execute("SELECT * FROM tools WHERE id = %s", (tool_id,))
    tool = cur.fetchone()

    if not tool:
        flash('Tool not found.', 'danger')
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')

        # Parse the domain from the new tool URL
        domain = urllib.parse.urlparse(url).netloc
        
        # Fetch the favicon from Google's Favicon API based on the new URL
        favicon_url = f"https://www.google.com/s2/favicons?sz=64&domain={domain}"

        # Update the tool with the new data, including the new favicon URL
        cur.execute("""
            UPDATE tools SET name = %s, url = %s, logo_url = %s WHERE id = %s
        """, (name, url, favicon_url, tool_id))

        conn.commit()
        cur.close()
        conn.close()

        flash('Tool updated successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    cur.close()
    conn.close()

    return render_template('edit_web_tool.html', tool=tool)


# _____Delete Web Tool_____
@app.route('/delete_tool/<int:tool_id>', methods=['POST'])
@login_required(role='staff')
def delete_tool(tool_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Delete the tool
    cur.execute("DELETE FROM tools WHERE id = %s", (tool_id,))
    conn.commit()

    cur.close()
    conn.close()

    flash('Tool deleted successfully!', 'success')
    return redirect(url_for('user_dashboard'))






# @app.route('/add_tool', methods=['GET', 'POST'])
# @login_required(role='staff')
# def add_tool():
#     if request.method == 'POST':
#         tool_name = request.form['name']
#         tool_url = request.form['url']
        

#         conn = get_db_connection()
#         cur = conn.cursor()

#         # Insert new tool into the tools table
#         cur.execute("""
#             INSERT INTO tools (name, url)
#             VALUES (%s, %s)
#             RETURNING id
#         """, (tool_name, tool_url))
#         new_tool_id = cur.fetchone()[0]

#         # Now, assign this tool to the logged-in staff member
#         user_id = session.get('user_id')
#         cur.execute("""
#             INSERT INTO staff_tools (staff_id, tool_id, added_by_admin)
#             VALUES (%s, %s, FALSE)
#         """, (user_id, new_tool_id))

#         conn.commit()
#         cur.close()
#         conn.close()

#         flash('Tool added and assigned to your account successfully.', 'success')
#         return redirect(url_for('user_dashboard'))

#     return render_template('add_tool.html')






# @app.route('/chat/<int:staff_id>', methods=['GET', 'POST'])
# def chat(staff_id):
#     if 'user_id' not in session:
#         flash('Please log in to access the chat.', 'warning')
#         return redirect(url_for('login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
#     cur = conn.cursor()
#     print(f"Current User ID: {user_id}")


#     # Check if a conversation already exists
#     cur.execute("""
#         SELECT id FROM conversations
#         WHERE name = %s
#     """, (f"Conversation between {user_id} and {staff_id}",))
    
#     conversation_result = cur.fetchone()
#     if conversation_result:
#         conversation_id = conversation_result[0]
#     else:
#         # Create a new conversation if it does not exist
#         cur.execute("""
#             INSERT INTO conversations (name)
#             VALUES (%s)
#             RETURNING id
#         """, (f"Conversation between {user_id} and {staff_id}",))
        
#         conversation_id = cur.fetchone()[0]

#     # Ensure both participants are added to the conversation
#     cur.execute("""
#         INSERT INTO conversation_participants (conversation_id, staff_id)
#         VALUES (%s, %s), (%s, %s)
#         ON CONFLICT DO NOTHING
#     """, (conversation_id, user_id, conversation_id, staff_id))
#     conn.commit()

#     if request.method == 'POST':
#         content = request.form['content']
#         cur.execute("""
#             INSERT INTO messages (conversation_id, sender_id, content)
#             VALUES (%s, %s, %s)
#         """, (conversation_id, user_id, content))
#         conn.commit()
#         flash('Message sent!', 'success')

#     cur.execute("""
#         SELECT m.sender_id, staffs.full_name, m.content, m.created_at
#         FROM messages m
#         JOIN staffs ON m.sender_id = staffs.id
#         WHERE m.conversation_id = %s
#         ORDER BY m.created_at
#     """, (conversation_id,))
#     messages = cur.fetchall()

    
#     print("Messages fetched:", messages)


#     print(f"Conversation ID: {conversation_id}")
#     print(f"Messages: {messages}")

#     cur.close()
#     conn.close()

#     return render_template('chat.html', messages=messages, conversation_id=conversation_id, staff_id=staff_id, user_id=user_id)





@app.route('/chat/<int:staff_id>', methods=['GET', 'POST'])
def chat(staff_id):
    if 'user_id' not in session:
        flash('Please log in to access the chat.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch the full name and profile picture of the staff member
    cur.execute("SELECT full_name, profile_pic FROM staffs WHERE id = %s", (staff_id,))
    staff_info = cur.fetchone()
    if not staff_info:
        flash('Staff not found.', 'danger')
        return redirect(url_for('dashboard'))  # Redirect if staff not found

    staff_full_name, staff_profile_pic = staff_info


    # Check if a conversation already exists between these two participants
    cur.execute("""
        SELECT id FROM conversations
        WHERE name = %s OR name = %s
    """, (f"Conversation between {user_id} and {staff_id}",
          f"Conversation between {staff_id} and {user_id}"))
    
    conversation_result = cur.fetchone()
    if conversation_result:
        conversation_id = conversation_result[0]
    else:
        # Create a new conversation if it doesn't exist
        cur.execute("""
            INSERT INTO conversations (name)
            VALUES (%s)
            RETURNING id
        """, (f"Conversation between {user_id} and {staff_id}",))   
        
        conversation_id = cur.fetchone()[0]

    # Add both participants to the conversation (if not already added)
    cur.execute("""
        INSERT INTO conversation_participants (conversation_id, staff_id)
        VALUES (%s, %s), (%s, %s)
        ON CONFLICT DO NOTHING
    """, (conversation_id, user_id, conversation_id, staff_id))
    conn.commit()

    # Handle message sending (POST request)
    if request.method == 'POST':
        content = request.form['content']
        if content.strip():
            cur.execute("""
                INSERT INTO messages (conversation_id, sender_id, content)
                VALUES (%s, %s, %s)
            """, (conversation_id, user_id, content))
            conn.commit()
            return '', 204  # Return empty response with no content status to prevent page reload
        else:
            flash('Message content cannot be empty!', 'warning')

    # Fetch and display all messages in this conversation
    cur.execute("""
        SELECT m.sender_id, staffs.full_name, m.content, m.created_at
        FROM messages m
        JOIN staffs ON m.sender_id = staffs.id
        WHERE m.conversation_id = %s
        ORDER BY m.created_at
    """, (conversation_id,))
    messages = cur.fetchall()

    cur.close()
    conn.close()

    # Pass the staff's full name to the template
    return render_template('chat.html', messages=messages, conversation_id=conversation_id, staff_id=staff_id, staff_full_name=staff_full_name, staff_profile_pic=staff_profile_pic, user_id=user_id)



@app.route('/fetch_messages/<int:conversation_id>', methods=['GET'])
def fetch_messages(conversation_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch messages for the given conversation_id
    cur.execute("""
        SELECT m.sender_id, staffs.full_name, m.content, m.created_at
        FROM messages m
        JOIN staffs ON m.sender_id = staffs.id
        WHERE m.conversation_id = %s
        ORDER BY m.created_at
    """, (conversation_id,))
    messages = cur.fetchall()

    cur.close()
    conn.close()

    # Return messages in JSON format
    return jsonify(messages)







# @app.route('/chat/<int:staff_id>', methods=['GET', 'POST'])
# def chat(staff_id):
#     if 'user_id' not in session:
#         flash('Please log in to access the chat.', 'warning')
#         return redirect(url_for('login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
#     cur = conn.cursor()
#     print(f"Current User ID: {user_id}, Chatting with Staff ID: {staff_id}")

#     # Check if a conversation already exists between these two participants
#     cur.execute("""
#         SELECT id FROM conversations
#         WHERE name = %s OR name = %s
#     """, (f"Conversation between {user_id} and {staff_id}",
#           f"Conversation between {staff_id} and {user_id}"))
    
#     conversation_result = cur.fetchone()
#     if conversation_result:
#         conversation_id = conversation_result[0]
#     else:
#         # Create a new conversation if it doesn't exist
#         cur.execute("""
#             INSERT INTO conversations (name)
#             VALUES (%s)
#             RETURNING id
#         """, (f"Conversation between {user_id} and {staff_id}",))
        
#         conversation_id = cur.fetchone()[0]

#     # Add both participants to the conversation (if not already added)
#     cur.execute("""
#         INSERT INTO conversation_participants (conversation_id, staff_id)
#         VALUES (%s, %s), (%s, %s)
#         ON CONFLICT DO NOTHING
#     """, (conversation_id, user_id, conversation_id, staff_id))
#     conn.commit()

#     # Print participants for debugging
#     cur.execute("SELECT * FROM conversation_participants WHERE conversation_id = %s", (conversation_id,))
#     participants = cur.fetchall()
#     print(f"Participants in conversation {conversation_id}: {participants}")

#     # Handle message sending (POST request)
#     if request.method == 'POST':
#         content = request.form['content']
#         if content.strip():
#             cur.execute("""
#                 INSERT INTO messages (conversation_id, sender_id, content)
#                 VALUES (%s, %s, %s)
#             """, (conversation_id, user_id, content))
#             conn.commit()
#             flash('Message sent!', 'success')
#         else:
#             flash('Message content cannot be empty!', 'warning')

#     # Fetch and display all messages in this conversation
#     cur.execute("""
#         SELECT m.sender_id, staffs.full_name, m.content, m.created_at
#         FROM messages m
#         JOIN staffs ON m.sender_id = staffs.id
#         WHERE m.conversation_id = %s
#         ORDER BY m.created_at
#     """, (conversation_id,))
#     messages = cur.fetchall()

#     print(f"Messages fetched for conversation {conversation_id}: {messages}")

#     cur.close()
#     conn.close()

#     return render_template('chat.html', messages=messages, conversation_id=conversation_id, staff_id=staff_id, user_id=user_id)



# @app.route('/fetch_messages/<int:conversation_id>', methods=['GET'])
# def fetch_messages(conversation_id):
#     conn = get_db_connection()
#     cur = conn.cursor()

#     # Fetch messages for the given conversation_id
#     cur.execute("""
#         SELECT m.sender_id, staffs.full_name, m.content, m.created_at
#         FROM messages m
#         JOIN staffs ON m.sender_id = staffs.id
#         WHERE m.conversation_id = %s
#         ORDER BY m.created_at
#     """, (conversation_id,))
#     messages = cur.fetchall()

#     cur.close()
#     conn.close()

#     # Return messages in JSON format
#     return jsonify(messages)



@app.route('/logout_tool/<int:tool_id>')
@login_required(role='staff')
def logout_tool(tool_id):
    flash(f'You have logged out of tool with ID {tool_id}.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    device_type = session.get('device_type')

    # If on a shared device, log the user out of all tools
    if device_type == 'shared':
        session.clear()
        flash("You have been logged out of all tools on this shared device.", "success")
        return redirect(url_for('login'))  # Ensure return after flash
    
    # If on a personal device, log the user out of the current session
    elif device_type == 'personal':
        session.clear()
        flash("You have been logged out of your personal account.", "success")
        return redirect(url_for('login'))  # Ensure return after flash
    
    # Admin logout path
    elif session.get('admin_logged_in'):
        session.clear()
        flash("Admin has been logged out.", "success")
        return redirect(url_for('admin_login'))  # Ensure return after flash
    
    # Fallback in case no condition is met
    else:
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for('login'))  # Ensure return after flash





@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
    
    
    
    
# Add Libery and Documentation where User can upload step by step procedure that follow to solve a Soution
