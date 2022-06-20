from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User

User = get_user_model()


class PostURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User1')
        cls.user2 = User.objects.create_user(username='NotAuthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )
        cls.hard_url_names = (
            ('posts:index', None, '/',),
            (
                'posts:group_list',
                (cls.group.slug,),
                f'/group/{cls.group.slug}/'
            ),
            (
                'posts:profile',
                (cls.user.username,),
                f'/profile/{cls.user.username}/'
            ),
            ('posts:post_create', None, '/create/'),
            (
                'posts:post_edit',
                (cls.post.pk,),
                f'/posts/{cls.post.pk}/edit/'
            ),
            ('posts:post_detail', (cls.post.pk,), f'/posts/{cls.post.pk}/'),
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user2)

    def test_404(self):
        """Запрос к несуществующей странице возвращает ошибку 404
        и кастомный шаблон"""
        response = self.client.get('/gertert')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_urls_uses_correct_reverse(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        templates_url_names = (
            ('posts:index', None, 'posts/index.html',),
            ('posts:group_list', (self.group.slug,), 'posts/group_list.html'),
            ('posts:profile', (self.user.username,), 'posts/profile.html'),
            ('posts:post_create', None, 'posts/create_post.html'),
            ('posts:post_edit', (self.post.pk,), 'posts/create_post.html'),
            ('posts:post_detail', (self.post.pk,), 'posts/post_detail.html'),
        )
        for name, args, template in templates_url_names:
            reverse_name = reverse(name, args=args)
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_hardurls_uses_correct_reverse(self):
        """Хардурл соответствует URL."""
        cache.clear()
        for name, args, hard_urls in self.hard_url_names:
            reverse_name = reverse(name, args=args)
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(reverse_name, hard_urls)

    def test_urls_for_author(self):
        """URL-адреса для автора доступны."""
        for name, args, not_used in self.hard_url_names:
            reverse_name = reverse(name, args=args)
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_for_not_author(self):
        """URL-адреса для НЕ автора доступы."""
        for name, args, not_used in self.hard_url_names:
            reverse_name = reverse(name, args=args)
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_2.get(reverse_name)
                if name == 'posts:post_edit':
                    self.assertRedirects(
                        response,
                        reverse('posts:post_detail', args=(self.post.pk,))
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_for_anonimus(self):
        """URL-адреса для гостя доступны."""
        for name, args, not_used in self.hard_url_names:
            reverse_name = reverse(name, args=args)
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                reverse_login = reverse('users:login')
                if name in ['posts:post_edit', 'posts:post_create']:
                    self.assertRedirects(
                        response, f'{reverse_login}?next={reverse_name}')
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)
