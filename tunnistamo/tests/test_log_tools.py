import logging

import freezegun

from tunnistamo.log_tools import LogfmtFormatter, UnsafeLogValue


@freezegun.freeze_time('2021-10-29 06:00:00')
def test_logfmt_formatter(caplog):
    caplog.set_level(logging.INFO)

    logger = logging.getLogger()

    logger.info('Testing "quote"', extra={
        'safe_value': 'something safe',
        'unsafe_value': UnsafeLogValue('unsafe äö?'),
        'multirow': 'first row\nsecond row',
        'a_bool': True,
        'number': 3,
    })

    logfmt_formatter = LogfmtFormatter()
    log_string = logfmt_formatter.format(caplog.records[0])

    assert log_string == (
        r'ts="2021-10-29 06:00:00,000" level=INFO msg="Testing \"quote\""'
        r' module="test_log_tools" a_bool=true multirow="first row\nsecond row"'
        r' number=3 safe_value="something safe" unsafe_value=dW5zYWZlIMOkw7Y/'
    )
