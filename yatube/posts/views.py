from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Follow, Group, Post, User
from .utils import paginator


@cache_page(20 * 1, key_prefix="index_page")
def index(request):
    posts = Post.objects.select_related('author', 'group').all()
    page_obj = paginator(request, posts=posts)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').all()
    page_obj = paginator(request, posts=posts)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group').all()
    page_obj = paginator(request, posts=posts)
    # if request.user.is_authentificated:
    if request.user.is_authenticated:
        follow_list = Follow.objects.filter(
            user=request.user, author=author).all()
        following = request.user != author and len(follow_list) != 0
        context = {
            'author': author,
            'following': following,
            'page_obj': page_obj,
        }
        return render(request, 'posts/profile.html', context)
    else:
        context = {
            'author': author,
            'page_obj': page_obj,
        }
        return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.order_by('-created').all()
    form = CommentForm(request.POST or None, files=request.FILES or None)
    context = {
        'form': form,
        'post': post,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', post.author.username)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'form': form,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts = (
        Post.objects
        .select_related('author', 'group')
        .filter(author__following__user=request.user)
    )
    page_obj = paginator(request, posts=posts)
    context = {
        'page_obj': page_obj
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follow_list = Follow.objects.filter(user=request.user, author=author).all()
    if request.user != author and len(follow_list) == 0:
        Follow.objects.create(
            author=author,
            user=request.user
        )
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username)
