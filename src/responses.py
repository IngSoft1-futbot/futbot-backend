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
                    "username_in_use": {
                        "summary": "Username already in use",
                        "value": {"detail": "Username already in use."}
                    },
                    "password_invalid": {
                        "summary": "Password does not meet requirements",
                        "value": {"detail": "Password does not meet requirements."}
                    }
                }
            }
        },
    },
    409: {
        "description": "Conflict in register time",
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