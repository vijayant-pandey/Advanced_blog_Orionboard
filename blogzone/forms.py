from django import forms
from .models import Post, Comment, Category, ContactMessage



class PostForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        help_text="Enter tags separated by commas (e.g. science, physics, environment)",
    )

    class Meta:
        model = Post
        fields = ["category", "title", "quote", "content", "cover_image", "status"]
        widgets = {
            "quote": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Optional highlight quote (will show as a big quote in the article)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        # pull user out of kwargs so we can customize choices
        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        # base choices for normal authors
        choices = [
            (Post.STATUS_DRAFT, "Draft"),
            (Post.STATUS_PENDING, "Submit for approval"),
        ]

        # if staff / superuser, also allow published from UI
        if user and user.is_staff:
            choices.append((Post.STATUS_PUBLISHED, "Published"))


        # Only allow Draft or Pending in UI; Published is for admin
        self.fields["status"].choices = choices
        self.fields["category"].queryset = Category.objects.all().order_by("name")
        self.fields["category"].required = False
# ============================================================================================

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3}),
        }
# ============================================================================================
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["first_name", "last_name", "email", "phone", "subject", "message"]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "First Name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Last Name",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Phone",
            }),
            "subject": forms.TextInput(attrs={
                "class": "form-control", 
                "placeholder": "Subject"
            }),
            "message": forms.Textarea(attrs={
                "class": "",
                "placeholder": "Enter a message",
                "rows": 4,
            }),
        }