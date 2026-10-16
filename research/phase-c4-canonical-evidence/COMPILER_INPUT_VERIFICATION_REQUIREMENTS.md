# Compiler Input Verification Requirements

ورودی مجاز کامپایلر پژوهشی از این پس باید برای هر شاهد داشته باشد: `canonical_id` + `db_record_id` + `quote_span{start,end}` + `raw_quote_sha256` + `print_edition_status`. هر ورودی فاقد این پنج فیلد، یا با هش ناسازگار با رجیستر قفل‌شده، باید **fail-closed** شود. برچسب تطبیق فنی هرگز به‌تنهایی مبنای رتبهٔ علمی نیست.
