from flask import Flask, request, jsonify, session
from flask_cors import CORS 
import hashlib
import os
import secrets
from datetime import datetime
from blake3 import blake3
import mysql.connector

app = Flask(__name__)
CORS(app)  
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

@app.route('/hash', methods=['GET'])
def get_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hash_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

@app.route('/hash/<int:id>', methods=['DELETE'])
def delete_history(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hash_history WHERE id = %s", (id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        conn.close()
        return jsonify({'status': 'failed', 'message': f'Data dengan ID {id} tidak ditemukan'}), 404

    # Hapus data
    cursor.execute("DELETE FROM hash_history WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'success', 'message': f'Data berhasil dihapus'}), 200



@app.route('/login', methods=['POST'])
def hash_password(password):
    return hashlib.blake2b(password.encode()).hexdigest()

def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({'status': 'failed', 'message': 'Username dan password harus diisi'}), 400

    password_hash = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM user WHERE username=%s', (username,))
    user = cursor.fetchone()

    if not user or user['password'] != password_hash:
        cursor.close()
        conn.close()
        return jsonify({'status': 'failed', 'message': 'Username atau password salah'}), 401

    token = secrets.token_hex(32)
    cursor.execute('UPDATE user SET session_token=%s WHERE id=%s', (token, user['id']))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        'status': 'success',
        'message': 'Login berhasil!',
        'token': token
    }), 200         

if __name__ == '__main__':
    app.run(debug=True)