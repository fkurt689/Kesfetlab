from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from datetime import timedelta
from .models import *
import google.generativeai as genai
from config import settings

# Ana Sayfa
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    categories = Category.objects.annotate(quiz_count=Count('quizzes')).all()
    featured_quizzes = Quiz.objects.filter(is_published=True).order_by('-created_at')[:6]
    
    context = {
        'categories': categories,
        'featured_quizzes': featured_quizzes,
    }
    return render(request, 'home.html', context)


# Kayıt
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')
        birth_date = request.POST.get('birth_date')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Bu kullanıcı adı zaten kullanılıyor.')
            return redirect('register')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            birth_date=birth_date if birth_date else None
        )
        login(request, user)
        messages.success(request, 'Kayıt başarılı! Hoş geldin!')
        return redirect('dashboard')
    
    return render(request, 'register.html')


# Giriş
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    
    return render(request, 'login.html')


# Çıkış
@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptın!')
    return redirect('home')


# Dashboard Yönlendirme
@login_required
def dashboard(request):
    if request.user.role == 'student':
        return student_dashboard(request)
    elif request.user.role == 'parent':
        return parent_dashboard(request)
    elif request.user.role == 'teacher':
        return teacher_dashboard(request)
    
    return render(request, 'dashboard.html')


# Öğrenci Dashboard
@login_required
def student_dashboard(request):
    from datetime import date
    
    user = request.user
    
    # İstatistikler
    total_attempts = QuizAttempt.objects.filter(user=user, completed_at__isnull=False).count()
    passed_quizzes = QuizAttempt.objects.filter(user=user, is_passed=True).count()
    total_quizzes = Quiz.objects.filter(is_published=True).count()
    
    # Son denemeler
    recent_attempts = QuizAttempt.objects.filter(
        user=user,
        completed_at__isnull=False
    ).select_related('quiz').order_by('-completed_at')[:5]
    
    # Rozetler
    user_badges = UserBadge.objects.filter(user=user).select_related('badge').order_by('-earned_at')
    
    # Son aktiviteler
    recent_activities = ActivityLog.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Haftalık ilerleme
    week_ago = timezone.now() - timedelta(days=7)
    weekly_attempts = QuizAttempt.objects.filter(
        user=user,
        completed_at__gte=week_ago,
        completed_at__isnull=False
    ).count()
    
    # Günün Bilgisi İstatistikleri
    today = date.today()
    daily_limit = DailyCardLimit.objects.filter(user=user, date=today).first()
    daily_cards_today = daily_limit.cards_read_today if daily_limit else 0
    total_cards_read = UserCardRead.objects.filter(user=user).count()
    total_cards = KnowledgeCard.objects.filter(is_active=True).count()
    cards_remaining = total_cards - total_cards_read
    
    context = {
        'total_attempts': total_attempts,
        'passed_quizzes': passed_quizzes,
        'total_quizzes': total_quizzes,
        'success_rate': (passed_quizzes / total_attempts * 100) if total_attempts > 0 else 0,
        'recent_attempts': recent_attempts,
        'user_badges': user_badges,
        'recent_activities': recent_activities,
        'weekly_attempts': weekly_attempts,
        # Günün Bilgisi
        'daily_cards_today': daily_cards_today,
        'total_cards_read': total_cards_read,
        'cards_remaining': cards_remaining,
    }
    
    return render(request, 'student_dashboard.html', context)

# Veli Dashboard
@login_required
def parent_dashboard(request):
    children = ParentStudent.objects.filter(parent=request.user).select_related('student')
    
    children_data = []
    for relation in children:
        child = relation.student
        
        total_attempts = QuizAttempt.objects.filter(
            user=child,
            completed_at__isnull=False
        ).count()
        
        passed = QuizAttempt.objects.filter(user=child, is_passed=True).count()
        
        recent_quiz = QuizAttempt.objects.filter(
            user=child,
            completed_at__isnull=False
        ).order_by('-completed_at').first()
        
        # Son 7 gün aktivite
        week_ago = timezone.now() - timedelta(days=7)
        weekly_quizzes = QuizAttempt.objects.filter(
            user=child,
            completed_at__gte=week_ago,
            completed_at__isnull=False
        ).count()
        
        children_data.append({
            'child': child,
            'total_attempts': total_attempts,
            'passed_quizzes': passed,
            'success_rate': (passed / total_attempts * 100) if total_attempts > 0 else 0,
            'recent_quiz': recent_quiz,
            'weekly_quizzes': weekly_quizzes,
        })
    
    context = {'children_data': children_data}
    return render(request, 'parent_dashboard.html', context)


