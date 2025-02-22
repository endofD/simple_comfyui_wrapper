import os
import json
import jwt
from flask import Flask, request, jsonify, send_from_directory
from urllib import request as url_request
from urllib.parse import urlencode
import datetime
import string
import uuid
import websocket
import time
import random
import threading
import queue

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
# ComfyUI API settings
COMFYUI_SERVER_ADDRESS = "127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())
FLASK_ADDR='http://127.0.0.1:5000'

# Load credentials from credentials.json
with open('credentials.json', 'r') as f:
    credentials = json.load(f)
    users = credentials['users']

SECRET_KEY = '0ed4fc625d9122e387e1e88b61fb40bb'

track_order = {}
track_set=set()
task_queue = queue.Queue()
cache_result = {}

#lock = threading.Lock()



#FIFO scheduler
def add_track(user,task):
    global track_order
    global track_set
    #order,status=[done,queue,executing],result=img_url,task
    if (user in track_order.keys()):
        #same request from frontend click
        return None
    track_set.add(user)
    track_order[user] = { 'o' : len(track_set)-1, 's' : 'queue','r':'','t':task }
    task_queue.put(user)
    return True

def order_update_status(user,s,url='NA'):
    global track_order
    track_order[user]['s']=s
    track_order[user]['r']=url

def pop_task_to_cache(user):
    global track_order
    global track_set
    global cache_result
    cache_result[user] = track_order.pop(user)
    track_set.remove(user)

def order_status_update():
    global track_order
    for u in track_order.keys():
        track_order[u]['o'] = track_order[u]['o'] - 1

def get_user_from_token():
    token = request.headers.get('Authorization').split(' ')[1]
    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])['user']

def fifo_scheduler():
    global track_order
    while True:
        user = task_queue.get()
        order_update_status(user,'excuting')
        task=track_order[user]['t']
        p=task['call'](task) #wait
        order_update_status(user,'done',p)
        pop_task_to_cache(user)
        order_status_update()
        task_queue.task_done()
        time.sleep(0.5)


