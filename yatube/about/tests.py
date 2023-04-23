from http import HTTPStatus

from django.test import TestCase, Client


class StaticPagesURLTests(TestCase):
    def setUp(self):
        self.user = Client()

    def test_about_url_exists_at_desired_location(self):
        """Проверка доступности адресов /about/."""
        url_names = {
            '/about/author/': HTTPStatus.OK,
            '/about/tech/': HTTPStatus.OK,
        }
        for address, response_code in url_names.items():
            with self.subTest(address=address):
                self.assertEqual(
                    self.user.get(address).status_code,
                    response_code
                )

    def test_about_url_uses_correct_template(self):
        """Проверка шаблонов для адресов /about/."""
        templates_url_names = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.user.get(address)
                self.assertTemplateUsed(response, template)
