from django.shortcuts import render, redirect
from django.contrib.auth import logout


def home(request):
    return render(request, "home.html")


def logout_view(request):
    """
    Simple logout on GET, then redirect to home.
    """
    logout(request)
    return redirect("home")
