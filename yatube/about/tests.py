from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse


class StaticViewsTests(TestCase):

    def test_urls_static_pages_guest_uses_correct_template(self):
        """URL-адрес для гостя использует соответствующий шаблон."""
        templates_url_names = {
            'about/author.html': '/about/author/',
            'about/tech.html': '/about/tech/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_(self):
        """URL-адреса about для гостя возвращают 200."""
        url_names = {
            '/about/author/',
            '/about/tech/',
        }
        for address in url_names:
            with self.subTest(address=address):
                test_urls = self.client.get(address)
                self.assertEqual(test_urls.status_code, HTTPStatus.OK)

    def test_hardurls_uses_correct_reverse_about(self):
        """Хардурлы about соответствуют URL."""
        hard_url_names = {
            'about:author': '/about/author/',
            'about:tech': '/about/tech/',
        }
        for name, url in hard_url_names.items():
            reverse_name = reverse(name)
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(reverse(name), url)
