import os
import uuid
import zipfile
import io
from flask import Flask, request, render_template, send_file, abort, jsonify, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB limit

# Create uploads folder if missing
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_share_path(share_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], share_id)
    os.makedirs(path, exist_ok=True)
    return path

# ---------- HOME PAGE ----------
@app.route('/')
def index():
    # List all existing shares (for demo)
    shares = []
    for item in os.listdir(app.config['UPLOAD_FOLDER']):
        share_path = os.path.join(app.config['UPLOAD_FOLDER'], item)
        if os.path.isdir(share_path):
            files = os.listdir(share_path)
            shares.append({
                'id': item,
                'files': files,
                'count': len(files)
            })
    return render_template('index.html', shares=shares)

# ---------- UPLOAD FILES ----------
@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected files'}), 400

    share_id = str(uuid.uuid4())[:8]        # short unique ID
    share_path = get_share_path(share_id)

    uploaded = []
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(share_path, filename))
            uploaded.append(filename)

    share_url = url_for('view_share', share_id=share_id, _external=True)

    return jsonify({
        'share_id': share_id,
        'share_url': share_url,
        'files': uploaded,
        'count': len(uploaded)
    })

# ---------- VIEW SHARE PAGE ----------
@app.route('/share/<share_id>')
def view_share(share_id):
    share_path = get_share_path(share_id)
    if not os.path.exists(share_path):
        abort(404)
    files = os.listdir(share_path)
    return render_template('share.html', share_id=share_id, files=files)

# ---------- DOWNLOAD ALL AS ZIP ----------
@app.route('/download/<share_id>')
def download_zip(share_id):
    share_path = get_share_path(share_id)
    if not os.path.exists(share_path):
        abort(404)

    files = os.listdir(share_path)
    if not files:
        abort(404)

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            file_path = os.path.join(share_path, file)
            zf.write(file_path, arcname=file)

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{share_id}.zip'
    )

# ---------- DOWNLOAD SINGLE FILE ----------
@app.route('/download/<share_id>/<filename>')
def download_single(share_id, filename):
    share_path = get_share_path(share_id)
    file_path = os.path.join(share_path, filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
