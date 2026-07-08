from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import RNGHistory
from accounts.forms import CustomRegisterForm
from accounts.forms import UserUpdateForm, ProfileUpdateForm


def register(request):
    if request.method == "POST":
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.save()

            return redirect("login")
    else:
        form = CustomRegisterForm()

    return render(request, "accounts/register.html", {"form": form})

@login_required
def history_page(request):
    qs = RNGHistory.objects.filter(user=request.user).order_by("-timestamp")
    paginator = Paginator(qs, 10)  # 10 history items per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "accounts/history.html", {"page_obj": page_obj})

@login_required
def profile_page(request):
    user = request.user
    is_admin = user.is_superuser or user.profile.user_type == "admin"

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, instance=user.profile)

        # 🔒 Non-admin protection
        if not is_admin:
            profile_form.fields.pop("user_type")
            profile_form.fields.pop("token")

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()

            profile = profile_form.save(commit=False)

            # 🔒 Force original values for non-admins (POST safety)
            if not is_admin:
                profile.user_type = user.profile.user_type
                profile.token = user.profile.token

            profile.save()

            messages.success(request, "Profile updated successfully.")
            return redirect("profile_page")
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=user.profile)

        if not is_admin:
            profile_form.fields.pop("user_type")
            profile_form.fields.pop("token")

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "is_admin": is_admin,
        },
    )

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def users_page(request):
    user = request.user
    is_admin = user.is_superuser or user.profile.user_type == "admin"

    if not is_admin:
        return redirect('/')

    if request.method == "POST":
        target_user_id = request.POST.get("user_id")
        new_type = request.POST.get("user_type")
        new_token = request.POST.get("token")

        try:
            target_user = User.objects.get(id=target_user_id)
            profile = target_user.profile

            profile.user_type = new_type
            profile.token = int(new_token)
            profile.save()

            messages.success(
                request,
                f"Updated {target_user.username} successfully."
            )
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        except ValueError:
            messages.error(request, "Invalid token value.")

        return redirect("users_page")

    users = User.objects.select_related("profile").order_by("username")

    return render(
        request,
        "accounts/users.html",
        {
            "users": users,
        }
    )