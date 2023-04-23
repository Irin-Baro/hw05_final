import tempfile
import shutil

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings

from posts.models import Post, Group, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='post_author')
        cls.another_user = User.objects.create_user(username='new_post_author')

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )

        cls.group = Group.objects.create(
            title='Заголовок группы',
            description='Описание группы',
            slug='test-slug',
        )

        cls.another_group = Group.objects.create(
            title='Заголовок другой группы',
            description='Описание другой группы',
            slug='another-slug',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_create_new_post(self):
        """Проверка создания новой записи."""
        self.authorized_user.force_login(self.another_user)
        Post.objects.all().delete()
        form_data = {
            'text': 'Новый пост',
            'group': self.group.id,
            'image': self.image
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), 1)
        new_post = Post.objects.get()
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.author, self.another_user)
        self.assertEqual(new_post.group_id, form_data['group'])
        self.assertEqual(new_post.image, f'posts/{self.image.name}')
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.another_user.username}))

    def test_edit_post(self):
        """Проверка редактирования записи."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Измененный текст',
            'group': self.another_group.id,
        }
        response = self.authorized_user.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        post = Post.objects.get(id=self.post.id)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group_id, form_data['group'])
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='some_author')

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

        cls.comment_form_data = {
            'text': 'Тестовый комментaрий',
            'post_id': cls.post.id,
        }

    def setUp(self):
        self.unauthorized_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_unauthorized_user_can_not_add_comment(self):
        """Проверка добавления комментария неавторизованным пользователем."""
        Comment.objects.all().delete()
        response = self.unauthorized_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=self.comment_form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), 0)
        self.assertFalse(Comment.objects.filter(
            text='Тестовый коммент',
            post=self.post.id,
            author=self.user).exists()
        )
        self.assertRedirects(
            response,
            f"{reverse('users:login')}?next="
            f"{reverse('posts:add_comment', kwargs={'post_id': self.post.id})}"
        )

    def test_authorized_user_can_add_comment(self):
        """Проверка добавления комментария авторизованным пользователем."""
        Comment.objects.all().delete()
        response = self.authorized_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=self.comment_form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.get(post_id=self.post.id)
        self.assertEqual(comment.text, self.comment_form_data['text'])
        self.assertEqual(comment.post_id, self.post.id)
        self.assertEqual(comment.author, self.user)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
