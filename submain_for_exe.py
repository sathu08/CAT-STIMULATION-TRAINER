import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import cv2
import numpy as np
import shutil
from PIL import Image
import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config["IMAGE_UPLOADS"] = "_internal/static/upload/"
app.config["IMAGE_UPLOADS_2"] = "_internal/static/second_folder/"
login_manager = LoginManager()
login_manager.init_app(app)
files = " "
update_image_name = ''
test_image_name = ''
score = 0
percent = 0
total_click = ''
total_score = ''
test_file_name = ''
correct_index = []


def users_name():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    user_name = cur.execute("Select name from users where  username = ?", (current_user.username,)).fetchone()
    cleaned_elements = tuple(element.strip("(),'") for element in user_name)
    user_name = cleaned_elements[0]
    cur.connection.commit()
    cur.close()
    return user_name


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


def del_coordinates_update(remaining_coordinates, image):
    path = '_internal/static/second_folder/%s' % image
    images = cv2.imread(path)
    for coord in remaining_coordinates:
        x, y, text = coord
        center_coordinates = (x, y)
        radius = 10
        color = (255, 0, 0)
        thickness = 2
        images = cv2.circle(images, center_coordinates, radius, color, thickness)
        org = (x + 15, y - 15)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        color = (255, 0, 0)
        thickness = 2
        images = cv2.putText(images, str(text), org, font, font_scale, color, thickness, cv2.LINE_AA)
    save_path = '_internal/static/upload/%s' % image
    cv2.imwrite(save_path, images)
    print(f"Image with text saved to {save_path}")


def coordinates_test_details(name, date, mark, image, model, points, ques, mis_points):
    image_with_text = ""
    image_with_value = ""
    path = '_internal/static/test_photos/%s' % image
    img = cv2.imread(path)
    h, w, c = img.shape
    extended_img = np.zeros([h, w + 500, c], dtype=np.uint8)
    extended_img.fill(255)
    extended_img[:, :w] = img
    data_to_print = [
        "Name: ",
        "Date: ",
        "total",
        "Ques:",
        "Score: ",
        "Model:",
        "Correct",
        "points:",
        "Mis Click",
        "points:",
    ]
    data_value = [
        str(name),
        str(date),
        "",
        str(ques),
        str(mark),
        str(model),
        "",
        str(points),
        "",
        str(mis_points),
    ]
    padding = 9
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.9
    color = (255, 0, 0)
    thickness = 2
    x = w + padding
    y = 50
    x1 = w + padding
    y1 = 50
    line_spacing = 30
    for item in data_to_print:
        org = (x, y)
        image_with_text = cv2.putText(extended_img, item, org, font, font_scale, color, thickness, cv2.LINE_AA)
        y += line_spacing
    for item in data_value:
        org = (x1 + 100, y1)
        image_with_value = cv2.putText(image_with_text, item, org, font, font_scale, color, thickness, cv2.LINE_AA)
        y1 += line_spacing
    save_path = '_internal/static/test_photos/%s' % image
    cv2.imwrite(save_path, image_with_value)
    print(f"Image with text saved to {save_path}")


def coordinates_test(x, y, image, text):
    path = '_internal/static/test_photos/%s' % image
    images = cv2.imread(path)
    center_coordinates = (x, y)
    radius = 10
    color = (255, 0, 0)
    thickness = 2
    image_with_circle = cv2.circle(images, center_coordinates, radius, color, thickness)
    org = (x + 15, y - 15)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    color = (255, 0, 0)
    thickness = 2
    image_with_text = cv2.putText(image_with_circle, str(text), org, font, font_scale, color, thickness, cv2.LINE_AA)
    save_path = '_internal/static/test_photos/%s' % image
    cv2.imwrite(save_path, image_with_text)
    print(f"Image with text saved to {save_path}")


