from rest_framework import serializers
from .models import TenantUser


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = TenantUser
        fields = [
            'id',
            'username',
            'email',
            'password',
            'confirm_password',
            'company_name'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match'}
            )
        return attrs

    def validate_email(self, value):
        if TenantUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered')
        return value

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = TenantUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            company_name=validated_data.get('company_name', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantUser
        fields = [
            'id',
            'username',
            'email',
            'company_name',
            'plan',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'plan', 'created_at', 'updated_at']


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantUser
        fields = ['username', 'company_name']

    def validate_username(self, value):
        user = self.context['request'].user
        if TenantUser.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError('Username already taken')
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_new_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError(
                {'confirm_new_password': 'Passwords do not match'}
            )
        return attrs