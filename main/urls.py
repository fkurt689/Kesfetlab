from django.urls import path
from . import views

urlpatterns = [
    # Ana sayfa ve auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('Hakkimizda/', views.about, name='about'),
    path('iletisim/', views.contact, name='contact'),
    path('toggle-theme/', views.toggle_theme, name='toggle_theme'),
    path('daily-knowledge/', views.daily_knowledge, name='daily_knowledge'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Quiz işlemleri
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/take/<int:attempt_id>/', views.quiz_take, name='quiz_take'),
    path('quiz/result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    
    # Profil ve liderlik
    path('profile/', views.profile, name='profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('settings/', views.settings, name='settings'),
]