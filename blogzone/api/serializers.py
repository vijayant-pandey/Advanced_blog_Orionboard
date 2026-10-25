from rest_framework import serializers
from django.db.models import Count, Q
from django.utils import timezone

from ..models import Post, Comment, Category, Tag, PostSection



class PostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "slug",
            "title",
            "quote",
            "content",
            "category",
            "tags",
            "author",
            "view_count",
            "edit_count",
            "likes_count",
            "comments_count",
            "status",
            "published_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "view_count",
            "edit_count",
            "likes_count",
            "comments_count",
            "status",
            "published_at",
            "created_at",
        ]

    def get_author(self, obj):
        return obj.author.username if obj.author_id else None

    def get_category(self, obj):
        return obj.category.name if obj.category_id else None

    def get_tags(self, obj):
        return [tag.name for tag in obj.tags.all()]

# ===================================================================================
class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    parent = serializers.IntegerField(source="parent_id", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "content",
            "parent",
            "created_at",
            "status",
        ]
        read_only_fields = ["id", "user", "created_at", "status"]

    def get_user(self, obj):
        return obj.user.username if obj.user_id else None

# ===================================================================================
class CommentCreateSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Comment
        fields = ["content", "parent_id"]

    def validate(self, attrs):
        content = attrs.get("content", "").strip()
        if not content:
            raise serializers.ValidationError("Content cannot be empty.")
        return attrs

# ======================================================================================

class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["content"]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        return value

    def to_representation(self, instance):
        # Use full read serializer for output
        return CommentSerializer(instance, context=self.context).data


# ========================================================================================

class DailyViewsSerializer(serializers.Serializer):
    date = serializers.DateField()
    views = serializers.IntegerField()

# ======================================================================================

class PostSectionInputSerializer(serializers.Serializer):
    heading = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField()
    order = serializers.IntegerField(required=False)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Section content cannot be empty.")
        return value

# =====================================================================================
class PostWriteSerializer(serializers.ModelSerializer):
    # tags sent as a list of names, e.g. ["science", "physics"]
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    # sections as an array of {heading, content}
    sections = PostSectionInputSerializer(many=True, required=False)

    class Meta:
        model = Post
        fields = [
            "title",
            "quote",
            "content",
            "category",
            "status",
            "cover_image",   # optional; use multipart/form-data
            "tags",
            "sections",
        ]

    def _handle_status(self, instance, status_value, user):
        """
        Apply status rules:
        - Non-staff: cannot directly publish; 'published' becomes 'pending'.
        - Staff: can publish; sets published_at if newly published.
        """
        if status_value == Post.STATUS_PUBLISHED and not user.is_staff:
            status_value = Post.STATUS_PENDING

        instance.status = status_value

        if (
            instance.status == Post.STATUS_PUBLISHED
            and instance.published_at is None
        ):
            instance.published_at = timezone.now()

    def _handle_tags_and_categories(self, post, tags_list):
        """
        Create tags & auto-add categories based on tag names.
        """
        tag_objs = []
        for name in tags_list:
            clean = name.strip()
            if not clean:
                continue
            tag_obj, _ = Tag.objects.get_or_create(name=clean)
            tag_objs.append(tag_obj)
            Category.objects.get_or_create(name=clean)

        if tag_objs:
            post.tags.set(tag_objs)
        else:
            post.tags.clear()

    def _handle_sections(self, post, sections_list):
        """
        Recreate sections from input.
        """
        # wipe old sections
        PostSection.objects.filter(post=post).delete()

        for idx, section_data in enumerate(sections_list):
            content = section_data.get("content", "").strip()
            if not content:
                continue
            heading = section_data.get("heading", "").strip()
            order = section_data.get("order", idx)

            PostSection.objects.create(
                post=post,
                order=order,
                heading=heading,
                content=content,
                # image via API can be added later if needed
            )

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        tags_data = validated_data.pop("tags", [])
        sections_data = validated_data.pop("sections", [])

        # Prepare instance without saving yet
        post = Post(**validated_data)
        post.author = user

        # Generate unique slug from title
        from django.utils.text import slugify
        base_slug = slugify(post.title)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        post.slug = slug

        # Status rules
        status_value = validated_data.get("status", Post.STATUS_DRAFT)
        self._handle_status(post, status_value, user)

        post.view_count = 0
        post.edit_count = 0
        post.save()

        # Tags and categories
        self._handle_tags_and_categories(post, tags_data)

        # Sections
        self._handle_sections(post, sections_data)

        return post

    def update(self, instance, validated_data):
        request = self.context["request"]
        user = request.user

        tags_data = validated_data.pop("tags", None)
        sections_data = validated_data.pop("sections", None)

        # Update simple fields
        for field in ["title", "quote", "content", "category", "cover_image"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if "status" in validated_data:
            status_value = validated_data["status"]
            self._handle_status(instance, status_value, user)

        # Increment edit count
        instance.edit_count = (instance.edit_count or 0) + 1
        instance.save()

        # Tags
        if tags_data is not None:
            self._handle_tags_and_categories(instance, tags_data)

        # Sections
        if sections_data is not None:
            self._handle_sections(instance, sections_data)

        return instance

    def to_representation(self, instance):
        """
        Use the read-only PostSerializer for output, so we don't have to
        re-implement tag/section representation here.
        """
        return PostSerializer(instance, context=self.context).data