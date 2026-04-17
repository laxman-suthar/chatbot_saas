import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Website
from .serializers import (
    WebsiteSerializer,
    WebsiteCreateSerializer,
    EmbedScriptSerializer
)


class WebsiteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Websites'],
        summary='List all websites for logged in user',
        responses={200: WebsiteSerializer(many=True)}
    )
    def get(self, request):
        websites = Website.objects.filter(owner=request.user)
        return Response(
            WebsiteSerializer(websites, many=True).data
        )

    @extend_schema(
        tags=['Websites'],
        summary='Register a new website',
        request=WebsiteCreateSerializer,
        responses={201: WebsiteSerializer},
        examples=[
            OpenApiExample(
                'Create Website Example',
                value={
                    'name': 'My Ecommerce Store',
                    'domain': 'https://myshop.com'
                }
            )
        ]
    )
    def post(self, request):
        serializer = WebsiteCreateSerializer(data=request.data)
        if serializer.is_valid():
            website = serializer.save(owner=request.user)
            return Response(
                WebsiteSerializer(website).data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class WebsiteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Websites'],
        summary='Get website details',
        responses={200: WebsiteSerializer}
    )
    def get(self, request, website_id):
        website = self.get_object(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(WebsiteSerializer(website).data)

    @extend_schema(
        tags=['Websites'],
        summary='Update website name or domain',
        request=WebsiteCreateSerializer,
        responses={200: WebsiteSerializer},
        examples=[
            OpenApiExample(
                'Update Example',
                value={
                    'name': 'Updated Store Name',
                    'domain': 'https://updatedshop.com'
                }
            )
        ]
    )
    def patch(self, request, website_id):
        website = self.get_object(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = WebsiteSerializer(
            website,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        tags=['Websites'],
        summary='Delete a website',
        responses={204: None}
    )
    def delete(self, request, website_id):
        website = self.get_object(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        website.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegenerateAPIKeyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Websites'],
        summary='Regenerate API key for a website',
        responses={200: WebsiteSerializer}
    )
    def post(self, request, website_id):
        try:
            website = Website.objects.get(
                id=website_id,
                owner=request.user
            )
            website.api_key = uuid.uuid4()
            website.save()
            return Response(WebsiteSerializer(website).data)
        except Website.DoesNotExist:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ToggleWebsiteStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Websites'],
        summary='Toggle website active/inactive status',
        responses={200: WebsiteSerializer}
    )
    def post(self, request, website_id):
        try:
            website = Website.objects.get(
                id=website_id,
                owner=request.user
            )
            website.is_active = not website.is_active
            website.save()
            return Response({
                'message': f"Website {'activated' if website.is_active else 'deactivated'}",
                'is_active': website.is_active
            })
        except Website.DoesNotExist:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class EmbedScriptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id, owner=request.user)
            
            # Generate api_key if null
            if not website.api_key:
                website.api_key = uuid.uuid4()
                website.save()

            scheme = request.scheme
            host = request.get_host().split(':')[0]  # removes port
            base_url = f"{scheme}://{host}"
            script_tag = (
                f'<script src="{base_url}/static/widget.js" '
                f'data-api-key="{website.api_key}"'
                f'data-ws-host="{request.get_host().split(":")[0]}"></script>'
            )
            return Response({
                'api_key': str(website.api_key),
                'script_tag': script_tag,
                'websocket_url': f'wss://{request.get_host()}/ws/chat/{website.id}/'
            })
        except Website.DoesNotExist:
            return Response({'error': 'Website not found'}, status=status.HTTP_404_NOT_FOUND)

class ResolveWebsiteView(APIView):
    permission_classes = []  # public endpoint

    def get(self, request):
        api_key = request.query_params.get('api_key')
        if not api_key:
            return Response({'error': 'api_key required'}, status=400)
        try:
            website = Website.objects.get(api_key=api_key, is_active=True)
            return Response({'website_id': str(website.id)})
        except Website.DoesNotExist:
            return Response({'error': 'Invalid api_key'}, status=404)