def coordinates(x, y, image, text):
    path = '_internal/static/upload/%s' % image
    images = cv2.imread(path)
    center_coordinates = (x, y)
    radius = 10
    color = (255, 0, 0)
    thickness = 2
    image_with_circle = cv2.circle(images.copy(), center_coordinates, radius, color, thickness)
    org = (x + 15, y - 15)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    color = (255, 0, 0)
    thickness = 2
    image_with_text = cv2.putText(image_with_circle, str(text), org, font, font_scale, color, thickness, cv2.LINE_AA)
    save_path = '_internal/static/upload/%s' % image
    cv2.imwrite(save_path, image_with_text)
    print(f"Image with text saved to {save_path}")


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user_query = "SELECT * FROM users WHERE id = ?"
    user_data = cursor.execute(user_query, (user_id,)).fetchone()

    if user_data:
        user_id = user_data['id']
        username = user_data['username']
        user_obj = User(user_id, username)
        conn.close()
        return user_obj
    conn.close()
    return None  # Return None if the user is not found.


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        user_query = "SELECT * FROM users WHERE username = ? AND password = ?"
        admin_query = "SELECT * FROM admins WHERE username = ? AND password = ?"
        user = cursor.execute(user_query, (username, password)).fetchone()
        if user:
            user_obj = User(user['id'], username)
            login_user(user_obj)
            conn.close()
            return redirect(url_for('user_page'))
        admin = cursor.execute(admin_query, (username, password)).fetchone()
        if admin:
            user_obj = User(admin['id'], username)
            login_user(user_obj)
            return redirect(url_for('admin_page'))
        else:
            flash('Login Failed')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    global percent, score
    percent, score = 0, 0
    correct_index.clear()
    return redirect(url_for('login'))


@app.route('/admin_page')
@login_required
def admin_page():
    return render_template('admin_home_screen.html')


@app.route('/reports', methods=['POST', 'GET'])
@login_required
def reports():
    if request.method == "GET":
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        languages = cur.execute('SELECT Model_Name FROM Test_Details').fetchall()
        unique_words = []
        seen_words = set()
        for language_tuple in languages:
            language = language_tuple[0]
            if language not in seen_words:
                seen_words.add(language)
                unique_words.append(language)
        return render_template("reports.html", languages=unique_words)

    if request.method == 'POST':
        report_name = request.form['messages']
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        report_details = cur.execute('SELECT * FROM Test_Details WHERE Model_Name = ? OR username = ?',
                                     (report_name, report_name)).fetchall()
        if len(report_details) > 0:
            cur.close()
            return render_template('reports.html', report_details=report_details)
        else:
            flash("No matching records found for '{}'.".format(report_name), 'warning')
            return render_template("reports.html")
    return render_template("reports.html")


@app.route('/admin_home_page', methods=['GET', 'POST'])
@login_required
def admin_home_page():
    if request.method == "POST":
        if 'cat' in request.form:
            return redirect(url_for('upload_image', model='CAT'))
        elif 'aoi' in request.form:
            return redirect(url_for('upload_image', model='AOI'))
    return render_template('admin_home.html')


@app.route('/admin_index/<model>')
@login_required
def admin_index(model):
    global files
    image = files
    return render_template("admin_index.html", uploaded_image=image, model=model)


@app.route('/upload-image/<model>', methods=['GET', 'POST'])
@login_required
def upload_image(model):
    if request.method == "POST":
        if "image" in request.files:
            image = request.files["image"]
            if image.filename == "":
                flash("No image selected for upload. Please choose an image file.")
            else:
                image_path = os.path.join(app.config["IMAGE_UPLOADS"], image.filename)
                image.save(image_path)
                new_width = 800
                new_height = 350
                img = Image.open(image_path)
                img = img.resize((new_width, new_height), Image.BILINEAR)
                img.save(image_path)
                image_path_2 = os.path.join(app.config["IMAGE_UPLOADS_2"], image.filename)
                shutil.copy(image_path, image_path_2)
                global files
                files = image.filename
                return redirect(url_for("admin_index", model=model))
        else:
            flash("No image selected for upload. Please choose an image file.")

    return render_template("upload.html", model=model)


@app.route('/click', methods=['POST'])
@login_required
def handle_click():
    data = request.get_json()
    x = data['x']
    y = data['y']
    model = data['model']
    value = data['value']
    defectArea = data['defectArea']
    response_data = {'x': x, 'y': y, 'value': value, defectArea: 'defectArea'}
    global files
    image = files
    model_name = os.path.splitext(image)
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO coordinates (x, y, Description,Model_Name, Image,Defect_Area,Type) "
                "VALUES (?,?,?,?,?,?,?)", (x, y, value, model_name[0], image, defectArea, model))
    details = cur.execute("select id from coordinates where(x=? and  y=? and  Description=? and"
                          " Model_Name=? and Image=? and Defect_Area=?)",
                          (x, y, value, model_name[0], image, defectArea))
    for i in details:
        coordinates(x, y, image, i[0])
    cur.connection.commit()
    cur.close()
    return jsonify(response_data)


