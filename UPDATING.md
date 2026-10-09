# آپدیت کردن Leantime بدون از دست رفتن فارسی‌سازی

این ریپو **upgrade-safe** است. هیچ فایل vendor تغییر نمی‌کند؛ کل کار در
`custom/` انجام می‌شود که بعد از آپدیت هم سر جایش می‌ماند (اگر volume سرور
را عوض کردید، فقط کافی است این فایل‌ها را دوباره deploy کنید).

## فایل‌های اصلی (که عوض می‌شوند)

| فایل ریپو | مسیر روی سرور | کار |
|---|---|---|
| `custom/Language/fa-IR.ini` | `/var/www/html/custom/Language/fa-IR.ini` | overlay ترجمه — بعد از `app/Language/fa-IR.ini` لود می‌شود |
| `css/custom-premium.min.css` | `/var/www/html/public/theme/default/css/custom.min.css` | فونت Vazirmatn + RTL + جلوگیری از overflow افقی |

**منبع حقیقت ترجمه `translations/fa-IR.json` است.** فایل INI را دستی ویرایش
نکنید — آن را اسکریپت می‌سازد.

## مراحل آپدیت Leantime

### ۱) فایل انگلیسی نسخه جدید را استخراج کنید

بعد از pull ایمیج جدید، فایل shipped انگلیسی را در بیاورید و با ابزار ما
مقایسه کنید:

```bash
docker exec code-leantime-1 cat /var/www/html/app/Language/en-US.ini > work/en-US-new.ini
python scripts/check_upstream.py work/en-US-new.ini
```

ابزار دو چیز را گزارش می‌دهد:

* `+ key` کلیدهای **جدیدی** که در نسخه جدید اضافه شده‌اند و باید ترجمه شوند
* `~ key` کلیدهایی که متن انگلیسی‌شان **عوض شده** (شاید ترجمه قدیمی دیگر درست نباشد)

خروجی ۱ یعنی کاری هست؛ ۰ یعنی ترجمه فعلی کافی است.

### ۲) کلیدهای جدید را به `translations/fa-IR.json` اضافه کنید

هر entry این ساختار را دارد:

```json
"menu.new_feature": {
  "en": "New feature",
  "fa": "ویژگی جدید"
}
```

دو کلید اختیاری هم هست که ترجمه را دور می‌زنند:

* `"tech": true` — کلیدهای فنی مثل `language.dateformat` که نباید ترجمه شوند
  (فرمت‌های تاریخ و نام روزها). ابزار build این‌ها را عین انگلیسی برمی‌دارد.
* `"literal": true` — مثل `language.code` که مقدار ثابت `fa-IR` دارد.

**نکته:** `scripts/build_overlay.py` اعتبارسنجی می‌کند که هر کلید غیر
tech/literal حداقل یک حرف فارسی داشته باشد. اگر فراموش کنید چیزی را
ترجمه کنید، build می‌ایستد و کلید را نشان می‌دهد.

### ۳) نسخه را بالا ببرید

`translations/VERSION` را با شماره نسخه Leantime + شماره داخلی خودمان ذخیره
می‌کنیم:

```
<leantime-version>.<our-internal>
```

قوانین:

* **patch** (آخرین رقم): فقط کلیدهای جدید اضافه کردیم
* **minor** (دومین رقم از راست): متن انگلیسی بالادست تغییر کرد یا ترجمه‌ها بازبینی شدند
* **major**: هماهنگ با آپدیت Leantime (بخش چپ‌تر)

مثال: روی Leantime 3.10.0 اولین نسخه `3.10.0.1` بود. اگر ۱۲ کلید جدید
اضافه کنیم → `3.10.0.2`. اگر Leantime به 3.11.0 آپدیت شد → `3.11.0.1`.

### ۴) بسازید و deploy کنید

```bash
python scripts/build_overlay.py                    # می‌سازد custom/Language/fa-IR.ini
python scripts/deploy.py                           # overlay + CSS، cache clear، restart php-fpm
```

`deploy.py` تمام لایه‌های کش را پاک می‌کند (که در غیر این صورت زبان قدیمی
را سرو می‌دادند) و php-fpm را برای opcache ری‌استارت می‌کند.

### ۵) تأیید کنید

```bash
curl -s https://leantime.ppsj.ir/auth/login | grep -o 'placeholder="[^"]*"'
# باید فارسی برگرداند: آدرس ایمیل را وارد کنید / رمز عبور را وارد کنید
```

## چرا overlay و نه ویرایش فایل اصلی؟

`app/Language/fa-IR.ini` داخل ایمیج است و **هر آپدیت آن را بازنویس می‌کند**.
Leantime مسیر `custom/Language/<locale>.ini` را بعد از فایل اصلی لود می‌کند
(طبق `app/Core/Language.php readIni`)، پس overlay ما همیشه برنده است و فایل
vendor دست‌نخورده می‌ماند.

به همین ترتیب CSS: `custom.min.css` و `custom.css` در پوشه theme بر اساس
`getAssetPath` چک می‌شوند و بر فایل‌های پیش‌فرض اولویت دارند.

## تله‌هایی که روی آن‌ها گیر کردیم

* **کامنت INI فقط `;` است.** `#` باعث parse failure **خاموش** می‌شود — برنامه
  ساکت به انگلیسی برمی‌گرداند و چیزی در لاگ نیست. همیشه بعد از تغییر INI
  با `parse_ini_file` در کانتینر تست کنید.
* **مسیر overlay** `APP_ROOT.'/custom/Language/'` است، نه `app/custom/Language/`.
  مسیر اشتباه ساکت کار نمی‌کند.
* **پاک کردن یک لایه کش کافی نیست.** `storage/framework/cache/installation/data/*`
  تنها یک فروشگاه از چند فروشگاه است؛ باید کل `storage/framework/cache/*` و
  `storage/framework/views/*` پاک شود و بعد php-fpm ری‌استارت شود (opcache).
* **فونت‌ها باید مسیر مطلق باشند.** `url('fonts/...')` نسبت به
  `/theme/default/css/` حل می‌شود و ۴۰۴ می‌دهد؛ از `/userfiles/rtl-fonts/...`
  استفاده کنید.
* **صفحه ورود فونت roboto می‌گرفت** چون مسیرهای بدون session
  `usersettings.themeFont` ندارند. CSS آن را به Vazirmatn اجبار می‌کند.

## Rollback

پشتیبان کامل قبل از تغییرات در `/root/lt-backup-pre-p0/` روی سرور است
(dump دیتابیس + CSS + فونت‌ها + فایل‌های زبان). نسخه قبلی overlay هم در
history گیت همین ریپو موجود است:

```bash
git show <commit>:custom/Language/fa-IR.ini
```
