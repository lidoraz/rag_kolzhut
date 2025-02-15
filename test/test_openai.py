import unittest
from unittest.mock import patch

# Assuming get_openai_response is defined in the module openai_module
from kolzhut_rag.retrive import get_openai_response


class TestOpenAIResponse(unittest.TestCase):
    # @patch('openai_module.get_openai_response')
    def test_get_openai_response(self): # mock_get_openai_response
        # Arrange
        # mock_get_openai_response.return_value = "Expected response"

        user_query = "What time is it?"
        context_text= ""
        model = "gpt-4o-mini"
        response = get_openai_response(user_query, context_text, model, stream=True)
        for chunk in response:
            print(chunk)
        # # Assert
        # self.assertEqual(response, "Expected response")


if __name__ == '__main__':
    unittest.main()