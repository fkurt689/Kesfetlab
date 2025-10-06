from django.db import models
from django.contrib.auth.models import AbstractUser

# Özelleştirilmiş User Modeli
class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Öğrenci'),
        ('teacher', 'Öğretmen'),
        ('parent', 'Veli'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.CharField(max_length=10, default='🚀', blank=True)
    total_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    dark_mode = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# Veli-Öğrenci İlişkisi
class ParentStudent(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='children', limit_choices_to={'role': 'parent'})
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parents', limit_choices_to={'role': 'student'})
    
    class Meta:
        unique_together = ('parent', 'student')
    
    def __str__(self):
        return f"{self.parent.username} -> {self.student.username}"


# Kategori (Quiz'ler için)
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # emoji
    color = models.CharField(max_length=7, default='#3B82F6')
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


# Quiz
class Quiz(models.Model):
    DIFFICULTY_CHOICES = (
        ('easy', 'Kolay'),
        ('medium', 'Orta'),
        ('hard', 'Zor'),
    )
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='easy')
    passing_score = models.IntegerField(default=70, help_text='Geçme puanı yüzde olarak')
    time_limit = models.IntegerField(null=True, blank=True, help_text='dakika cinsinden')
    points_reward = models.IntegerField(default=50, help_text='Başarılı olunca kazanılan puan')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'teacher'})
    
    class Meta:
        ordering = ['category', '-created_at']
    
    def __str__(self):
        return self.title
    
    def total_questions(self):
        return self.questions.count()


# Soru
class Question(models.Model):
    QUESTION_TYPES = (
        ('multiple_choice', 'Çoktan Seçmeli'),
        ('true_false', 'Doğru/Yanlış'),
        ('drag_drop', 'Sürükle Bırak'),
    )
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    question_text = models.TextField()
    explanation = models.TextField(blank=True, help_text='Cevap sonrası açıklama')
    image = models.ImageField(upload_to='questions/', null=True, blank=True)
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=10)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Soru {self.order}"


# Cevap Seçenekleri
class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.answer_text


# Rozet
class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=100)  # emoji
    color = models.CharField(max_length=7, default='#FFD700')
    requirement_type = models.CharField(max_length=50, help_text='ör: first_quiz, quiz_count_5, points_100')
    requirement_value = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name


# Kullanıcı Rozetleri
class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


# Quiz Denemesi
class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    max_score = models.IntegerField()
    percentage = models.FloatField(default=0)
    is_passed = models.BooleanField(default=False)
    time_spent = models.IntegerField(null=True, blank=True, help_text='saniye cinsinden')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} (%{self.percentage:.1f})"


# Kullanıcı Cevapları
class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('attempt', 'question')
    
    def __str__(self):
        return f"{self.attempt.user.username} - Q{self.question.order}"


# Aktivite Logu (İlerleme takibi için)
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)  # 'quiz_completed', 'badge_earned', 'level_up'
    description = models.TextField()
    points_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"
  
    # İletişim Mesajları
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"
    
    # Bilgi Kartı
class KnowledgeCard(models.Model):
    CATEGORY_CHOICES = (
        ('algorithm', 'Algoritma'),
        ('programming', 'Programlama'),
        ('internet', 'İnternet'),
        ('hardware', 'Donanım'),
        ('software', 'Yazılım'),
        ('ai', 'Yapay Zeka'),
        ('security', 'Güvenlik'),
        ('history', 'Teknoloji Tarihi'),
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    icon = models.CharField(max_length=10, default='💡')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return self.title


# Kullanıcının Okuduğu Kartlar
class UserCardRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_cards')
    card = models.ForeignKey(KnowledgeCard, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'card')
        ordering = ['-read_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.card.title}"


# Günlük Kart Sınırı Takibi
class DailyCardLimit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_cards')
    date = models.DateField(auto_now_add=True)
    cards_read_today = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'date')
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.cards_read_today}/5"
    
    # AI Chatbot Mesajları
class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at}"