from pydantic import BaseModel, EmailStr

class PACSS_attributes(BaseModel):
    power : int
    agility : int
    control : int
    speed : int
    strength : int

class Player(BaseModel):
    name : str
    shirt_numb : int
    pacss_attributes : PACSS_attributes


class Player_out(BaseModel):
    player_id : int
    name : str
    shirt_numb : int
    pacss_attributes : PACSS_attributes

class RequestBody(BaseModel):
    email : str
    password : str 