# Öğretmen Dashboard
@login_required
def teacher_dashboard(request):
    total_students = User.objects.filter(role='student').count()
    total_quizzes = Quiz.objects.filter(created_by=request.user).count()
    total_attempts = QuizAttempt.objects.filter(
        quiz__created_by=request.user,
        completed_at__isnull=False
    ).count()
    
    # Öğretmenin oluşturduğu quiz'lerin son denemeleri
    recent_attempts = QuizAttempt.objects.filter(
        quiz__created_by=request.user,
        completed_at__isnull=False
    ).select_related('user', 'quiz').order_by('-completed_at')[:10]
    
    # Quiz istatistikleri
    my_quizzes = Quiz.objects.filter(created_by=request.user).annotate(
        attempt_count=Count('attempts'),
        avg_score=Avg('attempts__percentage')
    )
    
    context = {
        'total_students': total_students,
        'total_quizzes': total_quizzes,
        'total_attempts': total_attempts,
        'recent_attempts': recent_attempts,
        'my_quizzes': my_quizzes,
    }
    
    return render(request, 'teacher_dashboard.html', context)


# Quiz Listesi
@login_required
def quiz_list(request):
    categories = Category.objects.prefetch_related('quizzes').all()
    
    # Kategori filtreleme
    category_id = request.GET.get('category')
    if category_id:
        quizzes = Quiz.objects.filter(category_id=category_id, is_published=True)
    else:
        quizzes = Quiz.objects.filter(is_published=True)
    
    # Zorluk filtreleme
    difficulty = request.GET.get('difficulty')
    if difficulty:
        quizzes = quizzes.filter(difficulty=difficulty)
    
    context = {
        'categories': categories,
        'quizzes': quizzes,
    }
    
    return render(request, 'quiz_list.html', context)


# Quiz Detay & Başlat
@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_published=True)
    
    # Kullanıcının önceki denemeleri
    previous_attempts = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz,
        completed_at__isnull=False
    ).order_by('-completed_at')
    
    best_attempt = previous_attempts.filter(is_passed=True).first()
    
    if request.method == 'POST':
        # Yeni deneme başlat
        max_score = sum(q.points for q in quiz.questions.all())
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            max_score=max_score
        )
        return redirect('quiz_take', attempt_id=attempt.id)
    
    context = {
        'quiz': quiz,
        'previous_attempts': previous_attempts[:5],
        'best_attempt': best_attempt,
        'question_count': quiz.questions.count(),
    }
    
    return render(request, 'quiz_detail.html', context)


# Quiz Çöz
@login_required
def quiz_take(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    
    if attempt.completed_at:
        return redirect('quiz_result', attempt_id=attempt_id)
    
    questions = attempt.quiz.questions.prefetch_related('answers').all()
    
    if request.method == 'POST':
        score = 0
        
        for question in questions:
            answer_id = request.POST.get(f'question_{question.id}')
            
            if answer_id:
                answer = get_object_or_404(Answer, id=answer_id)
                is_correct = answer.is_correct
                
                UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_answer=answer,
                    is_correct=is_correct
                )
                
                if is_correct:
                    score += question.points
        
        # Denemeyi tamamla
        attempt.score = score
        attempt.percentage = (score / attempt.max_score * 100) if attempt.max_score > 0 else 0
        attempt.is_passed = attempt.percentage >= attempt.quiz.passing_score
        attempt.completed_at = timezone.now()
        
        # Süre hesapla
        time_diff = attempt.completed_at - attempt.started_at
        attempt.time_spent = int(time_diff.total_seconds())
        
        attempt.save()
        
        # Başarılıysa puan ekle
        if attempt.is_passed:
            request.user.total_points += attempt.quiz.points_reward
            request.user.save()
            
            # Aktivite logu
            ActivityLog.objects.create(
                user=request.user,
                activity_type='quiz_completed',
                description=f'{attempt.quiz.title} quiz\'ini tamamladı',
                points_earned=attempt.quiz.points_reward
            )
            
            # Rozet kontrolü
            check_and_award_badges(request.user)
        
        return redirect('quiz_result', attempt_id=attempt_id)
    
    context = {
        'attempt': attempt,
        'questions': questions,
        'quiz': attempt.quiz,
    }
    
    return render(request, 'quiz_take.html', context)


# Quiz Sonuç
@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    user_answers = UserAnswer.objects.filter(attempt=attempt).select_related(
        'question',
        'selected_answer'
    ).prefetch_related('question__answers')
    
    # Doğru ve yanlış sayısını hesapla
    correct_count = user_answers.filter(is_correct=True).count()
    wrong_count = user_answers.filter(is_correct=False).count()
    
    context = {
        'attempt': attempt,
        'user_answers': user_answers,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
    }
    
    return render(request, 'quiz_result.html', context)


