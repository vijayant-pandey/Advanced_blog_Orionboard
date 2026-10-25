from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.core.mail import send_mail
from urllib.parse import urlparse, parse_qs


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
# =============================================================================================

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
# =============================================================================================


class Post(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"  
    STATUS_PUBLISHED = "published"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Submit for approval"),
        (STATUS_PUBLISHED, "Published"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    quote = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    cover_image = models.ImageField(upload_to="post_covers/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    view_count = models.PositiveIntegerField(default=0)
    edit_count = models.PositiveIntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)

    is_featured = models.BooleanField(
        default=False,
        verbose_name="Featured / Popular",
        help_text="Tick to show this post in the Popular sidebar widget.",
    )


    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    # def get_absolute_url(self):
    #     """
    #     Return canonical URL for the post detail view.
    #     Matches blogzone.urls pattern: path('<slug:slug>/', post_detail, name='post_detail')
    #     """
    #     try:
    #         return reverse('blogzone:post_detail', kwargs={'slug': self.slug})
    #     except Exception:
    #         # Fallback to slug path if reverse fails for any reason
    #         return f"/blog/{self.slug}/"


# =============================================================================================
class PostSection(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    order = models.PositiveIntegerField(default=0)
    heading = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to="post_sections/", blank=True, null=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Section {self.order} of {self.post.title}"
# =============================================================================================

class Like(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user} likes {self.post}"


# =============================================================================================
class Comment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        super().clean()
        # A comment cannot be its own parent
        if self.parent and self.parent_id == self.id:
            raise ValidationError("A comment cannot be its own parent.")

        # A reply must belong to the same post as its parent
        if self.parent and self.parent.post_id != self.post_id:
            raise ValidationError("Parent comment must be on the same post.")

    def __str__(self):
        # return f"Comment by {self.user} on {self.post}"
        snippet = (self.content[:30] + "...") if len(self.content) > 30 else self.content
        return f"{self.user.username} ({self.status}) on '{self.post.title}': {snippet}"

    @property
    def is_root(self):
        return self.parent is None


# ==========================================================================================
class ViewEvent(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="view_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="view_events",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"View on '{self.post.title}' at {self.created_at}"

# ============================================================================================
class FaqItem(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.question

# ================================================================================================



class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email}) - {self.subject or 'No subject'}"

# =================================================================================================
class Video(models.Model):
    title = models.CharField(max_length=200)
    youtube_url = models.URLField(help_text="Paste any YouTube URL")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0, help_text="Lower shows first")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def youtube_id(self):
        """
        Extract the video ID from various types of YouTube URLs.
        e.g.
        - https://www.youtube.com/watch?v=XXXX
        - https://youtu.be/XXXX
        - https://www.youtube.com/embed/XXXX
        - https://www.youtube.com/shorts/XXXX
        """
        url = urlparse(self.youtube_url)

        # youtu.be/XXXX
        if url.hostname and "youtu.be" in url.hostname:
            return url.path.lstrip("/")

        # youtube.com / m.youtube.com / www.youtube.com
        if url.hostname and "youtube" in url.hostname:
            # /watch?v=XXXX
            if url.path == "/watch":
                return parse_qs(url.query).get("v", [""])[0]

            # /embed/XXXX or /shorts/XXXX
            parts = url.path.split("/")
            if len(parts) >= 3 and parts[1] in ("embed", "shorts"):
                return parts[2]

        return ""

    @property
    def youtube_watch_url(self):
        """
        Clean watch URL that always works in a new tab.
        """
        vid = self.youtube_id
        return f"https://www.youtube.com/watch?v={vid}" if vid else self.youtube_url

    @property
    def thumbnail_url(self):
        """
        Use YouTube's default thumbnail if we have an ID.
        """
        vid = self.youtube_id
        if vid:
            return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
        return ""