from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class CustomUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'is_active',
            'is_staff',
            'is_verified',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_active', 'is_staff', 'is_verified', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def validate_username(self, value):
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        queryset = User.objects.filter(username__iexact=cleaned)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        if queryset.exists():
            raise serializers.ValidationError('Username is already in use.')
        return cleaned


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def validate_username(self, value):
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if User.objects.filter(username__iexact=cleaned).exists():
            raise serializers.ValidationError('Username is already in use.')
        return cleaned

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        if not validated_data.get('username'):
            validated_data.pop('username', None)
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        attrs['user'] = user
        return attrs
