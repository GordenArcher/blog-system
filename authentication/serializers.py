from rest_framework import serializers
from django.contrib.auth.models import User
from .models import LoginActivity


class LoginActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginActivity
        fields = '__all__'