@app.route('/create_account', methods=['POST', 'GET'])
@login_required
def create_account():
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute('INSERT INTO users (username, password, name) VALUES (?,?,?)', (username, password, name))
        cur.connection.commit()
        cur.close()
        return render_template("create_account.html")
    return render_template("create_account.html")


@app.route('/edit_models', methods=['GET', 'POST'])
@login_required
def edit_models():
    img = ''
    if request.method == "GET":
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        languages = cur.execute('SELECT Model_Name FROM coordinates').fetchall()
        unique_words = []
        seen_words = set()
        for language_tuple in languages:
            language = language_tuple[0]
            if language not in seen_words:
                seen_words.add(language)
                unique_words.append(language)
        return render_template("edit_models.html", languages=unique_words)

    if request.method == "POST":
        model_name = request.form["messages"]
        conn = get_db_connection()
        cur = conn.cursor()
        result = cur.execute('SELECT id, X, Y, Description, Image, Defect_Area ,Type FROM coordinates WHERE '
                             'Model_Name=?', (model_name,)).fetchall()
        if len(result) > 0:
            for detail in result:
                global update_image_name
                img = detail[4]
                update_image_name = img
            return render_template('edit_models.html', result_all=result, img=img)
        else:
            flash("No matching records found for '{}'.".format(model_name), 'warning')
            return render_template('edit_models.html', img=img)

    return render_template("edit_models.html", img=img)


@app.route('/delete_data/<int:id>', methods=['POST'])
@login_required
def delete_data(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM coordinates WHERE id = ?', (id,))
    model_name = os.path.splitext(update_image_name)
    del_remaining = cursor.execute('select id,x,y,Image from coordinates where Model_Name= ?',
                                   (model_name[0],))
    images_dict = {}
    for i in del_remaining:
        x, y, image, text = i[1], i[2], i[3], i[0]
        if image not in images_dict:
            images_dict[image] = []
        images_dict[image].append((int(x), int(y), text))
    for image in images_dict:
        del_coordinates_update(images_dict[image], image)
    conn.commit()
    conn.close()
    return render_template("edit_models.html")


@app.route('/update_models', methods=['GET', 'POST'])
@login_required
def update_models():
    global update_image_name
    update_name = update_image_name
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    modelType = cur.execute("select Type from coordinates where Image=?", (update_image_name,)).fetchone()
    cleaned_elements = tuple(element.strip("(),'") for element in modelType)
    modelType = cleaned_elements[0]
    # print(modelType)
    return render_template("update_models.html", update_name=update_name, modelType=modelType)


@app.route('/update_click', methods=['POST'])
@login_required
def update_click():
    data = request.get_json()
    x = data['x']
    y = data['y']
    value = data['value']
    defectArea = data['defectArea']
    modelType = data.get('modelType', 'default_value_if_missing')
    response_data = {'x': x, 'y': y, 'value': value, defectArea: 'defectArea', modelType: 'modelType'}
    global update_image_name
    update_name = update_image_name
    model_name = os.path.splitext(update_name)
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO coordinates (x, y, Description,Model_Name, Image,Defect_Area,Type)"
                " VALUES (?,?,?,?,?,?,?)", (x, y, value, model_name[0], update_name, defectArea, modelType))
    details = cur.execute("select id from coordinates where(x=? and  y=? and  Description=? and"
                          " Model_Name=? and Image=? and Defect_Area=?)",
                          (x, y, value, model_name[0], update_name, defectArea))
    for i in details:
        coordinates(x, y, update_name, i[0])
    cur.connection.commit()
    cur.close()
    return jsonify(response_data)


@app.route('/user_page', methods=['POST', 'GET'])
@login_required
def user_page():
    if request.method == "POST":
        if 'cat' in request.form:
            return redirect(url_for('take_test', model='CAT'))
        elif 'aoi' in request.form:
            return redirect(url_for('take_test', model='AOI'))
    return render_template("user_home_screen.html", user_name=users_name())


