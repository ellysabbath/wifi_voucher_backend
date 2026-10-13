from django.shortcuts import render

# Create your views here.
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ministry
from .serializers import MinistrySerializer


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


class MinistryListView(APIView):
    """
    GET  /api/ministries/   → list
    POST /api/ministries/   → create
    """

    def get(self, request):
        qs = Ministry.objects.all().order_by("name")

        q = request.query_params.get("q")
        active = request.query_params.get("active")

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(leader_name__icontains=q)
            )
        if active in {"true", "false"}:
            qs = qs.filter(is_active=(active == "true"))

        return Response(_paginate(request, qs, MinistrySerializer))

    def post(self, request):
        serializer = MinistrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MinistryDetailView(APIView):
    """
    GET    /api/ministries/<uuid:pk>/
    PUT    /api/ministries/<uuid:pk>/
    PATCH  /api/ministries/<uuid:pk>/
    DELETE /api/ministries/<uuid:pk>/
    """

    def _get(self, pk):
        try:
            return Ministry.objects.get(pk=pk)
        except Ministry.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Ministry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MinistrySerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Ministry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MinistrySerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Ministry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MinistrySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Ministry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response(
            {"detail": "Ministry deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )