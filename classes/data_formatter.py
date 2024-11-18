# data_formatter.py
import re
from .utils import log

class DataFormatter:
    def __init__(self, config):
        """
        Initialize the DataFormatter with the configuration.

        :param config: The configuration settings.

        The DataFormatter class is responsible for formatting the data based on the configuration settings.
        """
        self.config = config

    def format_data(self, data):
        """
        Format the data based on the configuration settings.

        :param data: The data to format.
        :return: The formatted data.
        """
        if not data:
            return data
        for source in data:
            log(f"Formatting data for {source}", 'debug')
            if not data:
                continue
            format_source = self.config.get(source, {}).get('formatters', {})
            log(f"Formatters: {format_source}", 'debug')
            if  not format_source:
                return data
            for format in format_source:
                method = format.get('method')
                settings = format.get('settings')
                if not method or not hasattr(self, method):
                    log(f"Method not set, or not defined", 'warning')
                    log(f"Method: {method}", 'debug')
                    continue
                try:
                    prop = format.get('property')
                    data = getattr(self, method)(data, source, prop, settings)
                    log(f"Formatted data for {source} using {method}", 'debug')
                    log(f"Formatted data: {data}", 'debug')
                except Exception as e:
                    log(f"An error occured in {method}", 'warning')
                    log(str(e), 'debug')
        return data
    
    def append_data(self, data, source, prop, formatted, overwrite=False):
        """
        Append the formatted data to the source property.

        :param data: The data to append to.
        :param source: The source of the data.
        :param prop: The property to append the formatted data to.
        :param formatted: The formatted data to append.
        :param overwrite: If True, overwrite the existing data.
        :return: The data with the formatted data appended.
        """
        if not formatted:
            return data
        if source not in data:
            data[source] = {}
        if prop in data[source] and not overwrite:
            return data
        data[source][prop] = formatted
        return data
    
    def get_value(self, data, source, prop):
        """
        Get the value of the property from the data.

        :param data: The data to get the value from.
        :param source: The source of the data.
        :param prop: The property to get the value from.
        :return: The value of the property.
        """
        value = data.get(source, {})
        keys = re.findall(r'\w+|\[\d+\]', prop)

        for key in keys:
            if isinstance(value, dict) and not key.startswith('['):
                value = value.get(key, None)
            elif isinstance(value, list) and re.match(r'\[\d+\]', key):
                index = int(key[1:-1])
                if 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                return None
            
        return value

    def limit_line_length(self, data, source, prop, settings):
        """
        Limit the line length of the text in the property.

        :param data: The data to format.
        :param source: The source of the data.
        :param prop: The property to format.
        :param settings: The settings for the formatter.
        :return: The data with the formatted data appended.
        """
        lines = []
        text = self.get_value(data, source, prop)
        if not text:
            return data
        max_length = settings.get('max_length', 125)
        while len(text) > max_length:
            wrap_at = text.rfind(' ', 0, max_length)
            if wrap_at == -1:
                wrap_at = max_length
            lines.append(text[:wrap_at].strip())
            text = text[wrap_at:].strip()
        lines.append(text)
        formatted = '\n'.join(lines)
        return self.append_data(data, source, prop+'_formatted', formatted)

    def conditional_data(self, data, source, prop, settings):
        """
        Append data based on a condition.

        :param data: The data to format.
        :param source: The source of the data.
        :param prop: The property to format.
        :param settings: The settings for the formatter.
        :return: The data with the formatted data appended.
        """
        text = self.get_value(data, source, prop)
        if not text:
            return data
        condition = settings.get('condition', None)
        new_prop = settings.get('property', None)
        overwrite = settings.get('overwrite', False)
        if not condition or not new_prop:
            return data
        new_value = None
        if condition == 'regex':
            condition_value = settings.get('condition_value', None)
            if not condition_value:
                return data
            if re.search(condition_value, text):
                new_value = settings.get('if_true', None)
            else:
                new_value = settings.get('if_false', None)
        return self.append_data(data, source, new_prop, new_value, overwrite)
        
    def replacer(self, data, source, prop, settings):
        """
        Replace text in the property.

        :param data: The data to format.
        :param source: The source of the data.
        :param prop: The property to format.
        :param settings: The settings for the formatter.
        :return: The data with the formatted data appended.
        """
        text = self.get_value(data, source, prop)
        if not text:
            return data
        replacements = settings.get('replacements', None)
        if not replacements:
            return data
        for replacement in replacements:
            pattern = replacement.get('pattern', None)
            replacement = replacement.get('replacement', None)
            if not pattern or not replacement:
                continue
            formatted = re.sub(pattern, replacement, text)
        return self.append_data(data, source, prop+'_formatted', formatted)