# Rozet Kontrolü
def check_and_award_badges(user):
    badges = Badge.objects.all()
    
    for badge in badges:
        # Zaten kazanılmış mı?
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            continue
        
        awarded = False
        
        # İlk quiz
        if badge.requirement_type == 'first_quiz':
            if QuizAttempt.objects.filter(user=user, is_passed=True).count() >= 1:
                awarded = True
        
        # Quiz sayısı
        elif badge.requirement_type.startswith('quiz_count_'):
            count = int(badge.requirement_type.split('_')[-1])
            if QuizAttempt.objects.filter(user=user, is_passed=True).count() >= count:
                awarded = True
        
        # Puan
        elif badge.requirement_type.startswith('points_'):
            points = int(badge.requirement_type.split('_')[-1])
            if user.total_points >= points:
                awarded = True
        
        # Perfect score
        elif badge.requirement_type == 'perfect_score':
            if QuizAttempt.objects.filter(user=user, percentage=100).exists():
                awarded = True
        
        if awarded:
            UserBadge.objects.create(user=user, badge=badge)
            
            # Aktivite logu
            ActivityLog.objects.create(
                user=user,
                activity_type='badge_earned',
                description=f'{badge.name} rozetini kazandı',
                points_earned=0
            )
            
           # messages.success(request, f'🎉 Tebrikler! "{badge.name}" rozetini kazandın!')


# Profil
@login_required
def profile(request):
    user_badges = UserBadge.objects.filter(user=request.user).select_related('badge')
    
    # İstatistikler
    total_attempts = QuizAttempt.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).count()
    
    passed_quizzes = QuizAttempt.objects.filter(user=request.user, is_passed=True).count()
    
    avg_score = QuizAttempt.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).aggregate(Avg('percentage'))['percentage__avg'] or 0
    
    context = {
        'user_badges': user_badges,
        'total_attempts': total_attempts,
        'passed_quizzes': passed_quizzes,
        'avg_score': round(avg_score, 1),
    }
    
    return render(request, 'profile.html', context)


# Liderlik Tablosu
@login_required
def leaderboard(request):
    top_students = User.objects.filter(role='student').order_by('-total_points')[:20]
    
    context = {
        'top_students': top_students,
        'user_rank': list(top_students).index(request.user) + 1 if request.user in top_students else None,
    }
    
    return render(request, 'leaderboard.html', context)

# Hakkında
def about(request):
    return render(request, 'about.html')

# İletişim
def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        
        messages.success(request, '✉️ Mesajınız başarıyla gönderildi! En kısa sürede size dönüş yapacağız.')
        return redirect('contact')
    
    return render(request, 'contact.html')

