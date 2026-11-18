---
course: "إدارة جودة البيانات"
code: "LDS-DMG-203"
version: "2027.1.0"
lab: "3.2"
language: "ar"
view: "trainee"
source: "https://sdaiaacademy.github.io/lds-dmg-203/labs/D3_2_root_cause.html"
---

# المختبر 3.2 · خطأ العناوين حتى نموذج الإدخال

تتبع خطأً متكررًا في مدينة موقع المراكز من سجل المشكلات عبر مسار البيانات حتى نموذج البوابة، وتكتب المنشأ والإجراءات التصحيحية والوقائية وملاكها ومقياسًا أسبوعيًا للتكرار.

اليوم 3 · الجلسة 2: السبب الجذري والوقاية

### ستخرج من هذا المختبر بـ

- تحليل سبب جذري لخطأ مدينة الموقع: أين يتركز، ومخطط السبب والنتيجة، والأسئلة الخمسة حتى المنشأ.
- إجراء تصحيحي وإجراءان وقائيان بملاكهم، ومقياس أسبوعي للتكرار بهدفه.

## ما تحتاجه

[**day3/lineage.txt**مسار عنوان المنشأة من التقديم إلى المستهلكين، وملاحظات الإصدارات.](https://sdaiaacademy.github.io/lds-dmg-203/labs/files/day3/lineage.txt) [**day3/form_spec.txt**مواصفة قسم العنوان في نموذج البوابة، الإصداران v2 وv3.](https://sdaiaacademy.github.io/lds-dmg-203/labs/files/day3/form_spec.txt) [**day3/address_weekly.csv**الطلبات المعتمدة أسبوعيًا، وكم منها مدينته لا يطابقها الرمز البريدي.](https://sdaiaacademy.github.io/lds-dmg-203/labs/files/day3/address_weekly.csv) [**data/applications.csv**القناة والإصدار وإجابة المربع لكل طلب.](https://sdaiaacademy.github.io/lds-dmg-203/labs/files/data/applications.csv)

مرشد ذكاء اصطناعي مسموح: اطلب منه أن يسألك أسئلة السبب الجذري أو أن يراجع مخططك، بكلماتك ودون صفوف من البيانات.

## الخطوات

### 1 · العزل 10 د

خذ لكل منشأة آخر طلب معتمد لها، وقسّم المنشآت المخالفة بالقناة، ثم بالإصدار، ثم بإجابة المربع، ثم بنوع المنشأة. توقف حين يبقى في المخالفات قسم واحد.

```
WITH last AS (
  SELECT * FROM applications WHERE decision = 'APPROVED'
  QUALIFY row_number() OVER (PARTITION BY centre_id ORDER BY submitted_at DESC) = 1)
SELECT a.channel, count(*) AS centres,
       sum(CASE WHEN length(c.postal_code) = 6
                 AND substr(c.postal_code, 1, 2) <> ci.postal_prefix THEN 1 ELSE 0 END) AS mismatched
FROM centres c JOIN cities ci USING (city_code) JOIN last a USING (centre_id)
GROUP BY ALL ORDER BY 1;
```

احفظه في ملف وشغّله بـ `uv run kit/sql.py -f`، ثم أضف الأعمدة `form_version` و`premises_same_as_owner` و`centre_type` واحدًا بعد الآخر.

### 2 · المسار والمواصفة 7 د

اقرأ المسار والمواصفة، وارسم مخطط السبب والنتيجة: النتيجة «زيارة تصل إلى مدينة خاطئة»، والفروع: النموذج، ومهمة التكامل، والقواعد، والناس، والقياس.

### 3 · الأسئلة الخمسة 6 د

ابدأ من «زيارة أحيلت إلى مكتب آخر» واسأل «لماذا؟» حتى تصل إلى قرار أو تصميم يمكن تغييره. كل جواب يُسند بدليل من الخطوة 1 أو من الملفين.

### 4 · الإجراءات 7 د

إجراء تصحيحي واحد للصفوف الحالية، وإجراءان وقائيان: واحد عند نقطة الإدخال وواحد في التكامل. لكل إجراء مالك بالاسم وموعد.

### 5 · مقياس التكرار 5 د

من `address_weekly.csv`: نسبة المخالفات من الطلبات المعتمدة أسبوعيًا قبل إطلاق v3 وبعده. عرّف المقياس وهدفه ومتى تُغلق المشكلة.

### ✱ تمرين إضافي

قدّر كم زيارة أحيلت بسبب هذا الخطأ منذ إطلاق الإصدار v3 (العمود `inspections.reassigned`).

## أسئلة تحقق

1. في أي قسم تتركز المخالفات كلها؟
2. ما المنشأ في جملة واحدة، ولماذا لا يكفي «خطأ إدخال من المتقدم»؟
3. ما نسبة المخالفات الأسبوعية قبل v3 وبعده؟
