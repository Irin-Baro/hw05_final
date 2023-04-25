from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm


def paginator(queryset, page_number):
    paginator = Paginator(queryset, settings.POST_PER_PAGE)
    return paginator.get_page(page_number)


def index(request):
    """Главная страница"""
    page_obj = paginator(
        Post.objects.select_related('author', 'group'), request.GET.get('page')
    )
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница сообщества"""
    group = get_object_or_404(Group, slug=slug)
    page_obj = paginator(
        group.posts.select_related('author'), request.GET.get('page')
    )
    context = {
        'page_obj': page_obj,
        'group': group,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Страница пользователя"""
    author = get_object_or_404(User, username=username)
    page_obj = paginator(
        author.posts.select_related('group'), request.GET.get('page')
    )
    following = (
        request.user.is_authenticated
        and author.following.select_related('user').exists()
    )
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница записи"""
    post = get_object_or_404(
        Post.objects.select_related('author', 'group'), pk=post_id)
    comments = post.comments.select_related('author')
    context = {
        'post': post,
        'comments': comments,
        'form': CommentForm()
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Страница для публикации записи"""
    form = PostForm(request.POST or None,
                    files=request.FILES or None
                    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """Страница для редактирования записи"""
    post = get_object_or_404(
        Post.objects.select_related('author', 'group'), pk=post_id)
    if post.author == request.user:
        form = PostForm(request.POST or None,
                        files=request.FILES or None,
                        instance=post
                        )
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post.id)
        return render(request, 'posts/create_post.html', {'form': form})
    return redirect('posts:post_detail', post.id)


@login_required
def add_comment(request, post_id):
    """Страница добавления комментария"""
    post = get_object_or_404(
        Post.objects.select_related('author', 'group'), pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Страница с постами авторов, на которых подписан пользователь"""
    page_obj = paginator(
        Post.objects
            .select_related('author', 'group')
            .filter(author__following__user=request.user),
        request.GET.get('page')
    )
    return render(request, 'posts/follow.html', {'page_obj': page_obj})


@login_required
def profile_follow(request, username):
    """Страница, чтобы подписаться на автора"""
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', author)


@login_required
def profile_unfollow(request, username):
    """Страница, чтобы отписаться от автора"""
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username)
