from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, F

User = get_user_model()


class Group(models.Model):
    """Модель сообщества"""
    title = models.CharField(
        max_length=200,
        verbose_name='Название сообщества',
        help_text='Укажите название сообщества'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='Уникальный фрагмент URL-адреса сообщества',
        help_text='Укажите уникальный фрагмент URL-адреса сообщества'
    )
    description = models.TextField(
        verbose_name='Описание сообщества',
        help_text='Здесь должно быть описание сообщества'
    )

    class Meta:
        verbose_name = 'Сообщество'
        verbose_name_plural = 'Сообщества'

    def __str__(self):
        return self.title


class Post(models.Model):
    """Модель записи"""
    NUMBER_OF_CHAR: int = 15

    text = models.TextField(
        verbose_name='Текст записи',
        help_text='Разместите здесь текст'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата публикации'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор записи',
        help_text='Укажите имя автора записи'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='posts',
        verbose_name='Сообщество',
        help_text='Укажите название сообщества'
    )
    image = models.ImageField(
        verbose_name='Картинка',
        help_text='Загрузите картинку',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return self.text[:self.NUMBER_OF_CHAR]


class Comment(models.Model):
    """Модель комментария"""
    NUMBER_OF_CHAR: int = 15

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Запись'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор комментария'
    )
    text = models.TextField(
        verbose_name='Текст комментария',
        help_text='Разместите здесь комментарий'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания комментария'
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return self.text[:self.NUMBER_OF_CHAR]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_followers'
            ),
            models.CheckConstraint(
                check=~Q(user=F('author')),
                name='not_follow_to_self'
            )
        )
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
