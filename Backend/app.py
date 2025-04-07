from flask import Flask, request, jsonify, session
import hashlib
import os
from datetime import datetime
from blake3 import blake3
import mysql.connector

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# --- Koneksi ke Database ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sttb"
    )

# --- Buat folder uploads jika belum ada ---
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Fungsi generate hash ---
def generate_hash(file_path, method):
    with open(file_path, 'rb') as f:
        file_data = f.read()

    if method == 'blake2b':
        return hashlib.blake2b(file_data).hexdigest()
    elif method == 'blake2s':
        return hashlib.blake2s(file_data).hexdigest()
    elif method == 'blake3':
        return blake3(file_data).hexdigest()
    else:
        return None

# --- Endpoint hashing file ---
@app.route('/hash', methods=['POST'])
def hash_file():
    file = request.files.get('file')
    method = request.form.get('method')

    if not file or not method:
        return jsonify({'error': 'File dan metode hashing wajib diisi'}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    hash_result = generate_hash(file_path, method)
    os.remove(file_path)

    if hash_result:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO hash_history (filename, method, hash_value) VALUES (%s, %s, %s)",
            (file.filename, method, hash_result)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'filename': file.filename,
            'method': method,
            'hash_value': hash_result,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 201
    else:
        return jsonify({'error': 'Metode hashing tidak dikenali'}), 400

# --- Endpoint untuk melihat history hashing ---
@app.route('/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hash_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE username=%s AND password=%s',username,password)
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
         return jsonify({
             "status" : "success",
             "message" : "login berhasil!"
         })
    else:
         return jsonify({
            "status" : "failed",
             "message" : "login gagal!"
         })
         



if __name__ == '__main__':
    app.run(debug=True)
 