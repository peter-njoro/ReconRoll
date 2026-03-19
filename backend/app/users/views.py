from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from .serializers import CustomUserSerializer, SignupSerializer, LoginSerializer
from .models import User


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return None


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, CsrfExemptSessionAuthentication]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            login(request, user)
            return Response(
                {
                    'user': CustomUserSerializer(user).data,
                    'token': token.key,
                    'message': 'User registered successfully'
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data.get('user')
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                login(request, user)
                return Response(
                    {
                        'user': CustomUserSerializer(user).data,
                        'token': token.key,
                        'message': 'Login successful'
                    },
                    status=status.HTTP_200_OK
                )
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        # Delete token so it can't be reused
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_username(self, request):
        username = (request.data.get('username') or '').strip()
        if not username:
            return Response({'username': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username__iexact=username).exclude(id=request.user.id).exists():
            return Response({'username': 'Username is already in use.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.username = username
        request.user.save(update_fields=['username', 'updated_at'])
        return Response(
            {'user': CustomUserSerializer(request.user).data, 'message': 'Username updated successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['delete'], permission_classes=[IsAuthenticated])
    def delete_account(self, request):
        user = request.user
        Token.objects.filter(user=user).delete()
        logout(request)
        user.delete()
        return Response({'message': 'Account deleted successfully'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def me(self, request):
        if request.user.is_authenticated:
            return Response(CustomUserSerializer(request.user).data)
        return Response(None, status=status.HTTP_401_UNAUTHORIZED)
