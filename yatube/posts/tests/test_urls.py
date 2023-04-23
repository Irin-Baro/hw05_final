from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class PostUrlTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_user = User.objects.create_user(username='author_user')
        cls.another_user = User.objects.create_user(username='another_user')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )

        cls.post = Post.objects.create(
            author=cls.author_user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        self.unauthorized_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.author_user)

    def test_url_matches_page_name(self):
        """Соответствие адресов страниц их именам."""
        urls_for_page_names = [
            ('/', reverse('posts:index')),
            (f'/group/{self.group.slug}/', reverse(
                'posts:group_list', kwargs={'slug': self.group.slug})),
            (f'/profile/{self.author_user}/', reverse(
                'posts:profile', kwargs={
                    'username': self.author_user.username})),
            (f'/posts/{self.post.id}', reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id})),
            ('/create/', reverse('posts:post_create')),
            (f'/posts/{self.post.id}/edit/', reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id})),
            (f'/posts/{self.post.id}/comment/', reverse(
                'posts:add_comment', kwargs={'post_id': self.post.id}))
        ]
        for url, reverse_name in urls_for_page_names:
            with self.subTest(url=url):
                self.assertEqual(url, reverse_name)

    def test_urls_available_to_any_user(self):
        """Проверка доступности страниц пользователям."""
        urls_for_users = [
            (reverse('posts:index'),
                HTTPStatus.OK, False),
            (reverse('posts:group_list', kwargs={'slug': self.group.slug}),
                HTTPStatus.OK, False),
            (reverse('posts:profile', kwargs={
                     'username': self.author_user.username}),
                HTTPStatus.OK, False),
            (reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
                HTTPStatus.OK, False),
            (reverse('posts:post_create'),
                HTTPStatus.OK, True),
            (reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
                HTTPStatus.OK, True),
            ('/nonexisting_page/', HTTPStatus.NOT_FOUND, False)
        ]
        for reverse_name, http_status, need_auth in urls_for_users:
            with self.subTest(reverse_name=reverse_name):
                if not need_auth:
                    response = self.unauthorized_user.get(reverse_name)
                else:
                    response = self.authorized_user.get(reverse_name)
                self.assertEqual(response.status_code, http_status)

    def test_urls_redirect(self):
        """Проверка редиректов на другие страницы"""
        self.authorized_user.force_login(self.another_user)
        redirect_urls_list = [
            (reverse('posts:post_create'),
             f"{reverse('users:login')}?next={reverse('posts:post_create')}",
             False),
            (reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
             f"{reverse('users:login')}?next="
             f"{reverse('posts:post_edit', kwargs={'post_id': self.post.id})}",
             False),
            (reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
             reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
             True),
            (reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
             reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
             True),
            (reverse('posts:profile_follow',
                     kwargs={'username': self.author_user.username}),
             reverse('posts:profile',
                     kwargs={'username': self.author_user.username}),
             True),
            (reverse('posts:profile_unfollow',
                     kwargs={'username': self.author_user.username}),
             reverse('posts:profile',
                     kwargs={'username': self.author_user.username}),
             True)
        ]
        for reverse_name, redirect_url, user_auth in redirect_urls_list:
            with self.subTest(reverse_name=reverse_name):
                if not user_auth:
                    response = self.unauthorized_user.get(
                        reverse_name, follow=True)
                else:
                    self.authorized_user.force_login(self.another_user)
                    response = self.authorized_user.get(
                        reverse_name, follow=True)
                self.assertRedirects(response, redirect_url)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        templates_url_names = [
            (reverse('posts:index'), 'posts/index.html'),
            (reverse('posts:group_list', kwargs={'slug': self.group.slug}),
             'posts/group_list.html'),
            (reverse('posts:profile', kwargs={
                     'username': self.author_user.username}),
             'posts/profile.html'),
            (reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
             'posts/post_detail.html'),
            (reverse('posts:post_create'), 'posts/create_post.html'),
            (reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
             'posts/create_post.html')
        ]
        for reverse_name, template in templates_url_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_user.get(reverse_name)
                self.assertTemplateUsed(response, template)
