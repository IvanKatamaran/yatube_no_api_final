import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from ..models import Group, Post, User

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group,
            image=cls.uploaded,
        )
        cls.name_request_tuple = (
            ('posts:index', None, None),
            ('posts:post_detail', (cls.post.id,), True),
            ('posts:profile', (cls.user.username,), None),
            ('posts:group_list', (cls.group.slug,), None),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_request(self, request, flag):
        cache.clear()
        response = self.authorized_client.get(request)
        if flag:
            post = response.context.get('post')
        else:
            post = response.context['page_obj'][0]
        with self.subTest('Общий тест атрибутов post не пройден', url=request):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.user)
            self.assertEqual(post.pub_date, self.post.pub_date)
            self.assertEqual(post.group.pk, self.group.pk)

    def test_general_pages_context(self):
        """Шаблоны index, profile, group_list, post_detail
        сформирован с правильным контекстом."""
        for url, arg, flag in self.name_request_tuple:
            self.check_request(request=reverse(url, args=arg), flag=flag)

    def test_index_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0]
        self.assertEqual(post.image.name, f'posts/{self.uploaded}')

    def test_group_list_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        post = response.context['page_obj'][0]
        self.assertEqual(post.image.name, f'posts/{self.uploaded}')
        self.assertEqual(response.context['group'], self.group)

    def test_profile_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user.username,)))
        post = response.context['page_obj'][0]
        self.assertEqual(post.image.name, f'posts/{self.uploaded}')
        self.assertEqual(response.context['author'], self.user)

    def test_post_detail_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.id,)))
        post = response.context.get('post')
        self.assertEqual(post.image.name, f'posts/{self.uploaded}')

    def test_group_list_context_new_group(self):
        """Пост попадает только в нужную группу."""
        new_post = Post.objects.create(
            author=self.user,
            text='Новый тестовый пост',
            group=self.group,
        )
        new_group = Group.objects.create(
            title='Новая группа',
            slug='test-slug-new',
            description='Описание для новой группы',
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(new_group.slug,)))
        self.assertEqual(len(response.context['page_obj']), 0)
        self.assertEqual(new_post.group, self.group)
        response2 = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        self.assertEqual(response2.context['page_obj'][0].group, self.group)

    def test_create_and_edit_post(self):
        """Тест контекста страниц создания и редактирования постов."""
        name_args = (
            ('posts:post_create', None),
            ('posts:post_edit', (self.post.id,)),
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for address, args in name_args:
            with self.subTest(address=address):
                response = self.authorized_client.get(
                    reverse(address, args=args)
                )
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get('form').fields.get(
                            value
                        )
                        self.assertIsInstance(form_field, expected)
                    self.assertIn('form', response.context)
                    self.assertIsInstance(response.context['form'], PostForm)

    def test_cache_index(self):
        """Тест кеширования главной страницы."""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        context_old = response.context.get('page_obj').object_list
        Post.objects.create(author=self.user, text='Тест кеширования',)
        context_new = response.context.get('page_obj').object_list
        self.assertEqual(context_old, context_new)
        cache.clear()
        self.assertEqual(context_old, context_new)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User11')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        for new_posts in range(settings.NEW_POSTS):
            Post.objects.create(
                text='текст для паджинатора',
                author=cls.user,
                group=cls.group,
            )

    def test_paginator(self):
        """Тест паджинаора, по 10 постов на страницу."""
        name_args = (
            ('posts:index', None),
            ('posts:group_list', (self.group.slug,)),
            ('posts:profile', (self.user.username,)),
        )
        for address, args in name_args:
            with self.subTest(address=address):
                reverse_name = reverse(address, args=args)
                pages = (
                    ('?page=1', settings.QUANTITY_POSTS),
                    ('?page=2', settings.QUANTITY_POSTS_NEXT_PAGE),
                )
                for page, count_posts in pages:
                    with self.subTest(page=page):
                        response = self.client.get(reverse_name + page)
                        self.assertEqual(
                            len(response.context['page_obj']), count_posts
                        )
