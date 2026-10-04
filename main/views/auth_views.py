from django.contrib.auth.views import LogoutView, LoginView
from django.urls import reverse_lazy
from ..forms import LoginUserForm


class LoginUser(LoginView):
    form_class = LoginUserForm
    template_name = 'main/LoginPage.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        return dict(list(context.items()))

    def get_success_url(self):
        return reverse_lazy('home')

