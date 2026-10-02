#solo como documentacion para manejo con swagger, no se usa en el codigo

REGISTER_RESPONSES = {
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "email_in_use": {
                        "summary": "Email already in use",
                        "value": {"detail": "Email already in use."}
                    },
                    "club_in_use": {
                        "summary": "Club name already in use",
                        "value": {"detail": "Club already in use."}
                    },
                    "password_invalid": {
                        "summary": "Password does not meet requirements",
                        "value": {"detail": "Password must contain at least one digit."}
                    }
                }
            }
        },
    },
    409: {
        "description": "Conflict",
        "content": {
            "application/json": {
                "examples": {
                    "conflict": {
                        "summary": "Conflict in register time",
                        "value": {"detail": "Conflict in register time."},
                    }
                }
            }
        }
    }
}


CREATE_TEAM_RESPONSES = {
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "team_name_in_use": {
                        "summary": "Team name already in use for this user",
                        "value": {"detail": "Team name already in use for this user."}
                    },
                    "team_incomplete": {
                        "summary": "Team incomplete, must be 3 starters & 3 subtitutes",
                        "value": {"detail": "Team incomplete, must be 3 starters & 3 subtitutes."}
                    },
                    "player_in_use":{
                        "summary": "Some players are already in use",
                        "value": {"detail": "Some players are already in use."}
                    }
                }
            }
        },
    },
    401: {
    "description": "Unauthorized",
    "content": {
        "application/json": {
            "examples": {
                "invalid_token": {
                    "summary": "Invalid or missing token",
                    "value": {"detail": "Could not validate credentials."}
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "examples": {
                    "user_not_owner": {
                        "summary": "Not allowed to create teams for another user",
                        "value": {"detail": "Not allowed to create teams for another user."}
                    },
                    "player_not_owner": {
                        "summary": "User is not the owner of the player",
                        "value": {"detail": "User is not the owner of the player."}
                    },
                    "behavior_not owner": {
                        "summary": "User is not the owner of the behavior",
                        "value": {"detail": "User is not the owner of the behavior."}
                    }
                }
            }
        }
    },
    404:{
        "description": "Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "user_not_found":{
                        "summary": "User can not find.",
                        "value": {"detail": "User can not find."}
                    },
                    "player_not_found":{
                        "summary": "Player can not find.",
                        "value": {"detail": "Player can not find."}
                    },
                    "behavior_not_found":{
                        "summary": "Behavior can not find.",
                        "value": {"detail": "Behavior can not find."}
                    }
                }
            }
        }
    },
    409: {
        "description": "Conflict",
        "content": {
            "application/json": {
                "examples": {
                    "conflict": {
                        "summary": "Conflict in creation time",
                        "value": {"detail": "Conflict in creation time."},
                    }
                }
            }
        }
    }
}

LOGIN_RESPONSES = {
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_credentials": {
                        "summary": "Invalid email or password",
                        "value": {
                            "status": "401 Unauthorized",
                            "message": "Invalid email or password."
                        }
                    }
                }
            }
        }
    }
}