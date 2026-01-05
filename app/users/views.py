from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from .serializers import CustomUserSerializer, SignupSerializer, LoginSerializer
from .models import CustomUser


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoints for user authentication and profile management.
    Replaces template-based views with JSON API responses for React frontend.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def signup(self, request):
        """Register a new user."""
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user: CustomUser = serializer.save()
            login(request, user)
            return Response(
                {
                    'user': CustomUserSerializer(user).data,
                    'message': 'User registered successfully'
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Authenticate user and create session."""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data.get('user')
            if user:
                login(request, user)
                return Response(
                    {
                        'user': CustomUserSerializer(user).data,
                        'message': 'Login successful'
                    },
                    status=status.HTTP_200_OK
                )
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Logout the current user."""
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile."""
        user = request.user
        if user.is_authenticated:
            return Response(CustomUserSerializer(user).data)
        return Response(
            {'detail': 'Not authenticated'},
            status=status.HTTP_401_UNAUTHORIZED
        )

