# Documentacion de respuestas para Swagger: se pasa en `responses=` de cada ruta en app.py.
# Los mensajes tienen que coincidir con los `detail` que devuelve app.py.

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
                        "summary": "Team incomplete, must be 3 starters & 3 substitutes",
                        "value": {"detail": "Team incomplete, must be 3 starters & 3 substitutes."}
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
                    "behavior_not_owner": {
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

CREATE_PLAYER_RESPONSES = {
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_points": {
                        "summary": "Points must total 300, each between 20 and 100",
                        "value": {"detail": "Points must total 300, each between 20 and 100."}
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
                        "summary": "Not allowed to create players for another user",
                        "value": {"detail": "Not allowed to create players for another user."}
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
                        "summary": "User could not be found.",
                        "value": {"detail": "User could not be found."}
                    }
                }
            }
        }
    }
}


# El login rechaza a quien ya manda un token valido
LOGIN_RESPONSES[400] = {
    "description": "Bad request",
    "content": {
        "application/json": {
            "examples": {
                "active_token": {
                    "summary": "Already has an active token",
                    "value": {"detail": "Ya posees un token activo. No puedes volver a iniciar sesion."}
                }
            }
        }
    },
}

GET_PLAYERS_RESPONSES = {
    401: CREATE_PLAYER_RESPONSES[401],
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "examples": {
                    "user_not_owner": {
                        "summary": "Not allowed to view players of another user",
                        "value": {"detail": "Not allowed to view players of another user."}
                    }
                }
            }
        }
    },
    404: CREATE_PLAYER_RESPONSES[404],
}

CREATE_FRIENDLY_MATCH_RESPONSES = {
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "id_mismatch": {
                        "summary": "Path and body ID mismatch",
                        "value": {"detail": "User ID in body does not match User ID in path."}
                    },
                    "invalid_duration": {
                        "summary": "Invalid match duration",
                        "value": {"detail": "Match duration must be between 1 and 5 minutes."}
                    },
                    "team_incomplete": {
                        "summary": "Team does not have exactly 3 starters",
                        "value": {"detail": "Team incomplete, must have exactly 3 starters."}
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
                        "summary": "Not allowed to create matches for another user",
                        "value": {"detail": "Not allowed to create matches for another user."}
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "user_not_found": {
                        "summary": "User not found",
                        "value": {"detail": "User not found."}
                    },
                    "team_not_found": {
                        "summary": "Team not found or does not belong to the user",
                        "value": {"detail": "Team not found or does not belong to the user."}
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
                        "summary": "Conflict in match creation",
                        "value": {"detail": "Conflict in match creation."}
                    }
                }
            }
        }
    }
}


GET_FRIENDLY_MATCHES_RESPONSES = {
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "examples": {
                    "internal_error": {
                        "summary": "Could not retrieve the available friendly matches",
                        "value": {"detail": "Internal Server Error"}
                    }
                }
            }
        }
    }
}

JOIN_FRIENDLY_MATCH_RESPONSES = {
    400: {
        "description": "Bad request",
        "content": {
            "application/json": {
                "examples": {
                    "own_match": {
                        "summary": "Cannot join your own match",
                        "value": {"detail": "User cannot join their own match."}
                    },
                    "team_incomplete": {
                        "summary": "Team does not have exactly 3 starters",
                        "value": {"detail": "Team incomplete, must have exactly 3 starters."}
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
                    "team_not_owner": {
                        "summary": "User is not the owner of the team",
                        "value": {"detail": "User is not the owner of the team."}
                    },
                    "not_authorized": {
                        "summary": "Missing or incorrect password for a private match",
                        "value": {"detail": "User is not authorized to join this match."}
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "match_not_found": {
                        "summary": "Match not found",
                        "value": {"detail": "Match not found."}
                    },
                    "team_not_found": {
                        "summary": "Team not found",
                        "value": {"detail": "Team not found."}
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
                    "already_taken": {
                        "summary": "Another player already joined",
                        "value": {"detail": "Unable to join: another player has already joined."}
                    },
                    "not_joinable": {
                        "summary": "Match finished or cancelled",
                        "value": {"detail": "The match is no longer available: it is in progress, finished, or cancelled."}
                    }
                }
            }
        }
    }
}