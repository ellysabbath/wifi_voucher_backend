from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Leader
from .serializers import LeaderSerializer

User = get_user_model()


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


class LeaderListView(APIView):
    """
    GET  /api/leaders/   → list (filters: q, active)
    POST /api/leaders/   → create
       Body: { "user_id": "<uuid>", "position": "...", "bio": "...",
               "display_order": 0, "is_active": true, "appointed_at": "YYYY-MM-DD" }
    """

    def get(self, request):
        qs = Leader.objects.select_related("user", "user__profile").all().order_by(
            "display_order", "id"
        )

        q = request.query_params.get("q")
        active = request.query_params.get("active")

        if q:
            qs = qs.filter(
                Q(position__icontains=q)
                | Q(bio__icontains=q)
                | Q(user__email__icontains=q)
                | Q(user__profile__full_name__icontains=q)
            )
        if active in {"true", "false"}:
            qs = qs.filter(is_active=(active == "true"))

        return Response(_paginate(request, qs, LeaderSerializer))

    def post(self, request):
        user_id = request.data.get("user_id")
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {"user_id": ["User not found."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Leader.objects.filter(user=user).exists():
                return Response(
                    {"user_id": ["This user is already a leader."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"user_id": ["user_id is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeaderDetailView(APIView):
    """
    GET    /api/leaders/<uuid:pk>/
    PUT    /api/leaders/<uuid:pk>/
    PATCH  /api/leaders/<uuid:pk>/
    DELETE /api/leaders/<uuid:pk>/
    """

    def _get(self, pk):
        try:
            return Leader.objects.select_related("user", "user__profile").get(pk=pk)
        except Leader.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Leader not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(LeaderSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Leader not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = LeaderSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Leader not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = LeaderSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response(
                {"detail": "Leader not found."}, status=status.HTTP_404_NOT_FOUND
            )
        obj.delete()
        return Response(
            {"detail": "Leader deleted."}, status=status.HTTP_204_NO_CONTENT
        )