from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from store.cart import merge_session_cart_into_user

from .forms import LoginForm, ProfileForm, SignUpForm, UserForm
from .models import Profile


def register(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            merge_session_cart_into_user(request, user)
            messages.success(request, f'Welcome to FoodHub, {user.first_name}! Your account is ready.')
            return redirect('store:home')
    else:
        form = SignUpForm()
    return render(request, 'accounts/register.html', {'form': form})


class FoodHubLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    authentication_form = LoginForm

    def form_valid(self, form):
        response = super().form_valid(form)
        merge_session_cart_into_user(self.request, self.request.user)
        messages.success(self.request, f'Welcome back, {self.request.user.first_name or self.request.user.username}!')
        return response


class FoodHubLogoutView(LogoutView):
    next_page = 'store:home'


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile_obj)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=profile_obj)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })
