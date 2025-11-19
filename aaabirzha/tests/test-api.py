from unittest.mock import patch
from fastapi.testclient import TestClient
from aaabirzha.main import app
import aaabirzha.main as main_module


client = TestClient(app)

class TestUserRegistration:
    @patch('main.db_fnc.create_user')
    @patch('main.hash_api_key')
    @patch('main.secrets.token_hex')
    def test_successful_user_registration(self, mock_token_hex, mock_hash_key, mock_create_user):
        mock_token_hex.return_value = "test123456789abc"

        expected_raw_key = "key-test123456789abc"

        test_hashed_key = "hashed_test_key_123"
        mock_hash_key.return_value = test_hashed_key

        mock_create_user.return_value = None

        user_data = {
            "name": "test_user"
        }

        response = client.post("/api/v1/public/register", json=user_data)

        assert response.status_code == 200

        response_data = response.json()
        assert "id" in response_data
        assert response_data["name"] == "test_user"

        mock_token_hex.assert_called_once_with(16)

        if getattr(main_module, 'USE_HASHED_API_KEYS', True):
            mock_hash_key.assert_called_once_with(expected_raw_key)
        else:
            mock_hash_key.assert_not_called()

        mock_create_user.assert_called_once()
        call_args = mock_create_user.call_args[0]

        user_id = call_args[0]
        assert isinstance(user_id, str) or hasattr(user_id, 'hex')

        assert call_args[1] == "test_user"
        assert call_args[2] is not None

    @patch('main.db_fnc.create_user')
    @patch('main.USE_HASHED_API_KEYS', True)
    @patch('main.hash_api_key')
    @patch('main.secrets.token_hex')
    def test_user_registration_with_hashed_keys(self, mock_token_hex, mock_hash_key, mock_create_user):
        mock_token_hex.return_value = "test123456789abc"

        test_hashed_key = "hashed_test_key_123"
        mock_hash_key.return_value = test_hashed_key

        mock_create_user.return_value = None

        user_data = {"name": "test_user_hashed"}

        response = client.post("/api/v1/public/register", json=user_data)

        assert response.status_code == 200

        mock_create_user.assert_called_once()
        db_call_args = mock_create_user.call_args[0]
        assert db_call_args[3] != test_hashed_key

    @patch('main.db_fnc.create_user')
    @patch('main.USE_HASHED_API_KEYS', False)
    @patch('main.hash_api_key')
    @patch('main.secrets.token_hex')
    def test_user_registration_without_hashed_keys(self, mock_token_hex, mock_hash_key, mock_create_user):
        mock_token_hex.return_value = "test123456789abc"
        expected_raw_key = "key-test123456789abc"

        mock_create_user.return_value = None

        user_data = {"name": "test_user_raw"}

        response = client.post("/api/v1/public/register", json=user_data)

        assert response.status_code == 200

        mock_hash_key.assert_not_called()

        mock_create_user.assert_called_once()
        db_call_args = mock_create_user.call_args[0]
        assert db_call_args[3] != expected_raw_key
        assert db_call_args[4] == expected_raw_key

    @patch('main.db_fnc.create_user')
    def test_user_registration_with_minimal_data(self, mock_create_user):
        mock_create_user.return_value = None

        user_data = {
            "name": "minimal_user"
        }

        response = client.post("/api/v1/public/register", json=user_data)

        assert response.status_code == 200
        assert response.json()["name"] == "minimal_user"
        mock_create_user.assert_called_once()

    def test_user_creation_returns_valid_structure(self):
        with patch('main.db_fnc.create_user') as mock_db, \
                patch('main.secrets.token_hex') as mock_token, \
                patch('main.hash_api_key') as mock_hash:
            mock_token.return_value = "mocked_hex_value"
            mock_hash.return_value = "mocked_hash_value"
            mock_db.return_value = None

            user_data = {"name": "structure_test_user"}

            response = client.post("/api/v1/public/register", json=user_data)

            assert response.status_code == 200
            user_response = response.json()

            assert "id" in user_response
            assert "name" in user_response
            assert user_response["name"] == "structure_test_user"