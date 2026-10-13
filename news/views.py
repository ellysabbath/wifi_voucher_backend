from django.shortcuts import render

# Create your views here.
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import News
from .serializers import NewsSerializer

User = get_user_model()


# =========================================================
# HELPERS
# =========================================================
def _paginate(request, queryset, serializer_class):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(200, max(1, int(request.query_params.get("page_size", 50))))
    except (TypeError, ValueError):
        page_size = 50

    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = queryset[start:end]

    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "results": serializer_class(items, many=True).data,
    }


def _resolve_author(request):
    """Fall back to the first superuser if no JWT is present."""
    if request.user and request.user.is_authenticated:
        return request.user

    return (
        User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_staff=True).first()
        or User.objects.first()
    )


# =========================================================
# LIST + CREATE
# =========================================================
class NewsListView(APIView):
    """
    GET  /api/news/   → list (filters: q, category, published)
    POST /api/news/   → create
    """

    def get(self, request):
        qs = News.objects.select_related("author").all().order_by("-created_at")

        q = request.query_params.get("q")
        category = request.query_params.get("category")
        published = request.query_params.get("published")

        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(content__icontains=q)
            )
        if category:
            qs = qs.filter(category=category)
        if published in {"true", "false"}:
            qs = qs.filter(is_published=(published == "true"))

        return Response(_paginate(request, qs, NewsSerializer))

    def post(self, request):
        author = _resolve_author(request)
        if not author:
            return Response(
                {"detail": "No user available to attribute this article."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = NewsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=author)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================================================
# DETAIL
# =========================================================
class NewsDetailView(APIView):
    """
    GET    /api/news/<uuid:pk>/
    PUT    /api/news/<uuid:pk>/
    PATCH  /api/news/<uuid:pk>/
    DELETE /api/news/<uuid:pk>/
    """

    def _get(self, pk):
        try:
            return News.objects.select_related("author").get(pk=pk)
        except News.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(NewsSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = NewsSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = NewsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND
            )
        obj.delete()
        return Response(
            {"detail": "Article deleted."}, status=status.HTTP_204_NO_CONTENT
        )