@app.route('/take_test/<model>', methods=['GET', 'POST'])
@login_required
def take_test(model):
    test_details = ""
    file_name = ""
    if request.method == "GET":
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        languages = cur.execute('SELECT Model_Name FROM coordinates').fetchall()
        unique_words = []
        seen_words = set()
        for language_tuple in languages:
            language = language_tuple[0]
            if language not in seen_words:
                seen_words.add(language)
                unique_words.append(language)
        return render_template("take_test.html", languages=unique_words, user_name=users_name(),
                               model=model)
    if request.method == "POST":
        search_test = request.form["messages"]
        conn = get_db_connection()
        cur = conn.cursor()
        test_detail = cur.execute('SELECT Model_Name, Image FROM coordinates WHERE Model_Name=? and Type = ?',
                                  (search_test, model)).fetchone()
        conn.close()
        if test_detail:
            global test_image_name, test_file_name
            img = cv2.imread('_internal/static/second_folder/%s' % test_detail[1])
            current_date = datetime.date.today()
            formatted_date = current_date.strftime("%d-%m-%Y")
            file_ext = os.path.splitext(test_detail[1])
            file_name = search_test + "_" + formatted_date + "_" + current_user.username + file_ext[1]
            test_file_name = file_name
            test_image_name = search_test
            copied_image = img.copy()
            save_path = ('_internal/static/test_photos/%s' % file_name)
            cv2.imwrite(save_path, copied_image)
            return render_template('take_test.html', test_details=test_detail, file_name=file_name,
                                   user_name=users_name(), model=model)
        else:
            flash("No matching records found for '{}'.".format(search_test), 'warning')
    return render_template("take_test.html", test_details=test_details, file_name=file_name,
                           user_name=users_name(), model=model)


@app.route('/model_test/<model>', methods=['GET', 'POST'])
@login_required
def model_test(model):
    global test_file_name
    return render_template("test_page.html", update_name=test_file_name,
                           user_name=users_name(), model=model)


@app.route('/model_test_click', methods=['POST'])
@login_required
def model_test_click():
    data = request.get_json()
    x = data['x']
    y = data['y']
    index_number = data.get('index')
    response_data = {'x': x, 'y': y, 'index': index_number}
    data_list = [x, y]
    global test_image_name, total_score, test_file_name, correct_index, total_click
    model_name = os.path.splitext(test_image_name)
    coordinates_test(x, y, test_file_name, index_number + 1)
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    details = cur.execute('select X,Y from coordinates WHERE Model_Name = ?', (model_name[0],)).fetchall()
    total_score = len(details)
    total_click = index_number + 1
    global score, percent
    for i in details:
        if score <= total_score:
            if (int(i[0]) - 50 <= int(data_list[0]) <= (int(i[0]) + 50)) and (
                    int(i[1]) - 50 <= int(data_list[1]) <= (int(i[1]) + 50)):
                score += 1
                print(index_number + 1)
                correct_index.append(index_number + 1)
                percent = (score / total_score) * 10
    cur.connection.commit()
    cur.close()
    return jsonify(response_data)


@app.route('/test_score')
@login_required
def Test_score():
    global percent, total_score, test_image_name, test_file_name, correct_index, total_click
    percent = int(percent)
    current_date = datetime.date.today()
    date = current_date.strftime("%d-%m-%Y")
    model_name = os.path.splitext(test_image_name)
    cleaned_elements = tuple(element.strip("(),'") for element in model_name)
    model_name = cleaned_elements[0]
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    model = cur.execute('SELECT Type FROM coordinates WHERE Model_Name=? ',
                        (model_name,)).fetchone()
    cleaned_model = tuple(element.strip("(),'") for element in model)
    model = cleaned_model[0]
    cur.execute(
        "INSERT INTO Test_Details (Model_Name,username,score,Total_Question,Test_img,Type,Name) VALUES (?,?,?,?,?,?,?)",
        (model_name, current_user.username, percent, total_score, test_file_name, model, users_name()))
    if int(total_click) > 0:
        mis_points = abs(len(correct_index) - int(total_click))
    else:
        mis_points = 0
    user_name = cur.execute("Select name from users where  username = ?", (current_user.username,)).fetchone()
    cleaned_elements = tuple(element.strip("(),'") for element in user_name)
    user_name = cleaned_elements[0]
    coordinates_test_details(user_name, date, percent, test_file_name, model_name, correct_index,
                             total_score, mis_points)
    cur.connection.commit()
    cur.close()
    return render_template("test_score.html", score=percent, model=model)


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
