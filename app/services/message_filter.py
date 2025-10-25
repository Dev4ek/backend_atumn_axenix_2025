import re
import json
from typing import List, Dict, Tuple
from datetime import datetime


class MessageFilter:
    def __init__(self):
        self.base_bad_words = [
            "мат", "оскорбление", "spam", "лох"  # базовый список
        ]
        
        self.spam_patterns = [
            (r'(.)\1{10,}', "Повторяющиеся символы"),
            (r'.*http.*http.*http.*', "Множественные ссылки"),
            (r'.*[A-Z]{15,}.*', "Избыток заглавных букв"),
            (r'.*\!{5,}.*', "Множественные восклицательные знаки"),
        ]

    def filter_message(self, text: str, custom_banned_words: List[str] = None) -> Dict:
        """Фильтрация сообщения с учетом кастомных запрещенных слов"""
        original_text = text
        violations = []
        filtered_text = text
        
        # Объединяем базовые и кастомные запрещенные слова
        all_banned_words = self.base_bad_words + (custom_banned_words or [])
        
        # Проверка запрещенных слов (только целые слова)
        for word in all_banned_words:
            if word.strip():  # Проверяем только непустые слова
                # Ищем только целые слова с границами
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                matches = pattern.finditer(filtered_text)
                
                found_matches = False
                temp_text = filtered_text
                
                for match in matches:
                    found_matches = True
                    # Заменяем найденное вхождение на звездочки
                    start, end = match.span()
                    replacement = '*' * (end - start)
                    temp_text = temp_text[:start] + replacement + temp_text[end:]
                
                if found_matches:
                    filtered_text = temp_text
                    violations.append(f"Запрещенное слово: '{word}'")
        
        # Проверка спам-паттернов
        for pattern, description in self.spam_patterns:
            if re.search(pattern, filtered_text, re.IGNORECASE):
                violations.append(description)
        
        # Проверка длины
        if len(filtered_text) > 2000:
            violations.append("Сообщение слишком длинное")
            filtered_text = filtered_text[:2000]
        
        return {
            "filtered_text": filtered_text,
            "violations": violations,
            "is_clean": len(violations) == 0,
            "original_text": original_text,
            "filtered_reason": "; ".join(violations) if violations else None
        }


# Альтернативная версия с более эффективной заменой
class AdvancedMessageFilter(MessageFilter):
    def filter_message(self, text: str, custom_banned_words: List[str] = None) -> Dict:
        """Улучшенная фильтрация с использованием одного регулярного выражения"""
        original_text = text
        violations = []
        
        # Объединяем базовые и кастомные запрещенные слова
        all_banned_words = custom_banned_words
        
        # Создаем одно большое регулярное выражение для всех запрещенных слов
        if all_banned_words:
            # Экранируем и объединяем слова через | с границами слов
            pattern_words = [re.escape(word) for word in all_banned_words if word.strip()]
            if pattern_words:
                # Ищем только целые слова с границами
                combined_pattern = re.compile(r'\b(' + '|'.join(pattern_words) + r')\b', re.IGNORECASE)
                
                def replace_match(match):
                    matched_text = match.group()
                    return '*' * len(matched_text)
                
                filtered_text, count = combined_pattern.subn(replace_match, text)
                
                if count > 0:
                    violations.append(f"Найдено {count} запрещенных слов")
        
        else:
            filtered_text = text
        
        # Проверка спам-паттернов
        for pattern, description in self.spam_patterns:
            if re.search(pattern, filtered_text, re.IGNORECASE):
                violations.append(description)
        
        # Проверка длины
        if len(filtered_text) > 2000:
            violations.append("Сообщение слишком длинное")
            filtered_text = filtered_text[:2000]
        
        return {
            "filtered_text": filtered_text,
            "violations": violations,
            "is_clean": len(violations) == 0,
            "original_text": original_text,
            "filtered_reason": "; ".join(violations) if violations else None
        }


# Версия которая заменяет и целые слова и части слов (по вашему первоначальному требованию)
class StrictMessageFilter(MessageFilter):
    def filter_message(self, text: str, custom_banned_words: List[str] = None) -> Dict:
        """Строгая фильтрация - заменяет и целые слова и части слов"""
        original_text = text
        violations = []
        
        # Объединяем базовые и кастомные запрещенные слова
        all_banned_words = self.base_bad_words + (custom_banned_words or [])
        
        # Создаем одно большое регулярное выражение для всех запрещенных слов
        if all_banned_words:
            # Экранируем и объединяем слова через | БЕЗ границ слов
            pattern_words = [re.escape(word) for word in all_banned_words if word.strip()]
            if pattern_words:
                # Ищем в любом месте текста, даже как часть других слов
                combined_pattern = re.compile('|'.join(pattern_words), re.IGNORECASE)
                
                def replace_match(match):
                    matched_text = match.group()
                    return '*' * len(matched_text)
                
                filtered_text, count = combined_pattern.subn(replace_match, text)
                
                if count > 0:
                    violations.append(f"Найдено {count} запрещенных слов/фрагментов")
        
        else:
            filtered_text = text
        
        # Проверка спам-паттернов
        for pattern, description in self.spam_patterns:
            if re.search(pattern, filtered_text, re.IGNORECASE):
                violations.append(description)
        
        # Проверка длины
        if len(filtered_text) > 2000:
            violations.append("Сообщение слишком длинное")
            filtered_text = filtered_text[:2000]
        
        return {
            "filtered_text": filtered_text,
            "violations": violations,
            "is_clean": len(violations) == 0,
            "original_text": original_text,
            "filtered_reason": "; ".join(violations) if violations else None
        }


# Создаем экземпляр фильтра (выберите нужный вариант)
message_filter = AdvancedMessageFilter()  # Только целые слова
# message_filter = StrictMessageFilter()  # Целые слова и части слов

# Тестирование
if __name__ == "__main__":
    test_cases = [
        "тылох настоящий!",
        "Этот человек - лох",
        "Привет, как дела?",
        "лохотрон и прелох",
        "Слово лох в тексте",
        "ТЫЛОХПЕТУХ",
        "бля это плохо"
    ]
    
    print("=== ТЕСТИРОВАНИЕ AdvancedMessageFilter (только целые слова) ===")
    filter_test = AdvancedMessageFilter()
    for test in test_cases:
        result = filter_test.filter_message(test, ["лох", "бля"])
        print(f"Оригинал: {test}")
        print(f"Фильтр:   {result['filtered_text']}")
        print(f"Нарушения: {result['violations']}")
        print("-" * 50)
    
    print("\n=== ТЕСТИРОВАНИЕ StrictMessageFilter (целые слова и части) ===")
    filter_strict = StrictMessageFilter()
    for test in test_cases:
        result = filter_strict.filter_message(test, ["лох", "бля"])
        print(f"Оригинал: {test}")
        print(f"Фильтр:   {result['filtered_text']}")
        print(f"Нарушения: {result['violations']}")
        print("-" * 50)