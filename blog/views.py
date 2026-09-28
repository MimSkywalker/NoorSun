from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, ListView

from core.throttling import check_throttle, get_client_ip, record_failed_attempt
from .forms import PostCommentForm
from .models import Post, PostCategory, PostComment


class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        qs = Post.objects.filter(status=Post.Status.PUBLISHED).select_related(
            'category', 'author'
        ).prefetch_related('tags')

        category_slug = self.request.GET.get('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug).distinct()

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(title__icontains=q)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = PostCategory.objects.all()
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Post.objects.filter(status=Post.Status.PUBLISHED).select_related(
            'category', 'author'
        ).prefetch_related('tags', 'comments')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approved_comments'] = self.object.comments.filter(
            is_approved=True)
        context['comment_form'] = PostCommentForm(user=self.request.user)
        return context


class PostCommentCreateView(CreateView):
    model = PostComment
    form_class = PostCommentForm
    http_method_names = ['post']

    def dispatch(self, request, *args, **kwargs):
        self.post_obj = get_object_or_404(
            Post, slug=kwargs['slug'], status=Post.Status.PUBLISHED
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        instance = PostComment(post=self.post_obj)
        if self.request.user.is_authenticated:
            instance.user = self.request.user
        kwargs['instance'] = instance
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            ip = get_client_ip(self.request)
            result = check_throttle(scope='blog_comment', ip=ip)
            if not result.allowed:
                messages.error(
                    self.request, "تعداد ثبت نظر بیش از حد مجاز بود. کمی بعد تلاش کنید.")
                return redirect(self.post_obj.get_absolute_url())
            record_failed_attempt(scope='blog_comment', ip=ip)

        messages.success(
            self.request, "نظر شما ثبت شد و پس از تأیید مدیر نمایش داده خواهد شد.")
        return super().form_valid(form)

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.post_obj.get_absolute_url())

    def get_success_url(self):
        return self.post_obj.get_absolute_url()