# Ayarlar
@login_required
def settings(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Profil Güncelleme
        if action == 'update_profile':
            username = request.POST.get('username')
            email = request.POST.get('email')
            birth_date = request.POST.get('birth_date')
            avatar_emoji = request.POST.get('avatar')
            
            # Kullanıcı adı kontrolü
            if username != request.user.username:
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Bu kullanıcı adı zaten kullanılıyor.')
                    return redirect('settings')
            
            request.user.username = username
            request.user.email = email
            if birth_date:
                request.user.birth_date = birth_date
            if avatar_emoji:
                request.user.avatar = avatar_emoji
            request.user.save()
            
            messages.success(request, '✅ Profiliniz başarıyla güncellendi!')
            return redirect('settings')
        
        # Şifre Değiştirme
        elif action == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Eski şifre kontrolü
            if not request.user.check_password(old_password):
                messages.error(request, '❌ Eski şifreniz hatalı!')
                return redirect('settings')
            
            # Yeni şifre eşleşme kontrolü
            if new_password != confirm_password:
                messages.error(request, '❌ Yeni şifreler eşleşmiyor!')
                return redirect('settings')
            
            # Şifre uzunluk kontrolü
            if len(new_password) < 6:
                messages.error(request, '❌ Şifre en az 6 karakter olmalı!')
                return redirect('settings')
            
            request.user.set_password(new_password)
            request.user.save()
            
            # Şifre değişince oturum kapanır, tekrar giriş yaptır
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            
            messages.success(request, '✅ Şifreniz başarıyla değiştirildi!')
            return redirect('settings')
        
        # Hesap Silme
        elif action == 'delete_account':
            password = request.POST.get('password')
            
            if not request.user.check_password(password):
                messages.error(request, '❌ Şifreniz hatalı!')
                return redirect('settings')
            
            request.user.delete()
            messages.success(request, '✅ Hesabınız başarıyla silindi.')
            return redirect('home')
    
    return render(request, 'settings.html')
# Tema Değiştir
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def toggle_theme(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request.user.dark_mode = data.get('dark_mode', False)
            request.user.save()
            return JsonResponse({'status': 'success'})
        except:
            pass
    
    # GET request - basit toggle
    request.user.dark_mode = not request.user.dark_mode
    request.user.save()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

# Günün Bilgisi
@login_required
def daily_knowledge(request):
    from datetime import date
    
    today = date.today()
    
    # Bugünkü limit kontrolü (yarat veya getir)
    daily_limit, created = DailyCardLimit.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={'cards_read_today': 0}
    )
    
    # Kullanıcının bugün okuduğu kartlar
    today_read_cards = UserCardRead.objects.filter(
        user=request.user,
        read_at__date=today
    ).values_list('card_id', flat=True)
    
    # Kullanıcının hiç okumadığı kartları getir
    unread_cards = KnowledgeCard.objects.filter(
        is_active=True
    ).exclude(
        id__in=UserCardRead.objects.filter(user=request.user).values_list('card_id', flat=True)
    )
    
    # Günlük limit kontrolü
    cards_left = 5 - daily_limit.cards_read_today
    limit_reached = daily_limit.cards_read_today >= 5
    
    # Gösterilecek kartlar
    if not limit_reached and unread_cards.exists():
        # Rastgele 1 kart göster
        import random
        available_cards = list(unread_cards)
        current_card = random.choice(available_cards) if available_cards else None
    else:
        current_card = None
    
    # Kart okundu olarak işaretle
    if request.method == 'POST' and current_card and not limit_reached:
        # Kartı okundu olarak kaydet
        UserCardRead.objects.get_or_create(user=request.user, card=current_card)
        
        # Günlük sayacı artır
        daily_limit.cards_read_today += 1
        daily_limit.save()
        
        # Puan ekle
        request.user.total_points += 5
        request.user.save()
        
        # Aktivite logu
        ActivityLog.objects.create(
            user=request.user,
            activity_type='card_read',
            description=f'"{current_card.title}" kartını okudu',
            points_earned=5
        )
        
        messages.success(request, f'✅ +5 Puan kazandın! ({daily_limit.cards_read_today}/5)')
        return redirect('daily_knowledge')
    
    # İstatistikler
    total_cards = KnowledgeCard.objects.filter(is_active=True).count()
    user_read_count = UserCardRead.objects.filter(user=request.user).count()
    
    context = {
        'current_card': current_card,
        'cards_left': cards_left,
        'limit_reached': limit_reached,
        'total_cards': total_cards,
        'user_read_count': user_read_count,
        'daily_read': daily_limit.cards_read_today,
    }
    
    return render(request, 'daily_knowledge.html', context)

@login_required
def chatbot_view(request):
    if request.method == 'POST':
        try:
            user_message = request.POST.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({
                    'error': 'Mesaj boş olamaz!'
                }, status=400)
            
            # Gemini API Key'i al
            from django.conf import settings as django_settings
            api_key = django_settings.GEMINI_API_KEY
            
            # ✅ TEST: API key'i konsola yazdır
            print(f"DEBUG - API KEY: {api_key}")
            print(f"DEBUG - API KEY uzunluğu: {len(api_key)}")
            
            # Gemini AI yapılandırması
            genai.configure(api_key=api_key)
            
            # GÜNCEL MODEL - gemini-2.0-flash
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # KISA Sistem promptu
            system_prompt = f"""Sen KesfetBot'sun 🤖 - Çocuklar için eğlenceli AI asistan.

ÖNEMLI KURALLAR:
- Cevapların MAKSIMUM 3-4 CÜMLE olmalı
- Çok kısa ve öz açıkla
- Sade Türkçe kullan
- 2-3 emoji yeterli

Kullanıcı: {request.user.username} ({request.user.total_points} puan)

Soru: {user_message}

KISA cevap ver!"""
            
            # AI'dan cevap al
            response = model.generate_content(system_prompt)
            ai_response = response.text
            
            # Mesajı kaydet
            ChatMessage.objects.create(
                user=request.user,
                message=user_message,
                response=ai_response
            )
            
            return JsonResponse({
                'success': True,
                'response': ai_response
            })
            
        except Exception as e:
            print(f"CHATBOT HATASI: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'error': f'Bir hata oluştu: {str(e)}'
            }, status=500)
    
    # GET request - chat geçmişini göster
    chat_history = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:20]
    
    context = {
        'chat_history': chat_history,
    }
    
    return render(request, 'chatbot.html', context)