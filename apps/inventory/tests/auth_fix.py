# Add this line after self.client = APIClient()
self.user = User.objects.create_user(username='testuser', password='testpass')
self.client.force_authenticate(user=self.user)
