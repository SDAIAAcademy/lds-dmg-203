# إدارة جودة البيانات: المختبرات

اثنا عشر مختبرًا لمقرر أكاديمية سدايا **LDS-DMG-203**، مدة كل منها 35 دقيقة في جلسة من 70 دقيقة. المختبرات صفحات
إرشادية بالعربية: الهدف، والملفات، وخطوات بدقائقها، وأسئلة تحقق، وتمرين إضافي ✱، وملاحظات للمدرب. يعمل المشارك
بأوامر قصيرة في الطرفية على محرك DuckDB، وفي جدول بيانات.

كل المختبرات في جهة واحدة: **هيئة أكمام لترخيص مراكز رعاية الأطفال**، جهة افتراضية في خمس مدن افتراضية. كل الأسماء
والأرقام والجداول اصطناعية، ولّدها `_tools/prepare_files.py` (البذرة 203).

## البداية السريعة

1. ثبّت [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. من مجلد `labs`:

```bash
uv run kit/sql.py "SELECT count(*) FROM centres"
```

الجواب المنتظر `1000`. أول تشغيل ينزّل Python عند الحاجة ومكتبتي `duckdb` و`pyyaml` فقط. لا حساب في أي خدمة، ولا مفتاح،
ولا يُنزَّل أي نموذج. يكفي حاسوب محمول بلا معالج رسوميات.

**بديل دون تثبيت (Google Colab):** ارفع مجلد `labs` إلى الجلسة، ثم في خلية:

```bash
!pip install duckdb pyyaml
%cd labs
!python kit/sql.py "SELECT count(*) FROM centres"
```

ثم استعمل `python` مكان `uv run` في كل أمر. هذا المسار لم يُجرَّب في كل مختبر.

## الأدوات في `kit/`

| الأداة | ما تفعله |
|---|---|
| `sql.py` | يشغّل استعلامًا على جداول الحالة (أو ملفًا بـ `-f`) ويطبع النتيجة |
| `profile.py` | تنميط جدول أو ملف CSV: الفراغ، والتميز، والأدنى والأعلى، والأكثر شيوعًا، والأشكال |
| `run_checks.py` | محرك الفحوص التصريحي: ملف YAML وكتالوج القواعد، ويكتب سجل التشغيل في `out/` |
| `scorecard.py` | بطاقة الأداء من سجل تشغيل: عنوانان، وبحسب البعد، وبحسب العنصر |
| `sample_estimate.py` | تقدير نسبة من عينة بمجال ثقة 95% (ويلسون) |
| `prerelease.py` | فحوص ما قبل النشر على مستخرج البيانات المفتوحة |
| `ai_fitness.py` | قياسات صلاحية جدول التدريب (`table`) ومجموعة الوثائق (`docs`) |
| `seed_defect.py` | للمقيّم: يزرع عيبًا جديدًا في نسخة من الجداول |
| `check_prework.py` | يصحح تمارين SQL في العمل التحضيري |

## نقطة البداية والحل

كل مختبر يبدأ من ملفات جاهزة في `files/` ولا يعتمد على عمل المشارك في مختبر سابق. المختبر 2.3 يبدأ من الكتالوج
المرجعي لا من كتالوج المشارك في 1.3، والمختبر 2.4 يبدأ من سجل التشغيل المرجعي لا من سجل المشارك في 2.3.

| المختبر | الصفحة | يبدأ من | الحل المرجعي |
|---|---|---|---|
| 1.1 | `D1_1_report_gap.html` | `day1/report_2026_10.csv`، `day1/report_method.txt`، `data/` | `solutions/D1_1_report_gap.md` |
| 1.2 | `D1_2_critical_elements.html` | `day1/requirements.csv`، `day1/data_dictionary.csv`، `day1/cde_worksheet.csv` | `solutions/D1_2_critical_elements.md` |
| 1.3 | `D1_3_rules.html` | `day1/cde_list.csv`، `day1/rules_template.csv`، `day1/assistant_suggestions.csv` | `solutions/D1_3_rules.md`، `solutions/reference/suggestions_review.csv` |
| 1.4 | `D1_4_thresholds.html` | `day1/rule_history.csv`، `day1/requirements.csv` | `solutions/D1_4_thresholds.md`، `solutions/reference/thresholds_reference.csv` |
| 2.1 | `D2_1_column_profiling.html` | `data/`، `day2/defect_log_template.csv` | `solutions/D2_1_column_profiling.md`، `solutions/reference/defect_log_reference.csv` |
| 2.2 | `D2_2_relationships.html` | `data/`، `day2/field_verification.csv` | `solutions/D2_2_relationships.md` |
| 2.3 | `D2_3_run_checks.html` | `day2/rules_reference.csv`، `day2/checks_start.yml` | `solutions/D2_3_run_checks.md`، `solutions/reference/checks_reference.yml` |
| 2.4 | `D2_4_scorecard.html` | `day2/draft_scorecard.csv`، `day2/run_log_reference.csv` | `solutions/D2_4_scorecard.md` |
| 3.1 | `D3_1_issue_triage.html` | `day3/issue_log.csv`، `day3/severity_guide.txt` | `solutions/D3_1_issue_triage.md`، `solutions/reference/issue_triage_reference.csv` |
| 3.2 | `D3_2_root_cause.html` | `day3/lineage.txt`، `day3/form_spec.txt`، `day3/address_weekly.csv`، `data/applications.csv` | `solutions/D3_2_root_cause.md` |
| 3.3 | `D3_3_operations.html` | `day3/open_data_extract.csv`، `day3/sharing_agreement_draft.txt`، `day3/priority_dispute.txt` | `solutions/D3_3_operations.md` |
| 3.4 | `D3_4_ai_fitness.html` | `day3/ai/` (جدول التفتيش و24 وثيقة) | `solutions/D3_4_ai_fitness.md` |

## تشغيل الحلول

```bash
uv run solutions/check.py            # كل المختبرات، والعمل التحضيري، وأداة المقيّم
uv run solutions/check.py 2.1 3.2    # بعضها
```

يعيد حساب كل مفتاح من ملفات الحالة بأدوات `kit/`، ويطبع الأرقام التي تقتبسها شرائح ما بعد المختبر و`PASS` لكل مختبر،
ويتحقق أن ملفات البداية ما زالت تحمل عيوبها المزروعة. يكتب في `out/` فقط، وهو مجلد يتجاهله git ويمكن حذفه. **لا يستدعي
أي مختبر نموذجًا لغويًا.** اقتراحات «المساعد» في المختبر 1.3 (`day1/assistant_suggestions.csv`) مكتوبة مسبقًا لتمثل ما
تقترحه أداة ذكاء اصطناعي، فيعمل المختبر نفسه في كل قاعة.

## العيوب العشرة المزروعة

في الجداول الأربعة (`data/applications.csv` و`centres.csv` و`licences.csv` و`inspections.csv`) عشرة عيوب، مفتاحها
في `solutions/reference/seeded_defects.json`. لا تُعطى للمشاركين قبل المختبرين 2.1 و2.2.

## إعادة توليد الملفات

```bash
uv run _tools/prepare_files.py && uv run _tools/derive_files.py && uv run solutions/check.py
```

## سياسة البيانات والذكاء الاصطناعي

جداول الحالة مصنفة «مقيد» داخل الحالة، كما تُعامل بيانات الترخيص الحقيقية: لا تُلصق ولا تُرفع في أي أداة ذكاء اصطناعي
توليدي، عامة كانت أو معتمدة. يدخل المساعدَ ما يكتبه المشارك بكلماته، وأسماء الأعمدة ووصفها. المختبر 2.1 دون أي مساعد.
