
import csv
import html
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import DATASET_CONFIG, HTML_OUTPUT_DIR

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(10**9)


class QueryAnalyzer:

    @staticmethod
    def detect_query_type(query: str) -> str:
        cleaned = query.strip()

        if "@" in cleaned:
            return "email"

        has_letters = bool(re.search(r"[а-яА-Яa-zA-Z]", cleaned))
        has_digits = bool(re.search(r"\d", cleaned))
        digits_only = re.sub(r"\D+", "", cleaned)
        letters_only = re.sub(r"[^а-яА-Яa-zA-Z]", "", cleaned)

        if has_letters and has_digits:
            car_pattern = re.match(
                r"^[а-яА-Яa-zA-Z]{1,2}\d{3}[а-яА-Яa-zA-Z]{2,3}\d{2,3}$",
                cleaned.replace(" ", ""),
            )
            if car_pattern:
                return "name"

        if has_letters and len(letters_only) >= len(cleaned) * 0.3:
            return "name"

        if len(digits_only) >= 5:
            norm = len(cleaned.replace(" ", "").replace("-", "").replace("(", "").replace(")", ""))
            if norm and len(digits_only) >= norm * 0.7:
                return "phone"

        return "name"


class DataNormalizer:

    @staticmethod
    def normalize_phone(value: str) -> str:
        digits = re.sub(r"\D+", "", str(value or ""))
        if not digits:
            return ""
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if digits.startswith("00"):
            digits = digits[2:]
        return digits


