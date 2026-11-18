# المختبر 2.3 · تنفيذ القواعد: الحل المرجعي

التحقق: `uv run solutions/check.py 2.3`. الملف المرجعي: `reference/checks_reference.yml`.

## التشغيل الأول

`PASS 9  FAIL 5  ERROR 0  NOT RUN 6`: الست غير المشغّلة هي R07 وR09 وR13 وR16 وR18 وR19.

## الفحوص الست

```yaml
  - {id: R07, ..., table: licences, type: unique, columns: [application_id], where: "status = 'ACTIVE'", threshold: 100}
  - id: R09
    table: licences
    from: licences JOIN centres USING (centre_id)
    type: row
    where: "centre_type = 'HOME'"
    must: "capacity_licensed <= 10"
  - id: R13
    table: centres
    from: centres JOIN cities USING (city_code)
    type: row
    must: "length(postal_code) = 6 AND substr(postal_code, 1, 2) = postal_prefix"
  - id: R16
    from: centres c JOIN districts d USING (district_code)
    key: c.centre_id
    type: row
    must: "d.city_code = c.city_code AND substr(c.postal_code, 1, 4) = d.postal_digits"
  - {id: R18, ..., table: inspections, type: row, must: "entered_at <= inspection_date + INTERVAL 5 DAY", threshold: 95}
  - {id: R19, ..., table: inspections, type: reference, column: licence_no, ref_table: licences, ref_column: licence_no, threshold: 100}
```

## سجل التشغيل الكامل

11 قاعدة تفشل من 20:

| القاعدة | المفحوص | الفاشل | النجاح % | العتبة | يقابل في سجل العيوب |
|---|---|---|---|---|---|
| R04 | 931 | 41 | 95.60 | 100 | D8 |
| R07 | 931 | 37 | 96.03 | 100 | D7 |
| R08 | 2,369 | 14 | 99.41 | 100 | D1 |
| R09 | 864 | 19 | 97.80 | 100 | D10 (12) + 7 حضانات منزلية مقاعدها 999 (D1) |
| R12 | 4,204 | 306 | 92.72 | 99.5 | D3 |
| R13 | 1,000 | 87 | 91.30 | 99 | D9 (56) + D2 (31): رمز من خمسة أرقام لا تُقرأ بادئته |
| R14 | 1,000 | 31 | 96.90 | 100 | D2 |
| R15 | 1,000 | 26 | 97.40 | 99 | D5 |
| R16 | 974 | 85 | 91.27 | 99 | D9 وD2 من زاوية الحي؛ المقام 974 لأن 26 منشأة بلا حي معروف |
| R18 | 4,204 | 444 | 89.44 | 95 | ليس عيبًا مزروعًا: تأخر الإدخال كما هو، ولا يظهر في التنميط |
| R19 | 4,204 | 17 | 99.60 | 100 | D6 |

## ما لم يلتقطه الكتالوج

D4: تواريخ التقديم 1900-01-01 في `applications.submitted_at`. الكتالوج لا يفحص جدول الطلبات. قاعدة مقترحة: `applications.submitted_at`، الصلاحية، `submitted_at >= DATE '2018-01-01'`، العتبة 100، المالك وليد الدغريري. تلتقط 9 صفوف وحدها.

## ما يُقبل

ملف يشغّل العشرين دون خطأ، وأعداد الفاشل مطابقة للجدول. صياغة مختلفة للفحص مقبولة إن أعطت العدد نفسه.
