from django.contrib import admin
from .models import *

# User Admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'total_points', 'level', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)


# ParentStudent Admin
@admin.register(ParentStudent)
class ParentStudentAdmin(admin.ModelAdmin):
    list_display = ('parent', 'student')
    list_filter = ('parent', 'student')


# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color', 'order')
    list_editable = ('order',)
    ordering = ('order',)


# Answer Inline
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    fields = ('answer_text', 'is_correct', 'order')


# Question Inline
class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ('question_type', 'question_text', 'explanation', 'image', 'order', 'points')
    show_change_link = True


# Question Admin
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question_type', 'question_text_short', 'order', 'points')
    list_filter = ('question_type', 'quiz__category')
    search_fields = ('question_text',)
    inlines = [AnswerInline]
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Soru'


# Quiz Admin
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'difficulty', 'passing_score', 'points_reward', 'is_published', 'created_by')
    list_filter = ('category', 'difficulty', 'is_published', 'created_at')
    search_fields = ('title', 'description')
    inlines = [QuestionInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Badge Admin
@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'requirement_type', 'requirement_value')
    list_filter = ('requirement_type',)
    search_fields = ('name', 'description')


# UserBadge Admin
@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'earned_at')
    list_filter = ('badge', 'earned_at')
    search_fields = ('user__username',)
    ordering = ('-earned_at',)


# QuizAttempt Admin
@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'percentage', 'is_passed', 'time_spent_min', 'completed_at')
    list_filter = ('is_passed', 'quiz__category', 'completed_at')
    search_fields = ('user__username', 'quiz__title')
    ordering = ('-completed_at',)
    
    def time_spent_min(self, obj):
        if obj.time_spent:
            return f"{obj.time_spent // 60} dakika"
        return '-'
    time_spent_min.short_description = 'Süre'


# UserAnswer Admin
@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question_short', 'selected_answer_short', 'is_correct')
    list_filter = ('is_correct', 'answered_at')
    
    def question_short(self, obj):
        return obj.question.question_text[:30]
    question_short.short_description = 'Soru'
    
    def selected_answer_short(self, obj):
        return obj.selected_answer.answer_text if obj.selected_answer else '-'
    selected_answer_short.short_description = 'Cevap'


# ActivityLog Admin
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'description', 'points_earned', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'description')
    ordering = ('-created_at',)
    
    # Contact Message Admin
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    # Knowledge Card Admin
@admin.register(KnowledgeCard)
class KnowledgeCardAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'icon', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('title', 'content')
    list_editable = ('is_active',)


# User Card Read Admin
@admin.register(UserCardRead)
class UserCardReadAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'read_at')
    list_filter = ('read_at',)
    search_fields = ('user__username', 'card__title')


# Daily Card Limit Admin
@admin.register(DailyCardLimit)
class DailyCardLimitAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'cards_read_today')
    list_filter = ('date',)
    search_fields = ('user__username',)