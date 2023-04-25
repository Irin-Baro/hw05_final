import shutil
import tempfile
from math import ceil
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Post, Group, Comment, Follow
from posts.forms import PostForm

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='some_user')

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.unauthorized_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_post_is_in_the_lists_of_posts(self):
        """
        Проверка контекста в шаблонах index,
        follow_index, group_list и profile.
        """
        reverse_name_list = [
            (reverse('posts:index'), False),
            (reverse('posts:follow_index'), True),
            (reverse('posts:group_list', kwargs={
                'slug': self.group.slug}), False),
            (reverse('posts:profile', kwargs={
                'username': self.user.username}), False)
        ]
        for reverse_name, need_auth in reverse_name_list:
            with self.subTest(reverse_name=reverse_name):
                if not need_auth:
                    response = self.unauthorized_user.get(reverse_name)
                else:
                    follower_user = User.objects.create_user(
                        username='follower_user')
                    self.authorized_user.force_login(follower_user)
                    Follow.objects.create(
                        user=follower_user,
                        author=self.user)
                    response = self.authorized_user.get(reverse_name)
                self.assertEqual(response.context['page_obj'][0], self.post)

    def test_post_detail_show_correct_context(self):
        """Контекст в шаблоне post_detail соответствует ожидаемому."""
        response = self.unauthorized_user.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post'), self.post)

    def test_comment(self):
        """Проверка комментария в шаблоне post_detail"""
        comment = Comment.objects.create(
            post_id=self.post.id,
            author=self.user,
            text='Тестовый комментарий'
        )
        response = self.authorized_user.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertIn(comment, response.context.get('comments'))

    def test_create_post_show_correct_context(self):
        """Проверка корректности формы."""
        reverse_name_list = [
            (reverse('posts:post_create')),
            (reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        ]
        for reverse_name in reverse_name_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_user.get(reverse_name)
                self.assertIsInstance(response.context['form'], PostForm)

    def post_edit_page_shows_correct_post_in_form(self):
        """Проверка, что на странице редактирования в форме правильный пост"""
        response = self.authorized_user.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('form').instance, self.post)

    def test_check_post_with_group_not_on_wrong_page(self):
        """Проверка, что пост не попал в неверную группу."""
        self.new_group = Group.objects.create(
            title='Новая группа',
            description='Описание новой группы',
            slug='new-slug',
        )
        reverse_name = reverse('posts:group_list', kwargs={
            'slug': self.new_group.slug})
        response = self.unauthorized_user.get(reverse_name)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_index_cache(self):
        """Тестирование кеша на главной страницы"""
        response = self.authorized_user.get(reverse('posts:index'))
        Post.objects.all().delete()
        response_after_post_delete = self.authorized_user.get(
            reverse('posts:index'))
        self.assertEqual(response.content, response_after_post_delete.content)
        cache.clear()
        response_after_cache_clear = self.authorized_user.get(
            reverse('posts:index'))
        self.assertNotEqual(
            response.content, response_after_cache_clear.content)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.number_of_posts = randint(1, 23)

        cls.user = User.objects.create_user(username='some_user')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )

        posts = (Post(
            text=f'Тестовый пост {post_number}',
            group=cls.group,
            author=cls.user,
        ) for post_number in range(cls.number_of_posts))
        Post.objects.bulk_create(posts)

        cls.reverse_name_list = [
            (reverse('posts:index')),
            (reverse('posts:group_list', kwargs={'slug': 'test-slug'})),
            (reverse('posts:profile', kwargs={
                'username': 'some_user'}))
        ]

    def setUp(self):
        cache.clear()
        self.unauthorized_user = Client()

    def test_paginator_on_first_page(self):
        """Проверка количества постов на первой странице."""
        if self.number_of_posts < settings.POST_PER_PAGE:
            posts_on_first_page = self.number_of_posts
        else:
            posts_on_first_page = settings.POST_PER_PAGE
        for reverse_name in self.reverse_name_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.unauthorized_user.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']),
                                 posts_on_first_page)

    def test_paginator_on_last_page(self):
        """Проверка количества постов на последней странице."""
        last_page_number = ceil(self.number_of_posts
                                / settings.POST_PER_PAGE)
        if self.number_of_posts > settings.POST_PER_PAGE:
            if self.number_of_posts % settings.POST_PER_PAGE != 0:
                posts_on_last_page = (self.number_of_posts
                                      % settings.POST_PER_PAGE)
            else:
                posts_on_last_page = settings.POST_PER_PAGE
            for reverse_name in self.reverse_name_list:
                with self.subTest(reverse_name=reverse_name):
                    response = self.unauthorized_user.get(
                        reverse_name + f'?page={str(last_page_number)}')
                    self.assertEqual(len(response.context['page_obj']),
                                     posts_on_last_page)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_user = User.objects.create_user(username='author_user')
        cls.another_user = User.objects.create_user(username='another_user')

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.another_user)

    def test_user_can_follow(self):
        """Пользователь может подписаться на автора."""
        Follow.objects.all().delete()
        self.authorized_user.get(
            reverse('posts:profile_follow', kwargs={
                    'username': self.author_user.username})
        )
        self.assertEqual(Follow.objects.all().count(), 1)
        self.assertTrue(Follow.objects.filter(
            user=self.another_user, author=self.author_user).exists())

    def test_user_can_unfollow(self):
        """Пользователь может отписаться от автора."""
        Follow.objects.all().delete()
        Follow.objects.create(
            user=self.another_user,
            author=self.author_user)
        self.authorized_user.get(
            reverse('posts:profile_unfollow', kwargs={
                    'username': self.author_user.username}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_new_post_for_followers(self):
        """Новая запись не появляется в ленте неподписчиков."""
        post = Post.objects.create(
            author=self.author_user,
            text='Новая запись для тестирования ленты'
        )
        response = self.authorized_user.get(
            reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'])
