from http import HTTPStatus

from django.test import TestCase, Client


class ViewTestClass(TestCase):
    def setUp(self):
        self.client = Client()

    def test_error_page(self):
        """Проверка доступа к несуществующей странице"""
        response = self.client.get('/nonexist-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
