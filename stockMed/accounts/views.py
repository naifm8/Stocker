from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.role == 'admin':
            return reverse_lazy('inventory:admin_dashboard')
        elif user.role == 'employee':
            return reverse_lazy('inventory:employee_dashboard')
        else:
            return reverse_lazy('accounts:login')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')
