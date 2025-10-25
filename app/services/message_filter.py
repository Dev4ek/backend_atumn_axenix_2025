import re
import json
from typing import List, Dict, Tuple
from datetime import datetime


class MessageFilter:
    def __init__(self):
        self.base_bad_words = [
            "мат", "оскорбление", "spam"  # базовый список
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
        
        # Проверка запрещенных слов
        for word in all_banned_words:
            if word.strip():  # Проверяем только непустые слова
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                if pattern.search(filtered_text):
                    filtered_text = pattern.sub('***', filtered_text)
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


message_filter = MessageFilter()