from fastapi.testclient import TestClient

import app
from schemas import Player_out

client = TestClient(app.app)


def test_login_success(monkeypatch):

    def mock_auth_login(email, password):
        return "abc123token"

    monkeypatch.setattr(app, "auth_login", mock_auth_login)

    response = client.post(
        "/auth/login/",
        json={
            "email": "test@example.com",
            "password": "123456"
        }
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "200",
        "data": {
            "access_token": "abc123token",
            "token_type": "bearer"
        },
        "message": "Login successful."
    }


def test_login_invalid_credentials(monkeypatch):

    def mock_auth_login(email, password):
        return None

    monkeypatch.setattr(app, "auth_login", mock_auth_login)

    response = client.post(
        "/auth/login/",
        json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401

    assert response.json() == {
        "status": "401 Unauthorized",
        "message": "Invalid email or password."
    }


def test_create_player_success(monkeypatch):

    def mock_verify_player(player):
        return True

    def mock_create_player(user_id, player):
        return Player_out(
            player_id=1,
            name=player.name,
            shirt_numb=player.shirt_numb,
            pacss_attributes=player.pacss_attributes
        )

    monkeypatch.setattr(app, "verify_player", mock_verify_player)
    monkeypatch.setattr(app, "create_player", mock_create_player)

    response = client.post(
        "/users/10/players",
        json={
            "name": "Messi",
            "shirt_numb": 10,
            "pacss_attributes": {
                "power": 60,
                "agility": 60,
                "control": 60,
                "speed": 60,
                "strength": 60
            }
        }
    )
    
    assert response.status_code == 201

    assert response.json() == {
        "status": "201",
        "data": {
            "player_id": 1,
            "name": "Messi",
            "shirt_numb": 10,
            "pacss_attributes": {
                "power": 60,
                "agility": 60,
                "control": 60,
                "speed": 60,
                "strength": 60
            }
        },
        "message": "Player created successfully"
    }


def test_create_player_invalid_pacss(monkeypatch):

    def mock_verify_player(player):
        return False

    monkeypatch.setattr(app, "verify_player", mock_verify_player)

    response = client.post(
        "/users/10/players",
        json={
            "name": "Messi",
            "shirt_numb": 10,
            "pacss_attributes": {
                "power": 100,
                "agility": 100,
                "control": 100,
                "speed": 100,
                "strength": 100
            }
        }
    )
     
    assert response.status_code == 400

    assert response.json() == {
        "status": "400 Bad Request",
        "message": "PACSS attributes exceed the maximum allowed points."
    }