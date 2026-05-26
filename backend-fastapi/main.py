# import 
from fastapi import FastAPI, HTTPException
from datamodel import SQLModels
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# instantiates app
app = FastAPI()

app.mount("/video", StaticFiles(directory="video"), name="video")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# handles get request to root...root being the "/"
@app.get("/users")
def get_users():
    pass 
    results  =  SQLModels.get_users() 
    return results 


# get single user 
@app.get("/users/:id") 
def get_user():
    pass 



# post new video 
@app.post("/video")
def post_video():
    pass


# get all the videos 
@app.get("/videos") 
def get_videos():
    return SQLModels.get_videos()


# get videos for a user
@app.get("/users/{user_id}/videos")
def get_videos_by_user(user_id: int): 
    return SQLModels.get_videos_by_user(user_id)
