from django.urls import path
from .views import CustomLoginView, logout_view, RegisterView, edit_member, delete_member, add_member

app_name = 'accounts'

urlpatterns = [
    # authentication pages
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', RegisterView.as_view(), name='register'),

    # user management
    path('add-member/', add_member, name='add_member'),
    path('members/<int:pk>/edit/', edit_member, name='member_edit'),
    path('members/<int:pk>/delete/', delete_member, name='member_delete'),
]




