from django.shortcuts import render

# Create your views here.
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book
from .serializers import BookSerializer

User = get_user_model()


# =========================================================
# HELPERS
# =========================================================
def _paginate(request, queryset, serializer_class):
    """Simple manual pagination — ?page=1&page_size=20"""
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(200, max(1, int(request.query_params.get("page_size", 20))))
    except (TypeError, ValueError):
        page_size = 20

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


def _resolve_uploader(request):
    """
    No permissions in this project.
    Try to attach the authenticated user if a valid JWT is present.
    Otherwise, fall back to the first superuser, then to any staff user.
    """
    if request.user and request.user.is_authenticated:
        return request.user

    # Fallback — keeps the ForeignKey non-null
    fallback = (
        User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_staff=True).first()
        or User.objects.first()
    )
    return fallback


# =========================================================
# LIST + CREATE
# =========================================================
class BookListView(APIView):
    """
    GET  /api/books/         → list (paginated + filters)
    POST /api/books/         → create
    """

    def get(self, request):
        qs = Book.objects.select_related("uploaded_by").all().order_by("-created_at")

        q = request.query_params.get("q")
        category = request.query_params.get("category")

        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(author__icontains=q)
                | Q(description__icontains=q)
            )
        if category:
            qs = qs.filter(category=category)

        return Response(_paginate(request, qs, BookSerializer))

    def post(self, request):
        uploader = _resolve_uploader(request)
        if not uploader:
            return Response(
                {"detail": "No user available to attribute this upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        # Require file_name explicitly, or derive it
        if not data.get("file_name"):
            return Response(
                {"file_name": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BookSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=uploader)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================================================
# DETAIL — RETRIEVE / UPDATE / DELETE
# =========================================================
class BookDetailView(APIView):
    """
    GET    /api/books/<uuid:pk>/
    PUT    /api/books/<uuid:pk>/
    PATCH  /api/books/<uuid:pk>/
    DELETE /api/books/<uuid:pk>/
    """

    def _get(self, pk):
        try:
            return Book.objects.select_related("uploaded_by").get(pk=pk)
        except Book.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(BookSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = BookSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND
            )
        obj.delete()
        return Response(
            {"detail": "Book deleted."}, status=status.HTTP_204_NO_CONTENT
        )