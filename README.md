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











