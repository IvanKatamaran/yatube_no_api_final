import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm, CommentForm
from ..models import Group, Post, User, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FormViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group,
        )
        cls.form = PostForm()
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
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый коммент',
            post=cls.post,
        )
        cls.form_comment = CommentForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create(self):
        """Валидная форма создает запись в Post."""
        count_posts = Post.objects.count()
        form_data = {
            'text': 'Тестовая пост',
            'group': self.group.pk,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args=(self.user.username,))
        )
        self.assertEqual(Post.objects.count(), count_posts + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовая пост',
                group=self.group.pk,
                author=self.user.pk,
                image='posts/small.gif'
            ).exists
        )
        response2 = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        post = response2.context['page_obj'][0]
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image.name, f'posts/{self.uploaded}')
        self.assertEqual(response2.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет пост с post_id."""
        newgroup = Group.objects.create(
            title='Тестовая группа New',
            slug='test-slug-new',
            description='Тестовое описание New',
        )
        form_data = {
            'text': 'Тестовый пост edit',
            'group': newgroup.pk,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=(self.post.pk,)
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                args=(self.post.pk,))
        )
        response2 = self.authorized_client.get(
            reverse('posts:group_list', args=(newgroup.slug,)))
        post = response2.context['page_obj'][0]
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, newgroup)
        self.assertEqual(response2.status_code, HTTPStatus.OK)
        response3 = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        self.assertEqual(len(response3.context['page_obj']), 0)

    def test_post_create_anonimus(self):
        """Гость не может создать запись в Post."""
        count_posts = Post.objects.count()
        form_data = {
            'text': 'не автор',
            'group': self.group.pk,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            '/auth/login/?next=/create/'
        )
        self.assertEqual(Post.objects.count(), count_posts)

    def test_comment_anonimus(self):
        """Гость не может комментировать посты."""
        count_comments = Comment.objects.count()
        form_data = {
            'text': 'комментарий',
        }
        response = self.client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.pk}/comment/'
        )
        self.assertEqual(Comment.objects.count(), count_comments)

    def test_comment_authorized(self):
        """Валидная форма создает записи в Comment."""
        count_comments = Comment.objects.count()
        form_data = {
            'text': 'комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(self.post.pk,))
        )
        self.assertEqual(Comment.objects.count(), count_comments + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=self.comment.text,
                post=self.post.pk,
                author=self.user.pk,
            ).exists
        )
        response2 = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.pk,)))
        comment = response2.context['comments'][0]
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.post.author)
        self.assertEqual(comment.post.pk, self.post.pk)
