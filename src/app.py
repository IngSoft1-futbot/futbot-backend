from fastapi import FastAPI, HTTPException, Body

from schemas import *

from fastapi.responses import JSONResponse

from tokenize import tokenize

from utils import verify_player

from product_repository import auth_login , create_player


app = FastAPI()

@app.post("/auth/login/") 
def login_endpoint(request : RequestBody):  
    user_token = auth_login(request.email , request.password)

    if user_token is None:
         return JSONResponse(
            status_code = 401,
            content={
                "status": "401 Unauthorized",
                "message": "Invalid email or password."
     })

    return {
        "status": "200",
        "data": {
            "access_token": user_token,
            "token_type": "bearer"
        },
       "message": "Login successful."
     }




@app.post("/users/{user_id}/players")
def create_user_player(user_id : int, player : Player):


    if (not verify_player(player)):
       return JSONResponse(
            status_code=400,
            content={
                "status": "400 Bad Request",
                "message": "PACSS attributes exceed the maximum allowed points."
            })
       
    
    created_player : Player_out = create_player(user_id ,player)
        
    content = {
             "status": "201",
             "data": created_player.model_dump(),
                "message": "Player created successfully"
         }
    return JSONResponse(status_code = 201,
    content=content)


