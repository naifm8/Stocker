from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import UserRegistrationForm, UserUpdateForm, UserCreationForm, MemberForm
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from inventory.models import Category

User = get_user_model()

def is_admin(u): 
    return u.is_authenticated and getattr(u, "role", "") == "admin"

class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST, request.FILES)
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
    return redirect('inventory:home')


'''user crud logics '''

User = get_user_model()

@login_required
@user_passes_test(is_admin)
def add_member(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            selected = form.cleaned_data['categories']
            Category.objects.filter(pk__in=selected.values('pk')).update(assigned_to=user)
            messages.success(request, "Member added successfully.")
            return redirect('inventory:admin_dashboard')
    else:
        form = MemberForm()
    return render(request, 'accounts/add_member.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_member(request, pk):
    member = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            user = form.save()
            selected = form.cleaned_data['categories']

            
            Category.objects.filter(assigned_to=user).exclude(pk__in=selected.values('pk')).update(assigned_to=None)
            Category.objects.filter(pk__in=selected.values('pk')).update(assigned_to=user)

            messages.success(request, "Member updated successfully.")
            return redirect('inventory:admin_dashboard')
    else:
        initial_categories = Category.objects.filter(assigned_to=member)
        form = MemberForm(instance=member, initial={'categories': initial_categories})
    return render(request, 'accounts/edit_member.html', {'form': form, 'member': member})


@login_required
@user_passes_test(is_admin)
def delete_member(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if user_obj.pk == request.user.pk:
            messages.error(request, "You cannot delete your own account.")
            return redirect('inventory:admin_dashboard')
        user_obj.delete()
        messages.success(request, "Member deleted successfully.")
        return redirect('inventory:admin_dashboard')
    return render(request, 'accounts/confirm_delete_member.html', {'member': user_obj})
