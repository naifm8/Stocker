from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import UserRegistrationForm

class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after registration
            messages.success(request, 'Account created successfully!')
            if user.role == 'admin':
                return redirect('inventory:admin_dashboard')
            else:
                return redirect('inventory:employee_dashboard')
        return render(request, 'accounts/register.html', {'form': form})


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

def logout_view(request):
    logout(request)
    return redirect('home')


