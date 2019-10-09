# coding=utf-8

from flask import Flask, send_from_directory, send_file, request
import socket, pythoncom, os, win32api, json, zipfile, shutil
from datetime import datetime

app = Flask(__name__)

@app.route('/RemoteFileExplorer')
def index():
    return send_from_directory('.', 'RemoteFileExplorer.html')

@app.route('/RemoteFileExplorer/resource/<file>')
def resource(file):
    return send_from_directory('.', file)

@app.route('/RemoteFileExplorer/hostname')
def hostname():
    return socket.gethostname()

def convert_bytes(num):
    for x in ['KB', 'MB', 'GB', 'TB']:
        num /= 1024.0
        if num < 1024.0: return "%3.1f %s" % (num, x)

def dir_info(path, name):
    full_path = os.path.join(path, name)
    return [ name, 
             "-", 
             datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S'), 
             "Folder" ]

def file_info(path, name):
    full_path = os.path.join(path, name)
    return [ name, 
             convert_bytes(os.stat(full_path).st_size), 
             datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%Y-%m-%d %H:%M:%S'), 
             os.path.splitext(name)[1].lower() ]

@app.route('/RemoteFileExplorer/list/')
@app.route('/RemoteFileExplorer/list/<path>')
def list_dir(path=None):
    pythoncom.CoInitialize()
    drives = win32api.GetLogicalDriveStrings().split('\\\000')[:-1]
    drives = [[drive, "-", "-", "Drive"] for drive in drives]
    folders = []
    files = []
    if path:
        if path.endswith(":"): path = path + "\\"
        for item in os.listdir(path):
            if os.path.isdir(os.path.join(path, item)):
                folders.append(dir_info(path, item))
            else:
                files.append(file_info(path, item))
    return json.dumps({ "drives": drives, "folders": folders, "files": files })

@app.route('/RemoteFileExplorer/make/<path>')
def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return "success"

def retrieve_paths(selection):
    paths = []
    for item_path in selection:
        if os.path.isdir(item_path):
            for root, directories, files in os.walk(item_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    paths.append(( file_path, os.path.relpath(file_path, os.path.join(item_path, '..')) ))
        else:
            paths.append(( item_path, os.path.relpath(item_path, os.path.join(item_path, '..')) ))
    return paths

@app.route('/RemoteFileExplorer/compress/<path>', methods=['POST'])
def compress_target(path):
    selection = request.form.getlist('selection[]')
    if len(selection) == 0: return "nothing selected"
    elif len(selection) == 1: basename = selection[0]
    else: basename = 'Inside[{0}]-Items[{1}]-Ts[{2}]'.format(os.path.basename(path), len(selection), datetime.now().strftime('%Y%m%d.%H%M%S.%f'))
    paths = retrieve_paths([os.path.join(path, item) for item in selection])
    filename = os.path.join(path, '{0}.zip'.format(basename))
    with zipfile.ZipFile(filename, 'w') as f:
        for file_path, rel_path in paths:
            f.write(file_path, rel_path)
    return "success"

@app.route('/RemoteFileExplorer/extract/<path>')
def extract_target(path):
    with zipfile.ZipFile(path, 'r') as f:
        f.extractall(os.path.dirname(path))
    return "success"

@app.route('/RemoteFileExplorer/download/<path>')
def download_target(path):
    if os.path.isfile(path):
        return send_file(path, as_attachment=True)
    else:
        return '"{0}" is a folder.'.format(path)

@app.route('/RemoteFileExplorer/upload/<path>', methods=['POST'])
def upload_to(path):
    file = request.files['file']
    file.save(os.path.join(path, file.filename))
    return "success"

def dest(path, item):
    return os.path.join(path, os.path.basename(item))

@app.route('/RemoteFileExplorer/move/<path>', methods=['POST'])
def move_to(path):
    selection = request.form.getlist('clipboard[]')
    for item in selection:
        if os.path.isdir(item) or os.path.isfile(item):
            shutil.move(item, path)
    return "success"

@app.route('/RemoteFileExplorer/copy/<path>', methods=['POST'])
def copy_to(path):
    selection = request.form.getlist('clipboard[]')
    for item in selection:
        if os.path.isdir(item):
            shutil.copytree(item, dest(path, item))
        elif os.path.isfile(item):
            shutil.copy2(item, path)
    return "success"

@app.route('/RemoteFileExplorer/rename/<path>', methods=['POST'])
def rename_target(path):
    old_path = os.path.join(path, request.form.get('oldName'))
    new_path = os.path.join(path, request.form.get('newName'))
    os.rename(old_path, new_path)
    return "success"

@app.route('/RemoteFileExplorer/remove/<path>')
def remove_target(path):
    if os.path.isfile(path): os.remove(path)
    else: shutil.rmtree(path)
    return "success"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
