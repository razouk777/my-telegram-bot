# استخدام نسخة بايثون رسمية
FROM python:3.9-slim

# تحديد مجلد العمل داخل البيئة
WORKDIR /app

# نسخ ملف المكتبات أولاً
COPY requirements.txt .

# تثبيت المكتبات المطلوبة
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات الكود
COPY . .

# الأمر الذي سيتم تشغيله عند بدء تشغيل البوت
CMD ["python3", "contact_bot.py"]