# Token Function
def generate_token(user):
    payload = {
        'user': user,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user'] in users
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False

def auth_required(f):
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        token = auth_header.split(' ')[1]
        if not verify_token(token):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

#Comfyui api
def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = url_request.Request(f"http://{COMFYUI_SERVER_ADDRESS}/prompt", data=data)
    return json.loads(url_request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urlencode(data)
    with url_request.urlopen(f"http://{COMFYUI_SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with url_request.urlopen(f"http://{COMFYUI_SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def process_comfyui(prompt):
    # Connect to ComfyUI and get images
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFYUI_SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = []

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                output_images.append(image_data)
    ws.close()
    return output_images
    # Return first image URL


#backend help functions
def save_img_result(dir_name,name_tag,img_s):
    date_str = datetime.datetime.now().strftime('%y%m%d')
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    comfyui_img_dir=os.path.join(dir_name,date_str,CLIENT_ID)
    comfyui_img_absdir=os.path.join(os.path.dirname(__file__),comfyui_img_dir)
    os.makedirs(comfyui_img_absdir, exist_ok=True)
    image_name = name_tag + "_" + random_str +'.png'
    image_abspath = os.path.join(comfyui_img_absdir,image_name)
    image_path = os.path.join(comfyui_img_dir,image_name)
    with open(image_abspath, 'wb') as f:
        f.write(img_s)
    return (image_path,)

def check_cache(login_user):
    if login_user in cache_result.keys():
        img_url = cache_result[login_user]['r']
        del cache_result[login_user]
        return img_url
    return None

def get_queue_nr(login_user):
    if login_user in track_order.keys():
        return track_order[login_user]['o']
    return None

def wait_cache_img(login_user,timeout=60):
    print("====wait cache in=======")
    tt=0 
    (img_url,intime)=(None,False)
    while(tt <= timeout):
        if login_user in cache_result.keys():
            img_url = cache_result[login_user]['r']
            intime = True
            del cache_result[login_user]
            break
        time.sleep(1)
        tt = tt + 1
    return (img_url,intime)

def get_promp_from_json(json_file):
    # Load prompt from file
    prompt_file_path = os.path.join(os.path.dirname(__file__), 'data', json_file)
    if not os.path.exists(prompt_file_path):
        return (None,False)
    try:
        with open(prompt_file_path, 'r') as f:
            prompt = json.load(f)
    except Exception as e:
        return (None,False)
    return (prompt,True)


#API for different workflow

def api1(task):   #t2i    input: text
    prompt = task['prompt']
    prompt['42']['inputs']['text'] = task['text']
    output_images = process_comfyui(prompt)
    (p,) = save_img_result("comfyui_img","t2i",output_images[0])
    return f"{FLASK_ADDR}/{p}"
    
def api2(task):   #i2i    input: url
    prompt = task['prompt']
    prompt['69']['inputs']['url'] = task['url']
    output_images = process_comfyui(prompt)
    (p,) = save_img_result("comfyui_img","i2i",output_images[0])
    return f"{FLASK_ADDR}/{p}"
 


thread = threading.Thread(target=fifo_scheduler)
thread.start()

#api1 

@app.route('/api/prompt_process', methods=['POST'])
@auth_required
def process_text():
    login_user = get_user_from_token()
    #check the finished task in cache_result
    img_result = check_cache(login_user)
    print(f" try get cache  in user {login_user}")
    if (img_result):
        print(f"--- found cache record for  {login_user}")
        return jsonify({ 'imageUrl': img_result,'message': "Cache result processed" }) ,200

    #check the queue status
    if (login_user in track_order.keys()):
        queue_nr = get_queue_nr(login_user)
        if (queue_nr >0) :
            return jsonify({ 'imageUrl': 'queue','message': f"Your last task result in Queue {queue_nr} , please wait" }) ,200
        else:
            if (track_order[login_user]['s'] == "executing"):
                return jsonify({ 'imageUrl': 'executing','message': f"Your have executing jobs, please wait" }) ,200

    # Get text from frontend
    data = request.get_json()
    text = data.get('text')
    task = {}

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    # Load prompt from file
    (prompt,ret,) = get_promp_from_json('api_test.json')
    if(ret):
        task['prompt'] = prompt
    else:
        return jsonify({'error': 'Prompt json file error'}), 500

    # Update task
    task['text'] = text
    task['call'] = api1


    if (add_track(login_user,task)):
        # add task to queue
        if(track_order[login_user]['o'] == 0):
            #there is no task in queue , waiting for the result and return
            (img_result,get_done,) = wait_cache_img(login_user,120)
            if (get_done):
                return jsonify({ 'imageUrl': img_result, 'message': f"prompt succeed" }),200
            else:
                return jsonify({ 'imageUrl': 'timeout','message': f"timeout for last job" }),400
        else:
            #there are some tasks in queue return the queue status
            queue_nr = get_queue_nr(login_user)
            if (queue_nr):
                return jsonify({ 'imageUrl': 'Queue','message': f"Your task in Queue {queue_nr} , please wait" }), 200
    else:
        return jsonify({'error': 'click too much'}), 500

#api2
@app.route('/api/process_img', methods=['POST'])
@auth_required
def process_img():
    login_user = get_user_from_token()
    #check the finished task in cache_result
    img_result = check_cache(login_user)
    print(f" try get cache  in user {login_user}")
    if (img_result):
        return jsonify({ 'imageUrl': img_result,'message': "Prompt processed" }) ,200

    #check the queue status
    if (login_user in track_order.keys()):
        queue_nr = get_queue_nr(login_user)
        if (queue_nr >0) :
            return jsonify({ 'imageUrl': 'queue','message': f"Your last task result in Queue {queue_nr} , please wait" }) ,200
        else:
            if (track_order[login_user]['s'] == "executing"):
                return jsonify({ 'imageUrl': 'executing','message': f"Your have executing jobs, please wait" }) ,200

    # Get text from frontend

    data = request.get_json()
    url = data.get('imageUrl')
    task = {}

    if not url:
        return jsonify({'error': 'No img url provided'}), 400

   # Load prompt from file
    (prompt,ret,) = get_promp_from_json('api_test_img.json')
    if(ret):
        task['prompt'] = prompt
    else:
        return jsonify({'error': 'Prompt json file error'}), 500

    # Update task
    task['url'] = url
    task['call'] = api2

    # Update text in prompt


    if (add_track(login_user,task)):
        # add task to queue
        if(track_order[login_user]['o'] == 0):
            #there is no task in queue , waiting for the result and return
            (img_result,get_done,) = wait_cache_img(login_user,120)
            if (get_done):
                return jsonify({ 'imageUrl': img_result }),200
            else:
                return jsonify({ 'imageUrl': 'timeout','message': f"timeout for last job" }),400
        else:
            #there are some tasks in queue return the queue status
            queue_nr = get_queue_nr(login_user)
            if (queue_nr):
                return jsonify({ 'imageUrl': 'Queue','message': f"Your task in Queue {queue_nr} , please wait" }), 200
    else:
        return jsonify({'error': 'click too much'}), 500

@app.route('/upload', methods=['POST'])
@auth_required
def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        # Generate dynamic upload directory
        (p,) = save_img_result('uploads','i2i',file.read())   #define the upload dir and name tags
        return jsonify({'message': 'File successfully uploaded', 'filename': file.filename,
         'upload_path': f"{FLASK_ADDR}/{p}"}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if username in users and users[username] == password:
        token = generate_token(username)
        return jsonify({'token': token}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

#uploads dir should mapping to save_img_result dir name in upload_file()
@app.route('/uploads/<sdate>/<client_id>/<file_name>')
def serve_uploads(sdate,client_id,file_name):
    return send_from_directory(os.path.join('uploads',sdate,client_id),file_name)

#comfyui img save dir name shoud mapping to  save_img_result dir name in  api2()
@app.route('/comfyui_img/<sdate>/<client_id>/<file_name>')
def serve_comfyui_url(sdate,client_id,file_name):
    return send_from_directory(os.path.join('comfyui_img',sdate,client_id),file_name)

#optional provide http default service
@app.route('/<filex>')
def show_file(filex):
    return send_from_directory('frontend', filex)

if __name__ == '__main__':
    # Ensure the base upload folder exists
    app.run(debug=True)
