import base64
import logging
import numbers


class UnsafeLogValue(str):
    def __str__(self):
        return base64.b64encode(self.encode('utf-8')).decode()


def quote_value(value):
    return value.replace('"', '\\"').replace('\n', '\\n')


class LogfmtFormatter(logging.Formatter):
    def _get_extra_keys(self, record):
        return [
            key for key in dir(record) if not key.startswith('_') and key not in [
                'args', 'asctime', 'created', 'filename',
                'funcName', 'getMessage', 'levelname', 'levelno', 'lineno',
                'message', 'module', 'msecs', 'msg', 'name', 'pathname',
                'process', 'processName', 'relativeCreated', 'stack_info',
                'thread', 'threadName', 'exc_info', 'stack_info',
                # 'exc_info', 'exc_text',
            ]
        ]

    def format(self, record):
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)

        if record.stack_info:
            record.stack_text = self.formatStack(record.stack_info)

        parts = [
            f'ts="{record.asctime}"',
            f'level={record.levelname}',
            f'msg="{quote_value(record.message)}"',
            f'module="{record.module}"',
        ]

        for key in self._get_extra_keys(record):
            value = getattr(record, key)

            if key == 'exc_text' and value is None:
                continue

            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, numbers.Number):
                pass
            else:
                if isinstance(value, (dict, object)):
                    value = str(value)

            if isinstance(value, str):
                value = quote_value(value)

                if ' ' in value:
                    value = f'"{value}"'

            parts.append(f'{key}={value}')

        return ' '.join(parts)
