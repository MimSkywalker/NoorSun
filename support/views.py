from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView

from .forms import TicketCreateForm, TicketMessageForm
from .models import FAQ, Ticket, TicketMessage
from core.throttling import check_throttle, record_failed_attempt


class TicketCreateView(CreateView):
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'support/ticket_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        instance = Ticket()
        if self.request.user.is_authenticated:
            instance.user = self.request.user
        kwargs['instance'] = instance
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            ip = get_client_ip(self.request)
            identifier = form.cleaned_data.get(
                'guest_phone') or form.cleaned_data.get('guest_email')
            throttle_result = check_throttle(
                scope='ticket_create', ip=ip, identifier=identifier)
            if not throttle_result.allowed:
                messages.error(
                    self.request, "تعداد ثبت درخواست بیش از حد مجاز بود. کمی بعد تلاش کنید.")
                return self.form_invalid(form)

        message_body = form.cleaned_data.pop('message')
        if self.request.user.is_authenticated:
            form.instance.guest_name = form.instance.guest_phone = form.instance.guest_email = ''
        response = super().form_valid(form)

        TicketMessage.objects.create(
            ticket=self.object,
            sender_type=TicketMessage.SenderType.USER,
            sender_user=self.request.user if self.request.user.is_authenticated else None,
            body=message_body,
        )
        messages.success(self.request, "تیکت شما ثبت شد.")
        return response

    def get_success_url(self):
        if self.request.user.is_authenticated:
            return reverse('support:ticket_detail', kwargs={'pk': self.object.pk})
        return reverse('support:ticket_created', kwargs={'pk': self.object.pk})


class TicketCreatedView(View):
    """"""

    def get(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, user__isnull=True)
        return render(request, 'support/ticket_created.html', {'ticket': ticket})


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'support/ticket_list.html'
    context_object_name = 'tickets'

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user)


class TicketDetailView(LoginRequiredMixin, View):
    """IDOR-safe: همیشه با user=request.user فیلتر می‌شود (همان الگوی Address/Order فازهای قبل)."""

    def get_ticket(self, request, pk):
        return get_object_or_404(Ticket, pk=pk, user=request.user)

    def get(self, request, pk):
        ticket = self.get_ticket(request, pk)
        form = TicketMessageForm()
        return render(request, 'support/ticket_detail.html', {'ticket': ticket, 'form': form})

    def post(self, request, pk):
        ticket = self.get_ticket(request, pk)
        if ticket.status == Ticket.Status.CLOSED:
            messages.error(
                request, "این تیکت بسته شده و امکان ارسال پیام جدید نیست.")
            return redirect('support:ticket_detail', pk=pk)

        form = TicketMessageForm(request.POST)
        if form.is_valid():
            TicketMessage.objects.create(
                ticket=ticket,
                sender_type=TicketMessage.SenderType.USER,
                sender_user=request.user,
                body=form.cleaned_data['body'],
            )
            messages.success(request, "پیام شما ثبت شد.")
            return redirect('support:ticket_detail', pk=pk)

        return render(request, 'support/ticket_detail.html', {'ticket': ticket, 'form': form})


class FAQListView(ListView):
    model = FAQ
    template_name = 'support/faq_list.html'
    context_object_name = 'faqs'

    def get_queryset(self):
        return FAQ.objects.filter(is_active=True)
