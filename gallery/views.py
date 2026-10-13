from django.shortcuts import render

# Create your views here.
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GalleryItem
from .serializers import GalleryItemSerializer

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
        page_size = min(500, max(1, int(request.query_params.get("page_size", 100))))
    except (TypeError, ValueError):
        page_size = 100

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
class GalleryListView(APIView):
    """
    GET  /api/gallery/   → list (filters: q, album)
    POST /api/gallery/   → create
    """

    def get(self, request):
        qs = GalleryItem.objects.select_related("uploaded_by").all().order_by(
            "-created_at"
        )

        q = request.query_params.get("q")
        album = request.query_params.get("album")

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(album__icontains=q))
        if album:
            qs = qs.filter(album=album)

        return Response(_paginate(request, qs, GalleryItemSerializer))

    def post(self, request):
        uploader = _resolve_uploader(request)
        if not uploader:
            return Response(
                {"detail": "No user available to attribute this upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = GalleryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=uploader)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================================================
# DETAIL
# =========================================================
class GalleryDetailView(APIView):
    """
    GET    /api/gallery/<uuid:pk>/
    PUT    /api/gallery/<uuid:pk>/
    PATCH  /api/gallery/<uuid:pk>/
    DELETE /api/gallery/<uuid:pk>/
    """

    def _get(self, pk):
        try:
            return GalleryItem.objects.select_related("uploaded_by").get(pk=pk)
        except GalleryItem.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Gallery item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(GalleryItemSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Gallery item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GalleryItemSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Gallery item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GalleryItemSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Gallery item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response(
            {"detail": "Gallery item deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )