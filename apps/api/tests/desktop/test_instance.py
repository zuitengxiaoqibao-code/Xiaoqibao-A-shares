import sys

import pytest

from qibao_desktop.instance import AlreadyRunningError, SingleInstance


@pytest.mark.skipif(sys.platform != "win32", reason="Windows mutex")
def test_named_mutex_rejects_second_instance() -> None:
    first = SingleInstance("qibao-test-exclusive")
    second = SingleInstance("qibao-test-exclusive")
    first.acquire()
    try:
        with pytest.raises(AlreadyRunningError):
            second.acquire()
    finally:
        first.close()