class HTMLReportGenerator:

    @staticmethod
    def escape_html(text: str) -> str:
        if text is None:
            return ""
        text = str(text)
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def generate(self, query: str, results: Dict[str, Dict], total_found: int, query_type: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_parts: List[str] = []
        html_parts.append("<!DOCTYPE html>")
        html_parts.append('<html lang="ru">')
        html_parts.append("<head>")
        html_parts.append('<meta charset="UTF-8">')
        html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html_parts.append(
            f"<title>Отчёт по поиску: {self.escape_html(query)}</title>"
        )
        html_parts.append("<style>")
        html_parts.append(self._get_css_styles())
        html_parts.append("</style>")
        html_parts.append("</head>")
        html_parts.append("<body>")
        html_parts.append('<div class="container">')

        html_parts.append(
            self._generate_header(query, query_type, total_found, timestamp)
        )

        html_parts.append(self._generate_datasets_section(results))

        html_parts.append(
            f'<div class="timestamp">Отчёт сгенерирован: {timestamp}</div>'
        )
        html_parts.append("</div>")
        html_parts.append(self._get_javascript())
        html_parts.append("</body>")
        html_parts.append("</html>")

        return "\n".join(html_parts)

    def _get_css_styles(self) -> str:
        return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .header-info {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        .header-info p { margin: 5px 0; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }
        .badge-query { background: #3498db; color: white; }
        .badge-phone { background: #e74c3c; color: white; }
        .badge-email { background: #9b59b6; color: white; }
        .badge-name { background: #27ae60; color: white; }
        .badge-total { background: #34495e; color: white; font-size: 1em; }
        .section { margin-bottom: 40px; }
        .section h2 {
            color: #34495e;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .section-controls { display: flex; gap: 10px; }
        .btn-control {
            background: #3498db;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            transition: background-color 0.3s ease;
        }
        .btn-control:hover { background: #2980b9; }
        .dataset-summary {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .collapsible-header {
            background: #e9ecef;
            padding: 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background-color 0.3s ease;
            user-select: none;
        }
        .collapsible-header:hover { background: #dee2e6; }
        .collapsible-header h3 {
            color: #495057;
            margin: 0;
            flex: 1;
        }
        .collapsible-header .count {
            margin-left: 15px;
            margin-right: 15px;
        }
        .toggle-icon {
            font-size: 1.2em;
            transition: transform 0.3s ease;
            color: #495057;
        }
        .collapsible-header.collapsed .toggle-icon { transform: rotate(-90deg); }
        .collapsible-content {
            max-height: 9999px;
            overflow: hidden;
            transition: max-height 0.4s ease, padding 0.4s ease;
            padding: 15px;
        }
        .collapsible-content.collapsed {
            max-height: 0;
            padding: 0 15px;
        }
        .count {
            font-size: 1.2em;
            font-weight: bold;
            color: #3498db;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 0.9em;
        }
        table th {
            background: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        table td {
            padding: 10px;
            border-bottom: 1px solid #dee2e6;
        }
        table tr:hover { background: #f8f9fa; }
        table tr:nth-child(even) { background: #fafafa; }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #6c757d;
            font-size: 1.1em;
        }
        .timestamp {
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            text-align: center;
        }
        @media print {
            body { background: white; padding: 0; }
            .container { box-shadow: none; }
        }
        '''

    def _generate_header(self, query: str, query_type: str, total_found: int, timestamp: str) -> str:
        html_parts: List[str] = []
        html_parts.append("<h1>Отчёт по поиску</h1>")
        html_parts.append('<div class="header-info">')
        html_parts.append(
            f"<p><strong>Запрос:</strong> "
            f'<span class="badge badge-query">{self.escape_html(query)}</span></p>'
        )
        type_badges = {
            "phone": "badge-phone",
            "email": "badge-email",
            "name": "badge-name",
        }
        html_parts.append(
            "<p><strong>Тип запроса:</strong> "
            f'<span class="badge {type_badges.get(query_type, "badge-query")}">'
            f"{self.escape_html(query_type)}</span></p>"
        )
        html_parts.append(
            "<p><strong>Всего найдено:</strong> "
            f'<span class="badge badge-total">{total_found}</span></p>'
        )
        html_parts.append(f"<p><strong>Дата и время:</strong> {timestamp}</p>")
        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _generate_datasets_section(self, results: Dict[str, Dict]) -> str:
        html_parts: List[str] = []
        html_parts.append('<div class="section">')
        html_parts.append("<h2>")
        html_parts.append("<span>Результаты по базам данных</span>")
        html_parts.append('<div class="section-controls">')
        html_parts.append(
            '<button class="btn-control" onclick="expandAll()">Развернуть все</button>'
        )
        html_parts.append(
            '<button class="btn-control" onclick="collapseAll()">Свернуть все</button>'
        )
        html_parts.append("</div>")
        html_parts.append("</h2>")

        for idx, (key, data) in enumerate(results.items()):
            dataset_id = f"dataset_{idx}"
            name = self.escape_html(str(data.get("name", key)))
            rows: List[Dict] = data.get("results") or []
            display_fields = data.get("display_fields") or []

            if not display_fields and rows:
                field_set = set()
                for row in rows:
                    field_set.update(row.keys())
                display_fields = sorted(field_set)

            html_parts.append('<div class="dataset-summary">')
            html_parts.append(
                f'<div class="collapsible-header" onclick="toggleCollapse(\'{dataset_id}\')">'
            )
            html_parts.append(f"<h3>{name}</h3>")
            html_parts.append(f'<span class="count">Найдено: {len(rows)}</span>')
            html_parts.append('<span class="toggle-icon">▼</span>')
            html_parts.append("</div>")
            html_parts.append(
                f'<div class="collapsible-content" id="{dataset_id}">'
            )

            if rows and display_fields:
                html_parts.append("<table>")
                html_parts.append("<thead><tr>")
                for col in display_fields:
                    html_parts.append(
                        f"<th>{self.escape_html(str(col))}</th>"
                    )
                html_parts.append("</tr></thead>")
                html_parts.append("<tbody>")

                for row in rows:
                    html_parts.append("<tr>")
                    for col in display_fields:
                        value = row.get(col, "")
                        html_parts.append(
                            f"<td>{self.escape_html(str(value))}</td>"
                        )
                    html_parts.append("</tr>")

                html_parts.append("</tbody>")
                html_parts.append("</table>")
            elif rows:
                html_parts.append(
                    f"<div class=\"no-results\">Найдено записей: {len(rows)}</div>"
                )
            else:
                html_parts.append(
                    '<div class="no-results">Совпадений не найдено</div>'
                )

            html_parts.append("</div>")
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _get_javascript(self) -> str:
        return '''<script>
        function toggleCollapse(datasetId) {
            const content = document.getElementById(datasetId);
            const header = content.previousElementSibling;
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                header.classList.remove('collapsed');
            } else {
                content.classList.add('collapsed');
                header.classList.add('collapsed');
            }
        }
        function expandAll() {
            const allContents = document.querySelectorAll('.collapsible-content');
            const allHeaders = document.querySelectorAll('.collapsible-header');
            allContents.forEach(content => content.classList.remove('collapsed'));
            allHeaders.forEach(header => header.classList.remove('collapsed'));
        }
        function collapseAll() {
            const allContents = document.querySelectorAll('.collapsible-content');
            const allHeaders = document.querySelectorAll('.collapsible-header');
            allContents.forEach(content => content.classList.add('collapsed'));
            allHeaders.forEach(header => header.classList.add('collapsed'));
        }
    </script>'''

    def save_report(self, query: str, results: Dict[str, Dict], total_found: int) -> str:
        project_root = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(project_root, HTML_OUTPUT_DIR)

        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)

        safe_query = re.sub(r"[^\w\s-]", "", query)[:50].strip()
        safe_query = re.sub(r"[-\s]+", "-", safe_query)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = (
            f"report_{safe_query}_{timestamp_str}.html"
            if safe_query
            else f"report_{timestamp_str}.html"
        )
        filepath = os.path.join(reports_dir, filename)

        html_content = self.generate(query, results, total_found, QueryAnalyzer.detect_query_type(query))
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filepath


class SearchService:

    def __init__(self):
        self.query_analyzer = QueryAnalyzer()
        self.data_normalizer = DataNormalizer()
        self.html_report_generator = HTMLReportGenerator()
        self.datasets = self._load_datasets()

    def _load_datasets(self) -> Dict:
        datasets = {}
        project_root = os.path.dirname(os.path.abspath(__file__))

        print(f"\nЗагрузка баз данных из: {project_root}")

        for key, config in DATASET_CONFIG.items():
            file_path = config.get("file", "")
            if file_path and not os.path.isabs(file_path):
                file_path = os.path.join(project_root, file_path)

            if file_path and os.path.exists(file_path):
                datasets[key] = {**config, "file_path": file_path}
                print(f"  {config['name']}: {file_path}")
            else:
                print(f"  {config['name']}: файл не найден ({file_path})")

        if not datasets:
            print("\nВНИМАНИЕ: Не найдено ни одной базы данных!")
            print(f"Убедитесь, что CSV файлы находятся в папке: {os.path.join(project_root, 'database')}")

        return datasets

    def search(self, query: str, max_results: int = 50) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {}

        if not self.datasets:
            print("Нет загруженных баз данных для поиска!")
            return results

        search_type = self.query_analyzer.detect_query_type(query)
        print(f"Поиск '{query}' (тип: {search_type}) в {len(self.datasets)} базах...")

        for key, dataset_config in self.datasets.items():
            try:
                found = self._search_in_dataset(dataset_config, query, search_type, max_results)
                if found:
                    results[key] = {
                        "name": dataset_config["name"],
                        "results": found,
                        "display_fields": dataset_config.get("display_fields", []),
                    }
                    print(f"  {dataset_config['name']}: найдено {len(found)}")
            except Exception as e:
                print(f"  Ошибка при поиске в {dataset_config['name']}: {e}")
                continue

        return results

    def _search_in_dataset(self, dataset_config: Dict, query: str, search_type: str, max_results: int) -> List[Dict]:
        file_path = dataset_config["file_path"]
        encoding = dataset_config.get("encoding") or "utf-8"
        separator = dataset_config.get("separator") or ";"
        search_fields = dataset_config.get("search_fields", {})
        display_fields = dataset_config.get("display_fields", [])
        has_header = dataset_config.get("has_header", True)

        fields = search_fields.get(search_type, [])
        if not fields:
            if search_type == "phone":
                fields = search_fields.get("phone", []) + search_fields.get("name", [])
            else:
                fields = [f for sub in search_fields.values() for f in (sub or [])]

        if not fields and display_fields:
            fields = display_fields

        results: List[Dict] = []

        try:
            with open(file_path, "r", encoding=encoding, errors="replace", newline="") as fp:
                if has_header:
                    reader = csv.DictReader(fp, delimiter=separator)
                else:
                    columns = dataset_config.get("columns", [])
                    if columns:
                        reader = csv.DictReader(fp, fieldnames=columns, delimiter=separator)
                    else:
                        fp.seek(0)
                        first_row = next(csv.reader(fp, delimiter=separator), [])
                        reader = csv.DictReader(fp, fieldnames=first_row, delimiter=separator)

                for row in reader:
                    if not any(str(v).strip() for v in row.values() if v):
                        continue

                    if self._matches(row, query, search_type, fields):
                        if display_fields:
                            result_row = {field: row.get(field, "") for field in display_fields}
                        else:
                            result_row = {k: v for k, v in row.items() if v}
                        results.append(result_row)

                        if len(results) >= max_results:
                            break
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}")

        return results

    def _matches(self, row: Dict[str, str], query: str, search_type: str, fields: List[str]) -> bool:
        if not fields:
            fields = list(row.keys())

        if search_type == "phone":
            target = self.data_normalizer.normalize_phone(query)
            if not target:
                return False
            for field in fields:
                value = self.data_normalizer.normalize_phone(row.get(field, ""))
                if not value:
                    continue
                if target == value or target in value or value in target:
                    if len(target) >= 7 and len(value) >= 7:
                        return True
            return False

        if search_type == "email":
            q = query.strip().lower()
            if "@" not in q:
                return False
            for field in fields:
                value = str(row.get(field, "")).strip().lower()
                if "@" in value and q in value:
                    return True
            return False

        q = query.strip().lower()
        if not q:
            return False

        query_words = [w.strip() for w in re.split(r"[\s,;]+", q) if len(w.strip()) >= 2]
        if not query_words:
            return False

        if len(query_words) >= 2:
            all_row_words: List[str] = []
            for field in fields:
                field_value = str(row.get(field, "")).strip()
                if field_value:
                    field_words = [w.strip() for w in re.split(r"[\s,;]+", field_value.lower()) if len(w.strip()) >= 2]
                    all_row_words.extend(field_words)

            for qw in query_words:
                if not any(qw == rw for rw in all_row_words):
                    return False
            return True

        for field in fields:
            value = str(row.get(field, "")).strip().lower()
            if not value:
                continue
            if q == value or q in value:
                return True

        return False

    def format_results(self, results: Dict[str, Dict], query: str) -> str:
        if not results:
            escaped_query = html.escape(query)
            return f"По запросу '<b>{escaped_query}</b>' ничего не найдено."

        search_type = self.query_analyzer.detect_query_type(query)
        type_emoji = {
            "phone": "",
            "email": "",
            "name": "",
        }
        emoji = type_emoji.get(search_type, "")
        escaped_query = html.escape(query)

        prefix = f"{emoji} " if emoji else ""
        message_parts: List[str] = [f"<b>{prefix}Результаты поиска: '{escaped_query}'</b>\n"]
        total = 0

        for key, data in results.items():
            name = html.escape(str(data["name"]))
            found = data["results"]
            count = len(found)
            total += count

            message_parts.append(f"\n<b>{name}</b>: найдено {count}")

            for i, result in enumerate(found[:3], 1):
                message_parts.append(f"\n<b>{i}.</b> {self._format_result_row(result)}")

            if count > 3:
                message_parts.append(f"\n<i>... и ещё {count - 3} результатов</i>")

        message_parts.append(f"\n\n<b>Всего найдено: {total} записей</b>")
        return "\n".join(message_parts)

    def _format_result_row(self, row: Dict) -> str:
        parts: List[str] = []
        for key, value in row.items():
            if value and str(value).strip():
                escaped_key = html.escape(str(key))
                escaped_value = html.escape(str(value))
                parts.append(f"<b>{escaped_key}:</b> <code>{escaped_value}</code>")
        return "\n".join(parts[:5])

    def save_html_report(self, query: str, results: Dict[str, Dict]) -> Optional[str]:
        if not results:
            print("Нет результатов для генерации HTML-отчёта")
            return None

        total = 0
        for key, data in results.items():
            rows = data.get("results") or []
            count = len(rows)
            total += count
            print(f"  {data.get('name', key)}: {count} записей")

        print(f"Генерация HTML-отчёта для запроса '{query}' (всего найдено: {total})")
        try:
            path = self.html_report_generator.save_report(query, results, total)
            if path and os.path.exists(path):
                print(f"HTML-отчёт сохранён: {path}")
                return path
            print(f"HTML-отчёт не был создан или файл не найден: {path}")
            return None
        except Exception as e:
            print(f"Ошибка при генерации HTML-отчёта: {e}")
            return None


def run_cli():
    service = SearchService()
    print(f"Загружено баз данных: {len(service.datasets)}")
    if not service.datasets:
        print("Не найдены CSV-файлы для поиска. Проверьте папку database/.")
        return

    print("\nВведите запрос для поиска (телефон, ФИО или email).")
    print("Пустой ввод — выход.\n")

    while True:
        try:
            query = input("Запрос: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not query:
            print("Выход.")
            break

        results = service.search(query)
        text = service.format_results(results, query)
        print("\n" + text + "\n")

        save = input("Сохранить HTML-отчёт? [y/N]: ").strip().lower()
        if save == "y":
            path = service.save_html_report(query, results)
            if path:
                print(f"HTML-отчёт сохранён: {path}")


if __name__ == "__main__":
    run_cli()
