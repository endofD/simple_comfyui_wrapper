# simple_comfyui_wrapper

Simple comfyui backend weksocket api wrapper  
simple frontend + Restfull api backend  


- rest api
- user management
- simple FIFO scheduler
- keep img from comfyui output
- 2 example for text input and img input



## restapi 

Light weight Flash framwork


## user management 

```json
{
  "users": {
    "user1": "password1",
    "user2": "password2"
  }
}
```

## FIFO scheduler

For each user only allow **one** instance  

if other user is executin ,request will be put in queue and return the Queue number.  
There is NO queue monitor code, you need create your own monitor code in your frontend.   
**Result will be cache** next submit will be **ignore** and get queue result from **cache**  


## all the upload and comfyui img will be keep

`data`  :  this DIR keep the Comfyui api workflow  
`uploads` : this DIR keep the user upload img  
`comfyui_img` : this DIR keep the img from Comfyui result

## frontend 2 example



# install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

change value  

`COMFYUI_SERVER_ADDRESS = "127.0.0.1:8188"`
`FLASK_ADDR='http://127.0.0.1:5000'`



![example_img1](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/1.png)


![example_img2](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/2.png)


![example_img3](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/3.png)


![example_img4](https://github.com/endofD/simple_comfyui_wrapper/raw/refs/heads/main/screen_shot/4.png)




# add workflow



1 copy the workflow api file into `data`

2 create a new `@app.route('/api/new_api', methods=['POST'])`  
load/overwrite value  and  **fill** the **task**

```python
(prompt,ret,) = get_promp_from_json('api_test.json')
data = request.get_json()
text = data.get('text')
task['prompt'] = prompt'
task['text'] = text
task['call'] = api1
```
get 


```python
def api1(task):   #t2i    input: text
    prompt = task['prompt']
    prompt['42']['inputs']['text'] = task['text']
    output_images = process_comfyui(prompt)
    (p,) = save_img_result("comfyui_img","t2i",output_images[0])
    return f"{FLASK_ADDR}/{p}"

```

just follow this template 


HAPPY hacking
