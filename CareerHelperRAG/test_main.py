import pytest
from flask import Flask, jsonify, request
from flask_testing import TestCase
from your_flask_app import app, complete_prompt  # replace 'your_flask_app' with the name of your Flask app file

class test_main(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        return app

    def test_chat_endpoint(self):
        with self.client:
            response = self.client.post('/chat', json={'user_input': 'Hello'})
            self.assertEqual(response.status_code, 200)
            self.assertIn('response', response.json)

            response = self.client.post('/chat', json={})
            self.assertEqual(response.status_code, 400)
            self.assertIn('response', response.json)
            self.assertEqual(response.json['response'], 'Invalid request. Missing user_input parameter.')

    def test_complete_prompt(self):
        result = complete_prompt('Hello')
        self.assertIsInstance(result, str)

        result = complete_prompt('')
        self.assertIsInstance(result, str)

if __name__ == '__main__':
    pytest.main()