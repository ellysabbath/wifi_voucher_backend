from django.shortcuts import render

# Create your views here.
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event
from .serializers import EventSerializer

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


def _resolve_creator(request):
    """
    No permissions in this project.
    Try to attach the authenticated user if a valid JWT is present.
    Otherwise fall back to the first superuser, then any staff, then any user.
    """
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
class EventListView(APIView):
    """
    GET  /api/events/    → list (filters: q, category, from, to)
    POST /api/events/    → create
    """

    def get(self, request):
        qs = Event.objects.select_related("created_by").all().order_by(
            "event_date", "event_time"
        )

        q = request.query_params.get("q")
        category = request.query_params.get("category")
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")

        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(location__icontains=q)
            )
        if category:
            qs = qs.filter(category=category)
        if date_from:
            qs = qs.filter(event_date__gte=date_from)
        if date_to:
            qs = qs.filter(event_date__lte=date_to)

        return Response(_paginate(request, qs, EventSerializer))

    def post(self, request):
        creator = _resolve_creator(request)
        if not creator:
            return Response(
                {"detail": "No user available to attribute this event."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=creator)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================================================
# DETAIL — RETRIEVE / UPDATE / DELETE
# =========================================================
class EventDetailView(APIView):
    """
    GET    /api/events/<uuid:pk>/
    PUT    /api/events/<uuid:pk>/
    PATCH  /api/events/<uuid:pk>/
    DELETE /api/events/<uuid:pk>/
    """

    def _get(self, pk):
        try:
            return Event.objects.select_related("created_by").get(pk=pk)
        except Event.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(EventSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = EventSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = EventSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response(
            {"detail": "Event deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )